// Stock of this branch: one row per medicine (available, near expiry, minimum level), batches inside with
// corrections, stock history. Extras (Additional settings): alerts, rack location, barcode search,
// opening stock, returns to the supplier, detailed batch prices.
import { EditOutlined, EnvironmentOutlined, HistoryOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, InputNumber, Modal, Segmented, Select, Space, Spin, Table, Tag, Tooltip } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import type { Rack, ScanResult, StockAlerts, StockBatch, StockRow, Supplier } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { LedgerDrawer } from './LedgerTab';
import { PurchaseModal } from './PurchaseModal';
import { ScanInput, expiryText, qty } from './common';
import { StockLabelsButton } from './StockLabels';

type Show = 'all' | 'low' | 'out' | 'expiring' | 'expired';

export function AlertTiles({ onPick, active }: { onPick?: (show: Show) => void; active?: Show }) {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<StockAlerts | null>(null);
  useEffect(() => { api.get<StockAlerts>('/stock/alerts/').then(({ data }) => setAlerts(data)).catch(() => setAlerts(null)); }, []);
  if (!alerts) return null;
  const tiles: { key: Show; color: string }[] = [
    { key: 'out', color: 'red' }, { key: 'low', color: 'orange' }, { key: 'expiring', color: 'gold' }, { key: 'expired', color: 'magenta' },
  ];
  return (
    <div className="alert-tiles">
      {tiles.map(({ key, color }) => (
        <button type="button" key={key} className={`alert-tile tile-${color}${active === key ? ' active' : ''}`}
          onClick={() => onPick?.(active === key ? 'all' : key)}>
          <span className="alert-count num">{alerts[key as keyof StockAlerts]}</span>
          <span className="alert-label">{t(`pharmacy.alerts.${key}`)}</span>
        </button>
      ))}
    </div>
  );
}

