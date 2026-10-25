// Small helpers for writing prescriptions quickly.

/** The quick choices for medicine days and follow-up days. */
export const DAY_CHOICES = [3, 5, 7, 15, 30, 60, 90, 120, 150, 180];

/**
 * Quick dosage: three digits become morning-noon-night.
 * "222" -> "2-2-2", "101" -> "1-0-1", "010" -> "0-1-0". Anything else is kept as typed (e.g. "1/2-0-1/2").
 */
export function quickDosage(value: string): string {
  const v = value.trim();
  return /^\d{3}$/.test(v) ? v.split('').join('-') : value;
}

/** "1/2", "½", "2", "2.5" -> number; ranges like "3-5" or words -> null. */
function amount(text: string): number | null {
  const v = text.trim().replace('½', '1/2');
  if (/^\d+(\.\d+)?$/.test(v)) return Number(v);
  const frac = /^(\d+)\/(\d+)$/.exec(v);
  return frac ? Number(frac[1]) / Number(frac[2]) : null;
}

/** "1-0-1" -> 2 doses a day; null if it is not a morning-noon-night pattern. */
export function dosesPerDay(frequency: string): number | null {
  const parts = frequency.split('-');
  if (parts.length < 2 || parts.length > 4) return null;
  let sum = 0;
  for (const p of parts) {
    const n = amount(p);
    if (n === null) return null;
    sum += n;
  }
  return sum;
}

// Units that can be counted or measured. kind: count (tablets...), mass (grams), volume (ml). factor = how many base units
// (1 piece / 1 g / 1 ml) one of this unit is. Same words as the dose units (Settings -> Dropdown values) and pack sizes.
type UnitKind = 'count' | 'mass' | 'volume';
const UNITS: Record<string, { kind: UnitKind; factor: number; plural: string }> = {
  tablet: { kind: 'count', factor: 1, plural: 'tablets' }, tablets: { kind: 'count', factor: 1, plural: 'tablets' }, tab: { kind: 'count', factor: 1, plural: 'tablets' },
  capsule: { kind: 'count', factor: 1, plural: 'capsules' }, capsules: { kind: 'count', factor: 1, plural: 'capsules' }, cap: { kind: 'count', factor: 1, plural: 'capsules' },
  pill: { kind: 'count', factor: 1, plural: 'pills' }, pills: { kind: 'count', factor: 1, plural: 'pills' }, globules: { kind: 'count', factor: 1, plural: 'pills' },
  vial: { kind: 'count', factor: 1, plural: 'vials' }, vials: { kind: 'count', factor: 1, plural: 'vials' },
  ampoule: { kind: 'count', factor: 1, plural: 'ampoules' }, ampoules: { kind: 'count', factor: 1, plural: 'ampoules' },
  sachet: { kind: 'count', factor: 1, plural: 'sachets' }, sachets: { kind: 'count', factor: 1, plural: 'sachets' },
  g: { kind: 'mass', factor: 1, plural: 'g' }, gm: { kind: 'mass', factor: 1, plural: 'g' }, gram: { kind: 'mass', factor: 1, plural: 'g' }, grams: { kind: 'mass', factor: 1, plural: 'g' },
  mg: { kind: 'mass', factor: 0.001, plural: 'mg' }, kg: { kind: 'mass', factor: 1000, plural: 'kg' },
  ml: { kind: 'volume', factor: 1, plural: 'ml' }, l: { kind: 'volume', factor: 1000, plural: 'l' }, litre: { kind: 'volume', factor: 1000, plural: 'l' },
  drops: { kind: 'volume', factor: 0.05, plural: 'drops' }, drop: { kind: 'volume', factor: 0.05, plural: 'drops' },
  teaspoon: { kind: 'volume', factor: 5, plural: 'teaspoons' }, tsp: { kind: 'volume', factor: 5, plural: 'teaspoons' },
  tablespoon: { kind: 'volume', factor: 15, plural: 'tablespoons' }, tbsp: { kind: 'volume', factor: 15, plural: 'tablespoons' },
};
// A spoon of powder (churna) is weighed, not poured: about 3 g a teaspoon and 10 g a tablespoon
const POWDER_SPOON: Record<string, number> = { teaspoon: 3, tsp: 3, tablespoon: 10, tbsp: 10 };

/** "pills (globules)" -> "pills", "Teaspoon" -> "teaspoon" */
function unitKey(label: string): string {
  return (label || '').toLowerCase().replace(/\(.*\)/, '').trim().split(/\s+/)[0] ?? '';
}

