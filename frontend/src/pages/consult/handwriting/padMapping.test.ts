import { describe, expect, it } from 'vitest';
import { boundsFromCorners, screenPoint, viewportPoint, wholeScreen } from './padMapping';

describe('viewportPoint', () => {
  it('maps the pad corners to the page corners', () => {
    expect(viewportPoint(0, 0, 1920, 1080)).toEqual({ x: 0, y: 0 });
    expect(viewportPoint(1920, 1080, 1920, 1080)).toEqual({ x: 1, y: 1 });
  });
  it('maps the middle of the screen to the middle of the page', () => {
    expect(viewportPoint(960, 540, 1920, 1080)).toEqual({ x: 0.5, y: 0.5 });
  });
  it('keeps a point outside the screen on the edge', () => {
    expect(viewportPoint(-20, 5000, 1920, 1080)).toEqual({ x: 0, y: 1 });
  });
  it('does not divide by zero', () => {
    expect(viewportPoint(10, 10, 0, 0)).toEqual({ x: 0, y: 0 });
  });
});

describe('screenPoint', () => {
  it('uses the whole screen when the pad was not calibrated', () => {
    expect(screenPoint(960, 540, wholeScreen(1920, 1080))).toEqual({ x: 0.5, y: 0.5 });
  });
  it('maps the two touched corners to the page corners', () => {
    const bounds = boundsFromCorners({ x: 100, y: 50 }, { x: 1700, y: 1000 });
    expect(bounds).toEqual({ left: 100, top: 50, right: 1700, bottom: 1000 });
    expect(screenPoint(100, 50, bounds!)).toEqual({ x: 0, y: 0 });
    expect(screenPoint(1700, 1000, bounds!)).toEqual({ x: 1, y: 1 });
  });
  it('accepts the corners in any order and refuses two touches that are too close', () => {
    expect(boundsFromCorners({ x: 1700, y: 1000 }, { x: 100, y: 50 })).toEqual({ left: 100, top: 50, right: 1700, bottom: 1000 });
    expect(boundsFromCorners({ x: 100, y: 50 }, { x: 120, y: 60 })).toBeNull();
  });
});
