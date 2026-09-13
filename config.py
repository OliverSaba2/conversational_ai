"""
Step 0: configuration, read from environment variables via a local .env
file (copy .env.example to .env). Keeps secrets out of source and .env
itself is gitignored.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv isn't installed - fall back to a tiny manual .env reader
    # so the project still works without the extra dependency.
    def _load_env_file():
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if not os.path.exists(env_path):
            return
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    _load_env_file()

CLINIC_NAME = os.environ.get("CLINIC_NAME", "CliniKit Clinic")
CLINIC_OPENING_HOURS = os.environ.get(
    "CLINIC_OPENING_HOURS", "Monday to Friday, 8:00 AM to 6:00 PM. We're closed on weekends."
)

# Structured version of the hours above, used to actually validate bookings.
CLINIC_OPEN_HOUR = int(os.environ.get("CLINIC_OPEN_HOUR", "8"))
CLINIC_CLOSE_HOUR = int(os.environ.get("CLINIC_CLOSE_HOUR", "18"))
CLINIC_CLOSED_WEEKDAYS = {
    day.strip().lower()
    for day in os.environ.get("CLINIC_CLOSED_WEEKDAYS", "saturday,sunday").split(",")
    if day.strip()
}
PATIENT_STORE_PATH = os.environ.get("PATIENT_STORE_PATH", "patients.json")
APPOINTMENT_STORE_PATH = os.environ.get("APPOINTMENT_STORE_PATH", "appointments.json")

CLINIC_DOCTORS = [
    name.strip()
    for name in os.environ.get(
        "CLINIC_DOCTORS", "Dr. George,Dr. Karim,Dr. Reed,Dr. Han,Dr. Lee"
    ).split(",")
    if name.strip()
]

# Unused by the mocked actions today - for a real clinic/EHR API key later.
CLINIC_API_KEY = os.environ.get("CLINIC_API_KEY")

# Casual login gate for admin_board.py - not hardened auth, don't expose it beyond your own machine.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
