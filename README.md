# CliniKit — AI Clinic Assistant

A chat assistant for a medical clinic. Patients can book, reschedule, or cancel an
appointment, ask about doctors, availability, or opening hours — through normal
conversation, typos and all. There's also an admin board to see and manage every
reservation.

Everything is local and mocked: no real calendar or database, just JSON files on
disk, so the whole thing runs on your machine with no external services.

## What's in here

- **The chat assistant** — a terminal chat (`main.py`) or a browser chat
  (`chat_app.py`), both backed by the same conversation logic in `session.py`.
- **The admin board** (`admin_board.py`) — a password-protected page showing every
  appointment and patient on file, with a Gantt-style schedule and a cancel button.

## Setup

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`. The defaults work out of the box — edit it if you
   want to change the clinic's name, hours, doctors, or admin login.

## Running it

Run these from inside the `conversational_ai` folder.

| What | Command |
|---|---|
| Chat in your terminal | `python main.py` |
| Chat in your browser | `streamlit run chat_app.py` |
| Admin board (login: `admin` / `admin` by default) | `streamlit run admin_board.py` |

In the terminal chat: type `quit` or `exit` to leave, `reset` to drop whatever you
were in the middle of and start over.

## Worth knowing

- Doctors are a fixed roster of 5 (`CLINIC_DOCTORS` in `.env`). Typos get corrected;
  a made-up doctor gets rejected.
- Appointments need at least an hour's gap per doctor, must fall within opening
  hours, and can't be in the past.
- Your card number is remembered, so next time you only need to give the card and
  the assistant already knows your name.
- `patients.json` and `appointments.json` are created the first time you use the
  assistant — delete them anytime to start fresh.
