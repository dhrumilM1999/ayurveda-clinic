// Numbers for the vitals graph (Graph button on the check-up screen): which vital signs can be drawn, how far back, and
// where each point sits inside its small chart. Plain functions so they can be tested.
// SAFE TO EDIT: VITAL_KEYS (the vital signs shown in the list) and RANGES (the quick buttons).
import type { Vital } from '../../../api/types';

export type VitalKey = 'weight_kg' | 'pulse' | 'temperature_f' | 'bp_systolic' | 'bp_diastolic' | 'spo2' | 'respiratory_rate' | 'bmi';

export const VITAL_KEYS: { key: VitalKey; unit: string }[] = [
  { key: 'weight_kg', unit: 'kg' },
  { key: 'pulse', unit: '/min' },
  { key: 'temperature_f', unit: '°F' },
  { key: 'bp_systolic', unit: 'mmHg' },
  { key: 'bp_diastolic', unit: 'mmHg' },
  { key: 'spo2', unit: '%' },
  { key: 'respiratory_rate', unit: '/min' },
  { key: 'bmi', unit: '' },
];

/** Quick range buttons: how many months back (0 = everything). */
export const RANGES: { id: string; months: number }[] = [
  { id: '1m', months: 1 }, { id: '3m', months: 3 }, { id: '6m', months: 6 }, { id: '1y', months: 12 }, { id: '3y', months: 36 }, { id: 'all', months: 0 },
];

export type SeriesPoint = { at: number; value: number };

/** The readings of one vital sign, oldest first, from `fromMs` on (0 = from the beginning). Empty readings are left out. */
export function seriesFor(rows: Vital[], key: VitalKey, fromMs: number): SeriesPoint[] {
  return rows
    .map((r) => ({ at: new Date(r.recorded_at).getTime(), raw: r[key] }))
    .filter((p) => p.raw !== null && p.raw !== undefined && p.raw !== '' && Number.isFinite(Number(p.raw)) && p.at >= fromMs)
    .map((p) => ({ at: p.at, value: Number(p.raw) }))
    .sort((a, b) => a.at - b.at);
}

/** Milliseconds of the start of a range ("3 months back from now"); 0 for "all". */
export function rangeStart(months: number, nowMs: number): number {
  if (!months) return 0;
  const d = new Date(nowMs);
  d.setMonth(d.getMonth() - months);
  return d.getTime();
}

/** Where to draw each point in a chart of width x height with a little padding. The line never leaves the chart. */
export function chartPoints(points: SeriesPoint[], width: number, height: number, pad = 12): { x: number; y: number }[] {
  if (!points.length) return [];
  const times = points.map((p) => p.at);
  const values = points.map((p) => p.value);
  const [t0, t1] = [Math.min(...times), Math.max(...times)];
  const [v0, v1] = [Math.min(...values), Math.max(...values)];
  const spanT = t1 - t0 || 1;
  const spanV = v1 - v0 || 1;
  return points.map((p) => ({
    x: points.length === 1 ? width / 2 : pad + ((p.at - t0) / spanT) * (width - 2 * pad),
    y: points.length === 1 || v1 === v0 ? height / 2 : height - pad - ((p.value - v0) / spanV) * (height - 2 * pad),
  }));
}
