"""
Step 3: mocked clinic actions, and the logic that decides which one to call.

The mocked actions just print what they would do and return a dict describing
the call - stand-ins for real calendar/EHR integrations.
"""


def check_availability(doctor=None, date=None, time=None):
    print(f"[MOCK] check_availability(doctor={doctor}, date={date}, time={time})")
    return {"action": "check_availability", "doctor": doctor, "date": date, "time": time}


def create_appointment(doctor=None, date=None, time=None):
    print(f"[MOCK] create_appointment(doctor={doctor}, date={date}, time={time})")
    return {"action": "create_appointment", "doctor": doctor, "date": date, "time": time}


def reschedule_appointment(doctor=None, new_date=None, time=None):
    print(f"[MOCK] reschedule_appointment(doctor={doctor}, new_date={new_date}, time={time})")
    return {"action": "reschedule_appointment", "doctor": doctor, "new_date": new_date, "time": time}


def cancel_appointment(doctor=None, date=None):
    print(f"[MOCK] cancel_appointment(doctor={doctor}, date={date})")
    return {"action": "cancel_appointment", "doctor": doctor, "date": date}


def handoff_to_human(reason=None):
    print(f"[MOCK] handoff_to_human(reason={reason})")
    return {"action": "handoff_to_human", "reason": reason}


def ask_for_more_information(missing_fields=None):
    print(f"[MOCK] ask_for_more_information(missing_fields={missing_fields})")
    return {"action": "ask_for_more_information", "missing_fields": missing_fields or []}


def decide_action(intent: str, entities: dict) -> dict:
    """
    Pick the right mocked action for the given intent + extracted entities.

    Key rule (the "ambiguous case" from the brief): if the patient explicitly
    said not to book/confirm yet, we must never call create_appointment -
    we just check availability instead.
    """
    doctor = entities.get("doctor")
    date = entities.get("preferred_date")
    time = entities.get("preferred_time")
    no_confirm = entities.get("explicit_no_confirm")

    if intent == "request_human":
        return handoff_to_human(reason="patient asked to speak with a human")

    if intent == "ask_opening_hours":
        return {"action": "answer_opening_hours"}

    if intent == "ask_doctor_availability":
        return check_availability(doctor=doctor, date=date, time=time)

    if intent == "cancel_appointment":
        if not doctor and not date:
            return ask_for_more_information(missing_fields=["doctor_or_date"])
        return cancel_appointment(doctor=doctor, date=date)

    if intent == "reschedule_appointment":
        if not date:
            return ask_for_more_information(missing_fields=["new_date"])
        return reschedule_appointment(doctor=doctor, new_date=date, time=time)

    if intent == "book_appointment":
        if no_confirm:
            # Patient is thinking out loud, not confirming a booking.
            return check_availability(doctor=doctor, date=date, time=time)
        missing = [name for name, value in [("date", date), ("time", time)] if not value]
        if missing:
            return ask_for_more_information(missing_fields=missing)
        return create_appointment(doctor=doctor, date=date, time=time)

    # intent == "unclear"
    return ask_for_more_information(missing_fields=["intent"])
