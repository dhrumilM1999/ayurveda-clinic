# Handwritten prescription with the digital pad (iScribe)

You write the prescription by hand on the pad. The software keeps **one picture**: your clinic letterhead, the patient's
name, ID and date, your handwriting, the QR code and your signature line. It is saved on that patient's check-up.

## One-time setup on the doctor's PC (5 minutes)

1. Plug in the iScribe pad (USB). Charge the pen for 3 hours the first time.
2. Install the free **iScribe4U** app from www.iteltronics.com (Downloads) and start it.
3. In iScribe4U use the **Toggle** button to choose **Mouse mode** (the pen then moves the cursor like a mouse).
4. Open the clinic software in the browser (Chrome or Edge). You can keep iScribe4U open in the background.

## Every day

1. Doctor: open the patient's check-up (Check-up screen). The appointments stay on the left.
2. Press the **Handwriting** tab (after Follow-up). One A4 page appears, fully on the screen.
3. Write on the pad with the pen. The writing appears live. Tools: Pen, Eraser, 3 colours, thickness, Undo, Clear all.
4. Press **Save prescription**. The software makes the combined picture (letterhead + patient line + your handwriting + QR +
   signature) and shows it. Then **Print** or **Write another page**.
5. The pharmacist sees the pages in the medicine-giving window (above the medicine list). Earlier pages of the check-up are
   listed at the bottom of the Handwriting tab.

The pad moves the cursor over the whole screen, so only the part of the pad that lies over the A4 page writes. Outside the
page the pad does nothing. If you go to another tab and come back, what you wrote is still there.

## What is saved

- Your handwriting alone (transparent picture) and the combined picture, both private (only logged-in staff who may see
  prescriptions can open them, and every view is written to the audit log).
- The picture has its own Rx number and QR code (scan to check the print-out is genuine), like every other prescription.
- A wrong page can be **removed** (it is hidden, never deleted). Write a new page instead.

## Printing

- **Print** opens the usual print window (A5 / A4, language, Download). A reprint says DUPLICATE COPY.
- If your clinic prints on a **pre-printed pad** (Settings, Branch details), the printed paper leaves the letterhead out,
  but the saved picture always includes the letterhead.
- Colour, letterhead on/off and footer text come from Settings, PDF settings (the same as the typed prescription).

## Good to know

- Handwriting is a **picture**. The pharmacy cannot give medicines from it automatically and the safety warnings (pregnancy,
  metals) do not run on it. Keep the typed medicine list too (Rx tab), or ask the pharmacist to read the picture.
- Gujarati, Hindi and English all work, because it is just a picture of what you write.
- If the pen draws in the wrong place, check that iScribe4U is in Mouse mode and the pad is not in Portrait/Landscape mismatch
  (the page is always A4 upright).
- No pad? A tablet with a pen, a touch screen or a mouse works the same way.

## For the person who edits files

- Page look: `backend/templates/documents/prescription_handwritten.html` (**SAFE TO EDIT**, the box height for the writing).
- Letterhead, signature, QR: `backend/templates/documents/_doc_base.html`.
- Code: `backend/apps/prescriptions/handwriting.py` (makes the pictures), `handwriting_views.py` (API),
  `frontend/src/pages/consult/handwriting/` (writing window; **ASK FIRST**).
- New library: `pypdfium2` (free, turns the PDF page into a picture).
