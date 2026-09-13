"""
Parses time strings ("4pm", "4:00", "16:30") into minutes-since-midnight,
so appointment_store can enforce an hour's gap between a doctor's
appointments. Vague times ("afternoon") return None - not one concrete time.
"""

import re

_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$")


def parse_time_to_minutes(time_str):
    if not time_str:
        return None
    match = _TIME_RE.match(time_str.strip().lower())
    if not match:
        return None

    hour, minute, meridiem = match.groups()
    hour = int(hour)
    minute = int(minute) if minute else 0
    if meridiem == "pm" and hour != 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


_AFTER_RE = re.compile(r"^after\s+(\d{1,2})\s*(am|pm)?$")


def is_malformed_time(time_str) -> bool:
    """True if this has the shape of a clock time but an impossible hour/
    minute ("25:00", "at 13pm") - distinct from a merely vague time."""
    if not time_str:
        return False
    text = time_str.strip().lower()

    match = _TIME_RE.match(text) or _AFTER_RE.match(text)
    if not match:
        return False
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.re is _TIME_RE and match.group(2) else 0
    meridiem = match.group(2) if match.re is _AFTER_RE else match.group(3)

    if meridiem:
        return not (1 <= hour <= 12 and 0 <= minute <= 59)
    return not (0 <= hour <= 23 and 0 <= minute <= 59)


def within_one_hour(time_a, time_b) -> bool:
    """True only if both parse to a concrete time less than 60 min apart."""
    minutes_a = parse_time_to_minutes(time_a)
    minutes_b = parse_time_to_minutes(time_b)
    if minutes_a is None or minutes_b is None:
        return False
    return abs(minutes_a - minutes_b) < 60


if __name__ == "__main__":
    samples = [
        ("4pm", "4:30pm"),
        ("4pm", "5pm"),
        ("4:00", "4:45"),
        ("16:00", "4pm"),
        ("afternoon", "4pm"),
        ("after 5", "5:30pm"),
    ]
    for a, b in samples:
        print(f"{a!r} vs {b!r} -> within_one_hour={within_one_hour(a, b)}")
