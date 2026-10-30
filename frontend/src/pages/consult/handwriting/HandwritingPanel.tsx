// The handwriting panel: the A4 page on the right side of the check-up screen. Drag its left edge to make it wider or
// narrower (the page always keeps its A4 shape and is never stretched). It stays mounted when closed, so nothing written is lost.
// SAFE TO EDIT: the words are in src/i18n/*.json under "handwriting"; the size limits are in panelSize.ts.
import { CloseOutlined, EditOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { clampPanelWidth } from './panelSize';
import { HandwritingSection } from './HandwritingSection';

export function HandwritingPanel({ open, width, workspaceRef, visitId, onWidth, onClose }: {
  open: boolean;
  width: number;
  workspaceRef: React.RefObject<HTMLElement>;
  visitId: string;
  onWidth: (width: number) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const drag = useRef<{ x: number; width: number } | null>(null);

  const onDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { x: e.clientX, width };
  };
  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const total = workspaceRef.current?.clientWidth ?? window.innerWidth;
    onWidth(clampPanelWidth(drag.current.width + (drag.current.x - e.clientX), total)); // dragging left makes it wider
  };
  const onUp = () => { drag.current = null; };

  return (
    <aside className="hw-panel" hidden={!open}>
      <div className="hw-resize" role="separator" aria-orientation="vertical" aria-label={t('handwriting.resize')} title={t('handwriting.resize')}
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp} />
      <div className="hw-panel-head">
        <b><EditOutlined /> {t('handwriting.title')}</b>
        <Button size="small" type="text" icon={<CloseOutlined />} onClick={onClose} aria-label={t('handwriting.hidePanel')} title={t('handwriting.hidePanel')} />
      </div>
      <HandwritingSection visitId={visitId} />
    </aside>
  );
}