export function StockTab() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can, hasFeature } = useAuth();
  const canStock = can('pharmacy.stock');
  const alerts = hasFeature('pharmacy_stock_alerts');
  const useRacks = hasFeature('pharmacy_racks');
  const barcode = hasFeature('pharmacy_barcode');
  const extraDetails = hasFeature('medicine_extra_details');
  const [params] = useSearchParams();
  const [show, setShow] = useState<Show>((params.get('show') as Show) || 'all');
  const [rack, setRack] = useState<string>();
  const [racks, setRacks] = useState<Rack[]>([]);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<StockRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchase, setPurchase] = useState<'purchase' | 'opening' | null>(null);
  const [history, setHistory] = useState<StockRow | null>(null);
  const [locating, setLocating] = useState<StockRow | null>(null);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!useRacks) return;
    api.get<Rack[]>('/racks/').then(({ data }) => setRacks(data.filter((r) => r.is_active))).catch(() => setRacks([]));
  }, [useRacks]);
  // Filters of a switched-off extra are not used
  const shown: Show = alerts ? show : 'all';
  const rackFilter = useRacks ? rack : undefined;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<StockRow[]>('/stock/', { params: { show: shown, q: query || undefined, rack: rackFilter } });
      setRows(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [shown, query, rackFilter, message, t]);
  useEffect(() => { load(); }, [load, version]);

  const changed = () => setVersion((v) => v + 1);

  const saveLevel = async (row: StockRow, level: number | null) => {
    if ((level ?? null) === (row.reorder_level === null ? null : Number(row.reorder_level))) return;
    try {
      await api.post('/stock/reorder-level/', { medicine: row.medicine, level });
      changed();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const onScan = async (code: string) => {
    try {
      const { data } = await api.get<ScanResult>('/stock/scan/', { params: { code } });
      setShow('all');
      setRack(undefined);
      setSearch(data.name);
      setQuery(data.name);
      setExpanded([data.medicine]);
      if (data.location) message.info(t('pharmacy.foundAt', { name: data.name, location: data.location }));
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  return (
    <>
      {alerts && <AlertTiles key={version} active={show} onPick={setShow} />}
      <div className="filter-bar">
        {barcode && <ScanInput onScan={onScan} />}
        <Input.Search allowClear placeholder={t('pharmacy.stockSearch')} value={search} style={{ width: 240 }}
          onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }} onSearch={(v) => setQuery(v.trim())} />
        {useRacks && (
          <Select allowClear placeholder={t('pharmacy.allRacks')} value={rack} onChange={setRack} style={{ width: 150 }}
            options={racks.map((r) => ({ value: r.id, label: `${r.code}${r.name ? ` · ${r.name}` : ''}` }))} />
        )}
        {alerts && (
          <Segmented value={show} onChange={(v) => setShow(v as Show)}
            options={(['all', 'low', 'out', 'expiring', 'expired'] as const).map((k) => ({ value: k, label: t(`pharmacy.show.${k}`) }))} />
        )}
        <Button icon={<ReloadOutlined />} onClick={changed} aria-label={t('appointments.refresh')} />
        <span style={{ flex: 1 }} />
        {canStock && (
          <Space>
            {hasFeature('pharmacy_opening_stock') && <Button onClick={() => setPurchase('opening')}>{t('pharmacy.openingStock')}</Button>}
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setPurchase('purchase')}>{t('pharmacy.addPurchase')}</Button>
          </Space>
        )}
      </div>
      <Table<StockRow>
        rowKey="medicine"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        scroll={{ x: 980 }}
        locale={{ emptyText: shown === 'all' && !query ? t('pharmacy.stockEmpty') : t('pharmacy.nothingHere') }}
        expandable={{
          expandedRowKeys: expanded,
          onExpandedRowsChange: (keys) => setExpanded(keys as string[]),
          expandedRowRender: (r) => <BatchList key={version} row={r} canStock={canStock} onChanged={changed} />,
        }}
        columns={[
          {
            title: t('rx.medicine'), key: 'name',
            render: (_: unknown, r: StockRow) => (
              <div style={{ lineHeight: 1.35 }}>
                <b>{r.name}</b> <span className="cell-sub">{r.pack_size}</span>
                <div className="cell-sub">{[...(extraDetails ? [r.generic_name, r.category] : []), r.manufacturer].filter(Boolean).join(' · ') || '—'}</div>
              </div>
            ),
          },
          ...(useRacks ? [{
            title: t('pharmacy.location'), key: 'loc', width: 130,
            render: (_: unknown, r: StockRow) => (
              <Space size={2}>
                {r.location ? <Tag icon={<EnvironmentOutlined />} color="geekblue" className="tag-tight" style={{ marginInlineStart: 0 }}>{r.location}</Tag> : <span className="cell-sub">—</span>}
                {canStock && <Button size="small" type="text" icon={<EditOutlined />} onClick={() => setLocating(r)} aria-label={t('pharmacy.setLocation')} />}
              </Space>
            ),
          }] : []),
          {
            title: t('pharmacy.available'), key: 'available', width: 130, align: 'right' as const,
            render: (_: unknown, r: StockRow) => (
              <Space size={6}>
                {r.out && <Tag color="red" className="tag-tight">{t('pharmacy.out')}</Tag>}
                {r.low && <Tag color="orange" className="tag-tight">{t('pharmacy.low')}</Tag>}
                <b className="num">{qty(r.usable)}</b>
              </Space>
            ),
          },
          ...(!hasFeature('pharmacy_expiry_tracking') ? [] : [{
            title: t('pharmacy.nearestExpiry'), key: 'expiry', width: 190,
            render: (_: unknown, r: StockRow) => (
              <Space size={6} wrap>
                <span className={r.expiring ? 'text-warn' : undefined}>{expiryText(r.nearest_expiry)}</span>
                {r.expiring && <Tooltip title={t('pharmacy.nearExpiryQty', { n: qty(r.near_expiry_quantity) })}><Tag color="gold" className="tag-tight">{t('pharmacy.soon')}</Tag></Tooltip>}
                {r.expired && (
                  <Tooltip title={t('pharmacy.expiredHelp', { n: qty(Number(r.available) - Number(r.usable)) })}>
                    <Tag color="magenta" className="tag-tight">{t('pharmacy.expired')}</Tag>
                  </Tooltip>
                )}
              </Space>
            ),
          }]),
          {
            title: <Tooltip title={t('pharmacy.reorderHelp')}>{t('pharmacy.reorderLevel')}</Tooltip>, key: 'level', width: 140,
            render: (_: unknown, r: StockRow) => (
              <InputNumber size="small" min={0} style={{ width: 90 }} disabled={!canStock} placeholder="—"
                defaultValue={r.reorder_level === null ? undefined : Number(r.reorder_level)}
                onBlur={(e) => saveLevel(r, e.target.value === '' ? null : Number(e.target.value))} />
            ),
          },
          {
            title: '', key: 'history', width: 50, align: 'right' as const,
            render: (_: unknown, r: StockRow) => (
              <Tooltip title={t('pharmacy.history')}>
                <Button size="small" type="text" icon={<HistoryOutlined />} onClick={() => setHistory(r)} aria-label={t('pharmacy.history')} />
              </Tooltip>
            ),
          },
        ]}
      />
      {purchase && <PurchaseModal opening={purchase === 'opening'} onClose={(saved) => { setPurchase(null); if (saved) changed(); }} />}
      {history && <LedgerDrawer medicine={history.medicine} name={history.name} onClose={() => setHistory(null)} />}
      {locating && <LocationModal row={locating} racks={racks} onClose={(saved) => { setLocating(null); if (saved) changed(); }} />}
    </>
  );
}

