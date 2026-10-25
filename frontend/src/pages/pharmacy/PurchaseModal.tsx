// Purchase invoice entry (or opening stock): one line per medicine batch. Stock goes up when saved.
// "Detailed purchase entry" and "Barcodes" (Additional settings) add the extra fields.
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Alert, App, Button, Checkbox, Col, DatePicker, Form, Input, InputNumber, Modal, Row, Select, Space } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Medicine, Page, Supplier } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { MedicinePicker, ScanInput } from './common';

type Line = {
  key: number;
  medicine?: string;
  medicine_name?: string;
  batch_no: string;
  barcode: string;
  mfg?: Dayjs | null;
  expiry?: Dayjs | null;
  quantity?: number;
  free?: number;
  rate?: number;
  discount?: number;
  gst?: number;
  mrp?: number;
  selling?: number;
};

let nextKey = 1;
const emptyLine = (): Line => ({ key: nextKey++, batch_no: '', barcode: '' });

/** Taxable value and GST of one line (purchase rate is WITHOUT GST, like on supplier bills). */
function lineMoney(l: Line) {
  const gross = (l.quantity ?? 0) * (l.rate ?? 0);
  const taxable = Math.round(gross * (100 - (l.discount ?? 0))) / 100;
  const gst = Math.round(taxable * (l.gst ?? 0)) / 100;
  return { taxable, gst, total: taxable + gst };
}

