// Supplier dues: what the clinic owes each distributor (medicines bought on credit), payments, and the full ledger.
// SAFE TO EDIT: the words are in src/i18n/*.json under "dues".
import { Alert, App, Button, Card, DatePicker, Drawer, Form, Input, InputNumber, Modal, Select, Space, Statistic, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { SupplierAccount, SupplierAccountRow, SupplierInvoice } from '../../api/types';
import { ListEmpty } from '../../components/ListEmpty';
import { money } from '../medicines/shared';

const MODES = ['cash', 'upi', 'bank', 'cheque', 'other'];

export function SupplierDuesTab() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<SupplierAccountRow[]>([]);
  const [totals, setTotals] = useState({ owed: '0', overdue: '0' });
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    api.get<{ total_owed: string; total_overdue: string; suppliers: SupplierAccountRow[] }>('/supplier-accounts/')
      .then(({ data }) => { setRows(data.suppliers); setTotals({ owed: data.total_owed, overdue: data.total_overdue }); setFailed(false); })
      .catch(() => { setRows([]); setFailed(true); })
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="form-help">{t('dues.help')}</div>
      <Space size={12} wrap style={{ marginBottom: 12 }}>
        <Card size="small"><Statistic title={t('dues.totalOwed')} value={Number(totals.owed)} precision={2} prefix="₹" /></Card>
        <Card size="small"><Statistic title={t('dues.totalOverdue')} value={Number(totals.overdue)} precision={2} prefix="₹"
          valueStyle={{ color: Number(totals.overdue) > 0 ? '#c2412d' : undefined }} /></Card>
      </Space>
      <Table<SupplierAccountRow>
        rowKey="id" loading={loading} dataSource={rows} pagination={false} size="middle"
        locale={{ emptyText: <ListEmpty failed={failed} onRetry={load} text={t('dues.none')} /> }}
        onRow={(r) => ({ onClick: () => setOpenId(r.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('pharmacy.supplier'), dataIndex: 'name', render: (v: string, r) => <div><b>{v}</b><div className="cell-sub">{r.phone}</div></div> },
          { title: t('dues.owed'), dataIndex: 'balance', align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
          { title: t('dues.overdue'), key: 'o', align: 'right' as const, render: (_: unknown, r) => (
            Number(r.ageing.overdue) > 0 ? <span className="num" style={{ color: '#c2412d' }}>{money(r.ageing.overdue)}</span> : <span className="cell-sub">—</span>) },
          { title: t('dues.notDue'), key: 'c', align: 'right' as const, render: (_: unknown, r) => <span className="num">{money(r.ageing.current)}</span> },
          { title: t('dues.lastPayment'), dataIndex: 'last_payment', render: (d: string | null) => (d ? dayjs(d).format('DD-MM-YYYY') : '—') },
          { title: t('dues.terms'), dataIndex: 'payment_terms_days', render: (d: number | null) => (d ? t('dues.days', { n: d }) : '—') },
        ]}
      />
      {openId && <SupplierDrawer id={openId} onClose={() => { setOpenId(null); load(); }} />}
    </>
  );
}

function SupplierDrawer({ id, onClose }: { id: string; onClose: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [data, setData] = useState<SupplierAccount | null>(null);
  const [paying, setPaying] = useState(false);
  const [openingOpen, setOpeningOpen] = useState(false);
  const [reversing, setReversing] = useState<string | null>(null);
  const [reason, setReason] = useState('');

  const load = useCallback(() => {
    api.get<SupplierAccount>(`/supplier-accounts/${id}/`).then(({ data: d }) => setData(d)).catch(() => setData(null));
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const reverse = async () => {
    try {
      await api.post(`/supplier-payments/${reversing}/reverse/`, { reason });
      message.success(t('common.saved'));
      setReversing(null); setReason(''); load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const status = (i: SupplierInvoice) => (
    <Tag bordered={false} color={i.status === 'paid' ? 'green' : i.status === 'partly' ? 'gold' : 'red'}>{t(`dues.status.${i.status}`)}</Tag>
  );

  return (
    <Drawer open width={760} onClose={onClose} title={data?.name ?? ''} destroyOnHidden>
      {data && (
        <>
          <Space size={12} wrap style={{ marginBottom: 12 }}>
            <Card size="small"><Statistic title={t('dues.owed')} value={Number(data.balance)} precision={2} prefix="₹" /></Card>
            <Card size="small"><Statistic title={t('dues.billed')} value={Number(data.billed)} precision={2} prefix="₹" /></Card>
            <Card size="small"><Statistic title={t('dues.paid')} value={Number(data.paid)} precision={2} prefix="₹" /></Card>
            {Number(data.returned) > 0 && <Card size="small"><Statistic title={t('dues.returned')} value={Number(data.returned)} precision={2} prefix="₹" /></Card>}
          </Space>
          <Space wrap style={{ marginBottom: 12 }}>
            <Button type="primary" disabled={Number(data.balance) <= 0} onClick={() => setPaying(true)}>{t('dues.pay')}</Button>
            <Button onClick={() => setOpeningOpen(true)}>{t('dues.openingBalance')}{Number(data.opening) ? `: ${money(data.opening)}` : ''}</Button>
          </Space>
          {Number(data.ageing.overdue) > 0 && <Alert type="error" showIcon style={{ marginBottom: 12 }} message={t('dues.overdueAlert', { amount: money(data.ageing.overdue) })} />}

          <Typography.Title level={5}>{t('dues.invoices')}</Typography.Title>
          <Table<SupplierInvoice> rowKey="id" size="small" pagination={false} dataSource={[...data.invoices].reverse()}
            locale={{ emptyText: t('dues.noInvoices') }}
            columns={[
              { title: t('pharmacy.invoiceNo'), dataIndex: 'invoice_no', render: (v: string) => v || '—' },
              { title: t('pharmacy.invoiceDate'), dataIndex: 'invoice_date', render: (d: string) => dayjs(d).format('DD-MM-YYYY') },
              { title: t('dues.dueOn'), dataIndex: 'due_date', render: (d: string, i) => (
                <span style={{ color: i.days_overdue > 0 ? '#c2412d' : undefined }}>{dayjs(d).format('DD-MM-YYYY')}{i.days_overdue > 0 ? ` (${t('dues.lateDays', { n: i.days_overdue })})` : ''}</span>) },
              { title: t('dues.billed'), dataIndex: 'payable', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
              { title: t('dues.paid'), dataIndex: 'paid', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
              { title: t('dues.stillDue'), dataIndex: 'balance', align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
              { title: '', key: 's', render: (_: unknown, i) => status(i) },
            ]} />

          <Typography.Title level={5} style={{ marginTop: 16 }}>{t('dues.ledger')}</Typography.Title>
          <Table rowKey={(e) => `${e.kind}-${e.id}-${e.date}-${e.label}`} size="small" pagination={false} dataSource={data.entries}
            columns={[
              { title: t('appointments.date'), dataIndex: 'date', width: 110, render: (d: string) => dayjs(d).format('DD-MM-YYYY') },
              { title: t('dues.entry'), dataIndex: 'label', render: (v: string, e) => (
                <span style={e.reversed ? { textDecoration: 'line-through', opacity: 0.6 } : undefined}>
                  {v}{e.reversed ? ` (${t('dues.reversed')})` : ''}
                  {e.kind === 'payment' && !e.reversed && <Button size="small" type="link" onClick={(ev) => { ev.stopPropagation(); setReversing(e.id); }}>{t('dues.reverse')}</Button>}
                </span>) },
              { title: t('dues.bill'), dataIndex: 'debit', align: 'right' as const, render: (v: string) => (Number(v) ? <span className="num">{money(v)}</span> : '') },
              { title: t('dues.credit'), dataIndex: 'credit', align: 'right' as const, render: (v: string) => (Number(v) ? <span className="num">{money(v)}</span> : '') },
              { title: t('dues.balance'), dataIndex: 'balance', align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
            ]} />
        </>
      )}
      {paying && data && <PayModal data={data} onClose={(saved) => { setPaying(false); if (saved) load(); }} />}
      {openingOpen && data && <OpeningModal data={data} onClose={(saved) => { setOpeningOpen(false); if (saved) load(); }} />}
      <Modal open={!!reversing} title={t('dues.reversePayment')} okText={t('dues.reverse')} cancelText={t('common.cancel')}
        onCancel={() => { setReversing(null); setReason(''); }} onOk={reverse} okButtonProps={{ danger: true, disabled: !reason.trim() }}>
        <div className="form-help">{t('dues.reverseHelp')}</div>
        <Input maxLength={200} placeholder={t('dues.reason')} value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </Drawer>
  );
}

function PayModal({ data, onClose }: { data: SupplierAccount; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const open = data.invoices.filter((i) => Number(i.balance) > 0);

  useEffect(() => { form.setFieldsValue({ amount: Number(data.balance), mode: 'cash', payment_date: dayjs() }); }, [form, data.balance]);

  const save = async () => {
    const v = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/supplier-payments/', {
        supplier: data.id, amount: v.amount, mode: v.mode, payment_date: v.payment_date.format('YYYY-MM-DD'),
        reference: v.reference ?? '', notes: v.notes ?? '', purchase_ids: v.invoices?.length ? v.invoices : undefined,
      });
      message.success(t('dues.paymentSaved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open title={t('dues.payTo', { name: data.name })} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}
      onOk={save} onCancel={() => onClose(false)} maskClosable={false}>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="amount" label={`${t('dues.amount')} (${t('dues.owedNow', { amount: money(data.balance) })})`} rules={[{ required: true, message: t('common.required') }]}>
          <InputNumber min={0.01} max={Number(data.balance)} precision={2} prefix="₹" style={{ width: '100%' }} />
        </Form.Item>
        <Space style={{ width: '100%' }} size={12} align="start">
          <Form.Item name="mode" label={t('dues.mode')}>
            <Select style={{ width: 160 }} options={MODES.map((m) => ({ value: m, label: t(`dues.modes.${m}`) }))} />
          </Form.Item>
          <Form.Item name="payment_date" label={t('appointments.date')} rules={[{ required: true, message: t('common.required') }]}>
            <DatePicker format="DD-MM-YYYY" allowClear={false} disabledDate={(d) => d.isAfter(dayjs(), 'day')} />
          </Form.Item>
        </Space>
        <Form.Item name="reference" label={t('dues.reference')}><Input maxLength={60} /></Form.Item>
        <Form.Item name="invoices" label={t('dues.whichInvoices')} extra={t('dues.whichInvoicesHelp')}>
          <Select mode="multiple" allowClear placeholder={t('dues.oldestFirst')}
            options={open.map((i) => ({ value: i.id, label: `${i.invoice_no || t('dues.noNumber')} · ${dayjs(i.invoice_date).format('DD-MM-YYYY')} · ${money(i.balance)}` }))} />
        </Form.Item>
        <Form.Item name="notes" label={t('dues.note')}><Input maxLength={300} /></Form.Item>
      </Form>
    </Modal>
  );
}

function OpeningModal({ data, onClose }: { data: SupplierAccount; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [amount, setAmount] = useState<number>(Number(data.opening));
  const [saving, setSaving] = useState(false);
  const save = async () => {
    setSaving(true);
    try {
      await api.post(`/supplier-accounts/${data.id}/opening/`, { amount });
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal open title={t('dues.openingBalance')} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}
      onOk={save} onCancel={() => onClose(false)}>
      <div className="form-help">{t('dues.openingHelp')}</div>
      <InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }} value={amount} onChange={(v) => setAmount(v ?? 0)} />
    </Modal>
  );
}
