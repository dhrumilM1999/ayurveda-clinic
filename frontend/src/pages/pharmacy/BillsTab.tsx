// Pharmacy bills: day closing summary, bill list, bill detail with payments, UPI QR, print and cancel.
import { LeftOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons';
import {
  App, Button, DatePicker, Descriptions, Drawer, Form, Input, InputNumber, Modal, QRCode, Segmented, Space, Spin, Table,
  Tag, Typography,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { CreditNoteRecord, DaySummary, InvoiceRecord, InvoiceStatus, Page, PaymentMode } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { InvoiceStatusTag, PrintButton, expiryText, qty } from './common';

/** QR code to pay what is still due by UPI (needs the branch's UPI ID in Settings). */
export function UpiPayment({ invoiceId }: { invoiceId: string }) {
  const { t } = useTranslation();
  const [info, setInfo] = useState<{ link: string; amount: string; vpa: string } | null>(null);
  useEffect(() => {
    api.get(`/invoices/${invoiceId}/upi/`).then(({ data }) => setInfo(data)).catch(() => setInfo(null));
  }, [invoiceId]);
  if (!info) return null;
  if (!info.vpa) return <div className="cell-sub" style={{ textAlign: 'center' }}>{t('billing.noUpiId')}</div>;
  if (!info.link) return null;
  return (
    <div className="upi-box">
      <QRCode value={info.link} size={150} bordered={false} />
      <div>
        <b>{t('billing.scanToPay', { amount: money(info.amount) })}</b>
        <div className="cell-sub">{info.vpa}</div>
        <div className="cell-sub">{t('billing.upiHelp')}</div>
      </div>
    </div>
  );
}

function SummaryCards({ day, series }: { day: Dayjs; series?: string }) {
  const { t } = useTranslation();
  const [s, setS] = useState<DaySummary | null>(null);
  useEffect(() => {
    api.get<DaySummary>('/invoices/summary/', { params: { date: day.format('YYYY-MM-DD'), series } }).then(({ data }) => setS(data)).catch(() => setS(null));
  }, [day, series]);
  if (!s) return null;
  const tiles = [
    { label: t('billing.summary.bills'), value: `${s.invoice_count}`, sub: money(s.billed) },
    { label: t('billing.modes.cash'), value: money(s.received.cash), sub: Number(s.refunds.cash) ? `- ${money(s.refunds.cash)} ${t('billing.summary.refunded')}` : '' },
    { label: t('billing.modes.upi'), value: money(s.received.upi), sub: Number(s.refunds.upi) ? `- ${money(s.refunds.upi)} ${t('billing.summary.refunded')}` : '' },
    { label: t('billing.modes.card'), value: money(s.received.card), sub: Number(s.refunds.card) ? `- ${money(s.refunds.card)} ${t('billing.summary.refunded')}` : '' },
    { label: t('billing.summary.cashInHand'), value: money(s.cash_in_hand), sub: t('billing.summary.cashHelp'), strong: true },
    { label: t('billing.summary.due'), value: money(s.still_due), sub: `${t('billing.summary.gst')} ${money(Number(s.cgst) + Number(s.sgst))}` },
  ];
  return (
    <div className="summary-tiles">
      {tiles.map((tile) => (
        <div key={tile.label} className={`summary-tile${tile.strong ? ' strong' : ''}`}>
          <div className="summary-label">{tile.label}</div>
          <div className="summary-value num">{tile.value}</div>
          <div className="cell-sub">{tile.sub || ' '}</div>
        </div>
      ))}
    </div>
  );
}

type Series = 'PH' | 'OP' | 'all';

/** Bills of one day with the day closing. series: PH (pharmacy tab), OP, or all with a filter (Billing screen). */
export function BillsTab({ series: fixed = 'PH', seriesFilter = false, version: outside = 0 }: { series?: Series; seriesFilter?: boolean; version?: number }) {
  const { t } = useTranslation();
  const [series, setSeries] = useState<Series>(fixed);
  const [day, setDay] = useState<Dayjs>(dayjs());
  const [status, setStatus] = useState<'all' | InvoiceStatus>('all');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<InvoiceRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Page<InvoiceRecord>>('/invoices/', {
        params: { series: series === 'all' ? undefined : series, page_size: 200, ...(query ? { q: query } : { date: day.format('YYYY-MM-DD') }),
          ...(status === 'all' ? {} : { status }) },
      });
      setRows(data.results);
    } finally {
      setLoading(false);
    }
  }, [day, status, query, series]);
  useEffect(() => { load(); }, [load, version, outside]);

  return (
    <>
      <div className="filter-bar">
        <Space.Compact>
          <Button icon={<LeftOutlined />} onClick={() => setDay(day.subtract(1, 'day'))} aria-label={t('appointments.prevDay')} />
          <DatePicker value={day} onChange={(d) => d && setDay(d)} format="ddd, DD-MM-YYYY" allowClear={false} style={{ width: 170 }} />
          <Button icon={<RightOutlined />} onClick={() => setDay(day.add(1, 'day'))} aria-label={t('appointments.nextDay')} />
        </Space.Compact>
        {seriesFilter && (
          <Segmented value={series} onChange={(v) => setSeries(v as Series)}
            options={[
              { value: 'all', label: t('billing.kinds.all') },
              { value: 'OP', label: t('billing.kinds.OP') },
              { value: 'PH', label: t('billing.kinds.PH') },
            ]} />
        )}
        <Segmented value={status} onChange={(v) => setStatus(v as typeof status)}
          options={(['all', 'unpaid', 'partly_paid', 'paid', 'cancelled'] as const).map((k) => ({
            value: k, label: k === 'all' ? t('appointments.filters.all') : t(`billing.status.${k}`),
          }))} />
        <Input.Search allowClear placeholder={t('billing.searchPlaceholder')} value={search} style={{ width: 240 }}
          onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }} onSearch={(v) => setQuery(v.trim())} />
        <Button icon={<ReloadOutlined />} onClick={() => setVersion((v) => v + 1)} aria-label={t('appointments.refresh')} />
      </div>
      {!query && <SummaryCards key={`${day.format()}-${version}-${outside}`} day={day} series={series === 'all' ? undefined : series} />}
      <Table<InvoiceRecord>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: t('billing.empty') }}
        onRow={(r) => ({ onClick: () => setOpen(r.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('billing.billNo'), dataIndex: 'number', render: (v: string) => <b className="mono">{v}</b> },
          ...(seriesFilter ? [{
            title: t('billing.kind'), dataIndex: 'series', width: 110,
            render: (v: string) => <Tag color={v === 'OP' ? 'blue' : 'purple'} className="tag-tight">{t(`billing.kinds.${v}`)}</Tag>,
          }] : []),
          { title: t('appointments.date'), dataIndex: 'invoice_date', width: 110, render: (d: string) => dayjs(d).format('DD-MM-YYYY') },
          {
            title: t('appointments.patient'), key: 'p',
            render: (_: unknown, r: InvoiceRecord) => (
              <div style={{ lineHeight: 1.35 }}>{r.customer_name}<div className="cell-sub">{r.patient_detail?.uhid}</div></div>
            ),
          },
          { title: t('pharmacy.total'), dataIndex: 'total_amount', width: 120, align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
          {
            title: t('billing.due'), dataIndex: 'balance', width: 110, align: 'right' as const,
            render: (v: string) => (Number(v) > 0 ? <span className="num text-out">{money(v)}</span> : <span className="cell-sub">—</span>),
          },
          { title: t('common.status'), dataIndex: 'status', width: 120, render: (s: InvoiceStatus) => <InvoiceStatusTag status={s} /> },
          {
            title: '', key: 'print', width: 110, align: 'right' as const,
            render: (_: unknown, r: InvoiceRecord) => <span onClick={(e) => e.stopPropagation()}><PrintButton id={r.id} /></span>,
          },
        ]}
      />
      {open && <InvoiceDrawer id={open} onClose={(changed) => { setOpen(null); if (changed) setVersion((v) => v + 1); }} />}
    </>
  );
}

