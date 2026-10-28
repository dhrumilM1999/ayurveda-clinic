// The follow-up (next visit) date: how far away it is and how loudly to show it. SAFE TO EDIT: SOON_DAYS.
import dayjs from 'dayjs';

export type FollowUpTone = 'today' | 'soon' | 'later' | 'past';
export interface FollowUp { days: number; tone: FollowUpTone }

/** A follow-up within this many days is shown stronger. */
export const SOON_DAYS = 3;

/** Both dates as 'YYYY-MM-DD'. null = no follow-up date. */
export function followUpInfo(date: string | null | undefined, today: string): FollowUp | null {
  if (!date) return null;
  const days = dayjs(date).startOf('day').diff(dayjs(today).startOf('day'), 'day');
  if (days < 0) return { days, tone: 'past' };
  if (days === 0) return { days, tone: 'today' };
  return { days, tone: days <= SOON_DAYS ? 'soon' : 'later' };
}
