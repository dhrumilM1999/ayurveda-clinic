import { describe, expect, it } from 'vitest';
import { listShortcutFor, LIST_SHORTCUT_HELP } from './shortcuts';

const key = (k: string, extra = {}) => ({ key: k, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...extra });

describe('appointments list shortcuts', () => {
  it('single keys act only when you are not typing in a box', () => {
    expect(listShortcutFor(key('n'), { typing: false })).toBe('book');
    expect(listShortcutFor(key('w'), { typing: false })).toBe('walkIn');
    expect(listShortcutFor(key('t'), { typing: false })).toBe('today');
    expect(listShortcutFor(key('['), { typing: false })).toBe('prevDay');
    expect(listShortcutFor(key(']'), { typing: false })).toBe('nextDay');
    expect(listShortcutFor(key('/'), { typing: false })).toBe('search');
    expect(listShortcutFor(key('?', { shiftKey: true }), { typing: false })).toBe('help');
    for (const k of ['n', 'w', 't', '[', ']', '/', '?']) expect(listShortcutFor(key(k), { typing: true })).toBeNull();
  });

  it('is not case sensitive (Caps Lock) and ignores Ctrl / Alt combinations', () => {
    expect(listShortcutFor(key('N'), { typing: false })).toBe('book');
    expect(listShortcutFor(key('n', { ctrlKey: true }), { typing: false })).toBeNull(); // Ctrl+N opens a browser window
    expect(listShortcutFor(key('w', { ctrlKey: true }), { typing: false })).toBeNull(); // Ctrl+W closes the tab
    expect(listShortcutFor(key('t', { altKey: true }), { typing: false })).toBeNull();
    expect(listShortcutFor(key('t', { metaKey: true }), { typing: false })).toBeNull();
  });

  it('other keys do nothing', () => {
    expect(listShortcutFor(key('x'), { typing: false })).toBeNull();
    expect(listShortcutFor(key('Enter'), { typing: false })).toBeNull();
  });

  it('every shortcut in the help list is a real action', () => {
    const keys = LIST_SHORTCUT_HELP.map((h) => h.keys);
    expect(new Set(keys).size).toBe(keys.length);
    for (const h of LIST_SHORTCUT_HELP) expect(listShortcutFor(key(h.keys === '?' ? '?' : h.keys), { typing: false })).not.toBeNull();
  });
});
