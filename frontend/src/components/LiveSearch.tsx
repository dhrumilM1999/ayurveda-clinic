// SAFE TO EDIT: the wait time (delay) and the minimum letters (minChars) used by every search box.
// ONE shared search box + helpers. Results update while the user types (no Enter needed).
//   <LiveSearch placeholder={t('...')} onSearch={setQuery} />       -> for list filters (tables)
//   useLiveLookup(fetcher, { minChars: 2 })                          -> for dropdown pickers (patient, medicine)
// See docs/SMALL_CHANGES.md ("How search works").
import { LoadingOutlined, SearchOutlined } from '@ant-design/icons';
import { Input } from 'antd';
import type { CSSProperties } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';

export const SEARCH_DELAY_MS = 300;

/** Returns `value` only after it stopped changing for `delay` ms. */
export function useDebouncedValue<T>(value: T, delay = SEARCH_DELAY_MS): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

/**
 * Search box for list screens. Calls onSearch(text) ~300 ms after the user stops typing,
 * at once on Enter, and with '' at once when cleared. Waits while a Gujarati/Hindi keyboard
 * (IME) is still composing a letter, so half-finished text is never searched.
 */
export function LiveSearch({ value, onSearch, placeholder, width, style, delay = SEARCH_DELAY_MS, minChars = 1, loading, size, autoFocus }: {
  onSearch: (text: string) => void;
  /** Optional: the parent's current search text. Only needed if the parent can set it too (e.g. after a barcode scan). */
  value?: string;
  placeholder?: string;
  width?: number | string;
  style?: CSSProperties;
  delay?: number;
  /** Shorter text than this shows everything (same as empty). Lists: 1. */
  minChars?: number;
  loading?: boolean;
  size?: 'small' | 'middle' | 'large';
  autoFocus?: boolean;
}) {
  const [text, setText] = useState('');
  const composing = useRef(false);
  const timer = useRef<number>();
  const last = useRef('');
  const callback = useRef(onSearch);
  callback.current = onSearch;

  const fire = useCallback((raw: string) => {
    window.clearTimeout(timer.current);
    const trimmed = raw.trim();
    const value = trimmed.length >= minChars ? trimmed : '';
    if (value === last.current) return;
    last.current = value;
    callback.current(value);
  }, [minChars]);

  const change = (raw: string) => {
    setText(raw);
    window.clearTimeout(timer.current);
    if (composing.current) return; // wait for compositionend
    if (!raw) fire('');
    else timer.current = window.setTimeout(() => fire(raw), delay);
  };

  useEffect(() => () => window.clearTimeout(timer.current), []);
  // The parent changed the text itself (not by typing)
  useEffect(() => {
    if (value !== undefined && value !== last.current) { last.current = value; setText(value); }
  }, [value]);

  return (
    <Input
      allowClear
      size={size}
      autoFocus={autoFocus}
      value={text}
      placeholder={placeholder}
      style={{ width, ...style }}
      prefix={loading ? <LoadingOutlined /> : <SearchOutlined style={{ opacity: 0.45 }} />}
      onChange={(e) => change(e.target.value)}
      onPressEnter={() => fire(text)}
      onCompositionStart={() => { composing.current = true; }}
      onCompositionEnd={(e) => { composing.current = false; change((e.target as HTMLInputElement).value); }}
    />
  );
}

/**
 * For dropdown pickers (Select showSearch filterOption={false}): call `search(text)` from onSearch.
 * Waits `delay` ms, skips texts shorter than `minChars`, cancels the old request and ignores its answer
 * (the latest typing always wins). `fetcher` must pass the signal to axios: api.get(url, { signal }).
 */
export function useLiveLookup<T>(
  fetcher: (text: string, signal: AbortSignal) => Promise<T[]>,
  { minChars = 2, delay = SEARCH_DELAY_MS, allowEmpty = false }: { minChars?: number; delay?: number; allowEmpty?: boolean } = {},
) {
  const [options, setOptions] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef<number>();
  const abort = useRef<AbortController>();
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const cancel = useCallback(() => {
    window.clearTimeout(timer.current);
    abort.current?.abort();
  }, []);
  useEffect(() => cancel, [cancel]);

  const run = useCallback(async (text: string) => {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setLoading(true);
    try {
      const rows = await fetcherRef.current(text, controller.signal);
      if (!controller.signal.aborted) setOptions(rows);
    } catch {
      /* cancelled or failed: keep the old list */
    } finally {
      if (abort.current === controller) setLoading(false);
    }
  }, []);

  const search = useCallback((raw: string) => {
    window.clearTimeout(timer.current);
    const text = raw.trim();
    if (allowEmpty && !text) { run(''); return; } // empty box = show the first rows
    if (text.length < minChars) {
      abort.current?.abort();
      setLoading(false);
      return;
    }
    setLoading(true);
    timer.current = window.setTimeout(() => run(text), delay);
  }, [minChars, delay, allowEmpty, run]);

  /** Load the first rows without typing (e.g. when the dropdown opens). */
  const loadNow = useCallback((text = '') => { window.clearTimeout(timer.current); run(text); }, [run]);

  return { options, setOptions, loading, search, loadNow };
}

/**
 * For screens that load their own data: `const next = useLatestRequest()`, then at the start of each load
 * `const signal = next()`, pass `{ signal }` to api.get and stop if `signal.aborted`. Older requests are cancelled.
 */
export function useLatestRequest() {
  const ref = useRef<AbortController>();
  useEffect(() => () => ref.current?.abort(), []);
  return useCallback(() => {
    ref.current?.abort();
    ref.current = new AbortController();
    return ref.current.signal;
  }, []);
}
