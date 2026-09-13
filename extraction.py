"""
Step 2: pull structured info out of the patient's message
(doctor name, date, time, and whether they explicitly said "don't book yet").
"""

import re

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

MONTHS = {
    "jan": "January", "january": "January",
    "feb": "February", "february": "February",
    "mar": "March", "march": "March",
    "apr": "April", "april": "April",
    "may": "May",
    "jun": "June", "june": "June",
    "jul": "July", "july": "July",
    "aug": "August", "august": "August",
    "sep": "September", "sept": "September", "september": "September",
    "oct": "October", "october": "October",
    "nov": "November", "november": "November",
    "dec": "December", "december": "December",
}
_MONTH_WORD = r"(?:" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")"

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


_DAY_WORD = r"(?:" + "|".join(WEEKDAYS) + r"|today|tomorrow)"


def _normalize_day(word: str) -> str:
    return word.capitalize() if word in WEEKDAYS else word


def extract_reschedule_dates(text: str):
    """
    "Move my appointment from Monday to Wednesday" -> (from="Monday", to="Wednesday").
    Returns (None, None) if the message doesn't use this "from X to Y" phrasing.
    """
    match = re.search(rf"from\s+({_DAY_WORD})\s+to\s+({_DAY_WORD})", text.lower())
    if not match:
        return None, None
    return _normalize_day(match.group(1)), _normalize_day(match.group(2))


def extract_calendar_date(text: str):
    """
    Explicit calendar dates: "13 September 2026", "September 13, 2026",
    "13/09/2026", "2026-09-13". Returns a human-readable string, or None.
    """
    text_lower = text.lower()

    # "13 September" / "13th September 2026"
    match = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_WORD})\.?,?\s*(\d{{4}})?\b", text_lower)
    if match:
        day, month, year = match.groups()
        if 1 <= int(day) <= 31:
            return f"{int(day)} {MONTHS[month]}" + (f" {year}" if year else "")

    # "September 13" / "September 13th, 2026"
    match = re.search(rf"\b({_MONTH_WORD})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s*(\d{{4}})?\b", text_lower)
    if match:
        month, day, year = match.groups()
        if 1 <= int(day) <= 31:
            return f"{int(day)} {MONTHS[month]}" + (f" {year}" if year else "")

    # ISO: "2026-09-13"
    match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text_lower)
    if match:
        year, month, day = match.groups()
        month_names = list(dict.fromkeys(MONTHS.values()))
        if 1 <= int(month) <= 12:
            return f"{int(day)} {month_names[int(month) - 1]} {year}"

    # Numeric day/month/year: "13/09/2026" or "13-09-2026"
    match = re.search(r"\b(\d{1,2})[/](\d{1,2})[/](\d{2,4})\b", text_lower)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = f"20{year}"
        month_names = list(dict.fromkeys(MONTHS.values()))
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{int(day)} {month_names[int(month) - 1]} {year}"

    return None


def extract_date(text: str):
    text_lower = text.lower()

    # "from Monday to Wednesday" - the date that matters (the target) is the
    # one after "to", not just whichever weekday happens to appear first.
    _, to_date = extract_reschedule_dates(text)
    if to_date:
        return to_date

    calendar_date = extract_calendar_date(text)
    if calendar_date:
        return calendar_date

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


def extract_entities(message: str, original: str = None) -> dict:
    """
    `message` is expected to already be typo/shorthand-normalized (see
    normalize.py) so date/time phrases match reliably. `original` (the raw,
    un-normalized text) is used for the doctor's name specifically, so a
    surname that happens to resemble clinic vocabulary doesn't get "corrected".
    """
    doctor_source = original if original is not None else message
    original_date, _ = extract_reschedule_dates(message)
    return {
        "doctor": extract_doctor(doctor_source),
        "preferred_date": extract_date(message),
        "preferred_time": extract_time(message),
        "original_date": original_date,
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