function BatchList({ row, canStock, onChanged }: { row: StockRow; canStock: boolean; onChanged: () => void }) {
  const { t } = useTranslation();
  const { hasFeature } = useAuth();
  const details = hasFeature('pharmacy_purchase_details');
  const barcode = hasFeature('pharmacy_barcode');
  const supplierReturns = hasFeature('pharmacy_supplier_returns');
  const batchesOn = hasFeature('pharmacy_batch_tracking');
  const expiryOn = hasFeature('pharmacy_expiry_tracking');
  const prices = hasFeature('pharmacy_selling_price');
  const rateOn = hasFeature('pharmacy_purchase_price');
  const suppliersOn = hasFeature('pharmacy_suppliers');
  const [batches, setBatches] = useState<StockBatch[] | null>(null);
  const [correcting, setCorrecting] = useState<StockBatch | null>(null);
  const [returning, setReturning] = useState<StockBatch | null>(null);

  const loadBatches = useCallback(() => {
    api.get<StockBatch[]>('/stock/batches/', { params: { medicine: row.medicine, in_stock: 1 } })
      .then(({ data }) => setBatches(data)).catch(() => setBatches([]));
  }, [row.medicine]);
  useEffect(() => { loadBatches(); }, [loadBatches]);
  const stockLabels = hasFeature('pharmacy_stock_labels');

  if (!batches) return <Spin size="small" />;
  const today = dayjs().format('YYYY-MM-DD');
  return (
    <>
      <Table<StockBatch>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={batches}
        className="inner-table"
        locale={{ emptyText: t('pharmacy.noBatches') }}
        columns={[
          ...(batchesOn ? [{ title: t('pharmacy.batch'), dataIndex: 'batch_no', render: (b: string, x: StockBatch) => <><span className="mono">{b}</span>{(barcode || stockLabels) && x.barcode && <div className="cell-sub mono">{x.barcode}</div>}</> }] : []),
          ...(details && expiryOn ? [{ title: t('pharmacy.mfg'), dataIndex: 'mfg_date', render: expiryText }] : []),
          ...(expiryOn ? [{
            title: t('pharmacy.expiry'), dataIndex: 'expiry_date',
            render: (d: string | null) => (d && d < today ? <Tag color="magenta" className="tag-tight" style={{ marginInlineStart: 0 }}>{expiryText(d)}</Tag> : expiryText(d)),
          }] : []),
          ...(prices ? [{ title: 'MRP', dataIndex: 'mrp', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> }] : []),
          ...(details && prices ? [{ title: t('pharmacy.sellingPrice'), dataIndex: 'sale_price', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> }] : []),
          ...(rateOn ? [{ title: t('pharmacy.purchaseRate'), dataIndex: 'purchase_rate', align: 'right' as const, render: (v: string | null) => <span className="num">{money(v)}</span> }] : []),
          ...(details ? [{ title: 'GST', dataIndex: 'gst_rate', align: 'right' as const, render: (v: string) => `${qty(v)}%` }] : []),
          ...(suppliersOn ? [{ title: t('pharmacy.supplier'), dataIndex: 'supplier_name', render: (v: string) => v || '—' }] : []),
          { title: t('pharmacy.available'), dataIndex: 'quantity', align: 'right' as const, render: (v: string) => <b className="num">{qty(v)}</b> },
          {
            title: '', key: 'actions', width: stockLabels ? 280 : 190, align: 'right' as const,
            render: (_: unknown, b: StockBatch) => canStock ? (
              <Space size={4}>
                {/* The labels may give the batch its barcode: reload to show it */}
                <StockLabelsButton batch={b} onPrinted={loadBatches} />
                <Button size="small" onClick={() => setCorrecting(b)}>{t('pharmacy.correct')}</Button>
                {supplierReturns && <Button size="small" onClick={() => setReturning(b)}>{t('pharmacy.returnToSupplier')}</Button>}
              </Space>
            ) : null,
          },
        ]}
      />
      {correcting && <CorrectModal batch={correcting} onClose={(saved) => { setCorrecting(null); if (saved) onChanged(); }} />}
      {returning && <SupplierReturnModal batch={returning} onClose={(saved) => { setReturning(null); if (saved) onChanged(); }} />}
    </>
  );
}

