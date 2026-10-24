// The handwritten prescription pages of one check-up (or of one patient): small pictures, click to enlarge,
// Print (same print window as every prescription) and Remove (for the doctor). Pictures are private: they are
// loaded through the API with the login, and every view is written to the audit log.
// SAFE TO EDIT: the words are in src/i18n/*.json under "handwriting".
import { DeleteOutlined, PrinterOutlined } from '@ant-design/icons';
import { App, Button, Empty, Image, Popconfirm, Space, Spin, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import type { HandwrittenPage } from '../../../api/types';
import { useAuth } from '../../../auth/AuthContext';
import { DocumentModal } from '../../../components/BillPreview';

/** A private picture shown through the API (needs the login, never a public link). */
export function PrivateImage({ pageId, kind = 'combined', width }: { pageId: string; kind?: 'combined' | 'ink'; width?: number }) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    let objectUrl: string | undefined;
    api.get(`/handwritten-prescriptions/${pageId}/image/`, { params: { kind }, responseType: 'blob' })
      .then(({ data }) => { objectUrl = URL.createObjectURL(data); setUrl(objectUrl); })
      .catch(() => setUrl(undefined));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [pageId, kind]);
  return url ? <Image src={url} width={width} alt="" /> : <Spin size="small" />;
}

export function HandwrittenPages({ visitId, patientId, prescriptionId, hideWhenEmpty, refreshKey = 0, onChanged }: {
  visitId?: string; patientId?: string; prescriptionId?: string; hideWhenEmpty?: boolean; refreshKey?: number; onChanged?: (count: number) => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [pages, setPages] = useState<HandwrittenPage[] | null>(null);
  const [printing, setPrinting] = useState<HandwrittenPage | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get<HandwrittenPage[]>('/handwritten-prescriptions/', {
        params: visitId ? { visit: visitId } : prescriptionId ? { prescription: prescriptionId } : { patient: patientId },
      });
      setPages(data);
      onChanged?.(data.length);
    } catch {
      setPages([]);
    }
  }, [visitId, patientId, prescriptionId, onChanged]);
  useEffect(() => { load(); }, [load, refreshKey]);

  const remove = async (page: HandwrittenPage) => {
    try {
      await api.delete(`/handwritten-prescriptions/${page.id}/`);
      message.success(t('handwriting.removed'));
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  if (pages === null) return <Spin size="small" />;
  if (!pages.length && hideWhenEmpty) return null;
  if (!pages.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('handwriting.noPages')} />;
  return (
    <>
      <div className="hw-pages">
        {pages.map((page, index) => (
          <figure key={page.id} className="hw-page">
            <PrivateImage pageId={page.id} width={150} />
            <figcaption>
              <Typography.Text strong>{t('handwriting.page', { n: index + 1 })}</Typography.Text>
              <div className="cell-sub">{dayjs(page.created_at).format('DD-MM-YYYY HH:mm')} · {page.paper.toUpperCase()}</div>
              <Space size={4} style={{ marginTop: 4 }}>
                <Button size="small" icon={<PrinterOutlined />} onClick={() => setPrinting(page)}>{t('handwriting.print')}</Button>
                {can('prescriptions.create') && (
                  <Popconfirm title={t('handwriting.removeAsk')} okText={t('common.yes')} cancelText={t('common.no')} onConfirm={() => remove(page)}>
                    <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.remove')} />
                  </Popconfirm>
                )}
              </Space>
            </figcaption>
          </figure>
        ))}
      </div>
      {printing && <DocumentModal kind="handwritten-rx" id={printing.id} title={t('handwriting.title')} onClose={() => setPrinting(null)} />}
    </>
  );
}
