import { describe, expect, it } from 'vitest';
import { refundShortfall } from './refundCheck';

const pay = (mode: 'cash' | 'upi' | 'card', amount: string) => ({ mode, amount });

describe('refund way vs the way the patient paid', () => {
  it('no warning when the patient paid in the way chosen', () => {
    expect(refundShortfall([pay('upi', '500')], [], 'upi', 500)).toBeNull();
  });

  it('warns when more is refunded by UPI than came in by UPI', () => {
    expect(refundShortfall([pay('cash', '300'), pay('upi', '200')], [], 'upi', 500)).toEqual({ received: 200, refund: 500 });
  });

  it('warns when nothing at all came in by that way (paid by UPI, refund in cash)', () => {
    expect(refundShortfall([pay('upi', '224')], [], 'cash', 112)).toEqual({ received: 0, refund: 112 });
  });

  it('counts money already refunded in that way earlier', () => {
    expect(refundShortfall([pay('upi', '500')], [{ refund_mode: 'upi', refund_amount: '300' }], 'upi', 300)).toEqual({ received: 200, refund: 300 });
  });

  it('no warning when there is nothing to refund', () => {
    expect(refundShortfall([pay('upi', '500')], [], 'cash', 0)).toBeNull();
  });
});
