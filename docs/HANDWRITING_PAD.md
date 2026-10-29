# Handwritten prescription with the digital pad (iScribe)

You write the prescription by hand on the pad. The software keeps **one picture**: your clinic letterhead, the patient's
name, ID and date, your handwriting, the QR code and your signature line. It is saved on that patient's check-up.

## One-time setup on the doctor's PC (5 minutes)

1. Plug in the iScribe pad (USB). Charge the pen for 3 hours the first time.
2. Install the free **iScribe4U** app from www.iteltronics.com (Downloads) and start it.
3. In iScribe4U use the **Toggle** button to choose **Mouse mode** (the pen then moves the cursor like a mouse).
4. Open the clinic software in the browser (Chrome or Edge). You can keep iScribe4U open in the background.

## Every day

1. Doctor: open the patient's check-up (Check-up screen).
2. Press **Handwriting** (top of the check-up).
3. Write on the pad with the pen. The writing appears live on the screen. Tools: Pen, Eraser, 3 colours, thickness,
   Undo, Clear all, Upright/Wide, paper A5 (half A4) or A4.
4. Press **Save prescription**. The software makes the combined picture and shows it. Then **Print** or **Write another
   page**.
5. The pharmacist sees the pages in the medicine-giving window (above the medicine list). Pages saved for the check-up are
   also listed under the Handwriting button.

## Pad mode (full screen): write on the whole pad

The iScribe pad (Mouse mode) moves the cursor over the WHOLE screen: pen at the pad's bottom-right corner = cursor at the
screen's bottom-right corner. Without pad mode you would have to aim at the small writing box.

1. In the Handwriting window press **Pad mode (full screen)**. The screen goes full screen.
2. Write anywhere on the pad. What you write on the pad appears in the same place on the page. A blue ring shows where
   the pen is on the page (the normal cursor is hidden).
3. To press a button (Save, Undo...), move the pen onto the button and tap. Taps on buttons never write.
4. **Leave pad mode** (or Esc) goes back to the normal window. Your writing is kept.

Pad mode opens in **Wide** (pad held sideways). If you hold the pad upright, press **Upright**.

**Writing sticks to an edge, or the ring does not match the pen?** Press **Set pad corners**, touch the pen at the pad's
TOP-LEFT corner, then at the BOTTOM-RIGHT corner. This is remembered on this computer. **Use whole screen** forgets it.

If the browser refuses full screen, press F11 and try again. Pad mode needs full screen so the pad and the screen line up.

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
  (use the Upright/Wide switch in the writing window to match the pad).
- No pad? A tablet with a pen, a touch screen or a mouse works the same way.

## For the person who edits files

- Page look: `backend/templates/documents/prescription_handwritten.html` (**SAFE TO EDIT**, the box height for the writing).
- Letterhead, signature, QR: `backend/templates/documents/_doc_base.html`.
- Code: `backend/apps/prescriptions/handwriting.py` (makes the pictures), `handwriting_views.py` (API),
  `frontend/src/pages/consult/handwriting/` (writing window; **ASK FIRST**).
- New library: `pypdfium2` (free, turns the PDF page into a picture).
