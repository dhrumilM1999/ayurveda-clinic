// Record medicines received from a supplier: one line per medicine batch. Stock goes up when saved.
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Col, DatePicker, Form, Input, InputNumber, Modal, Row, Select, Spin } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Medicine, Page, Supplier } from '../../api/types';
import { money } from '../medicines/shared';

type Line = {
  key: number;
  medicine?: string;
  medicine_name?: string;
  batch_no: string;
  expiry?: Dayjs | null;
  quantity?: number;
  purchase_rate?: number;
  mrp?: number;
};

let nextKey = 1;
const emptyLine = (): Line => ({ key: nextKey++, batch_no: '' });

function MedicinePicker({ value, label, onPick }: { value?: string; label?: string; onPick: (m: Medicine) => void }) {
  const { t } = useTranslation();
  const [options, setOptions] = useState<Medicine[]>([]);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number>();
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
    <Select size="small" showSearch filterOption={false} style={{ width: '100%' }} value={value}
      placeholder={t('rx.searchMedicine')} onSearch={search} onFocus={() => !options.length && search('')}
      notFoundContent={busy ? <Spin size="small" /> : t('rx.noMedicine')}
      options={[
        ...(value && !options.some((m) => m.id === value) ? [{ value, label }] : []),
        ...options.map((m) => ({ value: m.id, label: `${m.name}${m.pack_size ? ` (${m.pack_size})` : ''}` })),
      ]}
      onChange={(id) => { const m = options.find((o) => o.id === id); if (m) onPick(m); }} />
  );
}

export function PurchaseModal({ onClose }: { onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [lines, setLines] = useState<Line[]>([emptyLine()]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    form.setFieldsValue({ invoice_date: dayjs() });
    api.get<Supplier[]>('/suppliers/').then(({ data }) => setSuppliers(data.filter((s) => s.is_active))).catch(() => setSuppliers([]));
  }, [form]);

  const update = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  const total = lines.reduce((sum, l) => sum + (l.quantity ?? 0) * (l.purchase_rate ?? 0), 0);
  const ready = lines.filter((l) => l.medicine && l.batch_no.trim() && l.quantity && l.mrp !== undefined);

  const save = async () => {
    const values = await form.validateFields();
    if (!ready.length) {
      message.warning(t('pharmacy.addLineFirst'));
      return;
    }
    setSaving(true);
    try {
      await api.post('/purchases/', {
        supplier: values.supplier ?? null,
        invoice_no: values.invoice_no ?? '',
        invoice_date: values.invoice_date.format('YYYY-MM-DD'),
        notes: values.notes ?? '',
        items: ready.map((l) => ({
          medicine: l.medicine, batch_no: l.batch_no, quantity: l.quantity, mrp: l.mrp,
          purchase_rate: l.purchase_rate ?? null,
          // Expiry is printed as month/year: keep the last day of that month
          expiry_date: l.expiry ? l.expiry.endOf('month').format('YYYY-MM-DD') : null,
        })),
      });
      message.success(t('pharmacy.purchaseSaved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open width={1000} title={t('pharmacy.addPurchase')} onCancel={() => onClose(false)} keyboard={false} maskClosable={false}
      footer={(
        <div className="modal-footer-split">
          <span className="total-text">{t('pharmacy.purchaseTotal')}: <b className="num">{money(total)}</b></span>
          <span>
            <Button onClick={() => onClose(false)}>{t('common.cancel')}</Button>
            <Button type="primary" loading={saving} onClick={save} style={{ marginInlineStart: 8 }}>
              {t('pharmacy.savePurchase', { count: ready.length })}
            </Button>
          </span>
        </div>
      )}>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Row gutter={12}>
          <Col xs={24} md={10}>
            <Form.Item name="supplier" label={t('pharmacy.supplier')} extra={!suppliers.length ? t('pharmacy.noSuppliersYet') : undefined}>
              <Select allowClear showSearch optionFilterProp="label" options={suppliers.map((s) => ({ value: s.id, label: s.name }))} />
            </Form.Item>
          </Col>
          <Col xs={12} md={7}><Form.Item name="invoice_no" label={t('pharmacy.invoiceNo')}><Input maxLength={60} /></Form.Item></Col>
          <Col xs={12} md={7}>
            <Form.Item name="invoice_date" label={t('pharmacy.invoiceDate')} rules={[{ required: true, message: t('common.required') }]}>
              <DatePicker format="DD-MM-YYYY" style={{ width: '100%' }} allowClear={false} />
            </Form.Item>
          </Col>
        </Row>
      </Form>

      <div className="purchase-lines">
        <div className="purchase-head">
          <span>{t('rx.medicine')}</span><span>{t('pharmacy.batch')}</span><span>{t('pharmacy.expiry')}</span>
          <span>{t('pharmacy.qty')}</span><span>{t('pharmacy.purchaseRate')}</span><span>MRP</span>
          <span className="right">{t('pharmacy.amount')}</span><span />
        </div>
        {lines.map((l) => (
          <div className="purchase-line" key={l.key}>
            <MedicinePicker value={l.medicine} label={l.medicine_name}
              onPick={(m) => update(l.key, { medicine: m.id, medicine_name: m.name, mrp: l.mrp ?? (m.branch_price ? Number(m.branch_price) : undefined) })} />
            <Input size="small" value={l.batch_no} maxLength={60} placeholder="B1234"
              onChange={(e) => update(l.key, { batch_no: e.target.value.toUpperCase() })} />
            <DatePicker size="small" picker="month" format="MM-YYYY" value={l.expiry ?? null} placeholder="MM-YYYY"
              onChange={(d) => update(l.key, { expiry: d })} />
            <InputNumber size="small" min={0.01} value={l.quantity} style={{ width: '100%' }} onChange={(v) => update(l.key, { quantity: v ?? undefined })} />
            <InputNumber size="small" min={0} precision={2} value={l.purchase_rate} style={{ width: '100%' }} onChange={(v) => update(l.key, { purchase_rate: v ?? undefined })} />
            <InputNumber size="small" min={0} precision={2} value={l.mrp} style={{ width: '100%' }} onChange={(v) => update(l.key, { mrp: v ?? undefined })} />
            <span className="num right">{money((l.quantity ?? 0) * (l.purchase_rate ?? 0))}</span>
            <Button size="small" type="text" icon={<DeleteOutlined />} disabled={lines.length === 1} aria-label={t('common.remove')}
              onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))} />
          </div>
        ))}
        <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={() => setLines((ls) => [...ls, emptyLine()])}>
          {t('pharmacy.addLine')}
        </Button>
      </div>
    </Modal>
  );
}
