// Keyboard shortcuts of the Appointments list (single keys, only when you are not typing in a box).
// SAFE TO EDIT: the keys. The words are in src/i18n/*.json under "shortcuts".
import type { KeyLike } from '../consult/shortcuts';

export type ListAction = 'book' | 'walkIn' | 'today' | 'prevDay' | 'nextDay' | 'search' | 'help';

const KEYS: Record<string, ListAction> = { n: 'book', w: 'walkIn', t: 'today', '[': 'prevDay', ']': 'nextDay', '/': 'search', '?': 'help' };

export function listShortcutFor(e: KeyLike, ctx: { typing: boolean }): ListAction | null {
  if (ctx.typing || e.ctrlKey || e.metaKey || e.altKey) return null;
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  return KEYS[key] ?? null;
}

/** The cheat sheet shown with "?". `label` is the i18n key under "shortcuts". */
export const LIST_SHORTCUT_HELP: { keys: string; label: string }[] = [
  { keys: 'n', label: 'book' },
  { keys: 'w', label: 'walkIn' },
  { keys: 't', label: 'today' },
  { keys: '[', label: 'prevDay' },
  { keys: ']', label: 'nextDay' },
  { keys: '/', label: 'searchList' },
  { keys: '?', label: 'help' },
];
