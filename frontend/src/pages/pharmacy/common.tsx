// Pieces shared by the pharmacy and billing screens.
import { BarcodeOutlined, DownOutlined, PrinterOutlined } from '@ant-design/icons';
import { App, Button, Dropdown, Input, Select, Spin, Tag } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { DispenseStatus, InvoiceStatus, Medicine, Page } from '../../api/types';

/** "12-2027" (expiry is printed as month-year) */
export function expiryText(date: string | null | undefined) {
  return date ? dayjs(date).format('MM-YYYY') : '—';
}

/** 2.000 -> "2", 0.500 -> "0.5" */
export function qty(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '—';
  return String(Number(value));
}

const DISPENSE_COLORS: Record<DispenseStatus, string> = { pending: 'gold', partly: 'blue', done: 'green' };
export function DispenseStatusTag({ status }: { status: DispenseStatus }) {
  const { t } = useTranslation();
  return <Tag color={DISPENSE_COLORS[status]} className="tag-tight">{t(`pharmacy.status.${status}`)}</Tag>;
}

const INVOICE_COLORS: Record<InvoiceStatus, string> = { unpaid: 'red', partly_paid: 'gold', paid: 'green', cancelled: 'default' };
export function InvoiceStatusTag({ status }: { status: InvoiceStatus }) {
  const { t } = useTranslation();
  return <Tag color={INVOICE_COLORS[status]} className="tag-tight">{t(`billing.status.${status}`)}</Tag>;
}

/**
 * Barcode box: a USB barcode scanner "types" the code and presses Enter, so it works like a keyboard.
 * You can also type a batch number and press Enter.
 */
export function ScanInput({ onScan, placeholder, autoFocus, width = 240 }: {
  onScan: (code: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  width?: number;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState('');
  return (
    <Input
      allowClear
      autoFocus={autoFocus}
      prefix={<BarcodeOutlined />}
      placeholder={placeholder ?? t('pharmacy.scanPlaceholder')}
      value={value}
      style={{ width }}
      onChange={(e) => setValue(e.target.value)}
      onPressEnter={() => { const code = value.trim(); if (code) { onScan(code); setValue(''); } }}
    />
  );
}

/** Opens a PDF from the API in a new tab (the PDF needs the login, so it is fetched first). */
export async function openPdf(url: string, onError: (msg: string) => void, fallback: string) {
  const tab = window.open('', '_blank');
  try {
    const { data } = await api.get(url, { responseType: 'blob' });
    const blobUrl = URL.createObjectURL(data);
    if (tab) tab.location.href = blobUrl;
    else window.location.href = blobUrl;
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  } catch (err) {
    tab?.close();
    onError(errorMessage(err, fallback));
  }
}

/** "Print" button with paper sizes. kind: invoices | credit-notes */
export function PrintButton({ id, kind = 'invoices', size = 'small', type }: {
  id: string;
  kind?: 'invoices' | 'credit-notes';
  size?: 'small' | 'middle';
  type?: 'primary' | 'default';
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const print = (paper: string) => openPdf(`/${kind}/${id}/pdf/?size=${paper}`, (m) => message.error(m), t('common.loadFailed'));
  return (
    <Dropdown trigger={['click']} menu={{
      items: [
        { key: 'a4', label: t('billing.paper.a4') },
        { key: 'a5', label: t('billing.paper.a5') },
        { key: '80mm', label: t('billing.paper.thermal') },
      ],
      onClick: ({ key }) => print(key),
    }}>
      <Button size={size} type={type} icon={<PrinterOutlined />}>{t('billing.print')} <DownOutlined /></Button>
    </Dropdown>
  );
}

/** Search the medicine list by any name, synonym or barcode. */
export function MedicinePicker({ value, label, onPick, size = 'small', placeholder }: {
  value?: string;
  label?: string;
  onPick: (m: Medicine) => void;
  size?: 'small' | 'middle';
  placeholder?: string;
}) {
  const { t } = useTranslation();
  const [options, setOptions] = useState<Medicine[]>([]);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number>();
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const search = (text: string) => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      setBusy(true);
      try {
        const { data } = await api.get<Page<Medicine>>('/medicines/', { params: { q: text || undefined, page_size: 20 } });
        setOptions(data.results);
      } finally {
        setBusy(false);
      }
    }, 250);
  };
  return (
    <Select size={size} showSearch filterOption={false} style={{ width: '100%' }} value={value}
      placeholder={placeholder ?? t('rx.searchMedicine')} onSearch={search} onFocus={() => !options.length && search('')}
      notFoundContent={busy ? <Spin size="small" /> : t('rx.noMedicine')}
      options={[
        ...(value && !options.some((m) => m.id === value) ? [{ value, label }] : []),
        ...options.map((m) => ({ value: m.id, label: `${m.name}${m.pack_size ? ` (${m.pack_size})` : ''}` })),
      ]}
      onChange={(id) => { const m = options.find((o) => o.id === id); if (m) onPick(m); }} />
  );
}
