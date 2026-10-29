import { describe, expect, it } from 'vitest';
import { stockLabel } from './stockUnits';

describe('how much stock is shown', () => {
  it('a medicine sold loose shows tablets, not a fraction of a pack', () => {
    expect(stockLabel('0.975', '975', 'tablets')).toBe('975 tablets');
  });

  it('uses "units" when the medicine has no unit word', () => {
    expect(stockLabel('0.5', '30', '')).toBe('30 units');
  });

  it('a medicine counted in packs keeps the number of packs', () => {
    expect(stockLabel('12.000', null, '')).toBe('12');
    expect(stockLabel('2.5', undefined, 'tablets')).toBe('2.5');
  });

  it('no value at all gives a dash', () => {
    expect(stockLabel(null, null, '')).toBe('—');
  });
});
