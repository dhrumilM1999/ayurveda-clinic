// When the OPD bill window asks "Please confirm" before saving. SAFE TO EDIT: the rule below.
// The common case (the plain consultation fee, collected in full) is ONE click. Anything unusual still asks.

interface DraftLike { kind: 'consultation' | 'service' | 'other'; quantity: number; price: number; discount: number }

export function needsConfirm({ drafts, suggestedFee, payment, dueAfter }: {
  drafts: DraftLike[];
  suggestedFee: number | null;
  payment: { amount: number } | null;
  dueAfter: number;
}): boolean {
  if (drafts.length === 0) return !(payment && payment.amount === dueAfter); // only taking money for an existing bill
  const plainFee = drafts.length === 1 && drafts[0]!.kind === 'consultation' && drafts[0]!.quantity === 1
    && drafts[0]!.discount === 0 && suggestedFee !== null && drafts[0]!.price === suggestedFee;
  if (!plainFee) return true;
  return payment !== null && payment.amount !== dueAfter; // a part payment still asks; pay later / full does not
}
