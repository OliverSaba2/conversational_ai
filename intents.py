"""
Step 1: figure out what the patient is asking for.

Very simple keyword-based classifier. Good enough for an assistant demo -
in a real system you'd likely swap this for an LLM call or a proper NLU model.
"""

INTENTS = [
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "ask_opening_hours",
    "ask_doctor_availability",
    "request_human",
    "unclear",
]


def identify_intent(message: str) -> str:
    text = message.lower()

    # Order matters: check the more specific phrases before the generic ones.
    if any(kw in text for kw in ["speak to", "talk to", "call me", "human", "agent", "someone from the clinic"]):
        return "request_human"

    if "cancel" in text:
        return "cancel_appointment"

    if any(kw in text for kw in ["reschedule", "move my appointment", "move it", "change my appointment", "change the time"]):
        return "reschedule_appointment"

    if any(kw in text for kw in ["opening hours", "what time does", "open", "close"]):
        return "ask_opening_hours"

    if any(kw in text for kw in ["available", "availability", "anything available", "do you have"]):
        return "ask_doctor_availability"

    if any(kw in text for kw in ["book", "appointment", "see dr", "see doctor", "want to see"]):
        return "book_appointment"

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
