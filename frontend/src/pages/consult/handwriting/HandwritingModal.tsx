// "Handwriting" window of the doctor's check-up screen: a popup with one A4 page, written with the digital pad (or a tablet
// pen / touch screen / mouse). Press Save: the handwriting is kept as a picture, and ONE combined picture with the clinic
// letterhead is made for this patient's prescription. The page and the pad settings are in HandwritingSection.tsx.
// SAFE TO EDIT: the width of the window. The words are in src/i18n/*.json under "handwriting".
import { EditOutlined } from '@ant-design/icons';
import { App, Modal } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { HandwritingSection } from './HandwritingSection';

export function HandwritingModal({ open, visitId, patientName, onClose, onSaved }: {
  open: boolean; visitId: string; patientName: string; onClose: () => void; onSaved?: () => void;
}) {
  const { t } = useTranslation();
  const { modal } = App.useApp();
  const [hasInk, setHasInk] = useState(false);

  const close = () => {
    if (hasInk) {
      modal.confirm({ title: t('handwriting.unsavedAsk'), okText: t('handwriting.discard'), cancelText: t('common.cancel'), okButtonProps: { danger: true },
        onOk: () => { setHasInk(false); onClose(); } });
      return;
    }
    onClose();
  };

  // Esc is not used to close this window: in "whole pad" mode Esc switches that mode off instead
  return (
    <Modal open={open} onCancel={close} footer={null} width={860} centered destroyOnHidden maskClosable={false} keyboard={false}
      title={<span><EditOutlined /> {t('handwriting.title')} · {patientName}</span>}>
      <HandwritingSection visitId={visitId} heightOffset={90} onInkChange={setHasInk} onSaved={onSaved} />
    </Modal>
  );
}
