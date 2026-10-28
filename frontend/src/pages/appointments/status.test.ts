import { describe, expect, it } from 'vitest';
import { canOpenCheckup, nextStep, shownStatus } from './status';

describe('appointment status words (there is no "With doctor")', () => {
  it('an old With doctor record is shown as Waiting', () => {
    expect(shownStatus('in_consultation')).toBe('checked_in');
    expect(shownStatus('checked_in')).toBe('checked_in');
    expect(shownStatus('booked')).toBe('booked');
    expect(shownStatus('completed')).toBe('completed');
  });

  it('the main button is Check in (today only), then Done', () => {
    expect(nextStep('booked', true)).toBe('check-in');
    expect(nextStep('booked', false)).toBeNull();
    expect(nextStep('checked_in', true)).toBe('complete');
    expect(nextStep('in_consultation', true)).toBe('complete');
    expect(nextStep('completed', true)).toBeNull();
    expect(nextStep('cancelled', true)).toBeNull();
    expect(nextStep('no_show', true)).toBeNull();
  });

  it('the check-up can be opened any day, except for a cancelled or did-not-come appointment', () => {
    for (const s of ['booked', 'checked_in', 'in_consultation', 'completed'] as const) expect(canOpenCheckup(s)).toBe(true);
    expect(canOpenCheckup('cancelled')).toBe(false);
    expect(canOpenCheckup('no_show')).toBe(false);
  });
});
