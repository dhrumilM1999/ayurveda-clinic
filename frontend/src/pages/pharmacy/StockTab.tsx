// Stock of this branch: one row per medicine, batches inside, corrections, low-stock level, history.
import { HistoryOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { App, Button, Drawer, Form, Input, InputNumber, Modal, Segmented, Space, Spin, Table, Tag, Tooltip } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { StockBatch, StockMovement, StockRow } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { expiryText } from './DispenseTab';
import { PurchaseModal } from './PurchaseModal';

type Show = 'all' | 'low' | 'expiring' | 'expired';

export function StockTab() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const canStock = can('pharmacy.stock');
  const [show, setShow] = useState<Show>('all');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [rows, setRows] = useState<StockRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [purchaseOpen, setPurchaseOpen] = useState(false);
  const [history, setHistory] = useState<StockRow | null>(null);
  const [version, setVersion] = useState(0); // reload open batch lists after a change

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<StockRow[]>('/stock/', { params: { show, q: query || undefined } });
      setRows(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [show, query, message, t]);
  useEffect(() => { load(); }, [load]);

  const saveLevel = async (row: StockRow, level: number | null) => {
    if ((level ?? null) === (row.reorder_level === null ? null : Number(row.reorder_level))) return;
    try {
      await api.post('/stock/reorder-level/', { medicine: row.medicine, level });
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const changed = () => { load(); setVersion((v) => v + 1); };

  return (
    <>
      <div className="filter-bar">
        <Input.Search allowClear placeholder={t('medicines.searchPlaceholder')} value={search} style={{ width: 260 }}
          onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }} onSearch={(v) => setQuery(v.trim())} />
        <Segmented value={show} onChange={(v) => setShow(v as Show)}
          options={(['all', 'low', 'expiring', 'expired'] as const).map((k) => ({ value: k, label: t(`pharmacy.show.${k}`) }))} />
        <Button icon={<ReloadOutlined />} onClick={load} aria-label={t('appointments.refresh')} />
        <span style={{ flex: 1 }} />
        {canStock && <Button type="primary" icon={<PlusOutlined />} onClick={() => setPurchaseOpen(true)}>{t('pharmacy.addPurchase')}</Button>}
      </div>
      <Table<StockRow>
        rowKey="medicine"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        locale={{ emptyText: show === 'all' ? t('pharmacy.stockEmpty') : t('pharmacy.nothingHere') }}
        expandable={{ expandedRowRender: (r) => <BatchList key={version} row={r} canStock={canStock} onChanged={changed} /> }}
        columns={[
          {
            title: t('rx.medicine'), key: 'name',
            render: (_: unknown, r: StockRow) => (
              <div style={{ lineHeight: 1.35 }}>
                <b>{r.name}</b>
                <div className="cell-sub">{r.pack_size || '—'}</div>
              </div>
            ),
          },
          {
            title: t('pharmacy.available'), key: 'available', width: 150, align: 'right' as const,
            render: (_: unknown, r: StockRow) => (
              <Space size={6}>
                {r.low && <Tag color="red" className="tag-tight">{t('pharmacy.low')}</Tag>}
                <b className="num">{Number(r.usable)}</b>
              </Space>
            ),
          },
          {
            title: t('pharmacy.nearestExpiry'), key: 'expiry', width: 170,
            render: (_: unknown, r: StockRow) => (
              <Space size={6}>
                <span className={r.expiring ? 'text-warn' : undefined}>{expiryText(r.nearest_expiry)}</span>
                {r.expiring && <Tag color="orange" className="tag-tight">{t('pharmacy.soon')}</Tag>}
                {r.expired && (
                  <Tooltip title={t('pharmacy.expiredHelp', { n: Number(r.available) - Number(r.usable) })}>
                    <Tag color="red" className="tag-tight">{t('pharmacy.expired')}</Tag>
                  </Tooltip>
                )}
              </Space>
            ),
          },
          {
            title: <Tooltip title={t('pharmacy.reorderHelp')}>{t('pharmacy.reorderLevel')}</Tooltip>, key: 'level', width: 160,
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
      {purchaseOpen && <PurchaseModal onClose={(saved) => { setPurchaseOpen(false); if (saved) changed(); }} />}
      {history && <HistoryDrawer row={history} onClose={() => setHistory(null)} />}
    </>
  );
}

function BatchList({ row, canStock, onChanged }: { row: StockRow; canStock: boolean; onChanged: () => void }) {
  const { t } = useTranslation();
  const [batches, setBatches] = useState<StockBatch[] | null>(null);
  const [adjusting, setAdjusting] = useState<StockBatch | null>(null);

  useEffect(() => {
    api.get<StockBatch[]>('/stock/batches/', { params: { medicine: row.medicine } }).then(({ data }) => setBatches(data)).catch(() => setBatches([]));
  }, [row.medicine]);

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
        columns={[
          { title: t('pharmacy.batch'), dataIndex: 'batch_no', render: (b: string) => <span className="mono">{b}</span> },
          {
            title: t('pharmacy.expiry'), dataIndex: 'expiry_date',
            render: (d: string | null) => (d && d < today ? <Tag color="red" className="tag-tight" style={{ marginInlineStart: 0 }}>{expiryText(d)}</Tag> : expiryText(d)),
          },
          { title: 'MRP', dataIndex: 'mrp', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
          { title: t('pharmacy.purchaseRate'), dataIndex: 'purchase_rate', align: 'right' as const, render: (v: string | null) => <span className="num">{money(v)}</span> },
          { title: t('pharmacy.available'), dataIndex: 'quantity', align: 'right' as const, render: (v: string) => <b className="num">{Number(v)}</b> },
          {
            title: '', key: 'adjust', width: 110, align: 'right' as const,
            render: (_: unknown, b: StockBatch) => canStock ? <Button size="small" onClick={() => setAdjusting(b)}>{t('pharmacy.correct')}</Button> : null,
          },
        ]}
      />
      {adjusting && <AdjustModal batch={adjusting} onClose={(saved) => { setAdjusting(null); if (saved) onChanged(); }} />}
    </>
  );
}

const REASONS = ['damaged', 'expiredRemoved', 'countCorrection', 'returned'] as const;

function AdjustModal({ batch, onClose }: { batch: StockBatch; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const change: number | undefined = Form.useWatch('change', form);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/stock/adjust/', { batch: batch.id, change: values.change, reason: values.reason });
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open width={460} title={t('pharmacy.correctTitle', { name: batch.medicine_name, batch: batch.batch_no })}
      onCancel={() => onClose(false)} onOk={save} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}>
      <div className="form-help">{t('pharmacy.correctHelp', { n: Number(batch.quantity) })}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="change" label={t('pharmacy.change')} rules={[{ required: true, message: t('common.required') }]}
          extra={change ? t('pharmacy.afterChange', { n: Number(batch.quantity) + change }) : t('pharmacy.changeHelp')}>
          <InputNumber min={-Number(batch.quantity)} style={{ width: 160 }} placeholder="-2 / +3" />
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

function HistoryDrawer({ row, onClose }: { row: StockRow; onClose: () => void }) {
  const { t } = useTranslation();
  const [moves, setMoves] = useState<StockMovement[] | null>(null);
  useEffect(() => {
    api.get<StockMovement[]>('/stock/movements/', { params: { medicine: row.medicine } }).then(({ data }) => setMoves(data)).catch(() => setMoves([]));
  }, [row.medicine]);
  return (
    <Drawer open width={560} title={t('pharmacy.historyTitle', { name: row.name })} onClose={onClose}>
      {!moves ? <Spin /> : (
        <Table<StockMovement>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={moves}
          columns={[
            { title: t('pharmacy.when'), dataIndex: 'created_at', render: (d: string) => dayjs(d).format('DD-MM-YY HH:mm') },
            { title: t('pharmacy.batch'), dataIndex: 'batch_no', render: (b: string) => <span className="mono">{b}</span> },
            {
              title: t('pharmacy.change'), key: 'q', align: 'right' as const,
              render: (_: unknown, m: StockMovement) => (
                <b className={`num ${Number(m.quantity) < 0 ? 'text-out' : 'text-in'}`}>{Number(m.quantity) > 0 ? '+' : ''}{Number(m.quantity)}</b>
              ),
            },
            { title: t('pharmacy.balance'), dataIndex: 'balance_after', align: 'right' as const, render: (v: string) => <span className="num">{Number(v)}</span> },
            {
              title: t('pharmacy.reason'), key: 'r',
              render: (_: unknown, m: StockMovement) => (
                <div style={{ lineHeight: 1.35 }}>
                  {t(`pharmacy.kinds.${m.kind}`)}
                  <div className="cell-sub">{[m.reason, m.by].filter(Boolean).join(' · ')}</div>
                </div>
              ),
            },
          ]}
        />
      )}
    </Drawer>
  );
}
