// Short texts for the patient's history panel on the check-up screen (shown without clicking anything).
import type { Patient, RxLine } from '../../api/types';

/** The written medical history that is filled in: past illnesses, family history, operations, other notes. */
export function medicalHistoryLines(p: Pick<Patient, 'past_history' | 'family_history' | 'surgical_history' | 'other_notes'>): { key: string; text: string }[] {
  const rows: [string, string | undefined][] = [
    ['past', p.past_history], ['family', p.family_history], ['surgical', p.surgical_history], ['notes', p.other_notes],
  ];
  return rows.map(([key, text]) => ({ key, text: (text ?? '').trim() })).filter((r) => r.text);
}

/** "Varunadi Kwatha - 15 ml - 1-0-1 - 15 days" (missing parts are left out). */
export function medicineLine(l: Pick<RxLine, 'medicine_name' | 'dose' | 'dose_unit' | 'frequency' | 'duration' | 'duration_unit'>): string {
  const dose = [l.dose, l.dose_unit].filter(Boolean).join(' ');
  const days = l.duration ? `${l.duration} ${l.duration_unit}` : '';
  return [l.medicine_name, dose, l.frequency, days].filter(Boolean).join(' - ');
}
