// "Handwriting" tab of the doctor's check-up screen: one A4 page on the screen, written with the digital pad (or a tablet
// pen / touch screen / mouse). Press Save: the handwriting is kept as a picture, and ONE combined picture with the clinic
// letterhead is made for this patient's prescription. Earlier pages of this check-up are shown below.
// The pad moves the cursor over the WHOLE screen. "Use the whole pad" (the default for pad users) therefore reads the pen from
// the whole screen, so the whole pad is this page; while it is on, mouse clicks outside this panel are blocked on purpose
// (writing near a button must never press it). Switch it off to use the mouse on the rest of the screen.
// SAFE TO EDIT: pen colours (COLORS) and the starting thickness. The words are in src/i18n/*.json under "handwriting".
import { ClearOutlined, EditOutlined, PrinterOutlined, RedoOutlined, SaveOutlined, UndoOutlined } from '@ant-design/icons';
import { Alert, App, Button, Segmented, Slider, Space, Switch, Typography } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import type { HandwrittenPage } from '../../../api/types';
import { DocumentModal } from '../../../components/BillPreview';
import { isToolbarTarget } from './padMapping';
import { boundsFromCorners, loadBounds, loadRotation, rotationFromCorners, saveBounds, saveRotation, type PadBounds, type Rotation, type UnitPoint } from './padMapping';
import { HandwritingCanvas, type CanvasHandle, type Tool } from './HandwritingCanvas';
import { HandwrittenPages, PrivateImage } from './HandwrittenPages';

const COLORS = [
  { value: '#111111', key: 'black' },
  { value: '#1a3a8a', key: 'blue' },
  { value: '#b3261e', key: 'red' },
];

