"""
Step 3: mocked clinic actions. Each prints what it would do and returns a
dict describing the call - a stand-in for a real calendar/EHR integration.
session.py decides which one to call; appointment_store.py backs these.
"""

import appointment_store
from config import CLINIC_DOCTORS


def check_availability(doctor=None, date=None, time=None):
    print(f"[MOCK] check_availability(doctor={doctor}, date={date}, time={time})")
    return {"action": "check_availability", "doctor": doctor, "date": date, "time": time}


def list_doctors():
    print(f"[MOCK] list_doctors() -> {CLINIC_DOCTORS}")
    return {"action": "list_doctors", "doctors": CLINIC_DOCTORS}


def create_appointment(patient_name=None, patient_card=None, doctor=None, date=None, time=None):
    # No exclude_card (unlike reschedule) - a new booking can't collide with
    # ANY existing appointment for that doctor/time, even this patient's own.
    conflict = appointment_store.find_conflict(doctor, date, time)
    if conflict:
        print(f"[MOCK] create_appointment CONFLICT: {doctor} already booked on {date} at {time}")
        return {"action": "slot_unavailable", "doctor": doctor, "date": date, "time": time}

    print(f"[MOCK] create_appointment(patient={patient_name}, doctor={doctor}, date={date}, time={time})")
    appointment_store.add_appointment(patient_card, patient_name, doctor, date, time)
    return {
        "action": "create_appointment",
        "patient_name": patient_name,
        "patient_card": patient_card,
        "doctor": doctor,
        "date": date,
        "time": time,
    }


def reschedule_appointment(patient_name=None, patient_card=None, doctor=None, original_date=None, new_date=None, time=None):
    conflict = appointment_store.find_conflict(doctor, new_date, time, exclude_card=patient_card)
    if conflict:
        print(f"[MOCK] reschedule_appointment CONFLICT: {doctor} already booked on {new_date} at {time}")
        return {"action": "slot_unavailable", "doctor": doctor, "date": new_date, "time": time}

    print(
        f"[MOCK] reschedule_appointment(patient={patient_name}, doctor={doctor}, "
        f"original_date={original_date}, new_date={new_date}, time={time})"
    )
    appointment_store.update_appointment(patient_card, doctor, new_date, time)
    return {
        "action": "reschedule_appointment",
        "patient_name": patient_name,
        "patient_card": patient_card,
        "doctor": doctor,
        "original_date": original_date,
        "new_date": new_date,
        "time": time,
    }


def cancel_appointment(patient_name=None, patient_card=None, doctor=None, date=None):
    removed = appointment_store.remove_appointment(patient_card, doctor, date)
    if not removed:
        print(f"[MOCK] cancel_appointment: nothing on file for patient_card={patient_card}")
        return {"action": "no_appointment_found", "patient_name": patient_name}

    print(f"[MOCK] cancel_appointment(patient={patient_name}, doctor={doctor}, date={date})")
    return {"action": "cancel_appointment", "patient_name": patient_name, "patient_card": patient_card, "doctor": doctor, "date": date}


def handoff_to_human(reason=None):
    print(f"[MOCK] handoff_to_human(reason={reason})")
    return {"action": "handoff_to_human", "reason": reason}


def ask_for_more_information(missing_fields=None):
    print(f"[MOCK] ask_for_more_information(missing_fields={missing_fields})")
    return {"action": "ask_for_more_information", "missing_fields": missing_fields or []}


def await_confirmation(intent=None, doctor=None, date=None, time=None):
    """No side effect - we have everything we need, but the patient hasn't said yes yet."""
    print(f"[MOCK] await_confirmation(intent={intent}, doctor={doctor}, date={date}, time={time})")
    return {"action": "await_confirmation", "intent": intent, "doctor": doctor, "date": date, "time": time}


def no_appointment(intent=None, reason=None):
    """No side effect - the patient declined, or backed out mid-conversation."""
    print(f"[MOCK] no_appointment(intent={intent}, reason={reason})")
    return {"action": "no_appointment", "intent": intent, "reason": reason}


def no_appointment_found(patient_card=None, patient_name=None):
    """No side effect - the patient has nothing on file to reschedule/cancel."""
    print(f"[MOCK] no_appointment_found(patient_card={patient_card})")
    return {"action": "no_appointment_found", "patient_card": patient_card, "patient_name": patient_name}
