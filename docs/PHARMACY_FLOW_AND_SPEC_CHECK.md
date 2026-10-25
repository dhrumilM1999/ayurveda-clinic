# Pharmacy: the whole flow, and a check against `clinic_purchase_inventory_feature_spec.md`

Checked on 2026-10-25 against the code in `backend/apps/pharmacy/` (services, views, models) and the real demo data.

## 1. The flow, from buying a medicine to the patient taking it

```
Supplier (Pharmacy > Setup)            [switch: Suppliers]
   |
1. STOCK IN  (Pharmacy > Purchases > New purchase)
   supplier + invoice no + date, then one line per medicine and BATCH:
   batch no, mfg, expiry, paid qty, FREE qty, purchase rate, discount %, GST %, MRP, selling price
   -> stock of that batch goes up, one ledger line per (paid / free)
   -> same supplier + same invoice no is refused (double click / retry cannot double the stock)
   -> already-expired batch is refused; selling price above MRP is refused
   Opening stock (first day) uses the same screen, tick "Opening stock".
   |
2. LABELS  (Pharmacy > Stock > Print labels)
   one small label per pack: medicine, strength, pack size, MRP, GST, batch, expiry, barcode.
   A batch without a barcode gets a clinic code (12 digits starting 29) the first time.
   |
3. ALERTS  (Dashboard, Pharmacy > Stock)
   Low (reorder level) / Out / Near expiry (within 90 days) / Expired / "Asked for, not in stock".
   |
4. DOCTOR WRITES THE PRESCRIPTION
   The doctor sees "In stock: n / Only n left / Not in stock" next to each medicine.
   Saving a prescription does NOT touch stock.
   |
5. GIVE (DISPENSE)  (Pharmacy > Give medicines)
   Final prescriptions of the day. Per line the screen offers batches with stock, NOT expired,
   EARLIEST EXPIRY FIRST (FEFO) and picks the first one. Scan a label to pick the exact batch.
   On "Give": batch is locked, stock goes down by the quantity actually given (packs or loose units),
   one ledger line per batch, a bill is made, payment taken (cash / UPI / card) or left to pay later.
   A medicine already given for the same prescription cannot be given again.
   Schedule E1 medicines are given only against a prescription.
   |
6. BILL
   Pharmacy bill (series PH) with batch and expiry on each line, GST per line, or, with "One combined bill",
   the medicines go on the visit's OPD bill (consultation + medicines + therapy on one bill).
   |
7. COUNTER SALE (no prescription)
   Scan, choose batch (earliest expiry first), bill, payment. Not for Schedule E1.
   |
8. MISTAKES AND RETURNS
   Patient returns medicine: Sale return -> stock back up (unless damaged) + credit note on the bill.
   Send back to supplier: Purchase return -> stock down, reason required.
   Damaged / expired / manual correction: reason required, stock ledger line.
   Physical stock check: count the shelves, the differences are posted to the ledger.
   |
9. REPORTS
   Stock ledger (opening + in - out = closing), reorder list, daily sales, top selling, slow / non-moving,
   margin, GST. Every stock change is in the audit log.
```

Safety rules that are enforced by the database / code (not just the screen):
- Stock can never go below zero (database rule `stock_not_negative`).
- Two people selling the last pack at the same moment: one of them is refused (row lock).
- Expired batch cannot be sold. Selling price cannot be more than MRP. Nothing is hard-deleted.
- **Real check made today:** in the demo database the stock of all 137 batches equals the sum of their ledger lines (0 differences).

## 2. The spec, point by point (for a small clinic with its own medicine shop)

Legend: DONE = works as the spec says. PARTLY = works, a small gap. MISSING = not built. SKIP = the spec feature is not needed for a clinic of this size.