export function HandwritingSection({ visitId, onInkChange, onSaved }: {
  visitId: string; onInkChange?: (hasInk: boolean) => void; onSaved?: () => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const canvas = useRef<CanvasHandle>(null);
  const [hasInk, setHasInk] = useState(false);
  const [color, setColor] = useState(COLORS[1].value);
  const [width, setWidth] = useState(3);
  const [tool, setTool] = useState<Tool>('pen');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<HandwrittenPage | null>(null);
  const [printing, setPrinting] = useState(false);
  const [refresh, setRefresh] = useState(0);

  const [viewHeight, setViewHeight] = useState(window.innerHeight);
  useEffect(() => {
    const onResize = () => setViewHeight(window.innerHeight);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Use the whole pad (remembered on this computer)
  const [whole, setWhole] = useState(() => { try { return localStorage.getItem('hw-whole-pad') === '1'; } catch { return false; } });
  useEffect(() => { try { localStorage.setItem('hw-whole-pad', whole ? '1' : '0'); } catch { /* not remembered */ } }, [whole]);
  useEffect(() => {
    if (!whole) return undefined;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setWhole(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [whole]);

  // "Set pad corners": touch the pen at two opposite corners of the pad so the pad's place on the screen is known exactly
  const [bounds, setBounds] = useState<PadBounds | null>(() => loadBounds());
  const [rotation, setRotation] = useState<Rotation>(loadRotation); // how the pad is turned: the iScribe pad needs a quarter turn
  const turnPad = (value: Rotation) => { setRotation(value); saveRotation(value); };
  const [corner, setCorner] = useState<0 | 1 | 2>(0); // 0 = not setting, 1 = waiting for the first corner, 2 = for the second
  const firstCorner = useRef<UnitPoint | null>(null);
  useEffect(() => {
    if (corner === 0) return undefined;
    const onDown = (e: PointerEvent) => {
      if (isToolbarTarget(e.target)) return;
      e.stopPropagation(); // this touch is a corner, not writing
      const here = { x: e.screenX, y: e.screenY };
      if (corner === 1) { firstCorner.current = here; setCorner(2); return; }
      const found = firstCorner.current ? boundsFromCorners(firstCorner.current, here) : null;
      if (!found) { message.warning(t('handwriting.cornersTooClose')); setCorner(1); return; }
      setBounds(found);
      saveBounds(found);
      if (firstCorner.current) turnPad(rotationFromCorners(firstCorner.current, here)); // the two touches also tell how the pad is turned
      setCorner(0);
      message.success(t('handwriting.cornersSaved'));
    };
    window.addEventListener('pointerdown', onDown, true);
    return () => window.removeEventListener('pointerdown', onDown, true);
  }, [corner, message, t]);

  const inkChanged = (value: boolean) => { setHasInk(value); onInkChange?.(value); };

  const save = async () => {
    const blob = await canvas.current?.exportPng();
    if (!blob) { message.warning(t('handwriting.nothing')); return; }
    setSaving(true);
    try {
      const body = new FormData();
      body.append('visit', visitId);
      body.append('paper', 'a4');
      body.append('ink', blob, 'ink.png');
      const { data } = await api.post<HandwrittenPage>('/handwritten-prescriptions/', body);
      setSaved(data);
      inkChanged(false);
      setRefresh((n) => n + 1);
      onSaved?.();
    } catch (err) {
      message.error(errorMessage(err, t('handwriting.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const another = () => { setSaved(null); canvas.current?.clear(); };

  return (
    <div className="hw-section">
      {saved && (
        <div className="hw-saved">
          <Alert type="success" showIcon message={t('handwriting.saved')} description={t('handwriting.savedHelp', { number: saved.number })} style={{ marginBottom: 12 }} />
          <div style={{ textAlign: 'center' }}><PrivateImage pageId={saved.id} width={Math.min(420, window.innerWidth - 120)} /></div>
          <Space style={{ marginTop: 12, marginBottom: 12 }} wrap>
            <Button type="primary" icon={<PrinterOutlined />} onClick={() => setPrinting(true)}>{t('handwriting.print')}</Button>
            <Button icon={<EditOutlined />} onClick={another}>{t('handwriting.another')}</Button>
          </Space>
          {printing && <DocumentModal kind="handwritten-rx" id={saved.id} title={t('handwriting.title')} onClose={() => setPrinting(false)} />}
        </div>
      )}
      <div data-hw-ui style={{ marginBottom: 8 }}>
        <Space wrap size={[8, 6]}>
          <Switch checked={whole} onChange={setWhole} />
          <b>{t('handwriting.wholePad')}</b>
          {whole && (
            <>
              <Button size="small" type={corner ? 'primary' : 'default'} onClick={() => { firstCorner.current = null; setCorner(corner ? 0 : 1); }}>
                {corner === 1 ? t('handwriting.corner1') : corner === 2 ? t('handwriting.corner2') : t('handwriting.corners')}
              </Button>
              <Button size="small" onClick={() => turnPad(((rotation + 1) % 4) as Rotation)}>{t('handwriting.turnPad')}</Button>
              {bounds && !corner && <Button size="small" onClick={() => { setBounds(null); saveBounds(null); }}>{t('handwriting.cornersReset')}</Button>}
            </>
          )}
        </Space>
        {whole && <Alert type="info" showIcon style={{ marginTop: 6 }} message={t('handwriting.wholePadOn')} />}
      </div>
      {/* The writing page stays mounted (only hidden after saving) so nothing written is ever lost */}
      <div hidden={!!saved}>
        <Space wrap size={[12, 8]} style={{ marginBottom: 8 }} data-hw-ui>
          <Segmented value={tool} onChange={(v) => setTool(v as Tool)}
            options={[{ value: 'pen', label: t('handwriting.pen') }, { value: 'eraser', label: t('handwriting.eraser') }]} />
          <Space size={4}>
            {COLORS.map((c) => (
              <button key={c.key} type="button" aria-label={t(`handwriting.color.${c.key}`)} className={`hw-color${color === c.value && tool === 'pen' ? ' on' : ''}`}
                style={{ background: c.value }} onClick={() => { setColor(c.value); setTool('pen'); }} />
            ))}
          </Space>
          <Space size={6}>
            <span className="cell-sub">{t('handwriting.thickness')}</span>
            <Slider min={1} max={8} value={width} onChange={setWidth} style={{ width: 90, margin: 0 }} />
          </Space>
          <Button icon={<UndoOutlined />} onClick={() => canvas.current?.undo()} disabled={!hasInk}>{t('handwriting.undo')}</Button>
          <Button icon={<ClearOutlined />} onClick={() => canvas.current?.clear()} disabled={!hasInk}>{t('handwriting.clear')}</Button>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} disabled={!hasInk} onClick={save}>{t('handwriting.save')}</Button>
        </Space>
        <div className="hw-stage">
          <HandwritingCanvas ref={canvas} landscape={false} color={color} width={width} tool={tool}
            maxHeight={Math.max(viewHeight - (whole ? 380 : 270), 300)} padMode={whole} calibrating={corner > 0} rotation={rotation}
            bounds={bounds ?? undefined} onInkChange={inkChanged} />
        </div>
        <Typography.Text type="secondary" className="cell-sub" style={{ display: 'block', marginTop: 6 }}>{whole ? t('handwriting.sectionHintWhole') : t('handwriting.sectionHint')}</Typography.Text>
      </div>
      <div style={{ marginTop: 16 }}>
        <Typography.Text strong><RedoOutlined /> {t('handwriting.earlier')}</Typography.Text>
        <div style={{ marginTop: 8 }}><HandwrittenPages visitId={visitId} refreshKey={refresh} /></div>
      </div>
    </div>
  );
}
