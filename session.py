"""
Step 6: the multi-turn conversation state machine. Tracks who the patient is,
what they're booking/rescheduling/cancelling, and what's still missing -
across as many messages as it takes - and only acts once they say yes.
"""

import difflib
import re

import actions
import appointment_store
import booking_hours
import patient_store
from config import CLINIC_DOCTORS
from normalize import normalize_message
from intents import identify_intent
from extraction import extract_entities
from responses import generate_response

AFFIRMATIVE = [
    "yes", "y", "ye", "yh", "yeah", "yea", "yah", "yep", "yup", "ya", "aye",
    "yess", "yesss", "sure", "sure thing", "confirm", "confirmed", "correct",
    "right", "ok", "okay", "k", "kk", "fine", "alright", "all right",
    "of course", "definitely", "absolutely", "positive", "do it", "go ahead",
    "go for it", "proceed", "please do", "please", "sounds good",
    "that's right", "thats right", "affirmative", "book it", "please book it",
    "let's do it", "lets do it",
]

NEGATIVE = [
    "no", "n", "no no", "nope", "nah", "nah man", "nay", "negative", "don't",
    "dont", "not really", "no way", "nvm",
    "no thanks", "no thank you", "actually no", "wait no",
    "i don't think so", "i dont think so",
]

# "Drop this whole request" - checked before any sub-state, so it can't be
# misread as an answer to "what's your card number?" or similar.
ABORT_PHRASES = [
    "never mind", "nevermind", "forget it", "cancel that", "cancel it",
    "leave it", "not interested", "not now", "stop", "actually never mind",
]

# "I don't have a card" - lets the conversation move on instead of stalling.
CARD_DECLINE_PHRASES = [
    "no card", "dont have", "don't have", "i dont have one", "none",
    "n/a", "not sure", "no id", "skip", "i dont have a card",
]

SLOT_KEYS = ("doctor", "preferred_date", "preferred_time", "original_date")
BOOKING_INTENTS = ("book_appointment", "reschedule_appointment", "cancel_appointment")
SIDE_INTENTS = (
    "ask_opening_hours", "ask_doctor_availability", "list_doctors",
    "request_human", "greeting", "thanks", "goodbye",
)

# Card numbers are digits only - never letters, so a name can't be mistaken for one.
_CARD_DIGITS_RE = re.compile(r"\b\d{3,}\b")

_IDENTITY_LEAD_RE = re.compile(
    r"^(my name is|i am|i'm|im|this is|it's|its|name is|name|"
    r"my card( number)? is|card( number)? is|card|number)[:\-,]?\s*",
    re.IGNORECASE,
)
_IDENTITY_FILLER_RE = re.compile(r"\b(card|number|patient|my|is|and)\b", re.IGNORECASE)


def _clean(text: str) -> str:
    return re.sub(r"[^a-z0-9' ]", "", text.lower()).strip()


def _matches_any(text: str, phrases) -> bool:
    return any(re.search(rf"\b{re.escape(p)}\b", text) for p in phrases)


def _find_unclaimed_card_number(text: str, slots: dict):
    """A card number given up front ("Dr. George tomorrow at 4pm, card 12345") -
    skips digits that are actually part of an already-recognized date, so a
    year like "2026" doesn't get mistaken for one."""
    used_text = " ".join(str(slots.get(k) or "") for k in ("preferred_date", "original_date", "preferred_time"))
    for match in _CARD_DIGITS_RE.finditer(text):
        if match.group(0) not in used_text:
            return match.group(0)
    return None


