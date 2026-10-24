// Error log, screen side. ASK FIRST before editing.
// - Keeps a short trail of the last steps of this login (pages opened, API calls and their result). Never typed text.
// - When something breaks (a screen crash, a lost connection) it tells the server, which writes it in the Error log.
// - Each login gets its own session id, sent with every request, so the owner can see everything from one login.
import axios from 'axios';
import { tokenStore } from '../auth/tokenStore';

export interface TrailStep { t: string; type: 'page' | 'api' | 'error'; text: string }
export interface ErrorReport {
  kind: 'js' | 'react' | 'network' | 'api' | 'trail';
  message?: string;
  details?: string;
  path?: string;
  method?: string;
  status_code?: number | null;
  code?: string;
}

const SESSION_KEY = 'error_session_id';
const MAX_TRAIL = 30;
const MAX_REPORTS_PER_LOGIN = 40;
const SAME_REPORT_GAP_MS = 10_000;

const TRAIL_KEY = 'error_trail';

// Kept in this browser tab, so a page reload does not lose the steps
function loadTrail(): TrailStep[] {
  try { return JSON.parse(sessionStorage.getItem(TRAIL_KEY) ?? '[]') as TrailStep[]; } catch { return []; }
}
const trail: TrailStep[] = loadTrail();
const lastSent = new Map<string, number>();
let sent = 0;

const now = () => new Date().toTimeString().slice(0, 8);

function randomId(): string {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

export function getSessionId(): string {
  try {
    let id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = randomId();
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  } catch {
    return '';
  }
}

/** Called when someone logs in: a fresh session and an empty trail. */
export function startSession() {
  try { sessionStorage.setItem(SESSION_KEY, randomId()); } catch { /* the log is optional */ }
  trail.length = 0;
  saveTrail();
  sent = 0;
  lastSent.clear();
}

function saveTrail() {
  try { sessionStorage.setItem(TRAIL_KEY, JSON.stringify(trail)); } catch { /* the log is optional */ }
}

export function addStep(type: TrailStep['type'], text: string) {
  const step = text.slice(0, 200);
  const last = trail[trail.length - 1];
  if (last && last.type === type && last.text === step && type === 'page') return; // same page opened twice in a row
  trail.push({ t: now(), type, text: step });
  if (trail.length > MAX_TRAIL) trail.shift();
  saveTrail();
}

/** Only the address, never the part after "?" (it can hold a patient's name typed in a search box). */
export function plainPath(url: string | undefined): string {
  return (url ?? '').split('?')[0]!.replace(/^https?:\/\/[^/]+/, '');
}

export function currentScreen(): string {
  return window.location.pathname;
}

export async function sendReport(report: ErrorReport) {
  const access = tokenStore.getAccess();
  if (!access) return; // not logged in: the server cannot tell who it was
  const key = `${report.kind}|${report.message ?? ''}|${report.path ?? ''}|${report.code ?? ''}`;
  const last = lastSent.get(key) ?? 0;
  if (Date.now() - last < SAME_REPORT_GAP_MS || sent >= MAX_REPORTS_PER_LOGIN) return;
  lastSent.set(key, Date.now());
  sent += 1;
  try {
    // plain axios (not the app's api client) so a failing report can never trigger another report
    await axios.post('/api/v1/error-logs/report/', {
      ...report,
      message: (report.message ?? '').slice(0, 1000),
      details: (report.details ?? '').slice(0, 20000),
      screen: currentScreen(),
      trail: [...trail],
    }, {
      headers: {
        Authorization: `Bearer ${access}`,
        'X-Session-ID': getSessionId(),
        ...(tokenStore.getBranch() ? { 'X-Branch-ID': tokenStore.getBranch()! } : {}),
      },
      timeout: 8000,
    }).then(({ data }) => { lastCode = (data as { code?: string }).code ?? ''; });
  } catch {
    // The report is a best effort; never show an error about an error
  }
}

let lastCode = '';
export const lastErrorCode = () => lastCode;

/** Window-level catch-alls: a script error, or a promise that failed and nobody handled. */
export function installGlobalHandlers() {
  window.addEventListener('error', (e) => {
    if (/ResizeObserver loop/i.test(e.message)) return; // harmless browser notice
    addStep('error', e.message);
    sendReport({ kind: 'js', message: e.message, details: `${e.filename}:${e.lineno}:${e.colno}\n${(e.error as Error | undefined)?.stack ?? ''}` });
  });
  window.addEventListener('unhandledrejection', (e) => {
    const reason = e.reason as { isAxiosError?: boolean; name?: string; message?: string; stack?: string } | undefined;
    // A failed API call is already in the log (server side), or was reported as "network" by the API client
    if (reason?.isAxiosError || reason?.name === 'CanceledError') return;
    const message = reason?.message ?? String(reason);
    addStep('error', message);
    sendReport({ kind: 'js', message, details: reason?.stack ?? '' });
  });
}
