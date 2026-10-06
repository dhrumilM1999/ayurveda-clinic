// PDF preview in a popup on the same screen (no new browser tab): bills, credit notes and medicine labels.
// Bills: the preview is not counted as a print; "Print" loads the real copy (later copies say DUPLICATE COPY).
import { DownloadOutlined, PrinterOutlined, TagsOutlined } from '@ant-design/icons';
import { App, Button, Modal, Segmented, Space, Spin } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';

type Kind = 'invoices' | 'credit-notes';
type Choice = { value: string; label: string };

/**
 * A PDF on screen with a choice (paper size or label format), Download and Print.
 * fetchPdf(choice, forPrint) returns the PDF; forPrint=true is the copy that is printed / downloaded.
 */
export function PdfModal({ title, choices, initial, fetchPdf, fileName, onClose, choices2, initial2 }: {
  title: string;
  choices: Choice[];
  initial: string;
  fetchPdf: (choice: string, forPrint: boolean, choice2: string) => Promise<Blob>;
  fileName: string;
  onClose: () => void;
  /** An optional second choice, e.g. the language of the print-out */
  choices2?: Choice[];
  initial2?: string;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [choice, setChoice] = useState(initial);
  const [choice2, setChoice2] = useState(initial2 ?? '');
  const [url, setUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState<'load' | 'print' | 'download' | null>('load');
  const frame = useRef<HTMLIFrameElement>(null);
  const printOnLoad = useRef(false);
  const fetchRef = useRef(fetchPdf);
  fetchRef.current = fetchPdf;

  const show = useCallback((blob: Blob) => {
    const next = URL.createObjectURL(blob);
    setUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return next;
    });
  }, []);

  useEffect(() => {
    let alive = true;
    setBusy('load');
    fetchRef.current(choice, false, choice2)
      .then((blob) => alive && show(blob))
      .catch((err) => message.error(errorMessage(err, t('common.loadFailed'))))
      .finally(() => alive && setBusy(null));
    return () => { alive = false; };
  }, [choice, choice2, show, message, t]);

  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  // Print: load the copy to print into the same frame, then open the print window
  const print = async () => {
    setBusy('print');
    try {
      printOnLoad.current = true;
      show(await fetchRef.current(choice, true, choice2));
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
      const file = URL.createObjectURL(await fetchRef.current(choice, true, choice2));
      const a = document.createElement('a');
      a.href = file;
      a.download = `${fileName}.pdf`.replace(/[/\\ ]+/g, '-');
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(file), 10_000);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Modal open width={920} title={title} onCancel={onClose} keyboard={false} maskClosable={false}
      className="bill-preview-modal"
      footer={(
        <div className="modal-footer-split">
          <Space size={8} wrap>
            <Segmented value={choice} onChange={(v) => setChoice(String(v))} disabled={!!busy} options={choices} />
            {choices2 && <Segmented value={choice2} onChange={(v) => setChoice2(String(v))} disabled={!!busy} options={choices2} />}
          </Space>
          <Space size={8}>
            <Button onClick={onClose}>{t('common.close')}</Button>
            <Button icon={<DownloadOutlined />} loading={busy === 'download'} disabled={!url} onClick={download}>{t('billing.download')}</Button>
            <Button type="primary" icon={<PrinterOutlined />} loading={busy === 'print'} disabled={!url} onClick={print}>{t('billing.print')}</Button>
          </Space>
        </div>
      )}>
      <div className="bill-preview-frame">
        {busy === 'load' && <Spin className="bill-preview-spin" />}
        {url && <iframe ref={frame} title={title} src={`${url}#toolbar=0&navpanes=0&view=FitH`} onLoad={onFrameLoad} />}
      </div>
    </Modal>
  );
}

async function blobOf(path: string, params: Record<string, unknown>): Promise<Blob> {
  const { data } = await api.get(path, { params, responseType: 'blob' });
  return data;
}

export function BillPreviewModal({ id, kind = 'invoices', title, onClose }: {
  id: string;
  kind?: Kind;
  title?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  return (
    <PdfModal title={title ?? t('billing.preview')} fileName={title ?? 'bill'} initial="a4" onClose={onClose}
      choices={[
        { value: 'a4', label: t('billing.paper.a4') },
        { value: 'a5', label: t('billing.paper.a5') },
        { value: '80mm', label: t('billing.paper.thermal') },
        { value: '58mm', label: t('billing.paper.thermal58') },
      ]}
      fetchPdf={(paper, forPrint) => blobOf(`/${kind}/${id}/pdf/`, { size: paper, ...(forPrint ? {} : { preview: 1 }) })} />
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

/**
 * "Labels" button: medicine labels for a sale (dispense) or a prescription, in the clinic's default label
 * format (Additional settings). Shows nothing while "Medicine labels" is switched off.
 */
export function LabelsButton({ dispense, prescription, size = 'small' }: {
  dispense?: string;
  prescription?: string;
  size?: 'small' | 'middle';
}) {
  const { t } = useTranslation();
  const { hasFeature } = useAuth();
  const [initial, setInitial] = useState<string | null>(null);
  if (!hasFeature('medicine_labels') || (!dispense && !prescription)) return null;
  const open = async () => {
    try {
      const { data } = await api.get<{ code: string; value: string }[]>('/additional-choices/');
      setInitial(data.find((c) => c.code === 'label_format')?.value ?? 'standard');
    } catch {
      setInitial('standard');
    }
  };
  return (
    <>
      <Button size={size} icon={<TagsOutlined />} onClick={open}>{t('labels.button')}</Button>
      {initial && (
        <PdfModal title={t('labels.title')} fileName="medicine-labels" initial={initial} onClose={() => setInitial(null)}
          choices={(['compact', 'standard', 'detailed'] as const).map((v) => ({ value: v, label: t(`additional.choices.label_format.options.${v}`) }))}
          fetchPdf={(layout) => blobOf('/medicine-labels/', { layout, ...(dispense ? { dispense } : { prescription }) })} />
      )}
    </>
  );
}

type DocKind = 'prescription' | 'follow-up-card' | 'prakriti' | 'certificate';

/** A medical document (prescription, follow-up card, Prakriti report, certificate) on screen, in the patient's
 *  language (can be changed), with paper size, Download and Print. Reprints say DUPLICATE COPY. */
export function DocumentModal({ kind, id, title, language, detail, onClose }: {
  kind: DocKind;
  id: string;
  title: string;
  language?: string;
  /** Prescription only: the detailed prescription (full check-up summary), A4 first */
  detail?: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const sizes: Record<DocKind, string[]> = {
    prescription: detail ? ['a4', 'a5'] : ['a5', 'a4'], 'follow-up-card': ['a6', 'a5'], prakriti: ['a4', 'a5'], certificate: ['a4', 'a5'],
  };
  return (
    <PdfModal title={title} fileName={detail ? 'prescription-detailed' : `${kind}`} initial={sizes[kind][0]} onClose={onClose}
      choices={sizes[kind].map((v) => ({ value: v, label: t(`print.size.${v}`) }))}
      choices2={(['en', 'gu', 'hi'] as const).map((v) => ({ value: v, label: t(`print.lang.${v}`) }))}
      initial2={language && ['en', 'gu', 'hi'].includes(language) ? language : 'en'}
      fetchPdf={(size, forPrint, lang) => blobOf(`/documents/${kind}/${id}/`, {
        size, lang, ...(detail ? { detail: 1 } : {}), ...(forPrint ? {} : { preview: 1 }),
      })} />
  );
}
