// The iScribe pad (in Mouse mode) moves the cursor over the WHOLE screen: pen at the pad's bottom-right corner =
// cursor at the screen's bottom-right corner. So in "Pad mode" the writing is read from the whole screen, not from
// the small writing box: position on the pad = position on the page.
// SAFE TO EDIT: nothing here is meant to be edited.
export type UnitPoint = { x: number; y: number };

/** Cursor position on the screen -> position on the page, 0 (left/top) to 1 (right/bottom). */
export function viewportPoint(clientX: number, clientY: number, viewWidth: number, viewHeight: number): UnitPoint {
  const unit = (value: number, size: number) => (size > 0 ? Math.min(Math.max(value / size, 0), 1) : 0);
  return { x: unit(clientX, viewWidth), y: unit(clientY, viewHeight) };
}

/** True when the pen went down on a button or toolbar, so it must press the button and not start a stroke. */
export function isToolbarTarget(target: EventTarget | null): boolean {
  return target instanceof Element && target.closest('[data-hw-ui], .ant-modal-close') !== null;
}

// --- Where the pad is on the screen (absolute screen position, so full screen is not needed) ---
export type PadBounds = { left: number; top: number; right: number; bottom: number };

/** Normally the pad covers the whole screen. */
export function wholeScreen(screenWidth: number, screenHeight: number): PadBounds {
  return { left: 0, top: 0, right: screenWidth, bottom: screenHeight };
}

// Some pads report their position turned by a quarter: the iScribe pad held upright (clip at the top) moves the cursor as if it
// were lying sideways. Rotation 0 = as is, 1 = turned a quarter (the iScribe pad), 2 = upside down, 3 = the other quarter.
export type Rotation = 0 | 1 | 2 | 3;

/** A position on the screen area (0 to 1 each way) -> the position on the page, after turning the pad back upright. */
export function rotateUnit(point: UnitPoint, rotation: Rotation): UnitPoint {
  const { x, y } = point;
  if (rotation === 1) return { x: 1 - y, y: x };
  if (rotation === 2) return { x: 1 - x, y: 1 - y };
  if (rotation === 3) return { x: y, y: 1 - x };
  return { x, y };
}

/** Cursor position on the SCREEN (event.screenX / screenY) -> position on the page, 0 to 1. */
export function screenPoint(screenX: number, screenY: number, bounds: PadBounds, rotation: Rotation = 0): UnitPoint {
  return rotateUnit(viewportPoint(screenX - bounds.left, screenY - bounds.top, bounds.right - bounds.left, bounds.bottom - bounds.top), rotation);
}

/**
 * The doctor touched the pad's TOP-LEFT corner (as the pad is held) and then its BOTTOM-RIGHT corner. Where those two touches
 * land on the screen tells how the pad is turned.
 */
export function rotationFromCorners(topLeft: UnitPoint, bottomRight: UnitPoint): Rotation {
  const right = bottomRight.x >= topLeft.x;
  const down = bottomRight.y >= topLeft.y;
  if (right && down) return 0;
  if (right && !down) return 1;
  if (!right && !down) return 2;
  return 3;
}

/** The two corners the doctor touched (any order) -> the pad area. Null when the two touches are too close. */
export function boundsFromCorners(a: UnitPoint, b: UnitPoint, minSize = 200): PadBounds | null {
  const bounds = { left: Math.min(a.x, b.x), top: Math.min(a.y, b.y), right: Math.max(a.x, b.x), bottom: Math.max(a.y, b.y) };
  return bounds.right - bounds.left >= minSize && bounds.bottom - bounds.top >= minSize ? bounds : null;
}

const KEY = 'hw-pad-bounds';
const ROTATION_KEY = 'hw-pad-rotation';
/** The iScribe pad needs a quarter turn (checked with the real pad), so this is where a new computer starts. */
export const DEFAULT_ROTATION: Rotation = 1;

export function loadRotation(): Rotation {
  try {
    const value = Number(localStorage.getItem(ROTATION_KEY));
    return localStorage.getItem(ROTATION_KEY) !== null && [0, 1, 2, 3].includes(value) ? (value as Rotation) : DEFAULT_ROTATION;
  } catch {
    return DEFAULT_ROTATION;
  }
}

export function saveRotation(rotation: Rotation): void {
  try {
    localStorage.setItem(ROTATION_KEY, String(rotation));
  } catch {
    // private window: the choice is simply not remembered
  }
}

export function loadBounds(): PadBounds | null {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? 'null');
    const ok = raw && ['left', 'top', 'right', 'bottom'].every((k) => typeof raw[k] === 'number') && raw.right > raw.left && raw.bottom > raw.top;
    return ok ? (raw as PadBounds) : null;
  } catch {
    return null;
  }
}

export function saveBounds(bounds: PadBounds | null): void {
  try {
    if (bounds) localStorage.setItem(KEY, JSON.stringify(bounds));
    else localStorage.removeItem(KEY);
  } catch {
    // private window: the choice is simply not remembered
  }
}
