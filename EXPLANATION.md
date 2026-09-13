# How this works

## Short explanation

This is a chat assistant for a clinic. A patient can book, reschedule, or cancel an
appointment, ask about doctors, availability, or opening hours (typing however they'd
actually type, typos and all) and the assistant collects whatever's missing over as
many messages as it takes, then double-checks with the patient before it actually does
anything.

## Overall approach

The pipeline is: clean up the message → figure out the intent → pull out whatever
details are in it → hand both to a conversation state machine that decides what to do
next. That state machine (`session.py`) is the heart of the project, it's what
lets a patient say "book an appointment" in one message, "with Dr. George" in the next,
and "tomorrow at 4" in the one after that, and have it all add up to one request instead
of three separate half-finished ones.

## How I identify intent

`intents.py` checks the message against ordered lists of keywords/phrases - "cancel"
before "reschedule" before "book", small talk checked last so "hi, can I book an
appointment" is still a booking, not just a greeting. Order matters a lot here: more
specific phrases are checked first so they don't get swallowed by a generic one.

Before any of that runs, `normalize.py` spell-corrects the message against a small
vocabulary of clinic words using `difflib` ("tommorow" → "tomorrow", "cancle" →
"cancel"), so a typo doesn't just fail to match anything. A message with no obvious
keyword at all (someone who just says "Dr. George tomorrow at 4pm" without ever saying
"book") is still recognized as a booking if it has booking-shaped details in it.

## How I extract information

`extraction.py` pulls out doctor, date, time, and a couple of special flags using regex:
relative dates ("tomorrow", "next Friday"), explicit calendar dates in several formats,
and a "from Monday to Wednesday" pattern for reschedules. Doctor names are checked
against a fixed roster of five doctors, with typo tolerance, and don't require the word
"Dr.": just saying "George" is enough once we're already in a booking conversation.

None of this depends on the sentence being in a fixed order. A patient can give the
doctor, then the date, then the time, in any order, across any number of messages, and
it all gets merged into the same request.

## How I handle missing or ambiguous information

The assistant tracks exactly what it still needs (doctor, date, time, patient identity)
and asks for only that, nothing more. If several pieces are missing it asks for all of
them at once rather than one at a time. If the patient gives things in the "wrong"
order such as their name when asked for a card number or a card number when asked for a name,
that's accepted instead of rejected, because that can be how people answer.

The specific ambiguous case called out in the brief: "I might want to see Dr. George
tomorrow at 4, but don't book anything yet" is handled by detecting phrases like
"don't book"/"don't confirm" and routing straight to a plain availability check instead
of creating anything, even though all the booking details are technically present.

If a patient wants to reschedule or cancel and has more than one appointment on file,
the assistant lists them and asks which one, rather than guessing.

## How I avoid incorrect automated actions

This was the part I spent the most effort on, since it's the difference between a demo
and something you'd trust with a real clinic:

- **Nothing happens without an explicit yes.** Every booking, reschedule, or
  cancellation ends with "shall I go ahead? (yes/no)" and only a clear yes triggers the
  real action. A vague reply gets asked again, not assumed.
- **The doctor has to be real.** Names are checked against the clinic's actual roster
  (typos corrected, but a made-up doctor is rejected outright and the patient's told the
  real list).
- **Dates and times are checked for actually existing.** "31 February" or "25:00" get
  rejected as not being real, separately from just being vague ("next week" is fine to
  leave open, but a fake date is called out directly).
- **No double-booking.** A doctor can't have two appointments within an hour of each
  other; the check runs against every existing appointment, not just the current
  patient's own.
- **Nothing can happen in the past or outside opening hours.**
- **A stray "no" is never misread as data.** Early on, I had a bug where answering "no"
  to "what's your card number?" got taken literally as the patient's name. That's now
  guarded everywhere identity is captured, and "never mind"/"stop"/etc. are recognized
  as dropping the whole request, from any point in the conversation, rather than being
  fed into whatever question was just asked.
- **Every patient needs a first and last name on file**, and a returning patient is only
  ever matched by their own card number, so one patient's identity can't bleed into
  another's.

## How I'd improve it for production

- Replace the keyword/regex NLU with a real model (or an LLM call) for intent and slot
  extraction - it would generalize to phrasing I haven't thought to handle, instead of
  needing new keywords added by hand every time something slips through.
- Replace the JSON files with a real database. Right now two people booking at the exact
  same moment could race each other; a database with proper transactions fixes that, and
  it's also just the right long-term storage for real patient data.
- Real calendar/EHR integration instead of a flat "one hour per slot" assumption,
  different visit types need different durations, and a real system needs to talk to
  whatever the clinic's staff are actually using.
- Proper authentication on the admin board (hashed passwords, real sessions, maybe
  per-staff accounts) instead of the single shared username/password it has now, which I
  built as a placeholder, not something to expose beyond a local machine.
- Timezones. A single clinic in one timezone was a reasonable assumption for this
  exercise, but a production version can't assume everyone's on the same clock.
