import { describe, expect, it } from 'vitest';
import { SHORTCUT_HELP, shortcutFor, type KeyLike } from './shortcuts';

const key = (k: string, extra: Partial<KeyLike> = {}): KeyLike => ({ key: k, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...extra });

describe('check-up keyboard shortcuts', () => {
  it('Ctrl+S (and Cmd+S) saves, even while typing in a box', () => {
    expect(shortcutFor(key('s', { ctrlKey: true }), { typing: true })).toEqual({ type: 'save' });
    expect(shortcutFor(key('S', { metaKey: true }), { typing: true })).toEqual({ type: 'save' });
  });

  it('Alt+1 to Alt+9 and Alt+0 jump to the 1st to 10th section', () => {
    expect(shortcutFor(key('1', { altKey: true }), { typing: false })).toEqual({ type: 'section', index: 0 });
    expect(shortcutFor(key('9', { altKey: true }), { typing: true })).toEqual({ type: 'section', index: 8 });
    expect(shortcutFor(key('0', { altKey: true }), { typing: false })).toEqual({ type: 'section', index: 9 });
  });

  it('Ctrl+Enter completes the visit, Alt+N is the next patient, Alt+P prints, Alt+M finds a medicine', () => {
    expect(shortcutFor(key('Enter', { ctrlKey: true }), { typing: true })).toEqual({ type: 'complete' });
    expect(shortcutFor(key('n', { altKey: true }), { typing: false })).toEqual({ type: 'nextPatient' });
    expect(shortcutFor(key('p', { altKey: true }), { typing: false })).toEqual({ type: 'print' });
    expect(shortcutFor(key('m', { altKey: true }), { typing: true })).toEqual({ type: 'medicine' });
  });

  it('"/" focuses the patient search and "?" shows the help, but only when not typing', () => {
    expect(shortcutFor(key('/'), { typing: false })).toEqual({ type: 'focusSearch' });
    expect(shortcutFor(key('?', { shiftKey: true }), { typing: false })).toEqual({ type: 'help' });
    expect(shortcutFor(key('/'), { typing: true })).toBeNull();
    expect(shortcutFor(key('?', { shiftKey: true }), { typing: true })).toBeNull();
  });

  it('ordinary typing and unknown combinations do nothing', () => {
    expect(shortcutFor(key('a'), { typing: false })).toBeNull();
    expect(shortcutFor(key('1'), { typing: false })).toBeNull(); // a plain 1 is just a 1
    expect(shortcutFor(key('s'), { typing: false })).toBeNull(); // no Ctrl
    expect(shortcutFor(key('z', { altKey: true }), { typing: false })).toBeNull();
    expect(shortcutFor(key('Enter'), { typing: true })).toBeNull();
  });

  it('Alt+Ctrl combinations are left to the browser / system', () => {
    expect(shortcutFor(key('1', { altKey: true, ctrlKey: true }), { typing: false })).toBeNull();
  });

  it('the help list names every shortcut once', () => {
    const keys = SHORTCUT_HELP.map((h) => h.keys);
    expect(new Set(keys).size).toBe(keys.length);
    expect(keys).toContain('Ctrl + S');
    expect(keys).toContain('Alt + 1 … 9');
  });
});
