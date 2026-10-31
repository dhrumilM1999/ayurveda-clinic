// "Live" screens: a list that updates by itself (new appointment arrives, a check-up is completed) without pressing refresh.
// It asks the server again every few seconds while the browser tab is visible, and straight away when the doctor comes back
// to the tab. It never starts a new request while the last one is still running, and it stops when the tab is hidden.
// SAFE TO EDIT: nothing here; the seconds for each screen are set where the screen uses useLiveRefresh.

export type LiveEnv = {
  isHidden: () => boolean;
  onVisible: (handler: () => void) => () => void; // called when the tab/window becomes visible again; returns "stop listening"
  setTimer: (handler: () => void, ms: number) => unknown;
  clearTimer: (id: unknown) => void;
};

export const browserEnv: LiveEnv = {
  isHidden: () => typeof document !== 'undefined' && document.hidden,
  onVisible: (handler) => {
    const onChange = () => { if (!document.hidden) handler(); };
    document.addEventListener('visibilitychange', onChange);
    window.addEventListener('focus', handler);
    return () => { document.removeEventListener('visibilitychange', onChange); window.removeEventListener('focus', handler); };
  },
  setTimer: (handler, ms) => window.setInterval(handler, ms),
  clearTimer: (id) => window.clearInterval(id as number),
};

/** Starts the refreshing. `run` may return a promise; returns a function that stops everything. */
export function startLiveRefresh(run: () => unknown, seconds: number, env: LiveEnv = browserEnv): () => void {
  let busy = false;
  const tick = async () => {
    if (busy || env.isHidden()) return;
    busy = true;
    try {
      await run();
    } catch {
      // a failed refresh is silent: the list on the screen stays as it was and the next try comes soon
    } finally {
      busy = false;
    }
  };
  const timer = env.setTimer(tick, seconds * 1000);
  const stopListening = env.onVisible(tick);
  return () => { env.clearTimer(timer); stopListening(); };
}