def _extract_name(raw: str, card_span=None):
    """Pull a name out of free text ("card 12345, John Smith", "my name is John
    Smith"). `card_span` cuts out a card number so it isn't swallowed into the name."""
    text = raw
    if card_span:
        start, end = card_span
        text = text[:start] + " " + text[end:]
    text = _IDENTITY_LEAD_RE.sub("", text.strip())
    text = _IDENTITY_FILLER_RE.sub(" ", text)
    text = re.sub(r"[,.!]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.title() if text else None


def _is_full_name(name) -> bool:
    """First and last name required - a single word isn't enough."""
    return bool(name) and len(name.split()) >= 2


_DOCTOR_SURNAMES = [known.split()[-1].lower() for known in CLINIC_DOCTORS]


def _find_bare_doctor_mention(text: str):
    """A doctor mentioned without "Dr." ("George", "can I see Karim"). Only
    call this within a booking flow, so a stray word elsewhere can't misfire."""
    for word in re.findall(r"[a-z']+", text.lower()):
        if len(word) < 3:
            continue
        match = difflib.get_close_matches(word, _DOCTOR_SURNAMES, n=1, cutoff=0.82)
        if match:
            return CLINIC_DOCTORS[_DOCTOR_SURNAMES.index(match[0])]
    return None


def _match_known_doctor(raw_doctor):
    """Typo-correct against the clinic's roster; None if it's not one of them."""
    if not raw_doctor:
        return None
    for known in CLINIC_DOCTORS:
        if known.lower() == raw_doctor.lower():
            return known
    surname = raw_doctor.split()[-1].lower().strip(".")
    surnames = [known.split()[-1].lower() for known in CLINIC_DOCTORS]
    match = difflib.get_close_matches(surname, surnames, n=1, cutoff=0.75)
    return CLINIC_DOCTORS[surnames.index(match[0])] if match else None


def _join_list(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


class ConversationSession:
    def __init__(self):
        self.patient_name = None
        self.patient_card = None
        self.awaiting_identity_field = None
        self.reset()

    def reset(self):
        """Drop whatever appointment request was in progress (identity is kept)."""
        self.intent = None
        self.slots = {key: None for key in SLOT_KEYS}
        self.no_confirm = False
        self.awaiting_confirmation = False
        self.pending_intent = None
        self.awaiting_identity_field = None

    def full_reset(self):
        """Also forget who the patient is - a brand-new conversation."""
        self.reset()
        self.patient_name = None
        self.patient_card = None

    def opening_message(self) -> str:
        """The greeting the bot leads with, before the patient says anything."""
        return generate_response("greeting", {}, {"action": "smalltalk_greeting"})

    # -- slot helpers ------------------------------------------------------

    def _merge_entities(self, entities: dict):
        """entities["doctor"] must already be roster-checked by the caller."""
        for key in SLOT_KEYS:
            value = entities.get(key)
            if value:
                self.slots[key] = value
        if entities.get("explicit_no_confirm"):
            self.no_confirm = True

    def _missing_appointment_slots(self):
        if self.intent == "book_appointment":
            missing = []
            if not self.slots["doctor"]:
                missing.append("doctor")
            if not self.slots["preferred_date"]:
                missing.append("date")
            if not self.slots["preferred_time"]:
                missing.append("time")
            return missing
        if self.intent == "reschedule_appointment":
            return [] if self.slots["preferred_date"] else ["new_date"]
        if self.intent == "cancel_appointment":
            return [] if (self.slots["doctor"] or self.slots["preferred_date"]) else ["doctor_or_date"]
        return []

    def _identity_known(self) -> bool:
        return bool(self.patient_name)

    # -- reply-building helpers ---------------------------------------------

    def _result(self, intent, action_result, reply):
        structured_output = {
            "intent": intent,
            "patient_name": self.patient_name,
            "patient_card": self.patient_card,
            "doctor": self.slots["doctor"],
            "preferred_date": self.slots["preferred_date"],
            "preferred_time": self.slots["preferred_time"],
            "original_date": self.slots["original_date"],
            "awaiting_confirmation": self.awaiting_confirmation,
        }
        return {"structured_output": structured_output, "action": action_result, "reply": reply}

    def _ask_for_more_info(self, intent, missing):
        action_result = actions.ask_for_more_information(missing_fields=missing)
        reply = generate_response(intent, self.slots, action_result)
        return self._result(intent, action_result, reply)

    def _ask_to_confirm(self, intent):
        self.awaiting_confirmation = True
        self.pending_intent = intent
        action_result = actions.await_confirmation(
            intent=intent, doctor=self.slots["doctor"], date=self.slots["preferred_date"], time=self.slots["preferred_time"]
        )
        reply = generate_response(intent, self.slots, action_result)
        return self._result(intent, action_result, reply)

    def _execute_confirmed(self):
        intent = self.pending_intent
        slots = self.slots
        identity = {"patient_name": self.patient_name, "patient_card": self.patient_card}

        if intent == "book_appointment":
            action_result = actions.create_appointment(
                doctor=slots["doctor"], date=slots["preferred_date"], time=slots["preferred_time"], **identity
            )
        elif intent == "reschedule_appointment":
            action_result = actions.reschedule_appointment(
                doctor=slots["doctor"], original_date=slots["original_date"],
                new_date=slots["preferred_date"], time=slots["preferred_time"], **identity
            )
        else:  # cancel_appointment
            action_result = actions.cancel_appointment(doctor=slots["doctor"], date=slots["preferred_date"], **identity)

        reply = generate_response(intent, slots, action_result)
        self.awaiting_confirmation = False
        self.pending_intent = None

        if action_result.get("action") == "slot_unavailable":
            # Slot's taken - drop just the date/time and ask again.
            self.slots["preferred_date"] = None
            self.slots["preferred_time"] = None
            return self._result(intent, action_result, reply)

        self.reset()
        return self._result(intent, action_result, reply)

    def _decline(self, intent, reason):
        action_result = actions.no_appointment(intent=intent, reason=reason)
        reply = generate_response(intent, self.slots, action_result)
        self.reset()
        return self._result(intent, action_result, reply)

    def _handle_side_intent(self, intent, entities):
        if intent == "request_human":
            action_result = actions.handoff_to_human(reason="patient asked to speak with a human")
            reply = generate_response(intent, entities, action_result)
            self.reset()
            return self._result(intent, action_result, reply)

        if intent == "ask_opening_hours":
            action_result = {"action": "answer_opening_hours"}
            return self._result(intent, action_result, generate_response(intent, entities, action_result))

        if intent == "ask_doctor_availability":
            action_result = actions.check_availability(
                doctor=entities.get("doctor"), date=entities.get("preferred_date"), time=entities.get("preferred_time")
            )
            return self._result(intent, action_result, generate_response(intent, entities, action_result))

        if intent == "list_doctors":
            action_result = actions.list_doctors()
            return self._result(intent, action_result, generate_response(intent, entities, action_result))

        # greeting / thanks / goodbye
        action_result = {"action": f"smalltalk_{intent}"}
        reply = generate_response(intent, entities, action_result)
        if intent == "goodbye":
            self.full_reset()  # next "hi" should start a genuinely new chat
        return self._result(intent, action_result, reply)

    # -- patient identity (name + card number) ------------------------------

    def _start_identity_capture(self, raw_message: str = ""):
        # They may have already given a card number in this same message.
        card = _find_unclaimed_card_number(raw_message, self.slots) if raw_message else None
        if card:
            self.patient_card = card
            existing = patient_store.find_patient(card)
            if existing:
                self.patient_name = existing["name"]
                return self._resume_after_identity(welcome_back=True)
            self.awaiting_identity_field = "name"
            action_result = actions.ask_for_more_information(missing_fields=["patient_name"])
            return self._result(self.intent, action_result, "Thanks - and could I get your first and last name, please?")

        self.awaiting_identity_field = "card"
        action_result = actions.ask_for_more_information(missing_fields=["patient_card"])
        reply = "Before I go ahead - could I get your patient card number? (If you don't have one, just say so and I'll assign you one.)"
        return self._result(self.intent, action_result, reply)

    def _handle_identity_turn(self, raw_message: str):
        if self.awaiting_identity_field == "card":
            cleaned = _clean(raw_message)
            # Bare "no" means "I don't have one" here - never a card, and
            # never their name either (must not become the literal name "No").
            # They still need a card on file, so we assign a new one.
            if _matches_any(cleaned, CARD_DECLINE_PHRASES) or _matches_any(cleaned, NEGATIVE):
                self.patient_card = patient_store.generate_card_number()
                if self.patient_name:
                    self.awaiting_identity_field = None
                    patient_store.save_patient(self.patient_card, self.patient_name)
                    result = self._continue_booking_flow()
                    result["reply"] = f"No problem, I've set you up with card {self.patient_card}. " + result["reply"]
                    return result
                self.awaiting_identity_field = "name"
                action_result = actions.ask_for_more_information(missing_fields=["patient_name"])
                reply = f"No problem, I've assigned you card {self.patient_card} - worth noting for next time. And your first and last name?"
                return self._result(self.intent, action_result, reply)

            card_match = _CARD_DIGITS_RE.search(raw_message)
            if not card_match:
                # No digits - they may have answered with their name instead
                # (out of order). Only guess once (else a later "yes" would
                # overwrite a good name) and not if it's really a doctor's name.
                name_guess = None
                if not self.patient_name:
                    candidate = _extract_name(raw_message)
                    if (
                        candidate and _is_full_name(candidate)
                        and not _match_known_doctor(candidate) and not _find_bare_doctor_mention(raw_message)
                    ):
                        name_guess = candidate
                if name_guess:
                    self.patient_name = name_guess
                    action_result = actions.ask_for_more_information(missing_fields=["patient_card"])
                    reply = f"Nice to meet you, {name_guess}! And your patient card number?"
                    return self._result(self.intent, action_result, reply)

                action_result = actions.ask_for_more_information(missing_fields=["patient_card"])
                reply = (
                    "Sorry, a patient card number is just digits (e.g. 12345). "
                    "Could you give me your card number, or say if you don't have one?"
                )
                return self._result(self.intent, action_result, reply)

            card = card_match.group(0)
            self.patient_card = card
            existing = patient_store.find_patient(card)
            if existing:
                self.patient_name = existing["name"]
                self.awaiting_identity_field = None
                return self._resume_after_identity(welcome_back=True)

            if self.patient_name:  # already given, out of order - no need to ask again
                self.awaiting_identity_field = None
                patient_store.save_patient(self.patient_card, self.patient_name)
                return self._resume_after_identity(welcome_back=False)

            # New card - maybe the name's in this same message ("12345, John Smith").
            name = _extract_name(raw_message, card_span=card_match.span())
            if name and _is_full_name(name):
                self.patient_name = name
                self.awaiting_identity_field = None
                patient_store.save_patient(self.patient_card, self.patient_name)
                return self._resume_after_identity(welcome_back=False)

            self.awaiting_identity_field = "name"
            action_result = actions.ask_for_more_information(missing_fields=["patient_name"])
            return self._result(self.intent, action_result, "Thanks - and could I get your first and last name, please?")

        # awaiting_identity_field == "name" - they may slip a card number in here too.
        if _matches_any(_clean(raw_message), NEGATIVE):
            # Bare "no" is not a name - don't title-case it into one.
            action_result = actions.ask_for_more_information(missing_fields=["patient_name"])
            reply = "Sorry, we do need a name on file to book anything - could you tell me your first and last name?"
            return self._result(self.intent, action_result, reply)

        card_match = _CARD_DIGITS_RE.search(raw_message) if not self.patient_card else None
        if card_match:
            self.patient_card = card_match.group(0)

        name_guess = _extract_name(raw_message, card_span=card_match.span() if card_match else None)
        if not name_guess:
            # Just a card number again, not a name - keep waiting for one.
            action_result = actions.ask_for_more_information(missing_fields=["patient_name"])
            prefix = "Got it, thanks. " if card_match else ""
            return self._result(self.intent, action_result, f"{prefix}And could I get your first and last name, please?")

        if not _is_full_name(name_guess):
            action_result = actions.ask_for_more_information(missing_fields=["patient_name"])
            reply = f"Thanks {name_guess}, but I'll need your last name too - could you give me your full name?"
            return self._result(self.intent, action_result, reply)

        self.patient_name = name_guess
        self.awaiting_identity_field = None
        if self.patient_card:
            patient_store.save_patient(self.patient_card, self.patient_name)
        return self._resume_after_identity(welcome_back=False)

    def _resume_after_identity(self, welcome_back: bool):
        greeting = f"Welcome back, {self.patient_name}! " if welcome_back else f"Thanks, {self.patient_name}! "
        result = self._continue_booking_flow()
        result["reply"] = greeting + result["reply"]
        return result

    def _continue_booking_flow(self):
        """Assumes self.intent is set and identity is resolved (or declined)."""
        if self.no_confirm and self.intent == "book_appointment":
            action_result = actions.check_availability(
                doctor=self.slots["doctor"], date=self.slots["preferred_date"], time=self.slots["preferred_time"]
            )
            reply = generate_response(self.intent, self.slots, action_result)
            self.reset()
            return self._result(self.intent, action_result, reply)

        if self.intent in ("reschedule_appointment", "cancel_appointment"):
            early_result = self._match_against_appointment_book()
            if early_result is not None:
                return early_result

        missing = self._missing_appointment_slots()
        if missing:
            return self._ask_for_more_info(self.intent, missing)

        if self.intent in ("book_appointment", "reschedule_appointment"):
            invalid_reason = booking_hours.check_booking_time(
                self.slots["preferred_date"], self.slots["preferred_time"]
            )
            if invalid_reason:
                action_result = {"action": "invalid_booking_time", "reason": invalid_reason}
                reply = generate_response(self.intent, self.slots, action_result)
                if invalid_reason == "invalid_time":
                    self.slots["preferred_time"] = None
                elif invalid_reason == "invalid_date":
                    self.slots["preferred_date"] = None
                else:
                    self.slots["preferred_date"] = None
                    self.slots["preferred_time"] = None
                return self._result(self.intent, action_result, reply)

        return self._ask_to_confirm(self.intent)

    def _match_against_appointment_book(self):
        """Find which existing appointment reschedule/cancel means, from the
        patient's card. Returns a result to return, or None to proceed normally."""
        records = appointment_store.find_by_patient(self.patient_card)

        if not records:
            action_result = actions.no_appointment_found(patient_card=self.patient_card, patient_name=self.patient_name)
            reply = generate_response(self.intent, self.slots, action_result)
            self.reset()
            return self._result(self.intent, action_result, reply)

        if len(records) == 1:
            record = records[0]
            if not self.slots["doctor"]:
                self.slots["doctor"] = record["doctor"]
            date_slot = "original_date" if self.intent == "reschedule_appointment" else "preferred_date"
            if not self.slots[date_slot]:
                self.slots[date_slot] = record["date"]
            return None

        # Multiple appointments - narrow down by what they told us, or ask.
        matching = [r for r in records if not self.slots["doctor"] or r["doctor"] == self.slots["doctor"]]
        if len(matching) == 1:
            record = matching[0]
            date_slot = "original_date" if self.intent == "reschedule_appointment" else "preferred_date"
            if not self.slots[date_slot]:
                self.slots[date_slot] = record["date"]
            return None

        missing = self._missing_appointment_slots() or ["doctor_or_date"]
        options = ", ".join(f"{r['doctor']} on {r['date']}" for r in records)
        action_result = actions.ask_for_more_information(missing_fields=missing)
        reply = f"I have a few appointments on file for you ({options}) - which one do you mean?"
        return self._result(self.intent, action_result, reply)

    # -- main entry point ----------------------------------------------------

    def handle_message(self, message: str) -> dict:
        stripped = message.strip()
        if not stripped:
            return self._result(self.intent, {"action": "noop"}, "Sorry, I didn't catch that - could you say that again?")

        normalized = normalize_message(stripped)
        norm_lower = _clean(normalized)

        # "Never mind" drops the whole request, before anything else can
        # misread it as an answer to whatever we just asked.
        if self.intent and _matches_any(norm_lower, ABORT_PHRASES):
            pending = self.pending_intent if self.awaiting_confirmation else self.intent
            return self._decline(pending, reason="patient cancelled the request")

        # Already asked "shall I go ahead? (yes/no)" - resolve that first.
        if self.awaiting_confirmation:
            if _matches_any(norm_lower, NEGATIVE):
                return self._decline(self.pending_intent, reason="patient declined confirmation")
            if _matches_any(norm_lower, AFFIRMATIVE):
                return self._execute_confirmed()
            action_result = actions.await_confirmation(
                intent=self.pending_intent, doctor=self.slots["doctor"],
                date=self.slots["preferred_date"], time=self.slots["preferred_time"],
            )
            reply = "Sorry, just a yes or no is fine - " + generate_response(self.pending_intent, self.slots, action_result)
            return self._result(self.pending_intent, action_result, reply)

        # Already asked for the patient's card/name - that takes this turn.
        if self.awaiting_identity_field:
            detected = identify_intent(normalized)
            if detected in SIDE_INTENTS:
                return self._handle_side_intent(detected, extract_entities(normalized, original=stripped))
            return self._handle_identity_turn(stripped)

        # Mid-collection, the patient changed their mind entirely.
        if self.intent and _matches_any(norm_lower, NEGATIVE):
            return self._decline(self.intent, reason="patient cancelled the request before confirming")

        detected_intent = identify_intent(normalized)
        entities = extract_entities(normalized, original=stripped)

        # Small talk / side questions, without disturbing an in-progress booking.
        if detected_intent in SIDE_INTENTS:
            return self._handle_side_intent(detected_intent, entities)

        # Resolve any doctor mention against the roster - a bare "George"
        # needs it, and it feeds the intent inference just below too.
        unknown_doctor = None
        raw_doctor = entities.get("doctor")
        if raw_doctor:
            matched = _match_known_doctor(raw_doctor)
            if matched:
                entities["doctor"] = matched
            else:
                unknown_doctor = raw_doctor
                entities["doctor"] = None
        else:
            bare_doctor = _find_bare_doctor_mention(normalized)
            if bare_doctor:
                entities["doctor"] = bare_doctor

        # Front-loading every detail with no "book"/"cancel"/"reschedule"
        # keyword ("Dr. George tomorrow at 4pm") still counts as a request.
        if detected_intent == "unclear" and not self.intent:
            if entities.get("original_date"):
                detected_intent = "reschedule_appointment"
            elif entities.get("doctor") or entities.get("preferred_date") or entities.get("preferred_time"):
                detected_intent = "book_appointment"

        # A bare follow-up ("tomorrow at 4") is more detail for whatever we're collecting.
        intent = self.intent if (detected_intent == "unclear" and self.intent) else detected_intent

        if intent not in BOOKING_INTENTS:
            action_result = actions.ask_for_more_information(missing_fields=["intent"])
            return self._result("unclear", action_result, generate_response("unclear", entities, action_result))

        if self.intent != intent:
            self.slots = {key: None for key in SLOT_KEYS}
            self.no_confirm = False
        self.intent = intent

        self._merge_entities(entities)

        if unknown_doctor:
            action_result = actions.ask_for_more_information(missing_fields=["doctor"])
            reply = (
                f"Sorry, we don't have a doctor called {unknown_doctor} - our doctors are: "
                f"{_join_list(CLINIC_DOCTORS)}. Who would you like to see?"
            )
            return self._result(intent, action_result, reply)

        # "Don't book/confirm anything yet" - just a check, no identity needed.
        if self.no_confirm and intent == "book_appointment":
            action_result = actions.check_availability(
                doctor=self.slots["doctor"], date=self.slots["preferred_date"], time=self.slots["preferred_time"]
            )
            reply = generate_response(intent, self.slots, action_result)
            self.reset()
            return self._result(intent, action_result, reply)

        if not self._identity_known():
            return self._start_identity_capture(stripped)

        return self._continue_booking_flow()
