import { describe, expect, it } from 'vitest';
import { medicineLine, medicalHistoryLines } from './historySummary';

describe('patient history shown straight away on the check-up screen', () => {
  it('lists only the history that is filled in, in a fixed order', () => {
    const lines = medicalHistoryLines({ past_history: ' Kidney stone 2 years ago ', family_history: '', surgical_history: 'Appendix 2015', other_notes: undefined });
    expect(lines).toEqual([
      { key: 'past', text: 'Kidney stone 2 years ago' },
      { key: 'surgical', text: 'Appendix 2015' },
    ]);
  });

  it('is empty when the patient has no history written', () => {
    expect(medicalHistoryLines({})).toEqual([]);
  });

  it('one medicine of the last prescription in a short line', () => {
    expect(medicineLine({ medicine_name: 'Varunadi Kwatha', dose: '15', dose_unit: 'ml', frequency: '1-0-1', duration: 15, duration_unit: 'days' }))
      .toBe('Varunadi Kwatha - 15 ml - 1-0-1 - 15 days');
  });

  it('leaves out what is missing', () => {
    expect(medicineLine({ medicine_name: 'Triphala Churna', dose: '', dose_unit: '', frequency: '', duration: null, duration_unit: 'days' }))
      .toBe('Triphala Churna');
    expect(medicineLine({ medicine_name: 'Chyawanprash', dose: '1', dose_unit: 'teaspoon', frequency: '1-0-0', duration: 2, duration_unit: 'weeks' }))
      .toBe('Chyawanprash - 1 teaspoon - 1-0-0 - 2 weeks');
  });
});
