"""
A tiny local "patient directory" - a stand-in for a real patient-records
lookup. Backed by one JSON file, keyed by card number, so a returning
patient doesn't have to repeat their name.
"""

import random

import json_file
from config import PATIENT_STORE_PATH

_PATH = json_file.resolve_path(PATIENT_STORE_PATH)


def find_patient(card_number):
    """{"name": ..., "card_number": ...} for a known card, else None."""
    if not card_number:
        return None
    return json_file.load(_PATH, {}).get(card_number.strip().lower())


def save_patient(card_number, name):
    if not card_number or not name:
        return
    data = json_file.load(_PATH, {})
    data[card_number.strip().lower()] = {"name": name, "card_number": card_number.strip()}
    json_file.save(_PATH, data)


def list_all():
    """Every patient on file - used by the admin board."""
    return list(json_file.load(_PATH, {}).values())


def generate_card_number():
    """A new, unused card number - for a patient who doesn't have one."""
    existing = json_file.load(_PATH, {})
    while True:
        candidate = str(random.randint(100000, 999999))
        if candidate not in existing:
            return candidate
