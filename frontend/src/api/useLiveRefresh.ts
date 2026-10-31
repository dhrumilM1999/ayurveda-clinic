// React side of liveRefresh.ts: keeps calling `run` every `seconds` while the screen is open.
import { useEffect, useRef } from 'react';
import { startLiveRefresh } from './liveRefresh';

export function useLiveRefresh(run: () => unknown, seconds: number, enabled = true) {
  const latest = useRef(run);
  latest.current = run; // always the newest version of the function, without restarting the timer
  useEffect(() => {
    if (!enabled) return undefined;
    return startLiveRefresh(() => latest.current(), seconds);
  }, [seconds, enabled]);
}
