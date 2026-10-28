// Keyboard shortcuts of the check-up screen. SAFE TO EDIT: the keys below and the help list (the words are in
// src/i18n/*.json under "shortcuts"). The screen only asks shortcutFor(); nothing else knows the keys.

export interface KeyLike {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
}

export type ShortcutAction =
  | { type: 'save' }
  | { type: 'section'; index: number }
  | { type: 'complete' }
  | { type: 'nextPatient' }
  | { type: 'print' }
  | { type: 'medicine' }
  | { type: 'focusSearch' }
  | { type: 'help' };

/** What a key press means on the check-up screen (null = nothing, let the browser / the box have it). */
export function shortcutFor(e: KeyLike, ctx: { typing: boolean }): ShortcutAction | null {
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  const command = e.ctrlKey || e.metaKey;

  if (command && !e.altKey) {
    if (key === 's') return { type: 'save' };
    if (key === 'Enter') return { type: 'complete' };
    return null;
  }
  if (e.altKey && !command) {
    if (/^[0-9]$/.test(key)) return { type: 'section', index: key === '0' ? 9 : Number(key) - 1 };
    if (key === 'n') return { type: 'nextPatient' };
    if (key === 'p') return { type: 'print' };
    if (key === 'm') return { type: 'medicine' };
    return null;
  }
  if (!e.altKey && !command && !ctx.typing) {
    if (key === '/') return { type: 'focusSearch' };
    if (key === '?') return { type: 'help' };
  }
  return null;
}

/** The cheat sheet shown with "?". `label` is the i18n key under "shortcuts". */
export const SHORTCUT_HELP: { keys: string; label: string }[] = [
  { keys: 'Ctrl + S', label: 'save' },
  { keys: 'Alt + 1 … 9', label: 'section' },
  { keys: 'Alt + 0', label: 'section10' },
  { keys: 'Alt + M', label: 'medicine' },
  { keys: 'Alt + P', label: 'print' },
  { keys: 'Ctrl + Enter', label: 'complete' },
  { keys: 'Alt + N', label: 'nextPatient' },
  { keys: '/', label: 'focusSearch' },
  { keys: '?', label: 'help' },
];
