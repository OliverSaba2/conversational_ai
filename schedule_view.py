"""
Turns loose date/time strings ("tomorrow", "Friday", "4pm", "afternoon")
into real datetime ranges, purely for the admin board's Gantt chart -
booking/conflict logic elsewhere stays string-based.

Vague values get a reasonable anchor (a weekday -> its next occurrence,
"afternoon" -> 2pm); anything that truly can't be placed ("next week" alone)
is reported as unresolved rather than guessed at.
"""

import re
from datetime import date, datetime, timedelta

import pandas as pd

from time_utils import parse_time_to_minutes

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
VAGUE_TIME_MINUTES = {"morning": 9 * 60, "afternoon": 14 * 60, "evening": 18 * 60}


def resolve_date(date_str, today=None):
    """A date string -> a real `date`, or None if it can't be pinned down."""
    if not date_str:
        return None
    today = today or date.today()
    text = date_str.strip().lower()

    if text == "today":
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)

    if text in WEEKDAYS:
        delta = (WEEKDAYS.index(text) - today.weekday()) % 7
        delta = delta or 7  # naming today's own weekday means the NEXT one
        return today + timedelta(days=delta)

    match = re.match(r"^(\d{1,2})\s+([a-z]+)(?:\s+(\d{4}))?$", text)
    if match:
        day, month_name, year = match.groups()
        if month_name in MONTHS:
            month = MONTHS.index(month_name) + 1
            try:
                if year:
                    return date(int(year), month, int(day))
                candidate = date(today.year, month, int(day))
                return candidate if candidate >= today else date(today.year + 1, month, int(day))
            except ValueError:
                return None

    return None  # e.g. "next week" - not a single resolvable day


def is_impossible_date(date_str, today=None):
    """True if this has the shape of a specific calendar date but isn't a
    real one (e.g. "31 February") - distinct from a merely vague date."""
    if not date_str:
        return False
    match = re.match(r"^(\d{1,2})\s+([a-z]+)(?:\s+(\d{4}))?$", date_str.strip().lower())
    if not match:
        return False
    day, month_name, year = match.groups()
    if month_name not in MONTHS:
        return False
    month = MONTHS.index(month_name) + 1
    year = int(year) if year else (today or date.today()).year
    try:
        date(year, month, int(day))
        return False
    except ValueError:
        return True


def resolve_time_minutes(time_str):
    """A time string -> minutes since midnight, or None if too vague. A bare
    hour with no am/pm ("4:00") is assumed afternoon, since the clinic runs
    roughly 8am-6pm - display-only, doesn't affect real booking logic."""
    if not time_str:
        return None
    text = time_str.strip().lower()
    has_meridiem = "am" in text or "pm" in text

    minutes = parse_time_to_minutes(time_str)
    if minutes is not None:
        if not has_meridiem and 60 <= minutes <= 7 * 60:
            minutes += 12 * 60
        return minutes

    if text in VAGUE_TIME_MINUTES:
        return VAGUE_TIME_MINUTES[text]

    match = re.match(r"^after\s+(\d{1,2})\s*(am|pm)?$", text)
    if match:
        hour, meridiem = match.groups()
        hour = int(hour)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif not meridiem and 1 <= hour <= 7:
            hour += 12
        return hour * 60

    return None


def build_schedule_dataframe(appointments, duration_minutes=60, today=None):
    """-> (DataFrame for the Gantt chart, count of appointments left unplaced)."""
    rows = []
    unresolved = 0
    for appt in appointments:
        day = resolve_date(appt.get("date"), today=today)
        minutes = resolve_time_minutes(appt.get("time"))
        if day is None or minutes is None:
            unresolved += 1
            continue
        start = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minutes)
        end = start + timedelta(minutes=duration_minutes)
        rows.append(
            {
                "Doctor": appt.get("doctor") or "Unknown",
                "Patient": appt.get("patient_name") or "Unknown",
                "Start": start,
                "End": end,
                "Label": f"{appt.get('patient_name') or 'Unknown'} - {appt.get('time') or ''}",
            }
        )
    return pd.DataFrame(rows), unresolved
