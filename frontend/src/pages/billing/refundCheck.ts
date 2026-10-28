// Refund check for cancelling a bill: money should go back the way it came. If the patient paid by UPI and the clinic
// refunds in cash, that is allowed (it happens at a counter), but the day closing then shows UPI received and cash given.
// SAFE TO EDIT: nothing here is meant to be edited by hand.
type Mode = 'cash' | 'upi' | 'card';

export interface Shortfall { received: number; refund: number }

/** null = fine. Otherwise how much came in by this way (after earlier refunds) and how much we are about to give back. */
export function refundShortfall(
  payments: { mode: Mode; amount: string }[],
  creditNotes: { refund_mode: string; refund_amount: string }[],
  mode: Mode,
  refund: number,
): Shortfall | null {
  if (refund <= 0) return null;
  const came = payments.filter((p) => p.mode === mode).reduce((s, p) => s + Number(p.amount), 0);
  const gone = creditNotes.filter((n) => n.refund_mode === mode).reduce((s, n) => s + Number(n.refund_amount), 0);
  const received = Math.max(0, came - gone);
  return refund > received + 0.004 ? { received, refund } : null;
}
