// Sales (dispensed prescriptions) and sales returns: medicines brought back -> stock + credit note.
import { RollbackOutlined } from '@ant-design/icons';
import { App, Button, Checkbox, DatePicker, Form, Input, InputNumber, Modal, Segmented, Space, Spin, Table } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { InvoiceStatus, Page, SaleItem, SaleRow } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { PatientCell } from '../appointments/shared';
import { money } from '../medicines/shared';
import { InvoiceDrawer } from './BillsTab';
import { InvoiceStatusTag, PrintButton, qty } from './common';

export function SalesTab() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [day, setDay] = useState<Dayjs | null>(dayjs());
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<SaleRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [returning, setReturning] = useState<string | null>(null);
  const [bill, setBill] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Page<SaleRow>>('/sales/', {
        params: { page_size: 200, q: query || undefined, date: query || !day ? undefined : day.format('YYYY-MM-DD') },
      });
      setRows(data.results);
    } finally {
      setLoading(false);
    }
  }, [day, query]);
  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="filter-bar">
        <DatePicker value={day} onChange={setDay} format="ddd, DD-MM-YYYY" style={{ width: 170 }} placeholder={t('billing.anyDate')} />
        <Input.Search allowClear placeholder={t('billing.searchPlaceholder')} value={search} style={{ width: 260 }}
          onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }} onSearch={(v) => setQuery(v.trim())} />
        <span className="cell-sub">{t('pharmacy.salesHelp')}</span>
      </div>
      <Table<SaleRow>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: t('pharmacy.noSales') }}
        columns={[
          { title: t('pharmacy.when'), dataIndex: 'created_at', width: 130, render: (d: string) => dayjs(d).format('DD-MM-YY h:mm A') },
          { title: t('billing.billNo'), dataIndex: 'number', render: (v: string, r: SaleRow) => (r.invoice ? <a className="mono" onClick={() => setBill(r.invoice)}>{v}</a> : '—') },
          { title: t('appointments.patient'), key: 'p', render: (_: unknown, r: SaleRow) => <PatientCell patient={r.patient_detail} /> },
          { title: t('pharmacy.total'), dataIndex: 'total_amount', width: 120, align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
          { title: t('common.status'), dataIndex: 'invoice_status', width: 120, render: (s: InvoiceStatus | '') => (s ? <InvoiceStatusTag status={s} /> : '—') },
          {
            title: '', key: 'a', width: 200, align: 'right' as const,
            render: (_: unknown, r: SaleRow) => (
              <Space size={4}>
                {r.invoice && <PrintButton id={r.invoice} />}
                {can('pharmacy.dispense') && r.invoice_status !== 'cancelled' && (
                  <Button size="small" icon={<RollbackOutlined />} onClick={() => setReturning(r.id)}>{t('pharmacy.return')}</Button>
                )}
              </Space>
            ),
          },
        ]}
      />
      {returning && <ReturnModal saleId={returning} onClose={(saved) => { setReturning(null); if (saved) load(); }} />}
      {bill && <InvoiceDrawer id={bill} onClose={(changed) => { setBill(null); if (changed) load(); }} />}
    </>
  );
}

type Pick = { take: boolean; quantity: number; back: boolean };

function ReturnModal({ saleId, onClose }: { saleId: string; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [sale, setSale] = useState<SaleRow | null>(null);
  const [picks, setPicks] = useState<Record<string, Pick>>({});
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get<SaleRow>(`/sales/${saleId}/`).then(({ data }) => {
      setSale(data);
      setPicks(Object.fromEntries((data.items ?? []).map((i) => [i.id, { take: false, quantity: Number(i.quantity) - Number(i.returned_quantity), back: true }])));
    });
    form.setFieldsValue({ refund_mode: 'cash' });
  }, [saleId, form]);

  const set = (id: string, patch: Partial<Pick>) => setPicks((p) => ({ ...p, [id]: { ...p[id]!, ...patch } }));
  const left = (i: SaleItem) => Number(i.quantity) - Number(i.returned_quantity);
  const chosen = (sale?.items ?? []).filter((i) => picks[i.id]?.take && picks[i.id]!.quantity > 0);
  const value = chosen.reduce((s, i) => s + (Number(i.amount) * picks[i.id]!.quantity) / Number(i.quantity), 0);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const { data } = await api.post(`/sales/${saleId}/return/`, {
        ...values,
        items: chosen.map((i) => ({ dispense_item: i.id, quantity: picks[i.id]!.quantity, back_to_stock: picks[i.id]!.back })),
      });
      message.success(t('pharmacy.returnDone', { number: data.credit_note_number, amount: money(data.refund_amount) }));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open width={760} title={t('pharmacy.returnTitle', { number: sale?.number ?? '' })} onCancel={() => onClose(false)}
      onOk={save} okText={t('pharmacy.returnButton', { amount: money(value) })} okButtonProps={{ disabled: !chosen.length }}
      cancelText={t('common.cancel')} confirmLoading={saving} keyboard={false} maskClosable={false}>
      {!sale ? <Spin /> : (
        <>
          <div className="form-help">{t('pharmacy.returnHelp')}</div>
          <Table<SaleItem> size="small" rowKey="id" pagination={false} dataSource={sale.items}
            columns={[
              {
                title: '', key: 'take', width: 36,
                render: (_: unknown, i: SaleItem) => <Checkbox checked={picks[i.id]?.take} disabled={left(i) <= 0} onChange={(e) => set(i.id, { take: e.target.checked })} />,
              },
              {
                title: t('rx.medicine'), key: 'm',
                render: (_: unknown, i: SaleItem) => (
                  <div style={{ lineHeight: 1.35 }}>{i.medicine_name}
                    <div className="cell-sub">{t('pharmacy.batch')} {i.batch_no} · {t('pharmacy.sold')} {qty(i.quantity)}{Number(i.returned_quantity) ? ` · ${t('pharmacy.alreadyReturned', { n: qty(i.returned_quantity) })}` : ''}</div>
                  </div>
                ),
              },
              {
                title: t('pharmacy.qty'), key: 'q', width: 100,
                render: (_: unknown, i: SaleItem) => (
                  <InputNumber size="small" min={0.001} max={left(i)} value={picks[i.id]?.quantity} disabled={!picks[i.id]?.take}
                    style={{ width: 80 }} onChange={(v) => set(i.id, { quantity: Number(v ?? 0) })} />
                ),
              },
              {
                title: t('pharmacy.backToStock'), key: 'b', width: 150,
                render: (_: unknown, i: SaleItem) => (
                  <Segmented size="small" value={picks[i.id]?.back ? 'yes' : 'no'} disabled={!picks[i.id]?.take}
                    onChange={(v) => set(i.id, { back: v === 'yes' })}
                    options={[{ value: 'yes', label: t('pharmacy.sellable') }, { value: 'no', label: t('pharmacy.damagedShort') }]} />
                ),
              },
            ]} />
          <Form form={form} layout="vertical" requiredMark={false} style={{ marginTop: 12 }}>
            <Space size={12} align="start" wrap>
              <Form.Item name="reason" label={t('pharmacy.reason')} rules={[{ required: true, message: t('common.required') }]} style={{ width: 360 }}>
                <Input maxLength={200} placeholder={t('pharmacy.returnReasonPlaceholder')} />
              </Form.Item>
              <Form.Item name="refund_mode" label={t('billing.refundMode')}>
                <Segmented options={(['cash', 'upi', 'card'] as const).map((m) => ({ value: m, label: t(`billing.modes.${m}`) }))} />
              </Form.Item>
            </Space>
          </Form>
        </>
      )}
    </Modal>
  );
}
