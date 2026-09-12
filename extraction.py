"""
Step 2: pull structured info out of the patient's message
(doctor name, date, time, and whether they explicitly said "don't book yet").
"""

import re

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Phrases that mean "just checking, do not actually book/confirm anything".
NO_CONFIRM_PHRASES = [
    "don't book",
    "do not book",
    "don't confirm",
    "do not confirm",
    "not book anything",
    "just checking",
]


def extract_doctor(text: str):
    match = re.search(r"dr\.?\s+([a-z]+)", text, re.IGNORECASE)
    if match:
        return f"Dr. {match.group(1).capitalize()}"
    return None


def extract_date(text: str):
    text_lower = text.lower()
    if "tomorrow" in text_lower:
        return "tomorrow"
    if "today" in text_lower:
        return "today"
    for day in WEEKDAYS:
        if day in text_lower:
            return day.capitalize()
    if "next week" in text_lower:
        return "next week"
    return None


def extract_time(text: str):
    text_lower = text.lower()

    match = re.search(r"after\s+(\d{1,2})\s*(am|pm)?", text_lower)
    if match:
        hour, meridiem = match.groups()
        return f"after {hour}{meridiem or ''}".strip()

    match = re.search(r"\b(\d{1,2})(:\d{2})?\s*(am|pm)\b", text_lower)
    if match:
        return match.group(0)

    match = re.search(r"\bat\s+(\d{1,2})\b", text_lower)
    if match:
        return f"{match.group(1)}:00"

    if "morning" in text_lower:
        return "morning"
    if "afternoon" in text_lower:
        return "afternoon"
    if "evening" in text_lower:
        return "evening"
    return None


def extract_no_confirm_flag(text: str) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in NO_CONFIRM_PHRASES)


def extract_entities(message: str) -> dict:
    return {
        "doctor": extract_doctor(message),
        "preferred_date": extract_date(message),
        "preferred_time": extract_time(message),
        "explicit_no_confirm": extract_no_confirm_flag(message),
    }


if __name__ == "__main__":
    samples = [
        "Can I see Dr. George tomorrow afternoon?",
        "Book me Friday at 4 but don't confirm anything yet.",
        "I might want to see Dr. George tomorrow at 4, but don't book anything yet.",
    ]
    for s in samples:
        print(f"{s!r} -> {extract_entities(s)}")