export function PurchaseModal({ opening = false, onClose }: { opening?: boolean; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const { hasFeature } = useAuth();
  const details = hasFeature('pharmacy_purchase_details');
  const barcode = hasFeature('pharmacy_barcode');
  // Stock basics (Additional settings -> Medicine stock)
  const batches = hasFeature('pharmacy_batch_tracking');
  const expiryOn = hasFeature('pharmacy_expiry_tracking');
  const rateOn = hasFeature('pharmacy_purchase_price');
  const prices = hasFeature('pharmacy_selling_price');
  const suppliersOn = hasFeature('pharmacy_suppliers');
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [lines, setLines] = useState<Line[]>([emptyLine()]);
  const [saving, setSaving] = useState(false);
  const otherCharges: number = Form.useWatch('other_charges', form) ?? 0;
  const printedTotal: number | null | undefined = Form.useWatch('printed_total', form);
  const [acceptDifference, setAcceptDifference] = useState(false);
  const supplierPicked = Form.useWatch('supplier', form);

  useEffect(() => {
    form.setFieldsValue({ invoice_date: dayjs(), other_charges: 0, paid_now: 0, paid_mode: 'cash' });
    if (!opening && suppliersOn) api.get<Supplier[]>('/suppliers/').then(({ data }) => setSuppliers(data.filter((s) => s.is_active))).catch(() => setSuppliers([]));
  }, [form, opening]);

  const update = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  const pick = (key: number, m: Medicine) => update(key, {
    medicine: m.id, medicine_name: m.name, gst: Number(m.gst_rate),
    mrp: m.mrp ? Number(m.mrp) : undefined, selling: m.selling_price ? Number(m.selling_price) : undefined,
  });

  // Scanning a product barcode adds a line for that medicine (or fills the empty last line)
  const onScan = async (code: string) => {
    try {
      const { data } = await api.get<Page<Medicine>>('/medicines/', { params: { q: code, page_size: 5 } });
      const m = data.results.find((x) => x.barcode === code) ?? (data.results.length === 1 ? data.results[0] : undefined);
      if (!m) {
        message.warning(t('pharmacy.scanUnknown', { code }));
        return;
      }
      const last = lines[lines.length - 1];
      if (last && !last.medicine) pick(last.key, m);
      else {
        const line = emptyLine();
        setLines((ls) => [...ls, line]);
        window.setTimeout(() => pick(line.key, m), 0);
      }
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  const totals = lines.reduce((s, l) => {
    const m = lineMoney(l);
    return { taxable: s.taxable + m.taxable, gst: s.gst + m.gst };
  }, { taxable: 0, gst: 0 });
  const exact = totals.taxable + totals.gst + (otherCharges || 0);
  const grand = Math.round(exact);
  const ready = lines.filter((l) => l.medicine && (!batches || l.batch_no.trim()) && l.quantity && (!prices || l.mrp !== undefined));
  // The expiry printed on the pack is needed for every batch while expiry tracking is on (never guessed)
  const missingExpiry = expiryOn ? ready.filter((l) => !l.expiry) : [];
  // The total printed on the supplier invoice against the total calculated here (Rs 1 of rounding is fine)
  const showTotalCheck = !opening && rateOn && printedTotal !== null && printedTotal !== undefined;
  const difference = showTotalCheck ? Math.round((printedTotal! - grand) * 100) / 100 : 0;
  const differs = showTotalCheck && Math.abs(difference) > 1;

  const save = async () => {
    const values = await form.validateFields();
    if (!ready.length) {
      message.warning(t('pharmacy.addLineFirst'));
      return;
    }
    if (missingExpiry.length) {
      message.warning(t('pharmacy.expiryMissing', { name: missingExpiry[0]!.medicine_name }));
      return;
    }
    if (differs && !acceptDifference) {
      message.warning(t('pharmacy.tickSaveAnyway'));
      return;
    }
    setSaving(true);
    try {
      await api.post('/purchases/', {
        is_opening: opening,
        supplier: opening || !suppliersOn ? null : values.supplier ?? null,
        invoice_no: opening ? '' : values.invoice_no ?? '',
        invoice_date: values.invoice_date?.format('YYYY-MM-DD'),
        other_charges: opening ? 0 : values.other_charges ?? 0,
        printed_total: opening || !rateOn ? null : values.printed_total ?? null,
        accept_difference: acceptDifference,
        paid_now: opening || !supplierPicked ? 0 : values.paid_now ?? 0,
        paid_mode: values.paid_mode ?? 'cash',
        notes: values.notes ?? '',
        items: ready.map((l) => ({
          medicine: l.medicine, batch_no: l.batch_no, barcode: l.barcode, quantity: l.quantity, free_quantity: l.free ?? 0,
          purchase_rate: l.rate ?? null, discount_percent: l.discount ?? 0, gst_rate: l.gst ?? 0, mrp: l.mrp,
          selling_price: l.selling ?? null,
          // Dates are printed as month-year: manufacture = first day, expiry = last day of that month
          mfg_date: l.mfg ? l.mfg.startOf('month').format('YYYY-MM-DD') : null,
          expiry_date: l.expiry ? l.expiry.endOf('month').format('YYYY-MM-DD') : null,
        })),
      });
      message.success(opening ? t('pharmacy.openingSaved') : t('pharmacy.purchaseSaved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const field = (label: string, node: ReactNode, grow = false) => (
    <div className={`rx-field${grow ? ' rx-field-grow' : ''}`}><span>{label}</span>{node}</div>
  );

  return (
    <Modal open width={1100} title={opening ? t('pharmacy.openingStock') : t('pharmacy.addPurchase')} onCancel={() => onClose(false)}
      keyboard={false} maskClosable={false}
      footer={(
        <div className="modal-footer-split">
          <span className="total-text">
            {rateOn && (
              <>
                {!opening && details && <>{t('billing.taxable')} <span className="num">{money(totals.taxable)}</span> · GST <span className="num">{money(totals.gst)}</span> · </>}
                {t('pharmacy.purchaseTotal')}: <b className="num">{money(opening ? totals.taxable + totals.gst : grand)}</b>
              </>
            )}
          </span>
          <span>
            <Button onClick={() => onClose(false)}>{t('common.cancel')}</Button>
            <Button type="primary" loading={saving} onClick={save} style={{ marginInlineStart: 8 }}>
              {t('pharmacy.savePurchase', { count: ready.length })}
            </Button>
          </span>
        </div>
      )}>
      {opening && <div className="form-help">{t('pharmacy.openingHelp')}</div>}
      <Form form={form} layout="vertical" requiredMark={false}>
        <Row gutter={12}>
          {!opening && (
            <>
              {suppliersOn && <Col xs={24} md={8}>
                <Form.Item name="supplier" label={t('pharmacy.supplier')} extra={!suppliers.length ? t('pharmacy.noSuppliersYet') : undefined}>
                  <Select allowClear showSearch optionFilterProp="label" options={suppliers.map((s) => ({ value: s.id, label: s.name }))} />
                </Form.Item>
              </Col>}
              <Col xs={12} md={5}><Form.Item name="invoice_no" label={t('pharmacy.invoiceNo')}><Input maxLength={60} /></Form.Item></Col>
              <Col xs={12} md={5}>
                <Form.Item name="invoice_date" label={t('pharmacy.invoiceDate')} rules={[{ required: true, message: t('common.required') }]}>
                  <DatePicker format="DD-MM-YYYY" style={{ width: '100%' }} allowClear={false} />
                </Form.Item>
              </Col>
              {details && (
                <Col xs={12} md={6}>
                  <Form.Item name="other_charges" label={t('pharmacy.otherCharges')}>
                    <InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              )}
              {suppliersOn && supplierPicked && (
                <Col xs={24}>
                  <Space wrap align="end">
                    <Form.Item name="paid_now" label={t('dues.paidNow')} extra={t('dues.paidNowHelp')} style={{ marginBottom: 8 }}>
                      <InputNumber min={0} precision={2} prefix="₹" style={{ width: 180 }} />
                    </Form.Item>
                    <Form.Item name="paid_mode" label={t('dues.mode')} style={{ marginBottom: 8 }}>
                      <Select style={{ width: 140 }} options={['cash', 'upi', 'bank', 'cheque', 'other'].map((m) => ({ value: m, label: t(`dues.modes.${m}`) }))} />
                    </Form.Item>
                  </Space>
                </Col>
              )}
              {rateOn && (
                <Col xs={12} md={6}>
                  <Form.Item name="printed_total" label={t('pharmacy.printedTotal')} extra={t('pharmacy.printedTotalHelp')}
                    rules={[{ required: true, message: t('common.required') }]}>
                    <InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }}
                      onChange={() => setAcceptDifference(false)} />
                  </Form.Item>
                </Col>
              )}
            </>
          )}
        </Row>
      </Form>
      {differs && (
        <Alert type="warning" showIcon style={{ marginBottom: 10 }}
          message={t('pharmacy.totalDiffers', { diff: money(Math.abs(difference)), calc: money(grand), printed: money(printedTotal) })}
          description={<Checkbox checked={acceptDifference} onChange={(e) => setAcceptDifference(e.target.checked)}>{t('pharmacy.saveAnyway')}</Checkbox>} />
      )}
      {showTotalCheck && !differs && <Alert type="success" showIcon style={{ marginBottom: 10 }} message={t('pharmacy.totalMatches')} />}

      <div className="section-toolbar">
        <div className="section-title" style={{ margin: 0 }}>{t('pharmacy.lines', { n: lines.length })}</div>
        {barcode && <ScanInput onScan={onScan} placeholder={t('pharmacy.scanToAdd')} />}
      </div>
      <div className="rx-lines purchase-entry">
        {lines.map((l, index) => {
          const m = lineMoney(l);
          return (
            <div className="rx-line" key={l.key}>
              <div className="rx-controls" style={{ paddingLeft: 0 }}>
                <span className="rx-num" style={{ alignSelf: 'flex-end', marginBottom: 2 }}>{index + 1}</span>
                {field(t('rx.medicine'), <MedicinePicker value={l.medicine} label={l.medicine_name} onPick={(med) => pick(l.key, med)} />, true)}
                {batches && field(t('pharmacy.batch'), <Input size="small" value={l.batch_no} maxLength={60} style={{ width: 110 }} placeholder="B1234"
                  onChange={(e) => update(l.key, { batch_no: e.target.value.toUpperCase() })} />)}
                {barcode && field(t('pharmacy.barcode'), <Input size="small" value={l.barcode} maxLength={64} style={{ width: 130 }}
                  onChange={(e) => update(l.key, { barcode: e.target.value.trim() })} />)}
                {details && expiryOn && field(t('pharmacy.mfg'), <DatePicker size="small" picker="month" format="MM-YYYY" value={l.mfg ?? null} style={{ width: 104 }}
                  onChange={(d) => update(l.key, { mfg: d })} />)}
                {expiryOn && field(`${t('pharmacy.expiry')} *`, <DatePicker size="small" picker="month" format="MM-YYYY" value={l.expiry ?? null} style={{ width: 104 }}
                  disabledDate={(d) => d.isBefore(dayjs(), 'month')} onChange={(d) => update(l.key, { expiry: d })} />)}
                <Button size="small" type="text" icon={<DeleteOutlined />} disabled={lines.length === 1} aria-label={t('common.remove')}
                  style={{ alignSelf: 'flex-end' }} onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))} />
              </div>
              <div className="rx-controls" style={{ paddingLeft: 30, marginTop: 6 }}>
                {field(t('pharmacy.qty'), <InputNumber size="small" min={0.001} value={l.quantity} style={{ width: 80 }} onChange={(v) => update(l.key, { quantity: v ?? undefined })} />)}
                {details && field(t('pharmacy.free'), <InputNumber size="small" min={0} value={l.free} style={{ width: 70 }} onChange={(v) => update(l.key, { free: v ?? undefined })} />)}
                {rateOn && field(t('pharmacy.rateNoGst'), <InputNumber size="small" min={0} precision={2} value={l.rate} style={{ width: 96 }} onChange={(v) => update(l.key, { rate: v ?? undefined })} />)}
                {details && field(t('pharmacy.discount'), <InputNumber size="small" min={0} max={100} suffix="%" value={l.discount} style={{ width: 76 }} onChange={(v) => update(l.key, { discount: v ?? undefined })} />)}
                {details && field('GST', <InputNumber size="small" min={0} max={40} suffix="%" value={l.gst} style={{ width: 76 }} onChange={(v) => update(l.key, { gst: v ?? undefined })} />)}
                {prices && field('MRP', <InputNumber size="small" min={0} precision={2} value={l.mrp} style={{ width: 96 }} onChange={(v) => update(l.key, { mrp: v ?? undefined })} />)}
                {details && prices && field(t('pharmacy.sellingPrice'), <InputNumber size="small" min={0} max={l.mrp} precision={2} value={l.selling} style={{ width: 96 }}
                  placeholder={l.mrp ? String(l.mrp) : ''} onChange={(v) => update(l.key, { selling: v ?? undefined })} />)}
                {field(t('pharmacy.amount'), <span className="num line-amount">{money(m.total)}</span>)}
              </div>
            </div>
          );
        })}
        <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={() => setLines((ls) => [...ls, emptyLine()])} style={{ alignSelf: 'flex-start' }}>
          {t('pharmacy.addLine')}
        </Button>
      </div>
    </Modal>
  );
}
