// "Handwriting" tab of the doctor's check-up screen: one A4 page on the screen, written with the digital pad (or a tablet
// pen / touch screen / mouse). Press Save: the handwriting is kept as a picture, and ONE combined picture with the clinic
// letterhead is made for this patient's prescription. Earlier pages of this check-up are shown below.
// The pad moves the cursor over the whole screen, so only the part of the pad that lies over the page writes; outside the
// page the pad does nothing.
// SAFE TO EDIT: pen colours (COLORS) and the starting thickness. The words are in src/i18n/*.json under "handwriting".
import { ClearOutlined, EditOutlined, PrinterOutlined, RedoOutlined, SaveOutlined, UndoOutlined } from '@ant-design/icons';
import { Alert, App, Button, Segmented, Slider, Space, Typography } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import type { HandwrittenPage } from '../../../api/types';
import { DocumentModal } from '../../../components/BillPreview';
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
      {/* The writing page stays mounted (only hidden after saving) so nothing written is ever lost */}
      <div hidden={!!saved}>
        <Space wrap size={[12, 8]} style={{ marginBottom: 8 }}>
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
            maxHeight={Math.max(viewHeight - 270, 320)} onInkChange={inkChanged} />
        </div>
        <Typography.Text type="secondary" className="cell-sub" style={{ display: 'block', marginTop: 6 }}>{t('handwriting.sectionHint')}</Typography.Text>
      </div>
      <div style={{ marginTop: 16 }}>
        <Typography.Text strong><RedoOutlined /> {t('handwriting.earlier')}</Typography.Text>
        <div style={{ marginTop: 8 }}><HandwrittenPages visitId={visitId} refreshKey={refresh} /></div>
      </div>
    </div>
  );
}
