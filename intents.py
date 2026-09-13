"""
Step 1: figure out what the patient is asking for.

Very simple keyword-based classifier. Good enough for an assistant demo -
in a real system you'd likely swap this for an LLM call or a proper NLU model.
"""

import re

INTENTS = [
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "ask_opening_hours",
    "ask_doctor_availability",
    "list_doctors",
    "request_human",
    "greeting",
    "thanks",
    "goodbye",
    "unclear",
]


def identify_intent(message: str) -> str:
    text = message.lower()

    # Order matters: check the more specific phrases before the generic ones.
    # "don't call me" / "do not call me" is a negation, not a request to be called.
    wants_call = "call me" in text and not any(
        neg in text for neg in ["don't call me", "do not call me"]
    )
    if wants_call or any(kw in text for kw in ["speak to", "talk to", "human", "agent", "someone from the clinic"]):
        return "request_human"

    if "cancel" in text:
        return "cancel_appointment"

    if any(kw in text for kw in ["reschedule", "move my appointment", "move it", "change my appointment", "change the time"]):
        return "reschedule_appointment"

    if any(kw in text for kw in ["opening hours", "what time does", "open", "close", "closing"]):
        return "ask_opening_hours"

    # Checked before ask_doctor_availability - "what doctors do you have" is
    # asking for the roster, not a specific doctor's availability.
    if re.search(r"\bdoctors?\b", text) and any(
        kw in text for kw in ["list", "which", "what", "who are", "how many", "your doctors", "doctor list"]
    ):
        return "list_doctors"

    if any(kw in text for kw in ["available", "availability", "anything available", "do you have"]):
        return "ask_doctor_availability"

    if any(kw in text for kw in ["book", "appointment", "see dr", "see doctor", "want to see"]):
        return "book_appointment"

    # Small talk - checked last, since these words shouldn't outrank an
    # actual request (e.g. "hi, can I book an appointment" is still booking).
    if re.search(r"\b(thanks|thank you|thx|appreciate it)\b", text):
        return "thanks"

    if re.search(r"\b(bye|goodbye|farewell)\b", text) or any(
        kw in text for kw in ["see you", "that's all", "thats all", "nothing else"]
    ):
        return "goodbye"

    if re.search(r"\b(hi|hey|hello|greetings|howdy)\b", text) or any(
        kw in text for kw in ["good morning", "good afternoon", "good evening", "how are you"]
    ):
        return "greeting"

    return "unclear"


if __name__ == "__main__":
    samples = [
        "Can I see Dr. George tomorrow afternoon?",
        "Move my appointment from Monday to Wednesday.",
        "Cancel my appointment with Dr. Karim.",
        "What time does the clinic close?",
        "Do you have anything available after 5 tomorrow?",
        "Can somebody from the clinic call me?",
    ]
    for s in samples:
        print(f"{s!r} -> {identify_intent(s)}")
