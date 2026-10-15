# What happens when someone makes a mistake

We test the software the way a tired person at the counter would use it: wrong option, double click, typing
nonsense, opening a screen they should not, two people clicking at the same time. This page lists what is
protected and where the tests are. (All tests: `docker compose exec backend python -m pytest`.)

## Things you can undo yourself
| Mistake | What to do |
|---|---|
| Checked a patient in / started / marked Done / marked "Did not come" / cancelled by mistake | **Undo** (back-arrow) next to the appointment, within 60 minutes |
| Booked an appointment by mistake | row menu **⋮ → Undo this booking** (no message goes to the patient) |
| Pressed **Complete visit** by mistake | **Re-open check-up** on the check-up screen (not possible after the pharmacy gave medicines) |
| Wrong click on a Panchakarma session | **Undo** on the session row, within 60 minutes (what the therapist wrote is kept) |
| Stock or bill wrong | Stock correction with a reason, sale return, bill cancel with a credit note (nothing is deleted) |

## Refused politely (nothing is half-saved)
- Patient: empty or space-only name, wrong mobile number, impossible age, birth date in the future.
- Appointment: past date, a time the doctor does not sit, same slot twice, same patient twice on one day, wrong step order (start before check-in), check-in on the wrong day, cancel twice, reschedule to a bad time.
- Bill: negative or zero quantity, negative price, discount over 100%, GST outside 0 to 100, paying more than due, paying twice (double click), paying a cancelled bill, cancelling twice.
- Check-up: follow-up date before the check-up, wrong data in complaints/diagnosis.
- Prescription: a medicine that the pharmacy already gave cannot be removed or changed.
- Pharmacy: selling more than the stock, an expired batch, a batch of another medicine or branch, a wrong quantity, giving the same medicine again from the same prescription (double click), returning more than was sold, a stock correction that would go below zero.
- Settings: a negative price or fee, GST over 100, end time before start time, a room with no name, the same service name twice (clear message, not a crash).
- Owner account: you cannot switch off or reduce your own account, and the last organization admin cannot be removed.

## Safe against wrong people and wrong places
- A role only sees its own screens (therapist: no billing; receptionist: no check-up notes; pharmacist: no patient registration).
- Another branch's bills, stock, appointments and therapy plans cannot be opened or changed.
- Without login, with a fake login token, or without choosing a branch, nothing works.
- Too many wrong passwords slows the login down.

## Odd typing and odd links
- Wrong or empty import files, wrong upload types (exe, fake pdf, too big), odd characters (Gujarati, Hindi, emoji, code-like text) are accepted as plain text or refused, never run.
- A wrong id in a link, a broken filter or a hidden control character gives a clear message, not an error page.
- When the server is off, lists say **"Could not load this list"** with a **Try again** button (they no longer look empty).

## At the same moment
Bill numbers and token numbers never repeat when several people click together; a bill cannot be overpaid; the last pack of a medicine cannot be sold twice.

Tests: `backend/apps/common/tests/test_mistakes_*.py` (front desk, clinical, settings, inputs, concurrency) plus the module tests.
