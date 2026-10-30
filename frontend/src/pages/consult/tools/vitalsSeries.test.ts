import { describe, expect, it } from 'vitest';
import type { Vital } from '../../../api/types';
import { chartPoints, rangeStart, seriesFor } from './vitalsSeries';

const vital = (recorded_at: string, over: Partial<Vital> = {}): Vital => ({
  id: recorded_at, recorded_at, bp_systolic: null, bp_diastolic: null, pulse: null, temperature_f: null, spo2: null,
  respiratory_rate: null, weight_kg: null, height_cm: null, bmi: null, notes: '', branch_name: '', recorded_by_name: '', ...over,
});

describe('seriesFor', () => {
  const rows = [
    vital('2026-03-01T10:00:00Z', { weight_kg: '72.5', pulse: 80 }),
    vital('2026-01-01T10:00:00Z', { weight_kg: '75.0' }),
    vital('2026-02-01T10:00:00Z', { pulse: 78 }),
  ];
  it('gives the readings of one vital sign, oldest first, and skips visits without it', () => {
    expect(seriesFor(rows, 'weight_kg', 0).map((p) => p.value)).toEqual([75, 72.5]);
    expect(seriesFor(rows, 'pulse', 0).map((p) => p.value)).toEqual([78, 80]);
  });
  it('keeps only the readings from the start of the range', () => {
    expect(seriesFor(rows, 'weight_kg', new Date('2026-02-15T00:00:00Z').getTime()).map((p) => p.value)).toEqual([72.5]);
  });
  it('returns nothing for a vital sign that was never recorded', () => {
    expect(seriesFor(rows, 'spo2', 0)).toEqual([]);
  });
});

describe('rangeStart', () => {
  it('goes back the given months and treats 0 as everything', () => {
    const now = new Date('2026-10-30T12:00:00Z').getTime();
    expect(new Date(rangeStart(3, now)).getMonth()).toBe(6); // July
    expect(rangeStart(0, now)).toBe(0);
  });
});

describe('chartPoints', () => {
  it('keeps every point inside the chart and the highest value on top', () => {
    const pts = chartPoints([{ at: 1, value: 10 }, { at: 2, value: 20 }, { at: 3, value: 15 }], 300, 100, 10);
    expect(pts.every((p) => p.x >= 10 && p.x <= 290 && p.y >= 10 && p.y <= 90)).toBe(true);
    expect(pts[1].y).toBeLessThan(pts[0].y); // 20 is drawn above 10
  });
  it('puts a single reading in the middle and does not divide by zero', () => {
    expect(chartPoints([{ at: 5, value: 70 }], 300, 100)).toEqual([{ x: 150, y: 50 }]);
    const flat = chartPoints([{ at: 1, value: 5 }, { at: 2, value: 5 }], 300, 100);
    expect(flat.every((p) => p.y === 50)).toBe(true);
  });
  it('returns nothing for no readings', () => {
    expect(chartPoints([], 300, 100)).toEqual([]);
  });
});
