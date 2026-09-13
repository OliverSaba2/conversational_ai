"""
Step 0: clean up typos and shorthand ("cancle", "tommorow", "dont", "wanna")
before intent/entity extraction, by spell-correcting known clinic vocabulary
with difflib. Keeps intents.py/extraction.py plain keyword matching.
"""

import re
import difflib

VOCABULARY = [
    "tomorrow", "today", "morning", "afternoon", "evening", "week", "next",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "book", "appointment", "booking", "cancel", "cancellation", "reschedule",
    "available", "availability", "hours", "opening", "closing", "open", "close",
    "human", "agent", "doctor", "confirm", "please", "speak", "talk", "call",
    "from", "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
]

# Shorthand that isn't just a misspelling, so a similarity ratio would miss it.
SHORTHAND = {
    "tmrw": "tomorrow",
    "tmrrw": "tomorrow",
    "2mrw": "tomorrow",
    "2morrow": "tomorrow",
    "2moro": "tomorrow",
    "asap": "as soon as possible",
    "pls": "please",
    "plz": "please",
    "wanna": "want to",
    "gonna": "going to",
}

# Contractions typed without an apostrophe - matters for the "don't
# book"/"don't confirm" no-confirm check in extraction.py.
_APOSTROPHE_FIXES = [
    (r"\bdont\b", "don't"),
    (r"\bdoesnt\b", "doesn't"),
    (r"\bcant\b", "can't"),
    (r"\bwont\b", "won't"),
]


def _correct_word(word: str) -> str:
    lower = word.lower()
    if lower in SHORTHAND:
        return SHORTHAND[lower]
    if lower in VOCABULARY or len(lower) < 3:
        return word
    # Short words need a tighter match so we don't "correct" unrelated words
    # (e.g. "cat") into a distantly-similar vocabulary term.
    cutoff = 0.85 if len(lower) <= 4 else 0.78
    match = difflib.get_close_matches(lower, VOCABULARY, n=1, cutoff=cutoff)
    return match[0] if match else word


def normalize_message(text: str) -> str:
    """Expand chat shorthand and spell-correct known clinic vocabulary."""
    # Include digits so numeric shorthand ("2moro", "2mrw") is seen as a word too.
    corrected = re.sub(r"[A-Za-z0-9']+", lambda m: _correct_word(m.group(0)), text)
    for pattern, replacement in _APOSTROPHE_FIXES:
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    return corrected


if __name__ == "__main__":
    samples = [
        "can i bok an appintment with Dr Karim tommorow aftrnoon",
        "i wanna cancle my apointment, dont call me",
        "wat time r u guys closeing 2moro",
        "book me 13 septembr 2026",
    ]
    for s in samples:
        print(f"{s!r} -> {normalize_message(s)!r}")
