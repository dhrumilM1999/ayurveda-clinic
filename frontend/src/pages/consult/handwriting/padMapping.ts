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
