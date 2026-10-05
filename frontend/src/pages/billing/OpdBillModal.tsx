// OPD bill popup: consultation fee at check-in, services & charges after the check-up, and taking payment.
// Everything is checked on screen first, then confirmed; the bill preview opens on the same screen.
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Alert, App, Button, Input, InputNumber, Modal, Segmented, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { InvoiceLine, InvoiceRecord, OpdSuggestion, PaymentMode, ServiceCharge } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { BillPreviewModal } from '../../components/BillPreview';
import { money } from '../medicines/shared';
import { InvoiceStatusTag } from '../pharmacy/common';

type Kind = 'consultation' | 'service' | 'other';
type Draft = { key: number; kind: Kind; service?: string; description: string; quantity: number; price: number; discount: number };

let nextKey = 1;
const rupee = (n: number) => Math.round(n * 100) / 100;
const amountOf = (d: Draft) => rupee(d.price * d.quantity * (100 - d.discount) / 100);

export type OpdBillTarget = { appointment?: string; visit?: string; patient?: string; doctor?: string };

export function OpdBillModal({ target, onClose }: { target: OpdBillTarget; onClose: (changed: boolean) => void }) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const { can } = useAuth();
  const canCharge = can('billing.charge') || can('billing.create');
  const canTakePayment = can('billing.create');
  const [info, setInfo] = useState<OpdSuggestion | null>(null);
  const [services, setServices] = useState<ServiceCharge[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [payMode, setPayMode] = useState<PaymentMode | 'later'>('cash');
  const [payAmount, setPayAmount] = useState<number | null>(null);
  const [payRef, setPayRef] = useState('');
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<InvoiceRecord | null>(null);
  const [changed, setChanged] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get<OpdSuggestion>('/opd-bills/suggest/', { params: target }),
      api.get<ServiceCharge[]>('/services/', { params: { active: 1 } }),
    ]).then(([s, list]) => {
      setInfo(s.data);
      setServices(list.data);
      // First time: suggest the consultation fee (new case / follow-up) for this doctor
      const c = s.data.consultation;
      if (c && !s.data.consultation_billed) {
        setDrafts([{ key: nextKey++, kind: 'consultation', description: c.description, quantity: 1, price: Number(c.fee), discount: 0 }]);
      }
    }).catch((err) => { message.error(errorMessage(err, t('common.loadFailed'))); onClose(false); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const bill = info?.bill ?? null;
  const newTotal = Math.round(drafts.reduce((sum, d) => sum + amountOf(d), 0));
  const dueAfter = rupee((bill ? Number(bill.balance) : 0) + newTotal);
  const collect = payAmount ?? dueAfter;

  const update = (key: number, patch: Partial<Draft>) => setDrafts((all) => all.map((d) => (d.key === key ? { ...d, ...patch } : d)));
  const addService = (id: string) => {
    const s = services.find((x) => x.id === id);
    if (!s) return;
    setDrafts((all) => [...all, { key: nextKey++, kind: 'service', service: s.id, description: s.name, quantity: 1, price: Number(s.effective_price ?? s.price), discount: 0 }]);
  };
  const addOther = () => setDrafts((all) => [...all, { key: nextKey++, kind: 'other', description: '', quantity: 1, price: 0, discount: 0 }]);

  const serviceOptions = useMemo(() => services.map((s) => ({
    value: s.id, label: `${s.name} · ${money(s.effective_price ?? s.price)}`,
  })), [services]);

  const payment = canTakePayment && payMode !== 'later' && collect > 0
    ? { mode: payMode, amount: Math.min(collect, dueAfter), reference: payRef } : null;

  const submit = async () => {
    setSaving(true);
    try {
      let saved: InvoiceRecord;
      if (drafts.length) {
        const { data } = await api.post<InvoiceRecord>('/opd-bills/charge/', {
          ...(info!.visit ? { visit: info!.visit } : info!.appointment ? { appointment: info!.appointment } : { patient: info!.patient_detail.id, doctor: info!.doctor }),
          lines: drafts.map((d) => ({
            kind: d.kind, service: d.service ?? null, description: d.description, quantity: d.quantity,
            unit_price: d.price, discount_percent: d.discount,
          })),
          payment,
        });
        saved = data;
      } else {
        const { data } = await api.post<InvoiceRecord>(`/invoices/${bill!.id}/pay/`, payment);
        saved = data;
      }
      setChanged(true);
      message.success(t('opd.saved', { number: saved.number }));
      setPreview(saved); // show the bill on this screen
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  // Confirm before anything is saved
  const confirm = () => {
    if (drafts.some((d) => !d.description.trim())) {
      message.warning(t('opd.needDescription'));
      return;
    }
    const name = info!.patient_detail.full_name;
    const lines = [
      drafts.length ? (bill ? t('opd.confirmAdd', { amount: money(newTotal), number: bill.number }) : t('opd.confirmCreate', { amount: money(newTotal), name })) : '',
      payment ? t('opd.confirmPay', { amount: money(payment.amount), mode: t(`billing.modes.${payment.mode}`) }) : (canTakePayment && drafts.length ? t('opd.confirmLater') : ''),
    ].filter(Boolean);
    modal.confirm({
      title: t('opd.confirmTitle'),
      content: <div>{lines.map((l) => <div key={l}>{l}</div>)}</div>,
      okText: t('common.yes'), cancelText: t('common.no'),
      onOk: submit,
    });
  };

  if (preview) {
    return <BillPreviewModal id={preview.id} title={t('opd.previewTitle', { number: preview.number })} onClose={() => onClose(true)} />;
  }

  const mainLabel = drafts.length ? (bill ? t('opd.addToBill') : t('opd.createBill')) : t('opd.takePayment');
  const canSubmit = canCharge && (drafts.length > 0 || (!!bill && !!payment));
  const c = info?.consultation;

  return (
    <Modal open width={920} keyboard={false} maskClosable={false} onCancel={() => onClose(changed)}
      title={info ? t('opd.title', { name: info.patient_detail.full_name }) : t('opd.titlePlain')}
      footer={info ? (
        <div className="sell-footer">
          <div className="sell-pay">
            {canTakePayment && dueAfter > 0 ? (
              <>
                <span className="cell-sub">{t('opd.collectNow')}</span>
                <Segmented size="small" value={payMode} onChange={(v) => setPayMode(v as typeof payMode)}
                  options={(['cash', 'upi', 'card', 'later'] as const).map((m) => ({ value: m, label: t(`billing.modes.${m}`) }))} />
                {payMode !== 'later' && (
                  <>
                    <InputNumber size="small" min={0} max={dueAfter} prefix="₹" value={collect} style={{ width: 120 }} onChange={(v) => setPayAmount(v)} />
                    {payMode !== 'cash' && <Input size="small" placeholder={t('billing.reference')} value={payRef} maxLength={100} style={{ width: 150 }} onChange={(e) => setPayRef(e.target.value)} />}
                  </>
                )}
              </>
            ) : !canTakePayment ? <span className="cell-sub">{t('opd.receptionCollects')}</span> : null}
          </div>
          <Space size={8}>
            <span className="total-text">{t('opd.dueAfter')}: <b className="num">{money(dueAfter)}</b></span>
            <Button onClick={() => onClose(changed)}>{t('common.cancel')}</Button>
            <Button type="primary" loading={saving} disabled={!canSubmit} onClick={confirm}>{mainLabel}</Button>
          </Space>
        </div>
      ) : null}>
      {!info ? <Spin /> : (
        <>
          <div className="opd-head">
            <div>
              <b>{info.patient_detail.full_name}</b> <span className="cell-sub mono">{info.patient_detail.uhid}</span>
              <div className="cell-sub">{info.doctor_name ? t('opd.consultant', { name: info.doctor_name }) : t('opd.noDoctor')}</div>
            </div>
            {c && (
              <Space size={6} wrap>
                <Tag color={c.visit_kind === 'new' ? 'blue' : 'green'}>{t(`opd.kind.${c.visit_kind}`)}</Tag>
                {c.last_visit && <span className="cell-sub">{t('opd.lastVisit', { date: dayjs(c.last_visit).format('DD-MM-YYYY') })}</span>}
              </Space>
            )}
          </div>
          {c && !c.fee_set && <Alert type="warning" showIcon style={{ marginBottom: 12 }} message={t('opd.feeNotSet')} />}

          {bill && (
            <>
              <div className="section-toolbar">
                <div className="section-title" style={{ margin: 0 }}>{t('opd.onBill', { number: bill.number })}</div>
                <Space size={8}><InvoiceStatusTag status={bill.status} /><span className="cell-sub">{t('opd.paidOf', { paid: money(Number(bill.paid_amount) - Number(bill.refunded_amount)), total: money(bill.total_amount) })}</span></Space>
              </div>
              <Table<InvoiceLine> size="small" rowKey="id" pagination={false} dataSource={bill.lines ?? []} style={{ marginBottom: 12 }}
                columns={[
                  { title: t('opd.item'), dataIndex: 'description' },
                  { title: t('pharmacy.qty'), dataIndex: 'quantity', width: 80, align: 'right' as const, render: (v: string) => Number(v) },
                  { title: t('pharmacy.amount'), dataIndex: 'total_amount', width: 120, align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
                ]} />
            </>
          )}

          {canCharge && (
            <>
              <div className="section-toolbar">
                <div className="section-title" style={{ margin: 0 }}>{bill ? t('opd.addMore') : t('opd.charges')}</div>
                <Space size={8}>
                  <Select showSearch optionFilterProp="label" placeholder={t('opd.addService')} style={{ width: 280 }} value={null as unknown as string}
                    options={serviceOptions} onChange={addService} notFoundContent={t('opd.noServices')} />
                  {info.doctor && (bill ? !info.consultation_billed : true) && !drafts.some((d) => d.kind === 'consultation') && c && (
                    <Button icon={<PlusOutlined />} onClick={() => setDrafts((all) => [{ key: nextKey++, kind: 'consultation', description: c.description, quantity: 1, price: Number(c.fee), discount: 0 }, ...all])}>
                      {t('opd.consultation')}
                    </Button>
                  )}
                  <Button icon={<PlusOutlined />} onClick={addOther}>{t('opd.otherCharge')}</Button>
                </Space>
              </div>
              <Table<Draft> size="small" rowKey="key" pagination={false} dataSource={drafts}
                locale={{ emptyText: bill ? t('opd.nothingNew') : t('opd.addSomething') }}
                columns={[
                  {
                    title: t('opd.item'), key: 'd',
                    render: (_: unknown, d: Draft) => (
                      <Input size="small" value={d.description} maxLength={250} placeholder={t('opd.descriptionPlaceholder')}
                        onChange={(e) => update(d.key, { description: e.target.value })}
                        prefix={d.kind === 'consultation' ? <Tag color="blue" className="tag-tight">{t('opd.consultationShort')}</Tag> : undefined} />
                    ),
                  },
                  { title: t('pharmacy.qty'), key: 'q', width: 80, render: (_: unknown, d: Draft) => <InputNumber size="small" min={1} max={99} value={d.quantity} style={{ width: 64 }} onChange={(v) => update(d.key, { quantity: Number(v ?? 1) })} /> },
                  { title: t('fees.price'), key: 'p', width: 120, render: (_: unknown, d: Draft) => <InputNumber size="small" min={0} prefix="₹" value={d.price} style={{ width: 104 }} onChange={(v) => update(d.key, { price: Number(v ?? 0) })} /> },
                  { title: t('pharmacy.discount'), key: 'disc', width: 90, render: (_: unknown, d: Draft) => <InputNumber size="small" min={0} max={100} suffix="%" value={d.discount} style={{ width: 76 }} onChange={(v) => update(d.key, { discount: Number(v ?? 0) })} /> },
                  { title: t('pharmacy.amount'), key: 'a', width: 100, align: 'right' as const, render: (_: unknown, d: Draft) => <b className="num">{money(amountOf(d))}</b> },
                  { title: '', key: 'x', width: 40, render: (_: unknown, d: Draft) => <Button size="small" type="text" icon={<DeleteOutlined />} aria-label={t('common.remove')} onClick={() => setDrafts((all) => all.filter((x) => x.key !== d.key))} /> },
                ]} />
              {drafts.length > 0 && (
                <Typography.Paragraph className="cell-sub" style={{ marginTop: 8, marginBottom: 0, textAlign: 'right' }}>
                  {t('opd.newTotal')}: <b className="num">{money(newTotal)}</b>
                </Typography.Paragraph>
              )}
            </>
          )}
        </>
      )}
    </Modal>
  );
}

/** Small status button for appointment / queue rows: "Bill", "Paid", "Due ₹200". Opens the OPD bill popup. */
export function OpdBillButton({ appointmentId, bill, onChanged }: {
  appointmentId: string;
  bill?: { status: string; balance: string } | null;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [open, setOpen] = useState(false);
  if (!can('billing.charge') && !can('billing.create') && !can('billing.view')) return null;
  const due = bill ? Number(bill.balance) : 0;
  const label = !bill ? t('opd.chip.none') : due > 0 ? t('opd.chip.due', { amount: money(due) }) : t('opd.chip.paid');
  const canOpen = can('billing.charge') || can('billing.create');
  return (
    <>
      <Button size="small" type={!bill ? 'default' : due > 0 ? 'primary' : 'text'} danger={!!bill && due > 0} ghost={!!bill && due > 0}
        disabled={!canOpen} onClick={() => setOpen(true)}>₹ {label}</Button>
      {open && <OpdBillModal target={{ appointment: appointmentId }} onClose={(changed) => { setOpen(false); if (changed) onChanged(); }} />}
    </>
  );
}