const REASONS = ['damaged', 'expiredRemoved', 'countCorrection', 'foundExtra'] as const;

function CorrectModal({ batch, onClose }: { batch: StockBatch; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const kind: 'damaged' | 'expired' | 'adjust' = Form.useWatch('kind', form) ?? 'damaged';
  const change: number | undefined = Form.useWatch('change', form);
  useEffect(() => { form.setFieldsValue({ kind: 'damaged' }); }, [form]);
  const signed = change ? (kind === 'adjust' ? change : -Math.abs(change)) : 0;

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/stock/adjust/', { batch: batch.id, kind: values.kind, change: signed, reason: values.reason });
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open keyboard={false} maskClosable={false} width={480} title={t('pharmacy.correctTitle', { name: batch.medicine_name, batch: batch.batch_no })}
      onCancel={() => onClose(false)} onOk={save} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}>
      <div className="form-help">{t('pharmacy.correctHelp', { n: qty(batch.quantity) })}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="kind" label={t('pharmacy.correctionType')}>
          <Segmented options={(['damaged', 'expired', 'adjust'] as const).map((k) => ({ value: k, label: t(`pharmacy.kinds.${k}`) }))} />
        </Form.Item>
        <Form.Item name="change" label={kind === 'adjust' ? t('pharmacy.change') : t('pharmacy.packsRemoved')}
          rules={[{ required: true, message: t('common.required') }]}
          extra={change ? t('pharmacy.afterChange', { n: qty(Number(batch.quantity) + signed) }) : kind === 'adjust' ? t('pharmacy.changeHelp') : undefined}>
          <InputNumber min={kind === 'adjust' ? -Number(batch.quantity) : 0.001} max={kind === 'adjust' ? undefined : Number(batch.quantity)} style={{ width: 160 }} />
        </Form.Item>
        <Form.Item name="reason" label={t('pharmacy.reason')} rules={[{ required: true, message: t('common.required') }]}>
          <Input maxLength={200} />
        </Form.Item>
        <div className="chip-list" style={{ marginTop: -6 }}>
          {REASONS.map((r) => (
            <button type="button" key={r} className="pick-chip" onClick={() => form.setFieldValue('reason', t(`pharmacy.reasons.${r}`))}>
              {t(`pharmacy.reasons.${r}`)}
            </button>
          ))}
        </div>
      </Form>
    </Modal>
  );
}

