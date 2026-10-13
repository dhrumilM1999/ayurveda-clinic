// Pieces shared by the pharmacy and billing screens.
import { BarcodeOutlined } from '@ant-design/icons';
import { Input, Select, Spin, Tag } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { DispenseLine, DispenseStatus, InvoiceStatus, Medicine, Page, ScanResult } from '../../api/types';

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

/**
 * A sale line made from a scanned (or picked) medicine that is not on a prescription:
 * used for extra medicines in a prescription sale and for every line of a counter sale.
 */
export function lineFromScan(scan: ScanResult): DispenseLine {
  return {
    id: `extra:${scan.medicine}`, medicine: scan.medicine, medicine_name: scan.name, dosage_form: '',
    pack_size: scan.pack_size, pack_type: '', allow_loose: scan.allow_loose, units_per_pack: scan.units_per_pack,
    unit_label: '', location: scan.location, dose: '', dose_unit: '', frequency: '', timing: '', anupana: '',
    duration: null, duration_unit: 'days', instructions: '', given: null, batches: scan.batches, extra: true,
  };
}

// The bill print button now opens a preview popup on the same screen (components/BillPreview.tsx)
export { PrintButton } from '../../components/BillPreview';

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
