import { describe, expect, it } from 'vitest';
import { boundsFromCorners, rotateUnit, rotationFromCorners, screenPoint, viewportPoint, wholeScreen } from './padMapping';

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

// The real iScribe pad, held upright with the clip at the top, was written on at its top, right, left and bottom edges. The
// words appeared on the screen's left, top, bottom and right edges: the pad is reported turned by a quarter.
describe('a pad that reports a quarter turn', () => {
  const screen = wholeScreen(1920, 1080);
  it('puts the pad edges back where they belong (rotation 1)', () => {
    expect(screenPoint(0, 540, screen, 1)).toEqual({ x: 0.5, y: 0 }); // screen left = pad top
    expect(screenPoint(960, 0, screen, 1)).toEqual({ x: 1, y: 0.5 }); // screen top = pad right
    expect(screenPoint(960, 1080, screen, 1)).toEqual({ x: 0, y: 0.5 }); // screen bottom = pad left
    expect(screenPoint(1920, 540, screen, 1)).toEqual({ x: 0.5, y: 1 }); // screen right = pad bottom
  });
  it('turning four quarters gives the same point back', () => {
    const p = { x: 0.2, y: 0.7 };
    let q = p;
    for (let i = 0; i < 4; i++) q = rotateUnit(q, 1);
    expect(q.x).toBeCloseTo(p.x);
    expect(q.y).toBeCloseTo(p.y);
  });
  it('finds the turn from the two corners the doctor touches', () => {
    expect(rotationFromCorners({ x: 100, y: 100 }, { x: 900, y: 700 })).toBe(0);
    expect(rotationFromCorners({ x: 100, y: 700 }, { x: 900, y: 100 })).toBe(1); // top-left touched at the screen's bottom-left
    expect(rotationFromCorners({ x: 900, y: 700 }, { x: 100, y: 100 })).toBe(2);
    expect(rotationFromCorners({ x: 900, y: 100 }, { x: 100, y: 700 })).toBe(3);
  });
});
