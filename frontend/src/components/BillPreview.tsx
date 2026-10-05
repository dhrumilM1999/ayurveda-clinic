// Bill / credit note preview in a popup on the same screen (no new browser tab).
// The preview is not counted as a print; "Print" makes the real copy (later copies say DUPLICATE COPY).
import { DownloadOutlined, PrinterOutlined } from '@ant-design/icons';
import { App, Button, Modal, Segmented, Space, Spin } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';

type Kind = 'invoices' | 'credit-notes';
type Paper = 'a4' | 'a5' | '80mm';

async function fetchPdf(kind: Kind, id: string, paper: Paper, preview: boolean): Promise<string> {
  const { data } = await api.get(`/${kind}/${id}/pdf/`, { params: { size: paper, ...(preview ? { preview: 1 } : {}) }, responseType: 'blob' });
  return URL.createObjectURL(data);
}

export function BillPreviewModal({ id, kind = 'invoices', title, onClose }: {
  id: string;
  kind?: Kind;
  title?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [paper, setPaper] = useState<Paper>('a4');
  const [url, setUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState<'load' | 'print' | 'download' | null>('load');
  const frame = useRef<HTMLIFrameElement>(null);
  const printOnLoad = useRef(false);

  const show = useCallback(async (next: string) => {
    setUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return next;
    });
  }, []);

  useEffect(() => {
    let alive = true;
    setBusy('load');
    fetchPdf(kind, id, paper, true)
      .then((u) => (alive ? show(u) : URL.revokeObjectURL(u)))
      .catch((err) => message.error(errorMessage(err, t('common.loadFailed'))))
      .finally(() => alive && setBusy(null));
    return () => { alive = false; };
  }, [kind, id, paper, show, message, t]);

  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  // Print: load the real (counted) copy into the same frame, then open the print window
  const print = async () => {
    setBusy('print');
    try {
      printOnLoad.current = true;
      await show(await fetchPdf(kind, id, paper, false));
    } catch (err) {
      printOnLoad.current = false;
      message.error(errorMessage(err, t('common.loadFailed')));
      setBusy(null);
    }
  };

  const onFrameLoad = () => {
    if (!printOnLoad.current) return;
    printOnLoad.current = false;
    setBusy(null);
    window.setTimeout(() => frame.current?.contentWindow?.print(), 300);
  };

  const download = async () => {
    setBusy('download');
    try {
      const file = await fetchPdf(kind, id, paper, false);
      const a = document.createElement('a');
      a.href = file;
      a.download = `${title ?? 'bill'}.pdf`.replace(/[/\\ ]+/g, '-');
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(file), 10_000);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Modal open width={920} title={title ?? t('billing.preview')} onCancel={onClose} keyboard={false} maskClosable={false}
      className="bill-preview-modal"
      footer={(
        <div className="modal-footer-split">
          <Segmented value={paper} onChange={(v) => setPaper(v as Paper)} disabled={!!busy}
            options={[
              { value: 'a4', label: t('billing.paper.a4') },
              { value: 'a5', label: t('billing.paper.a5') },
              { value: '80mm', label: t('billing.paper.thermal') },
            ]} />
          <Space size={8}>
            <Button onClick={onClose}>{t('common.close')}</Button>
            <Button icon={<DownloadOutlined />} loading={busy === 'download'} disabled={!url} onClick={download}>{t('billing.download')}</Button>
            <Button type="primary" icon={<PrinterOutlined />} loading={busy === 'print'} disabled={!url} onClick={print}>{t('billing.print')}</Button>
          </Space>
        </div>
      )}>
      <div className="bill-preview-frame">
        {busy === 'load' && <Spin className="bill-preview-spin" />}
        {url && <iframe ref={frame} title={title ?? t('billing.preview')} src={`${url}#toolbar=0&navpanes=0&view=FitH`} onLoad={onFrameLoad} />}
      </div>
    </Modal>
  );
}

/** "View / print" button: opens the bill preview popup. */
export function PrintButton({ id, kind = 'invoices', size = 'small', type, label, title }: {
  id: string;
  kind?: Kind;
  size?: 'small' | 'middle';
  type?: 'primary' | 'default';
  label?: string;
  title?: string;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button size={size} type={type} icon={<PrinterOutlined />} onClick={() => setOpen(true)}>{label ?? t('billing.viewPrint')}</Button>
      {open && <BillPreviewModal id={id} kind={kind} title={title} onClose={() => setOpen(false)} />}
    </>
  );
}