/** What is in one pack, from the medicine: how many (or how much) and of what. null when it is not known. */
export interface PackInfo { pack_size?: string; units_per_pack?: string | number | null; pack_label?: string }
function packContent(pack: PackInfo | undefined, doseUnit: string): { amount: number; kind: UnitKind; unit: string } | null {
  if (!pack) return null;
  const size = /^\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)/.exec(pack.pack_size || '');
  if (size) {
    const unit = UNITS[size[2]!.toLowerCase()];
    if (unit) return { amount: Number(size[1]) * unit.factor, kind: unit.kind, unit: unit.plural };
  }
  const per = Number(pack.units_per_pack);
  if (per > 0 && UNITS[unitKey(doseUnit)]?.kind === 'count') return { amount: per, kind: 'count', unit: UNITS[unitKey(doseUnit)]!.plural };
  return null;
}

/** "bottle" -> "bottles" (the medicine's pack type, else "packs") */
function packWord(count: number, label?: string): string {
  const word = (label || 'pack').toLowerCase();
  if (count === 1) return word;
  return /(s|x|ch|sh)$/.test(word) ? `${word}es` : /[^aeiou]y$/.test(word) ? `${word.slice(0, -1)}ies` : `${word}s`;
}

export interface CoursePlan {
  /** the whole course in the dose's own unit, e.g. 360 tablets */
  total: number;
  unit: string;
  /** whole packs to give (rounded up) and what one pack holds, when the medicine's pack size is known and fits the dose unit */
  packs: number | null;
  packText: string;
  perDay: number;
  days: number;
  doses: number;
}

/**
 * The whole course worked out: dose x times a day x days = total (e.g. 4 pills x 1 x 90 = 360 pills), and, when the
 * medicine comes in ready packs of 20 / 30 / 60, how many whole packs that is. null when something is missing.
 */
export function coursePlan(line: { dose: string; dose_unit: string; frequency: string; duration: number | null; duration_unit: string } & PackInfo): CoursePlan | null {
  const dose = amount(line.dose || '');
  const perDay = dosesPerDay(line.frequency || '');
  const unit = UNITS[unitKey(line.dose_unit)];
  if (dose === null || perDay === null || !unit || !line.duration) return null;
  const days = line.duration * (line.duration_unit === 'weeks' ? 7 : line.duration_unit === 'months' ? 30 : 1);
  const total = Math.ceil(dose * perDay * days * 100) / 100;
  if (!total) return null;
  const plan: CoursePlan = { total, unit: unit.plural, packs: null, packText: '', perDay, days, doses: dose };
  const content = packContent(line, line.dose_unit);
  if (content) {
    // the dose in the pack's kind of unit (a spoon of powder is grams, a spoon of liquid is ml)
    let factor = unit.factor;
    if (content.kind === 'mass' && unit.kind === 'volume' && POWDER_SPOON[unitKey(line.dose_unit)]) factor = POWDER_SPOON[unitKey(line.dose_unit)]!;
    else if (content.kind !== unit.kind) return plan;
    const need = total * factor;
    plan.packs = Math.max(1, Math.ceil(need / content.amount - 1e-9));
    plan.packText = `${Math.round(content.amount * 100) / 100 === content.amount ? content.amount : Math.round(content.amount * 100) / 100} ${content.unit}`;
  }
  return plan;
}

/**
 * Quantity text for the whole course, e.g. "6 bottles (360 tablets)" when the pack size is known, else "360 tablets".
 * Only when dose, frequency, days and a countable unit are known; otherwise "" (the doctor types it).
 */
export function autoQuantity(line: { dose: string; dose_unit: string; frequency: string; duration: number | null; duration_unit: string } & PackInfo): string {
  const plan = coursePlan(line);
  if (!plan) return '';
  const totalText = `${plan.total} ${plan.total === 1 ? (line.dose_unit || '').toLowerCase().replace(/\(.*\)/, '').trim() || plan.unit : plan.unit}`;
  return plan.packs ? `${plan.packs} ${packWord(plan.packs, line.pack_label)} (${totalText})` : totalText;
}

/**
 * Is a dosage pattern such as "1-0-1" believable? Returns 'format' when it is not a morning-noon-night pattern
 * (e.g. "2222"), 'high' when one time is more than 10 (e.g. "2-2-22" from a typing slip), else null (fine).
 * Free words (e.g. "SOS", "as needed") and empty values are never flagged.
 */
export function dosageProblem(frequency: string): 'format' | 'high' | null {
  const v = (frequency || '').trim();
  if (!v || /[a-z]/i.test(v)) return null;
  if (/^\d{4,}$/.test(v)) return 'format';
  const parts = v.split('-');
  if (parts.length < 2 || parts.length > 4) return 'format';
  let high = false;
  for (const p of parts) {
    const n = amount(p);
    if (n === null) return 'format';
    if (n > 10) high = true;
  }
  return high ? 'high' : null;
}
