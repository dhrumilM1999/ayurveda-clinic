// Today's final prescriptions of this branch -> give medicines (and, when switched on in Additional settings:
// make the bill, take payment, print, discounts, loose sale, barcode scan, rack location).
import { CheckCircleFilled, EnvironmentOutlined, LeftOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons';
import {
  Alert, App, Button, Checkbox, DatePicker, Input, InputNumber, Modal, Result, Segmented, Select, Space, Spin, Table,
  Tag, Typography,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { DispenseDetail, DispenseLine, DispenseQueueRow, DispenseStatus, PaymentMode, ScanResult } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { LabelsButton } from '../../components/BillPreview';
import { PatientCell } from '../appointments/shared';
import { money } from '../medicines/shared';
import { UpiPayment } from './BillsTab';
import { DispenseStatusTag, PrintButton, ScanInput, expiryText, lineFromScan, qty } from './common';

const REFRESH_SECONDS = 30;

export function DispenseTab() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [day, setDay] = useState<Dayjs>(dayjs());
  const [filter, setFilter] = useState<'all' | DispenseStatus>('all');
  const [rows, setRows] = useState<DispenseQueueRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<DispenseQueueRow[]>('/dispensing/', { params: { date: day.format('YYYY-MM-DD') } });
      setRows(data);
    } finally {
      setLoading(false);
    }
  }, [day]);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_SECONDS * 1000);
    return () => window.clearInterval(timer);
  }, [load]);

  const counts = useMemo(() => ({
    all: rows.length,
    pending: rows.filter((r) => r.status === 'pending').length,
    partly: rows.filter((r) => r.status === 'partly').length,
    done: rows.filter((r) => r.status === 'done').length,
  }), [rows]);
  const shown = filter === 'all' ? rows : rows.filter((r) => r.status === filter);

  return (
    <>
      <div className="filter-bar">
        <Space.Compact>
          <Button icon={<LeftOutlined />} onClick={() => setDay(day.subtract(1, 'day'))} aria-label={t('appointments.prevDay')} />
          <DatePicker value={day} onChange={(d) => d && setDay(d)} format="ddd, DD-MM-YYYY" allowClear={false} style={{ width: 170 }} />
          <Button icon={<RightOutlined />} onClick={() => setDay(day.add(1, 'day'))} aria-label={t('appointments.nextDay')} />
        </Space.Compact>
        <Segmented value={filter} onChange={(v) => setFilter(v as typeof filter)}
          options={(['all', 'pending', 'partly', 'done'] as const).map((k) => ({
            value: k, label: `${k === 'all' ? t('appointments.filters.all') : t(`pharmacy.status.${k}`)} (${counts[k]})`,
          }))} />
        <Button icon={<ReloadOutlined />} onClick={load} aria-label={t('appointments.refresh')} />
      </div>
      <Table<DispenseQueueRow>
        rowKey="id"
        loading={loading}
        dataSource={shown}
        pagination={false}
        locale={{ emptyText: t('pharmacy.queueEmpty') }}
        columns={[
          {
            title: t('pharmacy.ready'), key: 'when', width: 110,
            render: (_: unknown, r: DispenseQueueRow) => (
              <div style={{ lineHeight: 1.35 }}>
                <b>{r.finalized_at ? dayjs(r.finalized_at).format('h:mm A') : '—'}</b>
                {r.token_number && <div><span className="token-chip">#{r.token_number}</span></div>}
              </div>
            ),
          },
          { title: t('appointments.patient'), key: 'patient', render: (_: unknown, r: DispenseQueueRow) => <PatientCell patient={r.patient_detail} /> },
          { title: t('appointments.doctor'), dataIndex: 'doctor_name' },
          { title: t('pharmacy.medicines'), dataIndex: 'item_count', width: 110, align: 'center' as const },
          { title: t('common.status'), dataIndex: 'status', width: 130, render: (s: DispenseStatus) => <DispenseStatusTag status={s} /> },
          {
            title: '', key: 'action', width: 120, align: 'right' as const,
            render: (_: unknown, r: DispenseQueueRow) => {
              const giving = r.status !== 'done' && can('pharmacy.dispense');
              return (
                <Button size="small" type={giving ? 'primary' : 'default'} onClick={() => setOpen(r.id)}>
                  {giving ? t('pharmacy.dispense') : t('common.view')}
                </Button>
              );
            },
          },
        ]}
      />
      {open && <SellModal prescriptionId={open} onClose={(done) => { setOpen(null); if (done) load(); }} />}
    </>
  );
}

