// Small helpers for writing prescriptions quickly.

/** The quick choices for medicine days and follow-up days. */
export const DAY_CHOICES = [3, 5, 7, 15, 30, 60, 90, 180];

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

// Units that can be counted or measured, with their plural for the quantity text
const COUNTABLE: Record<string, string> = {
  tablet: 'tablets', capsule: 'capsules', vial: 'vials', ampoule: 'ampoules', sachet: 'sachets', drops: 'drops',
  ml: 'ml', g: 'g', teaspoon: 'teaspoons', tablespoon: 'tablespoons',
};

/**
 * Total quantity for the whole course, e.g. dose 2 tablet, 2-2-2, 30 days -> "180 tablets".
 * Only when dose, frequency, days and a countable unit are known; otherwise "" (the doctor types it).
 */
export function autoQuantity(line: { dose: string; dose_unit: string; frequency: string; duration: number | null; duration_unit: string }): string {
  const dose = amount(line.dose || '');
  const perDay = dosesPerDay(line.frequency || '');
  const unit = COUNTABLE[(line.dose_unit || '').toLowerCase()];
  if (dose === null || perDay === null || !unit || !line.duration) return '';
  const days = line.duration * (line.duration_unit === 'weeks' ? 7 : line.duration_unit === 'months' ? 30 : 1);
  const total = Math.ceil(dose * perDay * days * 100) / 100;
  if (!total) return '';
  return `${total} ${total === 1 ? line.dose_unit.toLowerCase() : unit}`;
}
