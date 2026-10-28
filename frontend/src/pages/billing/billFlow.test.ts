import { describe, expect, it } from 'vitest';
import { needsConfirm } from './billFlow';

const fee = { kind: 'consultation' as const, quantity: 1, price: 500, discount: 0 };

describe('when the OPD bill asks "Please confirm"', () => {
  it('not for the plain consultation fee collected in full (the common case: one click)', () => {
    expect(needsConfirm({ drafts: [fee], suggestedFee: 500, payment: { amount: 500 }, dueAfter: 500 })).toBe(false);
  });

  it('not when the fee is left to pay later', () => {
    expect(needsConfirm({ drafts: [fee], suggestedFee: 500, payment: null, dueAfter: 500 })).toBe(false);
  });

  it('yes when the price was changed, a discount given or the quantity changed', () => {
    expect(needsConfirm({ drafts: [{ ...fee, price: 300 }], suggestedFee: 500, payment: { amount: 300 }, dueAfter: 300 })).toBe(true);
    expect(needsConfirm({ drafts: [{ ...fee, discount: 10 }], suggestedFee: 500, payment: { amount: 450 }, dueAfter: 450 })).toBe(true);
    expect(needsConfirm({ drafts: [{ ...fee, quantity: 2 }], suggestedFee: 500, payment: { amount: 1000 }, dueAfter: 1000 })).toBe(true);
  });

  it('yes when something else is added to the bill', () => {
    const service = { kind: 'service' as const, quantity: 1, price: 200, discount: 0 };
    expect(needsConfirm({ drafts: [fee, service], suggestedFee: 500, payment: { amount: 700 }, dueAfter: 700 })).toBe(true);
  });

  it('yes when only a part is collected', () => {
    expect(needsConfirm({ drafts: [fee], suggestedFee: 500, payment: { amount: 200 }, dueAfter: 500 })).toBe(true);
  });

  it('taking the rest of an existing bill in full needs no confirm, a part does', () => {
    expect(needsConfirm({ drafts: [], suggestedFee: 500, payment: { amount: 300 }, dueAfter: 300 })).toBe(false);
    expect(needsConfirm({ drafts: [], suggestedFee: 500, payment: { amount: 100 }, dueAfter: 300 })).toBe(true);
    expect(needsConfirm({ drafts: [], suggestedFee: 500, payment: null, dueAfter: 300 })).toBe(true);
  });
});
