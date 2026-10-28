import { describe, expect, it } from 'vitest';
import { followUpInfo } from './followUp';

describe('follow-up date highlight', () => {
  it('nothing to show without a date', () => {
    expect(followUpInfo(null, '2026-10-28')).toBeNull();
    expect(followUpInfo('', '2026-10-28')).toBeNull();
  });

  it('counts the days from today', () => {
    expect(followUpInfo('2026-11-11', '2026-10-28')).toEqual({ days: 14, tone: 'later' });
  });

  it('today and the next 3 days are "soon" so they stand out more', () => {
    expect(followUpInfo('2026-10-28', '2026-10-28')).toEqual({ days: 0, tone: 'today' });
    expect(followUpInfo('2026-10-29', '2026-10-28')).toEqual({ days: 1, tone: 'soon' });
    expect(followUpInfo('2026-10-31', '2026-10-28')).toEqual({ days: 3, tone: 'soon' });
    expect(followUpInfo('2026-11-01', '2026-10-28')).toEqual({ days: 4, tone: 'later' });
  });

  it('a date that has passed is marked as past', () => {
    expect(followUpInfo('2026-10-20', '2026-10-28')).toEqual({ days: -8, tone: 'past' });
  });

  it('works across a month and a year end', () => {
    expect(followUpInfo('2027-01-02', '2026-12-30')).toEqual({ days: 3, tone: 'soon' });
  });
});
