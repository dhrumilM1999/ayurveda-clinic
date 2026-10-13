// "Labels" button on a stock batch: pharmacy stock labels (medicine, pack, MRP, GST, batch, expiry, barcode).
// One label per pack by default. Shows only when "Pharmacy stock labels" is on (Additional settings).
import { BarcodeOutlined } from '@ant-design/icons';
import { Button, InputNumber, Modal, Space } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { StockBatch } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { PdfModal } from '../../components/BillPreview';

const MAX_LABELS = 500;

export function StockLabelsButton({ batch, onPrinted }: { batch: StockBatch; onPrinted?: () => void }) {
  const { t } = useTranslation();
  const { hasFeature } = useAuth();
  const [asking, setAsking] = useState(false);
  const [copies, setCopies] = useState(1);
  const [layout, setLayout] = useState<string | null>(null);
  if (!hasFeature('pharmacy_stock_labels')) return null;

  const start = () => {
    setCopies(Math.min(MAX_LABELS, Math.max(1, Math.floor(Number(batch.quantity)))));
    setAsking(true);
  };
  const show = async () => {
    setAsking(false);
    try {
      const { data } = await api.get<{ code: string; value: string }[]>('/additional-choices/');
      setLayout(data.find((c) => c.code === 'stock_label_format')?.value ?? 'compact');
    } catch {
      setLayout('compact');
    }
  };

  return (
    <>
      <Button size="small" icon={<BarcodeOutlined />} onClick={start}>{t('stockLabels.button')}</Button>
      {asking && (
        <Modal open width={420} title={t('stockLabels.title', { name: batch.medicine_name })} onCancel={() => setAsking(false)}
          onOk={show} okText={t('stockLabels.show')} cancelText={t('common.cancel')} destroyOnHidden>
          <div className="form-help">{t('stockLabels.help')}</div>
          <Space>
            <span>{t('stockLabels.howMany')}</span>
            <InputNumber min={1} max={MAX_LABELS} precision={0} value={copies} onChange={(v) => setCopies(Number(v ?? 1))} />
          </Space>
        </Modal>
      )}
      {layout && (
        <PdfModal title={t('stockLabels.title', { name: batch.medicine_name })} fileName={`labels-${batch.batch_no}`}
          initial={layout} onClose={() => { setLayout(null); onPrinted?.(); }}
          choices={(['compact', 'standard'] as const).map((v) => ({ value: v, label: t(`stockLabels.size.${v}`) }))}
          fetchPdf={async (choice) => {
            const { data } = await api.get('/stock/labels/', { params: { items: `${batch.id}:${copies}`, layout: choice }, responseType: 'blob' });
            return data;
          }} />
      )}
    </>
  );
}