| Spec item | Status | Note |
|---|---|---|
| Supplier master (GSTIN, licence, terms) | DONE | Also has opening balance? **No** (see ledger below). |
| Purchase entry: invoice header, lines, batch, expiry, free qty, rate, discount, GST, MRP | DONE | Free quantity is kept separate from paid quantity. |
| Multiple batches of one medicine on one invoice | DONE | Each is its own line / batch. |
| Duplicate supplier invoice blocked | DONE | Only when an invoice number is typed (see gap 5). |
| Draft purchase that does not touch stock | MISSING | A purchase is posted at once. Fine for a small shop *if* mistakes can be undone (gap 3). |
| Receive and verify (invoice qty vs received qty, damaged, short) | MISSING | Only one quantity is entered. SKIP for now: staff type what they really received. |
| Printed invoice total vs computed total (show the difference) | MISSING | The total is calculated by the software; the total printed on the supplier invoice is never typed, so a wrong rate, GST or discount is not noticed. **Worth building** (gap 2). |
| Post atomically, retry never doubles | DONE | One database transaction. |
| Cancel / reverse a wrong purchase (no delete) | MISSING | Today a wrong purchase can only be fixed by a stock correction, and the purchase stays in the register unchanged. **Worth building** (gap 3). |
| Batch-level stock + immutable stock-movement ledger | DONE | `StockBatch` + `StockMovement`; reconciles to 0 difference. |
| Movement types: purchase, sale, sale return, supplier return, expiry, damage, adjustment, count | DONE | Transfer between branches: not built (SKIP, one clinic). |
| Pack to base-unit conversion | DONE | Stock is in packs; loose sale as a part of a pack (`units_per_pack`). |
| Expiry: warn near expiry, block selling expired, FEFO suggestion | DONE | Near-expiry window 90 days (editable in `services.py`). |
| FEFO override only with authority and a reason | PARTLY | Staff can pick any non-expired batch, no reason asked, not logged as an override. Low risk for one pharmacist; can add "why not the earliest?" later. |
| Expiry date required when a batch is entered | **PARTLY / gap 1** | Expiry tracking is an extra switch (Additional settings). Even when it is on, the expiry box can be left empty, and batch number is required only when batch tracking is on. A batch with no expiry never shows as near-expiry and is never blocked. |
| Quarantine (separate non-sellable stock) | PARTLY | Damaged / expired are written off (out of stock). There is no "hold" state. SKIP for a small clinic. |
| Reserved stock | SKIP | Not needed: stock goes down only when given. |
| Supplier payments, payable, partial payment, ageing, supplier ledger | **MISSING** | There is no supplier payment or payable at all. The owner cannot see "how much do I owe which supplier, and what is overdue". **Biggest gap** for the owner (gap 4). |
| Supplier credit notes (linked to purchase returns) | PARTLY | Purchase return exists with the supplier's credit-note number as a reference; it does not reduce any payable because payables do not exist. |
| Purchase returns limited to quantity received minus returned | PARTLY | Limited to the stock in the batch (cannot return what is not there), not tied to one purchase invoice. OK for a small clinic. |
| Reports: purchase register, stock by batch, low stock, expiry, recent movements | DONE | Reorder, expiry alerts, ledger, purchase list with filters. |
| Reports: supplier ledger, outstanding, ageing, payment register | MISSING | Needs gap 4. |
| Reports: purchases by period / supplier | PARTLY | Purchase list can be filtered by date and supplier; no total-by-supplier page. |
| Prescription alone never reduces stock | DONE | Stock moves only on "Give". |
| Dispense only the quantity really handed; per batch; two batches = two movements | DONE | Also loose units. |
| Block negative stock / expired / insufficient | DONE | In code and in the database. |
| Free / zero-charge issue still reduces stock | PARTLY | Possible only by selling with 100 % discount. There is no separate "free issue" with a reason. Low priority. |
| No bill for a prescription that was never dispensed | DONE | Bill is made together with the "Give". |
| Consultation and medicine charges separate (or one bill by choice) | DONE | One OPD bill is the default; separate pharmacy bill by a switch. |
| Reverse a dispensing with reason, linked, history kept | DONE | As a Sale return with a reason and a credit note. |
| Repeated "Give" cannot deduct twice | DONE for prescriptions | Counter sale: two clicks make two separate sales (the button shows a spinner, but a very fast double click is not blocked). Small risk (gap 6). |
| Bill cancellation does not silently restore stock | DONE | Stock returns only through a Sale return. |
| Patient payment does not affect stock | DONE | |
| Stock formula reconciles (opening + in - out = closing) | DONE | Ledger screen shows opening, totals per kind, closing. |
| Roles: who can post, adjust, pay | PARTLY | Two permissions: `pharmacy.stock` (receive, correct, count) and `pharmacy.dispense` (give, sell, return). A pharmacist can both receive and write off stock; no second approval. Fine for one clinic. |
| Audit log of all of it | DONE | Create / change in the audit log; patient views logged. |
| Invoice scan / attachment | MISSING | SKIP for now, or later: attach a photo of the supplier invoice to the purchase. |
| Barcode support | DONE | Labels with Code 128 barcode, scan at the counter. |
| Multi-tenant isolation | DONE | Every row has organization and branch; tests cover it. |

## 3. What to fix, in the order that matters for your clinic

1. **Expiry date required when batch tracking is on** (small change). Without it a batch can hide from expiry control.
2. **Type the printed invoice total** when entering a purchase; show the difference from the computed total and ask to check rates / GST (small change).
3. **Cancel a wrong purchase** the safe way: a "reverse" action with a reason that takes the stock back out (only if that stock is still on the shelf) and keeps both lines in the register (medium change, no delete).
4. **Supplier payments and "what I owe" screen**: payable per purchase, payments (cash / UPI / bank, partial), balance per supplier, due dates from the supplier's payment days, ageing (medium to large change, new tables).
5. **Purchase without an invoice number**: today a double click would add the stock twice. Refuse an identical purchase made again within a few minutes (small change).
6. **Counter sale double click**: block a second identical sale within a few seconds (small change).
7. Later, if ever needed: "why not the earliest batch?" reason, free-issue with reason, attach invoice photo.

Not needed now: draft + verify step, quarantine, reservations, transfers, second approval, supplier advance, GST-return style accounting. The accountant keeps the formal books; the software keeps stock and who-owes-what.

Questions to answer before building 4: does the clinic buy on credit (pay the distributor later), or pay at once? If always at once, 4 can be a very small "mark paid" instead.
