// Counter sale: a walk-in customer buys medicines without a prescription.
// Scan the barcode on the stock label (or search by name): the medicine, batch, price and GST come in;
// scanning the same pack again adds one more. Then take payment and print the bill.
// Schedule E1 medicines are never sold here (only against a doctor's prescription).
// Shows when "Counter sale" and "Pharmacy bills" are on (Additional settings).
import { CheckCircleFilled, DeleteOutlined, EnvironmentOutlined, PlusOutlined } from '@ant-design/icons';
import {
  Alert, App, Button, Empty, Input, InputNumber, Modal, Result, Segmented, Select, Space, Table, Tag,
} from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { DispenseLine, Medicine, PaymentMode, ScanResult, StockBatch } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { UpiPayment } from './BillsTab';
import { MedicinePicker, PrintButton, ScanInput, expiryText, lineFromScan, qty } from './common';

type Choice = { batch: string; quantity: number; loose: boolean; units: number; discount: number };
type Done = { invoice: string; number: string; total_amount: string; invoice_status: string };

export function CounterSaleTab() {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const { can, hasFeature } = useAuth();
  const barcode = hasFeature('pharmacy_barcode');
  const discounts = hasFeature('pharmacy_discounts');
  const looseSale = hasFeature('pharmacy_loose_sale');
  const racks = hasFeature('pharmacy_racks');
  const [lines, setLines] = useState<DispenseLine[]>([]);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [customer, setCustomer] = useState('');
  const [phone, setPhone] = useState('');
  const [payMode, setPayMode] = useState<PaymentMode | 'later'>('cash');
  const [payAmount, setPayAmount] = useState<number | null>(null);
  const [payRef, setPayRef] = useState('');
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const [pickerKey, setPickerKey] = useState(0);

  const reset = () => {
    setLines([]); setChoices({}); setCustomer(''); setPhone(''); setPayMode('cash'); setPayAmount(null); setPayRef('');
    setDone(null);
  };
  const set = (id: string, patch: Partial<Choice>) => setChoices((c) => ({ ...c, [id]: { ...c[id]!, ...patch } }));
  const batchOf = (l: DispenseLine) => l.batches.find((b) => b.id === choices[l.id]?.batch);
  const lineAmount = (l: DispenseLine) => {
    const c = choices[l.id];
    const b = batchOf(l);
    if (!c || !b) return 0;
    const price = Number(b.sale_price);
    const gross = c.loose && l.units_per_pack
      ? (Math.round((price / Number(l.units_per_pack)) * 100) / 100) * (c.units || 0)
      : price * (c.quantity || 0);
    return Math.round(gross * (100 - (c.discount || 0))) / 100;
  };
  const total = Math.round(lines.reduce((s, l) => s + lineAmount(l), 0));

  // Add a medicine (from a scan or the name search); the same medicine again = one more pack
  const add = (found: ScanResult) => {
    if (found.schedule_e1) {
      message.error(t('pharmacy.e1NeedsRx', { name: found.name }));
      return;
    }
    if (!found.batches.length) {
      message.warning(t('pharmacy.outOfStockName', { name: found.name }));
      return;
    }
    const batch = found.scanned_batch && found.batches.some((b) => b.id === found.scanned_batch) ? found.scanned_batch : found.batches[0]!.id;
    const existing = lines.find((l) => l.medicine === found.medicine);
    if (existing) {
      const c = choices[existing.id]!;
      set(existing.id, c.batch === batch && !c.loose ? { quantity: c.quantity + 1 } : { batch, quantity: 1, loose: false });
    } else {
      const line = lineFromScan(found);
      setLines((ls) => [...ls, line]);
      setChoices((c) => ({ ...c, [line.id]: { batch, quantity: 1, loose: false, units: 0, discount: 0 } }));
    }
    message.success(t('pharmacy.scanned', { name: found.name }));
  };

  const onScan = async (code: string) => {
    try {
      const { data } = await api.get<ScanResult>('/stock/scan/', { params: { code } });
      add(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  // Without a scanner: search the medicine by name, then its batches (earliest expiry first, not expired)
  const onPick = async (m: Medicine) => {
    setPickerKey((k) => k + 1);
    try {
      const { data } = await api.get<StockBatch[]>('/stock/batches/', { params: { medicine: m.id, in_stock: 1 } });
      const today = dayjs().format('YYYY-MM-DD');
      add({
        medicine: m.id, name: m.name, pack_size: m.pack_size, schedule_e1: m.schedule_e1,
        allow_loose: !!(m.allow_loose && m.units_per_pack), units_per_pack: m.units_per_pack, location: '',
        scanned_batch: null, batches: data.filter((b) => !b.expiry_date || b.expiry_date >= today),
      });
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post<Done>('/counter-sales/', {
        customer_name: customer.trim(), customer_phone: phone.trim(),
        items: lines.map((l) => {
          const c = choices[l.id]!;
          return {
            batch: c.batch, discount_percent: discounts ? c.discount || 0 : 0,
            ...(looseSale && c.loose ? { loose_units: c.units } : { quantity: c.quantity }),
          };
        }),
        payment: payMode === 'later' ? null : { mode: payMode, amount: payAmount ?? total, reference: payRef },
      });
      setDone(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const confirmSave = () => {
    const paying = payMode !== 'later' ? Math.min(payAmount ?? total, total) : 0;
    modal.confirm({
      title: t('opd.confirmTitle'),
      content: (
        <div>
          <div>{t('counter.confirmSell', { count: lines.length, name: customer.trim() || t('counter.walkIn') })}</div>
          <div>{t('pharmacy.confirmBill', { amount: money(total) })}</div>
          {paying > 0
            ? <div>{t('opd.confirmPay', { amount: money(paying), mode: t(`billing.modes.${payMode}`) })}</div>
            : <div>{t('opd.confirmLater')}</div>}
        </div>
      ),
      okText: t('common.yes'), cancelText: t('common.no'),
      onOk: save,
    });
  };

  const phoneOk = !phone || /^\d{10}$/.test(phone);
  const canSell = can('pharmacy.dispense');

  return (
    <>
      <div className="counter-top">
        <Space wrap size={8}>
          {barcode && <ScanInput onScan={onScan} autoFocus width={280} placeholder={t('counter.scanPlaceholder')} />}
          <div style={{ width: 300 }}>
            <MedicinePicker key={pickerKey} size="middle" onPick={onPick} placeholder={t('counter.searchPlaceholder')} />
          </div>
        </Space>
        <Space wrap size={8}>
          <Input placeholder={t('counter.customerName')} value={customer} maxLength={200} style={{ width: 200 }}
            onChange={(e) => setCustomer(e.target.value)} />
          <Input placeholder={t('counter.customerPhone')} value={phone} maxLength={10} style={{ width: 150 }} inputMode="numeric"
            status={phoneOk ? undefined : 'error'} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))} />
        </Space>
      </div>
      <div className="cell-sub" style={{ margin: '4px 0 12px' }}>{t('counter.help')}</div>

      <Table<DispenseLine>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={lines}
        scroll={{ x: 900 }}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('counter.empty')} /> }}
        columns={[
          {
            title: t('rx.medicine'), key: 'medicine',
            render: (_: unknown, l: DispenseLine) => (
              <div style={{ lineHeight: 1.35 }}>
                <b>{l.medicine_name}</b> <span className="cell-sub">{l.pack_size}</span>
                {racks && l.location && <Tag icon={<EnvironmentOutlined />} color="geekblue" className="tag-tight">{l.location}</Tag>}
              </div>
            ),
          },
          {
            title: t('pharmacy.batch'), key: 'batch', width: 230,
            render: (_: unknown, l: DispenseLine) => (
              <Select size="small" style={{ width: '100%' }} value={choices[l.id]?.batch} popupMatchSelectWidth={false}
                onChange={(v) => set(l.id, { batch: v })}
                options={l.batches.map((b) => ({
                  value: b.id,
                  label: [
                    hasFeature('pharmacy_batch_tracking') ? b.batch_no : '',
                    hasFeature('pharmacy_expiry_tracking') ? `${t('pharmacy.exp')} ${expiryText(b.expiry_date)}` : '',
                    `${qty(b.quantity)} ${t('pharmacy.left')}`,
                  ].filter(Boolean).join(' · '),
                }))} />
            ),
          },
          {
            title: t('pharmacy.qty'), key: 'qty', width: 180,
            render: (_: unknown, l: DispenseLine) => {
              const c = choices[l.id];
              if (!c) return null;
              return (
                <Space size={4}>
                  {looseSale && l.allow_loose && (
                    <Segmented size="small" value={c.loose ? 'loose' : 'pack'} onChange={(v) => set(l.id, { loose: v === 'loose' })}
                      options={[{ value: 'pack', label: t('pharmacy.packs') }, { value: 'loose', label: t('pharmacy.units') }]} />
                  )}
                  {looseSale && c.loose ? (
                    <InputNumber size="small" min={1} style={{ width: 70 }} value={c.units || undefined}
                      onChange={(v) => set(l.id, { units: Number(v ?? 0) })} />
                  ) : (
                    <InputNumber size="small" min={0.5} step={1} max={Number(batchOf(l)?.quantity ?? 0) || undefined}
                      style={{ width: 70 }} value={c.quantity} onChange={(v) => set(l.id, { quantity: Number(v ?? 0) })} />
                  )}
                </Space>
              );
            },
          },
          {
            title: t('counter.price'), key: 'price', width: 100, align: 'right' as const,
            render: (_: unknown, l: DispenseLine) => <span className="num">{money(batchOf(l)?.sale_price)}</span>,
          },
          {
            title: 'GST', key: 'gst', width: 64, align: 'right' as const,
            render: (_: unknown, l: DispenseLine) => (batchOf(l) ? `${qty(batchOf(l)!.gst_rate)}%` : '—'),
          },
          ...(discounts ? [{
            title: t('pharmacy.discount'), key: 'disc', width: 90,
            render: (_: unknown, l: DispenseLine) => (
              <InputNumber size="small" min={0} max={100} suffix="%" style={{ width: 76 }} value={choices[l.id]?.discount}
                onChange={(v) => set(l.id, { discount: Number(v ?? 0) })} />
            ),
          }] : []),
          {
            title: t('pharmacy.amount'), key: 'amount', width: 100, align: 'right' as const,
            render: (_: unknown, l: DispenseLine) => <b className="num">{money(lineAmount(l))}</b>,
          },
          {
            title: '', key: 'remove', width: 44,
            render: (_: unknown, l: DispenseLine) => (
              <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.delete')}
                onClick={() => setLines((ls) => ls.filter((x) => x.id !== l.id))} />
            ),
          },
        ]}
      />

      {lines.length > 0 && canSell && (
        <div className="counter-footer">
          <div className="sell-pay">
            <Segmented value={payMode} onChange={(v) => setPayMode(v as typeof payMode)}
              options={(['cash', 'upi', 'card', 'later'] as const).map((m) => ({ value: m, label: t(`billing.modes.${m}`) }))} />
            {payMode !== 'later' && (
              <>
                <InputNumber min={0} max={total} prefix="₹" value={payAmount ?? total} style={{ width: 130 }} onChange={(v) => setPayAmount(v)} />
                {payMode !== 'cash' && (
                  <Input placeholder={t('billing.reference')} value={payRef} maxLength={100} style={{ width: 170 }}
                    onChange={(e) => setPayRef(e.target.value)} />
                )}
              </>
            )}
          </div>
          <Space>
            <span className="total-text">{t('pharmacy.total')}: <b className="num">{money(total)}</b></span>
            <Button onClick={reset}>{t('counter.clear')}</Button>
            <Button type="primary" icon={<PlusOutlined />} loading={saving} disabled={!phoneOk} onClick={confirmSave}>
              {t('counter.makeBill', { count: lines.length })}
            </Button>
          </Space>
        </div>
      )}
      {!phoneOk && <Alert type="error" showIcon style={{ marginTop: 8 }} message={t('counter.phoneInvalid')} />}

      {done && (
        <Modal open width={520} title={t('counter.title')} onCancel={reset}
          footer={<Button type="primary" onClick={reset}>{t('counter.next')}</Button>}>
          <Result className="compact-result" icon={<CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} />}
            title={t('pharmacy.billMade', { number: done.number })}
            subTitle={`${money(done.total_amount)} · ${t(`billing.status.${done.invoice_status}`)}`}
            extra={<PrintButton id={done.invoice} size="middle" type="primary" />} />
          {done.invoice_status !== 'paid' && <UpiPayment invoiceId={done.invoice} />}
        </Modal>
      )}
    </>
  );
}
