# Results

Real output from `ConversationSession.handle_message()` (same path `main.py` /
`chat_app.py` use). `[MOCK]` actions in `actions.py` never touch a real calendar - just
the local JSON files.

| Scenario | Sample input | Result |
|---|---|---|
| Multi-turn booking | "book an appointment" → card → name → "Dr. George" → "Sept 15 at 10am" → "yes" | Asked only for what was missing, booked on confirmation |
| Typos + unordered, one message | "appointmnet with dr goerge tommorow at 2pm" | Corrected and parsed doctor/date/time in one shot |
| Ambiguous "don't book yet" | "see Dr. George tomorrow at 4, but don't book anything yet" | `check_availability`, not a booking, despite full details |
| Made-up doctor | "book me with Dr. Nobody tomorrow" | Rejected, real doctor list offered |
| Impossible date/time | "31 February at 25:00" | `invalid_booking_time`: "31 February isn't a real date" |
| Outside opening hours | "Monday at 9pm" (closes 6pm) | `invalid_booking_time`: outside opening hours |
| Double booking | Same doctor booked 11:00, then 11:30 | First succeeds; second gets `slot_unavailable` on confirm |
| "no" as a reply | Asked for card, patient says "no" | Treated as "no card" (new one issued), never as a literal name |
| Small talk | "opening hours?" / "which doctors?" | Answered directly, no booking flow triggered |
| Bail out mid-flow | "book with Dr. George" → "never mind" | Request dropped cleanly, no partial booking |
| Returning patient | Known card number given | "Welcome back, John Smith" - skips the name question |

## Observed limitation

Card/name capture is its own sub-flow: info given while the assistant is specifically
waiting on a card or name (e.g. a doctor mentioned in that same message) isn't parsed and
has to be repeated after. The "give details in any order" flexibility in
[EXPLANATION.md](EXPLANATION.md) applies to doctor/date/time among themselves, not to
mixing them with identity questions.
