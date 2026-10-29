// The writing area for the digital pad (iScribe pad in Mouse mode, a tablet pen, a touch screen or a mouse).
// The pen draws live. Strokes are kept as normalised points, so the picture is identical on any screen size.
// SAFE TO EDIT: PAD_RATIO (shape of the writing area), SMOOTHING. The words are in src/i18n/*.json under "handwriting".
import { isToolbarTarget, viewportPoint } from './padMapping';
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';

// iScribe A4 pad: 210 x 291.5 mm (portrait); landscape is the other way round
const PAD_RATIO = 210 / 291.5;
const EXPORT_WIDTH = 1800; // pixels of the longer side of the saved handwriting picture

type Point = { x: number; y: number; p: number };
type Stroke = { color: string; width: number; pen: boolean; points: Point[] };

export type CanvasHandle = {
  undo: () => void;
  clear: () => void;
  hasInk: () => boolean;
  exportPng: () => Promise<Blob | null>;
};

export type Tool = 'pen' | 'eraser';

type Props = {
  landscape: boolean;
  color: string;
  width: number; // pen thickness in screen pixels at normal size
  tool: Tool;
  maxHeight: number; // pixels the writing area may use on this screen
  padMode?: boolean; // full-screen pad mode: the whole screen is the pad (see padMapping.ts)
  onInkChange?: (hasInk: boolean) => void;
};