function SupplierReturnModal({ batch, onClose }: { batch: StockBatch; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  useEffect(() => { api.get<Supplier[]>('/suppliers/').then(({ data }) => setSuppliers(data.filter((s) => s.is_active))).catch(() => undefined); }, []);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/purchase-returns/', {
        supplier: values.supplier ?? null, reference: values.reference ?? '', reason: values.reason,
        items: [{ batch: batch.id, quantity: values.quantity }],
      });
      message.success(t('pharmacy.supplierReturnDone'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open keyboard={false} maskClosable={false} width={500} title={t('pharmacy.returnToSupplierTitle', { name: batch.medicine_name, batch: batch.batch_no })}
      onCancel={() => onClose(false)} onOk={save} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="supplier" label={t('pharmacy.supplier')}>
          <Select allowClear showSearch optionFilterProp="label" options={suppliers.map((s) => ({ value: s.id, label: s.name }))} />
        </Form.Item>
        <Space size={12} align="start">
          <Form.Item name="quantity" label={t('pharmacy.qty')} rules={[{ required: true, message: t('common.required') }]}
            extra={t('pharmacy.availableN', { n: qty(batch.quantity) })}>
            <InputNumber min={0.001} max={Number(batch.quantity)} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="reference" label={t('pharmacy.debitNoteNo')}><Input maxLength={60} style={{ width: 200 }} /></Form.Item>
        </Space>
        <Form.Item name="reason" label={t('pharmacy.reason')} rules={[{ required: true, message: t('common.required') }]}>
          <Input maxLength={200} placeholder={t('pharmacy.supplierReturnPlaceholder')} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function LocationModal({ row, racks, onClose }: { row: StockRow; racks: Rack[]; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const rackId: string | undefined = Form.useWatch('rack', form);
  const rack = racks.find((r) => r.id === rackId);
  useEffect(() => { form.setFieldsValue({ rack: row.rack ?? undefined, shelf: row.shelf || undefined, bin: row.bin }); }, [form, row]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/stock/location/', { medicine: row.medicine, rack: values.rack ?? null, shelf: values.shelf ?? '', bin: values.bin ?? '' });
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open keyboard={false} maskClosable={false} width={460} title={t('pharmacy.locationTitle', { name: row.name })} onCancel={() => onClose(false)} onOk={save}
      okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}>
      {!racks.length && <div className="form-help">{t('pharmacy.noRacksYet')}</div>}
      <Form form={form} layout="vertical" requiredMark={false}>
        <Space size={12} align="start" wrap>
          <Form.Item name="rack" label={t('pharmacy.rack')}>
            <Select allowClear style={{ width: 160 }} options={racks.map((r) => ({ value: r.id, label: `${r.code}${r.name ? ` · ${r.name}` : ''}` }))} />
          </Form.Item>
          <Form.Item name="shelf" label={t('pharmacy.shelf')}>
            <Select allowClear style={{ width: 100 }} disabled={!rack}
              options={Array.from({ length: rack?.shelves ?? 0 }, (_, i) => ({ value: String(i + 1), label: String(i + 1) }))} />
          </Form.Item>
          <Form.Item name="bin" label={t('pharmacy.bin')}><Input maxLength={20} style={{ width: 120 }} placeholder="Box 12" /></Form.Item>
        </Space>
      </Form>
    </Modal>
  );
}
