"""
A tiny local "appointment book" - a stand-in for a real scheduling/EHR
system. Backed by one JSON file, holding a list of
{patient_card, patient_name, doctor, date, time} records.
"""

import json_file
from config import APPOINTMENT_STORE_PATH
from time_utils import within_one_hour

_PATH = json_file.resolve_path(APPOINTMENT_STORE_PATH)


def _load() -> list:
    return json_file.load(_PATH, [])


def _save(records: list) -> None:
    json_file.save(_PATH, records)


def find_conflict(doctor, date, time, exclude_card=None):
    """The other patient's record blocking this doctor+date+time, if any -
    a doctor needs an hour's gap between appointments on the same date."""
    if not (doctor and date and time):
        return None
    for record in _load():
        if record["doctor"] != doctor or record["date"] != date or record["patient_card"] == exclude_card:
            continue
        if record["time"] == time or within_one_hour(record["time"], time):
            return record
    return None


def find_by_patient(patient_card):
    """All appointments currently on file for this patient."""
    if not patient_card:
        return []
    return [r for r in _load() if r["patient_card"] == patient_card]


def list_all():
    """Every appointment on file - used by the admin board."""
    return _load()


def add_appointment(patient_card, patient_name, doctor, date, time):
    records = _load()
    records.append(
        {"patient_card": patient_card, "patient_name": patient_name, "doctor": doctor, "date": date, "time": time}
    )
    _save(records)


def update_appointment(patient_card, doctor, date, time):
    """Move the patient's (first) appointment on file to a new doctor/date/time."""
    records = _load()
    for record in records:
        if record["patient_card"] == patient_card:
            record["doctor"] = doctor or record["doctor"]
            record["date"] = date
            record["time"] = time or record.get("time")
            _save(records)
            return True
    return False


def remove_appointment(patient_card, doctor=None, date=None):
    """Remove the patient's matching appointment (first match, optionally narrowed by doctor/date)."""
    records = _load()
    remaining = []
    removed = False
    for record in records:
        matches = (
            record["patient_card"] == patient_card
            and (not doctor or record["doctor"] == doctor)
            and (not date or record["date"] == date)
        )
        if matches and not removed:
            removed = True
            continue
        remaining.append(record)
    if removed:
        _save(remaining)
    return removed