type Choice = { give: boolean; batch?: string; quantity: number; loose: boolean; units: number; discount: number };
type Done = { dispense: string; invoice: string | null; number: string; total_amount: string; invoice_status: string };

function SellModal({ prescriptionId, onClose }: { prescriptionId: string; onClose: (done: boolean) => void }) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const { can, hasFeature } = useAuth();
  const billing = hasFeature('pharmacy_billing');
  const discounts = hasFeature('pharmacy_discounts');
  const looseSale = hasFeature('pharmacy_loose_sale');
  const barcode = hasFeature('pharmacy_barcode');
  const racks = hasFeature('pharmacy_racks');
  const [detail, setDetail] = useState<DispenseDetail | null>(null);
  // Medicines scanned at the counter that are not on the prescription (go on the same bill)
  const [extras, setExtras] = useState<DispenseLine[]>([]);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [payMode, setPayMode] = useState<PaymentMode | 'later'>('cash');
  const [payAmount, setPayAmount] = useState<number | null>(null);
  const [payRef, setPayRef] = useState('');
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const canSell = can('pharmacy.dispense');

  useEffect(() => {
    api.get<DispenseDetail>(`/dispensing/${prescriptionId}/`).then(({ data }) => {
      setDetail(data);
      // Suggest: earliest-expiry batch (FEFO), 1 pack, for lines not given yet
      setChoices(Object.fromEntries(data.lines.map((l) => [l.id, {
        give: !!l.batches.length && !l.given, batch: l.batches[0]?.id, quantity: 1, loose: false, units: 0, discount: 0,
      }])));
    }).catch((err) => { message.error(errorMessage(err, t('common.loadFailed'))); onClose(false); });
  // Load once per prescription (the list behind refreshes every 30 s; that must not reset the choices)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prescriptionId]);

  const set = (id: string, patch: Partial<Choice>) => setChoices((c) => ({ ...c, [id]: { ...c[id]!, ...patch } }));
  const batchOf = (l: DispenseLine) => l.batches.find((b) => b.id === choices[l.id]?.batch);
  const lineAmount = (l: DispenseLine) => {
    const c = choices[l.id];
    const b = batchOf(l);
    if (!c?.give || !b) return 0;
    const price = Number(b.sale_price);
    const gross = c.loose && l.units_per_pack
      ? (Math.round((price / Number(l.units_per_pack)) * 100) / 100) * (c.units || 0)
      : price * (c.quantity || 0);
    return Math.round(gross * (100 - (c.discount || 0))) / 100;
  };
  const lines = useMemo(() => [...(detail?.lines ?? []), ...extras], [detail, extras]);
  const selected = lines.filter((l) => choices[l.id]?.give && choices[l.id]?.batch);
  const total = Math.round(selected.reduce((s, l) => s + lineAmount(l), 0));
  const allDiscount = (value: number) =>
    setChoices((c) => Object.fromEntries(Object.entries(c).map(([k, v]) => [k, { ...v, discount: value }])));

  // Barcode: pick the matching line and batch, or add one more pack.
  // A medicine not on the prescription is added as an extra line on the same bill (never Schedule E1).
  const onScan = async (code: string) => {
    if (!detail) return;
    try {
      const { data } = await api.get<ScanResult>('/stock/scan/', { params: { code } });
      const line = lines.find((l) => l.medicine === data.medicine);
      if (!line) {
        if (data.schedule_e1) {
          message.error(t('pharmacy.e1NeedsRx', { name: data.name }));
          return;
        }
        if (!data.batches.length) {
          message.warning(t('pharmacy.outOfStock'));
          return;
        }
        const extra = lineFromScan(data);
        setExtras((e) => [...e, extra]);
        setChoices((c) => ({ ...c, [extra.id]: { give: true, batch: data.scanned_batch ?? data.batches[0]!.id, quantity: 1, loose: false, units: 0, discount: 0 } }));
        message.success(t('pharmacy.addedExtra', { name: data.name }));
        return;
      }
      const batch = data.scanned_batch && line.batches.some((b) => b.id === data.scanned_batch) ? data.scanned_batch : line.batches[0]?.id;
      if (!batch) {
        message.warning(t('pharmacy.outOfStock'));
        return;
      }
      const c = choices[line.id]!;
      set(line.id, { give: true, batch, quantity: c.give && c.batch === batch && !c.loose ? c.quantity + 1 : c.quantity || 1 });
      message.success(t('pharmacy.scanned', { name: data.name }));
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post<Done>(`/dispensing/${prescriptionId}/sell/`, {
        items: selected.map((l) => {
          const c = choices[l.id]!;
          return {
            prescription_item: l.extra ? null : l.id, batch: c.batch, discount_percent: discounts ? c.discount || 0 : 0,
            ...(looseSale && c.loose ? { loose_units: c.units } : { quantity: c.quantity }),
          };
        }),
        payment: !billing || payMode === 'later' ? null : { mode: payMode, amount: payAmount ?? total, reference: payRef },
      });
      setDone(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  // Confirm before medicines leave the stock and a bill is made
  const confirmSave = () => {
    const paying = billing && payMode !== 'later' ? Math.min(payAmount ?? total, total) : 0;
    modal.confirm({
      title: t('opd.confirmTitle'),
      content: (
        <div>
          <div>{t('pharmacy.confirmGive', { count: selected.length, name: detail?.patient_detail.full_name ?? '' })}</div>
          {billing && <div>{t('pharmacy.confirmBill', { amount: money(total) })}</div>}
          {billing && (paying > 0
            ? <div>{t('opd.confirmPay', { amount: money(paying), mode: t(`billing.modes.${payMode}`) })}</div>
            : <div>{t('opd.confirmLater')}</div>)}
        </div>
      ),
      okText: t('common.yes'), cancelText: t('common.no'),
      onOk: save,
    });
  };

  if (done && !done.invoice) {
    return (
      <Modal open width={520} title={t('pharmacy.dispense')} onCancel={() => onClose(true)}
        footer={<Button type="primary" onClick={() => onClose(true)}>{t('common.close')}</Button>}>
        <Result className="compact-result" icon={<CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} />}
          title={t('pharmacy.givenDone')} extra={<LabelsButton dispense={done.dispense} size="middle" />} />
      </Modal>
    );
  }

  if (done && done.invoice) {
    return (
      <Modal open width={520} title={t('pharmacy.dispense')} onCancel={() => onClose(true)}
        footer={<Button type="primary" onClick={() => onClose(true)}>{t('common.close')}</Button>}>
        <Result className="compact-result" icon={<CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} />}
          title={t('pharmacy.billMade', { number: done.number })}
          subTitle={`${money(done.total_amount)} · ${t(`billing.status.${done.invoice_status}`)}`}
          extra={<Space size={8}><PrintButton id={done.invoice} size="middle" type="primary" /><LabelsButton dispense={done.dispense} size="middle" /></Space>} />
        {done.invoice_status !== 'paid' && <UpiPayment invoiceId={done.invoice} />}
      </Modal>
    );
  }

  const rxText = (l: DispenseLine) => [
    `${l.dose} ${l.dose_unit}`.trim(), l.frequency, l.timing, l.anupana,
    l.duration ? `${l.duration} ${t(`consult.units.${l.duration_unit}`)}` : '',
  ].filter(Boolean).join(' · ');

  return (
    <Modal open width={1060} keyboard={false} maskClosable={false} onCancel={() => onClose(false)}
      title={detail ? t('pharmacy.dispenseTitle', { name: detail.patient_detail.full_name }) : t('pharmacy.dispense')}
      footer={canSell ? (
        <div className="sell-footer">
          <div className="sell-pay">
            {billing && <Segmented size="small" value={payMode} onChange={(v) => setPayMode(v as typeof payMode)}
              options={(['cash', 'upi', 'card', 'later'] as const).map((m) => ({ value: m, label: t(`billing.modes.${m}`) }))} />}
            {billing && payMode !== 'later' && (
              <>
                <InputNumber size="small" min={0} max={total} prefix="₹" value={payAmount ?? total} style={{ width: 120 }}
                  onChange={(v) => setPayAmount(v)} />
                {payMode !== 'cash' && (
                  <Input size="small" placeholder={t('billing.reference')} value={payRef} maxLength={100} style={{ width: 160 }}
                    onChange={(e) => setPayRef(e.target.value)} />
                )}
              </>
            )}
          </div>
          <Space>
            {billing && <span className="total-text">{t('pharmacy.total')}: <b className="num">{money(total)}</b></span>}
            <Button onClick={() => onClose(false)}>{t('common.cancel')}</Button>
            <Button type="primary" loading={saving} disabled={!selected.length} onClick={confirmSave}>
              {!billing ? t('pharmacy.giveOnly', { count: selected.length })
                : hasFeature('combined_opd_bill') ? t('pharmacy.giveToOpd', { count: selected.length })
                  : t('pharmacy.giveAndBill', { count: selected.length })}
            </Button>
          </Space>
        </div>
      ) : <Button onClick={() => onClose(false)}>{t('common.close')}</Button>}>
      {!detail ? <Spin /> : (
        <>
          <div className="section-toolbar">
            <span className="cell-sub">{detail.patient_detail.uhid} · {t('pharmacy.byDoctor', { name: detail.doctor_name })}</span>
            {canSell && (
              <Space size={8}>
                <LabelsButton prescription={prescriptionId} />
                {discounts && (
                  <>
                    <span className="cell-sub">{t('pharmacy.discountAll')}</span>
                    <InputNumber size="small" min={0} max={100} suffix="%" style={{ width: 90 }} onChange={(v) => allDiscount(Number(v ?? 0))} />
                  </>
                )}
                {barcode && <ScanInput onScan={onScan} autoFocus />}
              </Space>
            )}
          </div>
          {detail.allergies.length > 0 && (
            <Alert type="error" showIcon style={{ marginBottom: 12 }} message={<><b>{t('patients.allergyAlert')}:</b> {detail.allergies.join(', ')}</>} />
          )}
          {billing && detail.sales.some((s) => s.number) && (
            <div className="cell-sub" style={{ marginBottom: 8 }}>
              {t('pharmacy.earlierBills')}: {detail.sales.map((s) => s.number).filter(Boolean).join(', ')}
            </div>
          )}
          <Table<DispenseLine>
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={lines}
            scroll={{ x: 980 }}
            columns={[
              {
                title: '', key: 'give', width: 36,
                render: (_: unknown, l: DispenseLine) => (
                  <Checkbox checked={!!choices[l.id]?.give} disabled={!l.batches.length || !canSell}
                    onChange={(e) => set(l.id, { give: e.target.checked })} aria-label={t('pharmacy.give')} />
                ),
              },
              {
                title: t('rx.medicine'), key: 'medicine',
                render: (_: unknown, l: DispenseLine) => (
                  <div style={{ lineHeight: 1.35 }}>
                    <b>{l.medicine_name}</b> <span className="cell-sub">{l.pack_size}</span>
                    {racks && l.location && <Tag icon={<EnvironmentOutlined />} color="geekblue" className="tag-tight">{l.location}</Tag>}
                    {l.extra
                      ? <div><Tag color="purple" className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.notOnRx')}</Tag></div>
                      : <div className="cell-sub">{rxText(l)}</div>}
                    {l.instructions && <div className="cell-sub">{l.instructions}</div>}
                    {l.given && <Tag color="green" className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.alreadyGiven', { n: qty(l.given) })}</Tag>}
                  </div>
                ),
              },
              {
                title: t('pharmacy.batch'), key: 'batch', width: 250,
                render: (_: unknown, l: DispenseLine) => {
                  if (!l.medicine) return <Tag className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.notFromStock')}</Tag>;
                  if (!l.batches.length) return <Tag color="red" className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.outOfStock')}</Tag>;
                  return (
                    <Select size="small" style={{ width: '100%' }} value={choices[l.id]?.batch} disabled={!canSell}
                      onChange={(v) => set(l.id, { batch: v })} popupMatchSelectWidth={false}
                      options={l.batches.map((b) => ({
                        value: b.id,
                        label: [
                          hasFeature('pharmacy_batch_tracking') ? b.batch_no : '',
                          hasFeature('pharmacy_expiry_tracking') ? `${t('pharmacy.exp')} ${expiryText(b.expiry_date)}` : '',
                          `${qty(b.quantity)} ${t('pharmacy.left')}`,
                          hasFeature('pharmacy_selling_price') ? money(b.sale_price) : '',
                        ].filter(Boolean).join(' · '),
                      }))} />
                  );
                },
              },
              {
                title: t('pharmacy.qty'), key: 'qty', width: 190,
                render: (_: unknown, l: DispenseLine) => {
                  const c = choices[l.id];
                  if (!l.batches.length || !c) return null;
                  const disabled = !canSell || !c.give;
                  return (
                    <Space size={4}>
                      {looseSale && l.allow_loose && (
                        <Segmented size="small" value={c.loose ? 'loose' : 'pack'} disabled={disabled}
                          onChange={(v) => set(l.id, { loose: v === 'loose' })}
                          options={[{ value: 'pack', label: t('pharmacy.packs') }, { value: 'loose', label: l.unit_label || t('pharmacy.units') }]} />
                      )}
                      {looseSale && c.loose ? (
                        <InputNumber size="small" min={1} style={{ width: 70 }} value={c.units || undefined} disabled={disabled}
                          onChange={(v) => set(l.id, { units: Number(v ?? 0) })} />
                      ) : (
                        <InputNumber size="small" min={0.5} step={1} max={Number(batchOf(l)?.quantity ?? 0) || undefined}
                          style={{ width: 70 }} value={c.quantity} disabled={disabled}
                          onChange={(v) => set(l.id, { quantity: Number(v ?? 0) })} />
                      )}
                    </Space>
                  );
                },
              },
              ...(discounts ? [{
                title: t('pharmacy.discount'), key: 'disc', width: 90,
                render: (_: unknown, l: DispenseLine) => l.batches.length ? (
                  <InputNumber size="small" min={0} max={100} suffix="%" style={{ width: 76 }} value={choices[l.id]?.discount}
                    disabled={!canSell || !choices[l.id]?.give} onChange={(v) => set(l.id, { discount: Number(v ?? 0) })} />
                ) : null,
              }] : []),
              ...(billing ? [{
                title: t('pharmacy.amount'), key: 'amount', width: 100, align: 'right' as const,
                render: (_: unknown, l: DispenseLine) => {
                  const a = lineAmount(l);
                  return a ? <span className="num">{money(a)}</span> : <span className="cell-sub">—</span>;
                },
              }] : []),
            ]}
          />
          {detail.notes && <Typography.Paragraph className="pre-line cell-sub" style={{ marginTop: 12, marginBottom: 0 }}>{detail.notes}</Typography.Paragraph>}
        </>
      )}
    </Modal>
  );
}
