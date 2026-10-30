import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CENTRE_MIN, GAP, PANEL_DEFAULT, PANEL_MIN, clampPanelWidth, loadPanel, savePanel } from './panelSize';

describe('clampPanelWidth', () => {
  it('keeps a width that fits', () => {
    expect(clampPanelWidth(500, 1200)).toBe(500);
  });
  it('never makes the panel narrower than the minimum', () => {
    expect(clampPanelWidth(100, 1200)).toBe(PANEL_MIN);
  });
  it('keeps room for the check-up form', () => {
    expect(clampPanelWidth(900, 1200)).toBe(1200 - CENTRE_MIN - GAP);
  });
  it('on a small screen still gives the panel its minimum', () => {
    expect(clampPanelWidth(600, 700)).toBe(PANEL_MIN);
  });
});

describe('remembered panel', () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => { store.set(k, v); },
      removeItem: (k: string) => { store.delete(k); },
    });
  });
  it('starts open at the default width', () => {
    expect(loadPanel()).toEqual({ open: true, width: PANEL_DEFAULT });
  });
  it('remembers the width and closed state after a reload', () => {
    savePanel({ open: false, width: 612 });
    expect(loadPanel()).toEqual({ open: false, width: 612 });
  });
  it('ignores a damaged saved value', () => {
    localStorage.setItem('hw-panel', '{oops');
    expect(loadPanel()).toEqual({ open: true, width: PANEL_DEFAULT });
  });
});
