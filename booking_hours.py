"""
Step 3b: is a requested date/time bookable - a real date/time, within
opening hours, on a day the clinic's open, and not already in the past?
Reuses schedule_view's date/time resolution; anything too vague to resolve
(but not outright impossible) isn't blocked.
"""

from datetime import datetime, timedelta

from config import CLINIC_CLOSE_HOUR, CLINIC_CLOSED_WEEKDAYS, CLINIC_OPEN_HOUR
from schedule_view import is_impossible_date, resolve_date, resolve_time_minutes
from time_utils import is_malformed_time


def check_booking_time(date_str, time_str, now=None):
    """None if bookable (or unresolvable, not blocked). Else one of
    "invalid_date"/"invalid_time"/"past"/"closed_day"/"outside_hours"."""
    now = now or datetime.now()

    if is_impossible_date(date_str, today=now.date()):
        return "invalid_date"
    if is_malformed_time(time_str):
        return "invalid_time"

    day = resolve_date(date_str, today=now.date())
    minutes = resolve_time_minutes(time_str)
    if day is None or minutes is None:
        return None

    appointment_dt = datetime.combine(day, datetime.min.time()) + timedelta(minutes=minutes)
    if appointment_dt < now:
        return "past"
    if day.strftime("%A").lower() in CLINIC_CLOSED_WEEKDAYS:
        return "closed_day"
    if not (CLINIC_OPEN_HOUR * 60 <= minutes < CLINIC_CLOSE_HOUR * 60):
        return "outside_hours"
    return None
