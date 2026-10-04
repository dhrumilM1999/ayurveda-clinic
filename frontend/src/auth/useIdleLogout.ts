// Logs the user out after some minutes without mouse or keyboard use
// (the number of minutes comes from IDLE_TIMEOUT_MINUTES in .env).
import { useEffect } from 'react';

const EVENTS = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];

export function useIdleLogout(minutes: number | undefined, onIdle: () => void) {
  useEffect(() => {
    if (!minutes) return;
    let timer = window.setTimeout(onIdle, minutes * 60_000);
    const reset = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(onIdle, minutes * 60_000);
    };
    EVENTS.forEach((name) => window.addEventListener(name, reset, { passive: true }));
    return () => {
      window.clearTimeout(timer);
      EVENTS.forEach((name) => window.removeEventListener(name, reset));
    };
  }, [minutes, onIdle]);
}
