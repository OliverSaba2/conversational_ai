"""
Step 4: turn (intent, entities, action_result) into a natural-language reply.
"""

from config import CLINIC_DOCTORS, CLINIC_NAME, CLINIC_OPENING_HOURS

# Human-readable labels for the field names session.py uses in missing_fields.
FIELD_LABELS = {
    "date": "date",
    "time": "time",
    "new_date": "new date you'd like",
    "doctor": "doctor's name",
    "patient_name": "your first and last name",
    "patient_card": "your patient card number",
}

INTENT_ACTION_PHRASE = {
    "book_appointment": "book an appointment",
    "reschedule_appointment": "reschedule your appointment",
    "cancel_appointment": "cancel your appointment",
}

INTENT_PAST_PARTICIPLE = {
    "book_appointment": "booked",
    "reschedule_appointment": "changed",
    "cancel_appointment": "cancelled",
}


def _join_list(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _join_labels(fields):
    return _join_list([FIELD_LABELS.get(f, f) for f in fields])


def generate_response(intent: str, entities: dict, action_result: dict) -> str:
    action = action_result.get("action")
    doctor = entities.get("doctor")
    date = entities.get("preferred_date")
    time = entities.get("preferred_time")

    doctor_part = f" with {doctor}" if doctor else ""
    date_part = f" on {date}" if date else ""
    time_part = f" at {time}" if time else ""

    if action == "answer_opening_hours":
        return f"Our clinic is open {CLINIC_OPENING_HOURS}"

    if action == "check_availability":
        return (
            f"Let me check availability{doctor_part}{date_part}{time_part} for you. "
            f"I won't book anything until you confirm."
        )

    if action == "create_appointment":
        return f"Done! Your appointment{doctor_part} is booked{date_part}{time_part}."

    if action == "reschedule_appointment":
        original_date = action_result.get("original_date")
        move_part = f" from {original_date} to {date}" if original_date else date_part
        return f"Your appointment{doctor_part} has been moved{move_part}{time_part}."

    if action == "cancel_appointment":
        return f"Your appointment{doctor_part}{date_part} has been cancelled."

    if action == "slot_unavailable":
        result_doctor = action_result.get("doctor") or doctor
        return (
            f"Sorry, {result_doctor or 'that doctor'} already has an appointment around that time"
            f"{date_part}{time_part} - we keep at least an hour between appointments per doctor. "
            "Could you try a different time?"
        )

    if action == "no_appointment_found":
        return "I don't see any appointment on file for you. Would you like to book one instead?"

    if action == "invalid_booking_time":
        reason = action_result.get("reason")
        if reason == "invalid_date":
            return f"Sorry, {date or 'that'} isn't a real date. Could you give me a valid one?"
        if reason == "invalid_time":
            return f"Sorry, {time or 'that'} isn't a real time. Could you give me a valid one?"
        if reason == "past":
            return f"Sorry, {date or 'that date'}{time_part} has already passed. Could you give me a date and time in the future?"
        if reason == "closed_day":
            return f"Sorry, the clinic isn't open then - we're open {CLINIC_OPENING_HOURS} Could you pick a different day?"
        if reason == "outside_hours":
            return f"Sorry, that's outside our opening hours - we're open {CLINIC_OPENING_HOURS} Could you pick a different time?"
        return "Sorry, that date/time doesn't work for us - could you try a different one?"

    if action == "list_doctors":
        doctors = action_result.get("doctors") or CLINIC_DOCTORS
        return f"Our doctors are: {_join_list(doctors)}."

    if action == "handoff_to_human":
        return "Sure, connecting you with a member of our clinic staff now."

    if action == "smalltalk_greeting":
        return (
            f"Hello! I'm the {CLINIC_NAME} assistant. I can help you book, reschedule or cancel "
            "an appointment, check a doctor's availability, or clinic hours. How can I help today?"
        )

    if action == "smalltalk_thanks":
        return "You're welcome! Is there anything else I can help with?"

    if action == "smalltalk_goodbye":
        return "Take care! Reach out anytime you need help with an appointment."

    if action == "await_confirmation":
        intent_phrase = INTENT_ACTION_PHRASE.get(action_result.get("intent"), "do that")
        original_date = entities.get("original_date")
        if action_result.get("intent") == "reschedule_appointment" and original_date:
            detail = f" from {original_date} to {date}{time_part}"
        else:
            detail = f"{doctor_part}{date_part}{time_part}"
        return f"Just to confirm: {intent_phrase}{detail}. Shall I go ahead? (yes/no)"

    if action == "no_appointment":
        participle = INTENT_PAST_PARTICIPLE.get(action_result.get("intent"), "made")
        return f"No problem, no appointment has been {participle}. Is there anything else I can help with?"

    if action == "ask_for_more_information":
        missing = action_result.get("missing_fields") or []
        if "intent" in missing:
            return "Sorry, could you clarify what you'd like help with (booking, rescheduling, cancelling, etc.)?"
        if "doctor_or_date" in missing:
            return "Could you tell me which doctor or which appointment date you mean so I can help with that?"
        reply = f"Could you tell me the {_join_labels(missing)} so I can help with that?"
        if "doctor" in missing:
            reply += f" Our doctors are: {_join_list(CLINIC_DOCTORS)}."
        return reply

    return "Sorry, I didn't quite understand that. Could you rephrase it?"