export const HandwritingCanvas = forwardRef<CanvasHandle, Props>(function HandwritingCanvas(
  { landscape, color, width, tool, maxHeight, padMode = false, onInkChange }, ref,
) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const strokes = useRef<Stroke[]>([]);
  const current = useRef<Stroke | null>(null);
  const penSeen = useRef(false);
  const erasing = useRef(false);
  const writing = useRef(false); // pad mode: a stroke is being written
  const ringRef = useRef<HTMLDivElement>(null); // pad mode: where the pen is on the page
  const [size, setSize] = useState({ w: 600, h: 800 });
  const ratio = landscape ? 1 / PAD_RATIO : PAD_RATIO; // width / height

  // Fit the writing area into the space we have
  useEffect(() => {
    const fit = () => {
      const availW = wrapRef.current?.parentElement?.clientWidth ?? 600;
      let w = availW;
      let h = w / ratio;
      if (h > maxHeight) { h = maxHeight; w = h * ratio; }
      setSize({ w: Math.floor(w), h: Math.floor(h) });
    };
    fit();
    const observer = new ResizeObserver(fit);
    if (wrapRef.current?.parentElement) observer.observe(wrapRef.current.parentElement);
    return () => observer.disconnect();
  }, [ratio, maxHeight]);

  const drawStroke = useCallback((ctx: CanvasRenderingContext2D, stroke: Stroke, w: number, h: number, scale: number) => {
    const pts = stroke.points;
    if (!pts.length) return;
    ctx.strokeStyle = stroke.color;
    ctx.fillStyle = stroke.color;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    const base = stroke.width * scale;
    const widthAt = (p: Point) => (stroke.pen ? base * (0.55 + Math.min(Math.max(p.p, 0), 1) * 0.9) : base);
    if (pts.length === 1) {
      ctx.beginPath();
      ctx.arc(pts[0].x * w, pts[0].y * h, widthAt(pts[0]) / 2, 0, Math.PI * 2);
      ctx.fill();
      return;
    }
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1];
      const b = pts[i];
      ctx.lineWidth = widthAt(b);
      ctx.beginPath();
      // a smooth curve through the middle points
      const mx = ((a.x + b.x) / 2) * w;
      const my = ((a.y + b.y) / 2) * h;
      const px = i > 1 ? ((pts[i - 2].x + a.x) / 2) * w : a.x * w;
      const py = i > 1 ? ((pts[i - 2].y + a.y) / 2) * h : a.y * h;
      ctx.moveTo(px, py);
      ctx.quadraticCurveTo(a.x * w, a.y * h, mx, my);
      ctx.stroke();
    }
  }, []);

  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.w, size.h);
    const all = current.current ? [...strokes.current, current.current] : strokes.current;
    for (const s of all) drawStroke(ctx, s, size.w, size.h, 1);
  }, [size, drawStroke]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(size.w * dpr);
    canvas.height = Math.floor(size.h * dpr);
    redraw();
  }, [size, redraw]);

  const changed = () => onInkChange?.(strokes.current.length > 0);

  useImperativeHandle(ref, () => ({
    undo() { strokes.current.pop(); redraw(); changed(); },
    clear() { strokes.current = []; redraw(); changed(); },
    hasInk: () => strokes.current.length > 0,
    exportPng: () => {
      if (!strokes.current.length) return Promise.resolve(null);
      const long = EXPORT_WIDTH;
      const w = landscape ? long : Math.round(long * ratio);
      const h = landscape ? Math.round(long / ratio) : long;
      const out = document.createElement('canvas');
      out.width = w;
      out.height = h;
      const ctx = out.getContext('2d');
      if (!ctx) return Promise.resolve(null);
      const scale = w / size.w; // thickness grows with the picture
      for (const s of strokes.current) drawStroke(ctx, s, w, h, scale);
      return new Promise((resolve) => out.toBlob((blob) => resolve(blob), 'image/png'));
    },
  }));

  // One pen/mouse movement -> a point on the page. Normal mode: position inside the writing box. Pad mode: position on the
  // whole screen, because the pad covers the whole screen (see padMapping.ts).
  type Area = { left: number; top: number; width: number; height: number };
  const screenArea = (): Area => ({ left: 0, top: 0, width: window.innerWidth, height: window.innerHeight });
  const toPoint = (e: PointerEvent, area: Area): Point => {
    const { x, y } = viewportPoint(e.clientX - area.left, e.clientY - area.top, area.width, area.height);
    return { x, y, p: e.pointerType === 'pen' ? e.pressure : 0.5 };
  };

  const eraseAt = (pt: Point) => {
    const rx = 14 / size.w;
    const ry = 14 / size.h;
    const before = strokes.current.length;
    strokes.current = strokes.current.filter((s) => !s.points.some((q) => Math.abs(q.x - pt.x) < rx && Math.abs(q.y - pt.y) < ry));
    if (strokes.current.length !== before) { redraw(); changed(); }
  };

  // Returns false when the movement must not start writing (palm on the screen, right mouse button)
  const begin = (e: PointerEvent, area: Area): boolean => {
    if (e.pointerType === 'pen') penSeen.current = true;
    if (e.pointerType === 'touch' && penSeen.current) return false; // palm resting on the screen while a pen is used
    if (e.pointerType === 'mouse' && e.button !== 0) return false;
    const pt = toPoint(e, area);
    if (tool === 'eraser') { current.current = null; erasing.current = true; eraseAt(pt); return true; }
    current.current = { color, width, pen: e.pointerType === 'pen', points: [pt] };
    redraw();
    return true;
  };

  // Pad mode: a small ring on the page shows where the pen is (the real cursor is hidden)
  const showRing = (e: PointerEvent) => {
    const ring = ringRef.current;
    if (!ring) return;
    const { x, y } = viewportPoint(e.clientX, e.clientY, window.innerWidth, window.innerHeight);
    ring.style.display = 'block';
    ring.style.transform = `translate(${x * size.w}px, ${y * size.h}px)`;
  };

  const move = (e: PointerEvent, area: Area) => {
    if (tool === 'eraser') {
      if (erasing.current) eraseAt(toPoint(e, area));
      return;
    }
    const stroke = current.current;
    if (!stroke) return;
    const events = typeof e.getCoalescedEvents === 'function' ? e.getCoalescedEvents() : [];
    for (const ev of events.length ? events : [e]) stroke.points.push(toPoint(ev, area));
    redraw();
  };

  const end = () => {
    erasing.current = false;
    if (current.current) {
      strokes.current.push(current.current);
      current.current = null;
      redraw();
      changed();
    }
  };

  // Pad mode: listen on the whole window (the pad moves the cursor over the whole screen)
  const latest = useRef({ begin, move, end, showRing });
  latest.current = { begin, move, end, showRing };
  useEffect(() => {
    if (!padMode) return undefined;
    const onDown = (e: PointerEvent) => { if (!isToolbarTarget(e.target)) writing.current = latest.current.begin(e, screenArea()); };
    const onMove = (e: PointerEvent) => { latest.current.showRing(e); if (writing.current) latest.current.move(e, screenArea()); };
    const onUp = () => { writing.current = false; latest.current.end(); };
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
    const ring = ringRef.current;
    return () => {
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
      if (ring) ring.style.display = 'none';
    };
  }, [padMode]);

  // Normal mode: the writing box itself
  const boxArea = (el: HTMLElement): Area => el.getBoundingClientRect();
  const onDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (padMode) return;
    if (begin(e.nativeEvent, boxArea(e.currentTarget))) e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onMove = (e: React.PointerEvent<HTMLCanvasElement>) => { if (!padMode) move(e.nativeEvent, boxArea(e.currentTarget)); };
  const onUp = () => { if (!padMode) end(); };

  return (
    <div ref={wrapRef} className="hw-wrap" style={{ width: size.w, height: size.h }}>
      <canvas
        ref={canvasRef}
        className="hw-canvas"
        style={{ width: size.w, height: size.h, cursor: tool === 'eraser' ? 'cell' : 'crosshair' }}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onContextMenu={(e) => e.preventDefault()}
      />
      {padMode && <div ref={ringRef} className="hw-ring" aria-hidden="true" />}
    </div>
  );
});
