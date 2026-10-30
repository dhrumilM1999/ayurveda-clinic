// Size and open/closed state of the handwriting panel (the A4 page on the right side of the check-up screen).
// The doctor drags the edge of the panel to make it wider or narrower; the choice is remembered on this computer, so after
// a page reload the panel is the same size.
// SAFE TO EDIT: PANEL_DEFAULT (starting width in pixels), PANEL_MIN, CENTRE_MIN (the check-up form always keeps this much room).
export const PANEL_MIN = 300;
export const PANEL_DEFAULT = 440;
export const CENTRE_MIN = 420;
export const GAP = 12; // space between the form and the panel (same as the grid gap in styles.css, .workspace)

const KEY = 'hw-panel';

/** The panel width allowed for a workspace this wide: never narrower than PANEL_MIN, never squeezing the form. */
export function clampPanelWidth(width: number, workspaceWidth: number): number {
  const max = Math.max(PANEL_MIN, workspaceWidth - CENTRE_MIN - GAP);
  return Math.round(Math.min(Math.max(width, PANEL_MIN), max));
}

export type PanelState = { open: boolean; width: number };

export function loadPanel(): PanelState {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? 'null');
    const width = typeof raw?.width === 'number' && Number.isFinite(raw.width) ? Math.max(raw.width, PANEL_MIN) : PANEL_DEFAULT;
    return { open: raw?.open !== false, width };
  } catch {
    return { open: true, width: PANEL_DEFAULT };
  }
}

export function savePanel(state: PanelState): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // private window: the choice is simply not remembered
  }
}
