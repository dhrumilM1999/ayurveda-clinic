// "Handwriting" window of the doctor's check-up screen: write on the digital pad (or a tablet / touch screen / mouse),
// press Save: the handwriting is kept as a picture, and ONE combined picture with the clinic letterhead is made for
// this patient's prescription. Earlier pages of this check-up are shown below.
// SAFE TO EDIT: pen colours (COLORS) and the starting thickness. The words are in src/i18n/*.json under "handwriting".
import { ClearOutlined, EditOutlined, FullscreenExitOutlined, FullscreenOutlined, PrinterOutlined, RedoOutlined, SaveOutlined, UndoOutlined } from '@ant-design/icons';
import { Alert, App, Button, Modal, Segmented, Slider, Space, Typography } from 'antd';
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

export function HandwritingModal({ open, visitId, patientName, onClose, onSaved }: {
  open: boolean; visitId: string; patientName: string; onClose: () => void; onSaved?: () => void;
}) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const canvas = useRef<CanvasHandle>(null);
  const [hasInk, setHasInk] = useState(false);
  const [landscape, setLandscape] = useState(false);
  const [color, setColor] = useState(COLORS[1].value);
  const [width, setWidth] = useState(3);
  const [tool, setTool] = useState<Tool>('pen');
  const [paper, setPaper] = useState<'a5' | 'a4'>('a5');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<HandwrittenPage | null>(null);
  const [printing, setPrinting] = useState(false);
  const [refresh, setRefresh] = useState(0);
  // Pad mode: full screen, the whole screen is the pad (pen at the pad's corner = the page's corner)
  const [padMode, setPadMode] = useState(false);

  useEffect(() => {
    const onChange = () => { if (!document.fullscreenElement) setPadMode(false); };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const leavePad = () => {
    setPadMode(false);
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => undefined);
  };
  const enterPad = () => {
    setPadMode(true);
    void document.documentElement.requestFullscreen().catch(() => message.warning(t('handwriting.padNoFullscreen')));
  };

  const close = () => {
    leavePad();
    if (hasInk && !saved) {
      modal.confirm({ title: t('handwriting.unsavedAsk'), okText: t('handwriting.discard'), cancelText: t('common.cancel'), okButtonProps: { danger: true },
        onOk: () => { setHasInk(false); onClose(); } });
      return;
    }
    setSaved(null);
    onClose();
  };

  const save = async () => {
    const blob = await canvas.current?.exportPng();
    if (!blob) { message.warning(t('handwriting.nothing')); return; }
    setSaving(true);
    try {
      const body = new FormData();
      body.append('visit', visitId);
      body.append('paper', paper);
      body.append('ink', blob, 'ink.png');
      const { data } = await api.post<HandwrittenPage>('/handwritten-prescriptions/', body);
      setSaved(data);
      setHasInk(false);
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
    <Modal open={open} onCancel={close} footer={null} width={padMode ? '100vw' : 1040} centered={!padMode} destroyOnHidden maskClosable={false}
      closable={!padMode} wrapClassName={padMode ? 'hw-pad-wrap' : undefined} style={padMode ? { top: 0, margin: 0, maxWidth: '100vw', paddingBottom: 0 } : undefined}
      title={<span><EditOutlined /> {t('handwriting.title')} · {patientName}</span>}>
      {saved ? (
        <div className="hw-saved">
          <Alert type="success" showIcon message={t('handwriting.saved')} description={t('handwriting.savedHelp', { number: saved.number })} style={{ marginBottom: 12 }} />
          <div style={{ textAlign: 'center' }}><PrivateImage pageId={saved.id} width={Math.min(420, window.innerWidth - 120)} /></div>
          <Space style={{ marginTop: 12 }} wrap>
            <Button type="primary" icon={<PrinterOutlined />} onClick={() => setPrinting(true)}>{t('handwriting.print')}</Button>
            <Button icon={<EditOutlined />} onClick={another}>{t('handwriting.another')}</Button>
            <Button onClick={close}>{t('handwriting.done')}</Button>
          </Space>
          {printing && <DocumentModal kind="handwritten-rx" id={saved.id} title={t('handwriting.title')} onClose={() => setPrinting(false)} />}
        </div>
      ) : (
        <>
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
            <Segmented value={landscape ? 'l' : 'p'} onChange={(v) => setLandscape(v === 'l')}
              options={[{ value: 'p', label: t('handwriting.portrait') }, { value: 'l', label: t('handwriting.landscape') }]} />
            <Space size={6}>
              <span className="cell-sub">{t('handwriting.paper')}</span>
              <Segmented value={paper} onChange={(v) => setPaper(v as 'a5' | 'a4')} options={[{ value: 'a5', label: 'A5' }, { value: 'a4', label: 'A4' }]} />
            </Space>
            {padMode ? (
              <Button icon={<FullscreenExitOutlined />} onClick={leavePad}>{t('handwriting.padExit')}</Button>
            ) : (
              <Button icon={<FullscreenOutlined />} onClick={enterPad}>{t('handwriting.padMode')}</Button>
            )}
          </Space>
          <div className="hw-stage">
            <HandwritingCanvas ref={canvas} landscape={landscape} color={color} width={width} tool={tool}
              maxHeight={padMode ? Math.max(window.innerHeight - 190, 320) : Math.max(window.innerHeight - 330, 320)} padMode={padMode} onInkChange={setHasInk} />
          </div>
          <div className="hw-actions" data-hw-ui>
            <Typography.Text type="secondary" className="cell-sub">{padMode ? t('handwriting.padHint') : t('handwriting.hint')}</Typography.Text>
            <Button type="primary" size="large" icon={<SaveOutlined />} loading={saving} disabled={!hasInk} onClick={save}>
              {t('handwriting.save')}
            </Button>
          </div>
          {!padMode && <div style={{ marginTop: 16 }}>
            <Typography.Text strong><RedoOutlined /> {t('handwriting.earlier')}</Typography.Text>
            <div style={{ marginTop: 8 }}><HandwrittenPages visitId={visitId} refreshKey={refresh} /></div>
          </div>}
        </>
      )}
    </Modal>
  );
}

