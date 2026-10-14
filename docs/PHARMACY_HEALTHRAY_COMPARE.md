# Pharmacy: our app compared with Healthray Pharmacy

Looked at on 15 Oct 2026: the Healthray Pharmacy menu and dashboard (layout only; no patient data copied, nothing saved).
Healthray is a big solution (small shops to multi-speciality hospitals). We only want what a **small clinic** needs.

Healthray menu: Dashboard, Account Master, Sale, Purchase, Item Master, Initialization (Stores, Users, Patient Deposit,
Purchase Credit Note, Stock Order, Package Master, Profiler, Purchase Order, Transfer Stock, Department Master,
Order Processing, Receive Stock, Pharmacy Expense ...), Pay Bill (Purchase Payment, Sales Payment), Reports (about 30).

Legend: **Built** = we have it. **Partly** = we have a piece. **Not yet** = small-clinic item we will build/propose.
**Not needed** = hospital-scale, skipped on purpose.

## Billing and sale

| Healthray feature | Our app | Notes |
|---|---|---|
| Sale from prescription, bill + print | Built | Dispense tab |
| Walk-in counter sale, scan to bill | Built | Counter sale tab |
| Batch choice, expiry check at sale | Built | Expired batch is refused; FEFO suggestion |
| Item / bill discount | Built | `pharmacy_discounts` switch |
| Loose (part-pack) sale | Built | `pharmacy_loose_sale` |
| Sales return + credit note | Built | Sales tab |
| Payment modes (cash, UPI, card) | Built | Razorpay/credit/bank: Not needed now |
| Round-off on the bill | Built | Invoice has round-off |
| Hold a bill and resume later | **Not yet** -> build (Counter sale) | |
| Patient deposit / credit account | Not needed | Pay-later bill already exists |
| Package master, online sales order, payer companies (TPA) | Not needed | Hospital / insurance |

## Stock

| Healthray feature | Our app | Notes |
|---|---|---|
| Stock by batch, expiry, MRP | Built | |
| Stock alert / expiry report | Built | Alert tiles + filters in the Stock tab |
| Reorder level per medicine | Built | |
| Reorder / purchase suggestion list | **Partly** -> build | We have levels but no "what to buy" list |
| Non-moving items | **Not yet** -> build | |
| Top selling items | **Not yet** -> build | |
| Stock ledger / daily stock | Built | Ledger tab |
| Stock check (physical count) | Built | |
| Barcode labels | Built | |
| Transfer stock, department stock, stores | Not needed | Multi-store |
| Loss booking (damage/expiry write-off) | Built | Stock correction with a reason |

## Purchase

| Healthray feature | Our app | Notes |
|---|---|---|
| Purchase entry, suppliers | Built | |
| Purchase return / credit note | Built | Return to supplier |
| Purchase order, order processing | Not needed (for now) | The reorder list covers a small clinic |
| Supplier due / purchase payment | **Not yet** - needs new database fields | Proposed, asking the owner first |
| Pharmacy expense | Not needed | |

## Reports and alerts

| Healthray report | Our app | Notes |
|---|---|---|
| Daily report / collection report | **Partly** -> build | Clinic-wide collection exists; no pharmacy-only daily report |
| GST report | Built (whole clinic, Reports screen) | Pharmacy-only GST summary: **build** (small) |
| Sales-purchase report | **Not yet** -> build | In the pharmacy daily report |
| Margin / profit report | **Not yet** -> build | From purchase price and sale price |
| Discount report | Partly | Shown in the daily report totals |
| Stock alert / expiry report | Built | |
| Item-wise report | **Not yet** -> build | In "Top selling" |
| Patient ledger / due, supplier ledger | Not needed / later | |
| Tally, consolidated, operator-wise, activity | Not needed | Audit log covers activity |

## Build order (most useful first)

1. Reorder (purchase suggestion) list — per medicine: stock, level, suggested quantity, usual supplier.
2. Pharmacy daily report — sales, returns, collection per payment mode, purchases, discounts for a date range.
3. Top-selling and non-moving medicines.
4. Margin report (sale value minus purchase cost).
5. Pharmacy GST summary.
6. Hold / resume a counter-sale bill.
7. Proposed, not built (needs database change, owner to decide): supplier dues and purchase payments.

All new items are optional per-organization switches in *Additional settings* (`pharmacy_reports`, `pharmacy_hold_bills`).
