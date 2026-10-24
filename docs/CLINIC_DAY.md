# A clinic day, step by step (who does what)

This is the daily flow the software is built and tested for. Hand this page to the doctor and the staff.

## First day only (the owner / pharmacist)
1. **Settings, Clinic**: clinic name, logo. **Branch details**: address, phone, timings line, GSTIN.
2. **Staff**: add the doctor (with registration number and signature picture), receptionist, pharmacist, therapist.
3. **Doctor schedules** and **Fees and services**: timings, consultation fee (new case / follow-up), your services list.
4. **Medicines**: check the list. **Pharmacy, Purchases, Opening stock**: enter the stock you already have (medicine,
   batch, expiry, quantity, MRP). Later stock comes in through **Purchases**.
5. **Settings, PDF settings**: paper, colour, letterhead. Print a test prescription and bill.

## Every patient
| Who | What | Where |
|---|---|---|
| Receptionist | Register the new patient (name, mobile, age, consent). Book an appointment, or **Walk-in** (gets a token). For a walk-in press **Bill the consultation**, take the fee. Booked patients: **Check in** when they arrive; the fee bill opens. | Patients, Appointments |
| Doctor | Open the patient from **Check-up**. Write complaints, examination, diagnosis. **Rx (medicines)**: search a medicine. Next to each medicine you see **In stock: n**, **Only n left** or **Not in stock**, so you can choose another one. Or press **Handwriting** and write on the pad. Press **Complete visit**. A mistake? **Re-open check-up** (until the pharmacy has given the medicines). | Check-up |
| Pharmacist | **Pharmacy, Dispense**: the prescription appears when the doctor completes the visit. A red tag shows **n not in stock**. Open it: medicines in stock are ticked, a medicine that is missing says **Out of stock**. Press **Give ... & add to OPD bill**: stock goes down and the medicines are added to the patient's **same bill** as the consultation. | Pharmacy |
| Owner | **Dashboard**: patients today, collection (cash, UPI, card). **Pharmacy, Stock**: tiles for Out of stock, Low stock, Near expiry, Expired, and **Asked for, not in stock** (medicines doctors wrote that the shelf does not have; order these first). **Reports**. | Dashboard, Pharmacy, Reports |

## When a medicine is not in stock
1. The doctor sees **Not in stock** while prescribing and may choose another medicine.
2. If the doctor keeps it, the pharmacist sees **n not in stock** in the queue and **Out of stock** on that line. The other medicines can still be given; the missing one stays on the prescription.
3. The owner / pharmacist sees it in the tile **Asked for, not in stock** (last 30 days) = the list to order from the supplier.
4. When the stock arrives (Purchases), the pharmacist opens the same prescription again and gives the remaining medicine; it is added to the same bill.

## One bill
By default the **consultation, services and medicines are on ONE bill per visit** (Settings, Additional settings, "Medicines on the OPD bill"). The dashboard counts it as OPD collection. Turn it off if you want separate pharmacy bills.

## Mistakes
Wrong click? See `docs/MISTAKE_PROTECTION.md`: **Undo** next to appointments and sessions, **Re-open check-up**, **Return** a sale, **Cancel** a bill with a credit note. Nothing is ever deleted.
