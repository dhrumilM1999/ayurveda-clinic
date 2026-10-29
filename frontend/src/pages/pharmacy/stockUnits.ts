// How stock is written on screen. Stock is counted in packs inside the system, but a medicine that is sold loose
// (for example a jar of 1000 tablets) is shown in tablets: after giving 25 it reads "975 tablets", not 0.975.
// SAFE TO EDIT: the word used when a medicine has no unit ("units").
export function stockLabel(packs: string | number | null | undefined, units: string | null | undefined, unit: string | null | undefined): string {
  if (units !== null && units !== undefined && units !== '') return `${Number(units)} ${unit || 'units'}`;
  if (packs === null || packs === undefined || packs === '') return '—';
  return String(Number(packs));
}
