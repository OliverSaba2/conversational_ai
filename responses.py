"""
Step 4: turn (intent, entities, action_result) into a natural-language reply.
"""

CLINIC_OPENING_HOURS = "Monday to Friday, 8:00 AM to 6:00 PM. We're closed on weekends."


def generate_response(intent: str, entities: dict, action_result: dict) -> str:
    action = action_result.get("action")
    doctor = entities.get("doctor")
    date = entities.get("preferred_date")
    time = entities.get("preferred_time")

    doctor_part = f" with {doctor}" if doctor else ""
    date_part = f" on {date}" if date else ""
    time_part = f" at {time}" if time else ""

    if action == "answer_opening_hours":
        return f"Our clinic is open {CLINIC_OPENING_HOURS}"

    if action == "check_availability":
        return (
            f"Let me check availability{doctor_part}{date_part}{time_part} for you. "
            f"I won't book anything until you confirm."
        )

    if action == "create_appointment":
        return f"Done! Your appointment{doctor_part} is booked{date_part}{time_part}."

    if action == "reschedule_appointment":
        return f"Your appointment{doctor_part} has been moved{date_part}{time_part}."

    if action == "cancel_appointment":
        return f"Your appointment{doctor_part}{date_part} has been cancelled."

    if action == "handoff_to_human":
        return "Sure, connecting you with a member of our clinic staff now."

    if action == "ask_for_more_information":
        missing = action_result.get("missing_fields") or []
        if "intent" in missing:
            return "Sorry, could you clarify what you'd like help with (booking, rescheduling, cancelling, etc.)?"
        return f"Could you tell me the {', '.join(missing)} so I can help with that?"

    return "Sorry, I didn't quite understand that. Could you rephrase it?"