export function InvoiceDrawer({ id, onClose }: { id: string; onClose: (changed: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [inv, setInv] = useState<InvoiceRecord | null>(null);
  const [changed, setChanged] = useState(false);
  const [payOpen, setPayOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  const load = useCallback(() => {
    api.get<InvoiceRecord>(`/invoices/${id}/`).then(({ data }) => setInv(data)).catch((err) => message.error(errorMessage(err, t('common.loadFailed'))));
  }, [id, message, t]);
  useEffect(() => { load(); }, [load]);
  const after = () => { setChanged(true); load(); };

  return (
    <Drawer open width={720} onClose={() => onClose(changed)} title={inv ? t('billing.billTitle', { number: inv.number }) : ''}
      extra={inv && (
        <Space>
          {can('billing.create') && inv.status !== 'cancelled' && Number(inv.balance) > 0 && (
            <Button type="primary" onClick={() => setPayOpen(true)}>{t('billing.takePayment')}</Button>
          )}
          <PrintButton id={inv.id} size="middle" />
        </Space>
      )}>
      {!inv ? <Spin /> : (
        <>
          <Descriptions size="small" column={2} bordered items={[
            { key: 'p', label: t('appointments.patient'), children: `${inv.customer_name} ${inv.patient_detail ? `· ${inv.patient_detail.uhid}` : ''}` },
            { key: 'd', label: t('appointments.date'), children: dayjs(inv.invoice_date).format('DD-MM-YYYY') },
            { key: 's', label: t('common.status'), children: <InvoiceStatusTag status={inv.status} /> },
            { key: 'b', label: t('billing.madeBy'), children: inv.created_by_name },
          ]} />
          {inv.status === 'cancelled' && <div className="cell-sub" style={{ marginTop: 8 }}>{t('billing.cancelledBecause', { reason: inv.cancel_reason })}</div>}

          <div className="section-title">{t('billing.items')}</div>
          <Table size="small" rowKey="id" pagination={false} dataSource={inv.lines} scroll={{ x: 600 }}
            columns={[
              {
                title: t('billing.item'), key: 'd',
                render: (_: unknown, l: NonNullable<InvoiceRecord['lines']>[number]) => (
                  <div style={{ lineHeight: 1.35 }}>
                    {l.description}
                    {l.batch_no && <div className="cell-sub">{t('pharmacy.batch')} {l.batch_no} · {t('pharmacy.exp')} {expiryText(l.expiry_date)}</div>}
                    {Number(l.credited_quantity) > 0 && <Tag color="purple" className="tag-tight" style={{ marginInlineStart: 0 }}>{t('billing.returned', { n: qty(l.credited_quantity) })}</Tag>}
                  </div>
                ),
              },
              { title: t('pharmacy.qty'), key: 'q', width: 90, align: 'right' as const, render: (_: unknown, l: NonNullable<InvoiceRecord['lines']>[number]) => `${qty(l.quantity)} ${l.unit_label}` },
              { title: t('billing.rate'), dataIndex: 'unit_price', width: 90, align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
              { title: 'GST', dataIndex: 'gst_rate', width: 60, align: 'right' as const, render: (v: string) => `${qty(v)}%` },
              { title: t('pharmacy.amount'), dataIndex: 'total_amount', width: 100, align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
            ]} />

          <div className="bill-totals">
            {Number(inv.discount_amount) > 0 && <><span>{t('pharmacy.discount')}</span><span className="num">- {money(inv.discount_amount)}</span></>}
            <span>{t('billing.taxable')}</span><span className="num">{money(inv.taxable_amount)}</span>
            <span>CGST + SGST</span><span className="num">{money(Number(inv.cgst_amount) + Number(inv.sgst_amount))}</span>
            {Number(inv.round_off) !== 0 && <><span>{t('billing.roundOff')}</span><span className="num">{money(inv.round_off)}</span></>}
            <b>{t('pharmacy.total')}</b><b className="num">{money(inv.total_amount)}</b>
            <span>{t('billing.paid')}</span><span className="num">{money(inv.paid_amount)}</span>
            {Number(inv.credited_amount) > 0 && <><span>{t('billing.credited')}</span><span className="num">- {money(inv.credited_amount)}</span></>}
            {Number(inv.refunded_amount) > 0 && <><span>{t('billing.refunded')}</span><span className="num">{money(inv.refunded_amount)}</span></>}
            <b>{t('billing.due')}</b><b className={`num${Number(inv.balance) > 0 ? ' text-out' : ''}`}>{money(inv.balance)}</b>
          </div>

          {inv.status !== 'cancelled' && Number(inv.balance) > 0 && <UpiPayment invoiceId={inv.id} />}

          {inv.payments && inv.payments.length > 0 && (
            <>
              <div className="section-title">{t('billing.payments')}</div>
              <Table size="small" rowKey="id" pagination={false} dataSource={inv.payments}
                columns={[
                  { title: t('pharmacy.when'), dataIndex: 'paid_at', render: (d: string) => dayjs(d).format('DD-MM-YY HH:mm') },
                  { title: t('billing.mode'), dataIndex: 'mode', render: (m: PaymentMode) => t(`billing.modes.${m}`) },
                  { title: t('billing.reference'), dataIndex: 'reference', render: (v: string) => v || '—' },
                  { title: t('billing.receivedBy'), dataIndex: 'received_by' },
                  { title: t('pharmacy.amount'), dataIndex: 'amount', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
                ]} />
            </>
          )}

          {inv.credit_notes && inv.credit_notes.length > 0 && (
            <>
              <div className="section-title">{t('billing.creditNotes')}</div>
              <Table<CreditNoteRecord> size="small" rowKey="id" pagination={false} dataSource={inv.credit_notes}
                columns={[
                  { title: t('billing.noteNo'), dataIndex: 'number', render: (v: string) => <span className="mono">{v}</span> },
                  { title: t('pharmacy.reason'), dataIndex: 'reason' },
                  { title: t('pharmacy.amount'), dataIndex: 'total_amount', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
                  {
                    title: t('billing.refunded'), key: 'r', align: 'right' as const,
                    render: (_: unknown, n: CreditNoteRecord) => (Number(n.refund_amount) ? `${money(n.refund_amount)} (${t(`billing.modes.${n.refund_mode}`)})` : '—'),
                  },
                  { title: '', key: 'print', width: 110, align: 'right' as const, render: (_: unknown, n: CreditNoteRecord) => <PrintButton id={n.id} kind="credit-notes" /> },
                ]} />
            </>
          )}

          {can('billing.refund') && inv.status !== 'cancelled' && (
            <div style={{ marginTop: 16 }}>
              <Button danger onClick={() => setCancelOpen(true)}>{t('billing.cancelBill')}</Button>
              <div className="cell-sub" style={{ marginTop: 4 }}>{inv.lines?.some((l) => l.kind === 'medicine') ? t('billing.cancelHelp') : t('billing.cancelHelpNoMedicine')}</div>
            </div>
          )}
        </>
      )}
      {payOpen && inv && <PaymentModal invoice={inv} onClose={(saved) => { setPayOpen(false); if (saved) after(); }} />}
      {cancelOpen && inv && <CancelModal invoice={inv} onClose={(saved) => { setCancelOpen(false); if (saved) after(); }} />}
    </Drawer>
  );
}

function PaymentModal({ invoice, onClose }: { invoice: InvoiceRecord; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const mode: PaymentMode = Form.useWatch('mode', form) ?? 'cash';
  useEffect(() => { form.setFieldsValue({ mode: 'cash', amount: Number(invoice.balance) }); }, [form, invoice.balance]);
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post(`/invoices/${invoice.id}/pay/`, values);
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal open keyboard={false} maskClosable={false} width={440} title={t('billing.takePayment')} onCancel={() => onClose(false)} onOk={save}
      okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}>
      <div className="form-help">{t('billing.dueNow', { amount: money(invoice.balance) })}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="mode" label={t('billing.mode')}>
          <Segmented options={(['cash', 'upi', 'card'] as const).map((m) => ({ value: m, label: t(`billing.modes.${m}`) }))} />
        </Form.Item>
        <Form.Item name="amount" label={t('pharmacy.amount')} rules={[{ required: true, message: t('common.required') }]}>
          <InputNumber min={0.01} max={Number(invoice.balance)} prefix="₹" precision={2} style={{ width: 180 }} />
        </Form.Item>
        {mode !== 'cash' && (
          <Form.Item name="reference" label={t('billing.reference')}><Input maxLength={100} /></Form.Item>
        )}
      </Form>
    </Modal>
  );
}

function CancelModal({ invoice, onClose }: { invoice: InvoiceRecord; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  useEffect(() => { form.setFieldsValue({ refund_mode: 'cash' }); }, [form]);
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post(`/invoices/${invoice.id}/cancel/`, values);
      message.success(t('billing.cancelled'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };
  const paid = Number(invoice.paid_amount) - Number(invoice.refunded_amount);
  return (
    <Modal open keyboard={false} maskClosable={false} width={460} title={t('billing.cancelBill')} onCancel={() => onClose(false)} onOk={save}
      okText={t('billing.cancelBill')} okButtonProps={{ danger: true }} cancelText={t('common.close')} confirmLoading={saving}>
      <div className="form-help">{t('billing.cancelConfirmHelp')}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="reason" label={t('pharmacy.reason')} rules={[{ required: true, message: t('common.required') }]}>
          <Input maxLength={200} />
        </Form.Item>
        {paid > 0 && (
          <Form.Item name="refund_mode" label={t('billing.refundBy', { amount: money(paid) })}>
            <Segmented options={(['cash', 'upi', 'card'] as const).map((m) => ({ value: m, label: t(`billing.modes.${m}`) }))} />
          </Form.Item>
        )}
      </Form>
      <Typography.Text type="secondary">{t('billing.neverDeleted')}</Typography.Text>
    </Modal>
  );
}
