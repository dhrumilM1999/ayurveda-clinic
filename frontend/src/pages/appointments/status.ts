// What the appointment statuses mean on screen. SAFE TO EDIT: the rules below.
// There is no "With doctor" step for the clinic: Booked -> Waiting (checked in) -> Done. Old records that still say
// "in consultation" are shown as Waiting.
import type { AppointmentStatus } from '../../api/types';

export function shownStatus(status: AppointmentStatus): AppointmentStatus {
  return status === 'in_consultation' ? 'checked_in' : status;
}

/** The one main button on a row: Check in (only on the day), then Done. */
export function nextStep(status: AppointmentStatus, isToday: boolean): 'check-in' | 'complete' | null {
  if (status === 'booked') return isToday ? 'check-in' : null;
  if (status === 'checked_in' || status === 'in_consultation') return 'complete';
  return null;
}

/** The doctor can open the check-up of any appointment, on any day (not a cancelled or did-not-come one). */
export function canOpenCheckup(status: AppointmentStatus): boolean {
  return ['booked', 'checked_in', 'in_consultation', 'completed'].includes(status);
}
