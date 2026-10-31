import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { startLiveRefresh, type LiveEnv } from './liveRefresh';

function fakeEnv() {
  const state = { hidden: false, visibleHandler: null as null | (() => void) };
  const env: LiveEnv = {
    isHidden: () => state.hidden,
    onVisible: (h) => { state.visibleHandler = h; return () => { state.visibleHandler = null; }; },
    setTimer: (h, ms) => setInterval(h, ms),
    clearTimer: (id) => clearInterval(id as ReturnType<typeof setInterval>),
  };
  return { env, state };
}

describe('startLiveRefresh', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('asks again every few seconds', async () => {
    const { env } = fakeEnv();
    const run = vi.fn().mockResolvedValue(undefined);
    startLiveRefresh(run, 5, env);
    await vi.advanceTimersByTimeAsync(15000);
    expect(run).toHaveBeenCalledTimes(3);
  });

  it('waits while the browser tab is hidden and refreshes at once when it is shown again', async () => {
    const { env, state } = fakeEnv();
    const run = vi.fn().mockResolvedValue(undefined);
    startLiveRefresh(run, 5, env);
    state.hidden = true;
    await vi.advanceTimersByTimeAsync(20000);
    expect(run).not.toHaveBeenCalled();
    state.hidden = false;
    state.visibleHandler?.();
    await vi.advanceTimersByTimeAsync(0);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it('does not start a new request while the last one is still running', async () => {
    const { env } = fakeEnv();
    let finish: () => void = () => undefined;
    const run = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
    startLiveRefresh(run, 5, env);
    await vi.advanceTimersByTimeAsync(20000);
    expect(run).toHaveBeenCalledTimes(1);
    finish();
    await vi.advanceTimersByTimeAsync(5000);
    expect(run).toHaveBeenCalledTimes(2);
  });

  it('keeps going after a failed refresh', async () => {
    const { env } = fakeEnv();
    const run = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined);
    startLiveRefresh(run, 5, env);
    await vi.advanceTimersByTimeAsync(10000);
    expect(run).toHaveBeenCalledTimes(2);
  });

  it('stops when asked', async () => {
    const { env, state } = fakeEnv();
    const run = vi.fn().mockResolvedValue(undefined);
    const stop = startLiveRefresh(run, 5, env);
    stop();
    await vi.advanceTimersByTimeAsync(20000);
    expect(run).not.toHaveBeenCalled();
    expect(state.visibleHandler).toBeNull();
  });
});
