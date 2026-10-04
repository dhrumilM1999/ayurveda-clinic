// Physical stock check: start a count (all or one rack), type what is on the shelf, then complete it.
// Differences are posted to the stock ledger as "Physical count difference".
import { CheckOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, InputNumber, Modal, Progress, Select, Space, Spin, Table, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Page, Rack, StockCheck, StockCheckItem } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { expiryText, qty } from './common';

export function StockCheckTab() {
  const { t } = useTranslation();
  const { can, hasFeature } = useAuth();
  const racks = hasFeature('pharmacy_racks');
  const [rows, setRows] = useState<StockCheck[]>([]);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Page<StockCheck>>('/stock-checks/', { params: { page_size: 50 } });
      setRows(data.results);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  const hasOpen = rows.some((r) => r.status === 'open');

  return (
    <>
      <div className="section-toolbar">
        <span className="cell-sub">{t('pharmacy.checkHelp')}</span>
        {can('pharmacy.stock') && (
          <Button type="primary" icon={<PlusOutlined />} disabled={hasOpen} onClick={() => setStarting(true)}>{t('pharmacy.startCheck')}</Button>
        )}
      </div>
      <Table<StockCheck>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: t('pharmacy.noChecks') }}
        onRow={(r) => ({ onClick: () => setOpen(r.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('pharmacy.checkTitle'), dataIndex: 'title', render: (v: string) => <b>{v}</b> },
          ...(racks ? [{ title: t('pharmacy.rack'), dataIndex: 'rack_code', width: 90, render: (v: string) => v || t('pharmacy.allRacks') }] : []),
          { title: t('appointments.date'), dataIndex: 'created_at', width: 120, render: (d: string) => dayjs(d).format('DD-MM-YYYY') },
          {
            title: t('pharmacy.counted'), key: 'c', width: 180,
            render: (_: unknown, r: StockCheck) => <Progress size="small" percent={r.item_count ? Math.round((r.counted_count * 100) / r.item_count) : 0} format={() => `${r.counted_count}/${r.item_count}`} />,
          },
          { title: t('pharmacy.mismatches'), dataIndex: 'mismatch_count', width: 110, align: 'center' as const, render: (n: number) => (n ? <Tag color="orange" className="tag-tight" style={{ marginInlineStart: 0 }}>{n}</Tag> : '0') },
          {
            title: t('common.status'), dataIndex: 'status', width: 120,
            render: (s: string) => <Tag color={s === 'open' ? 'gold' : 'green'} className="tag-tight" style={{ marginInlineStart: 0 }}>{t(`pharmacy.checkStatus.${s}`)}</Tag>,
          },
          { title: t('pharmacy.enteredBy'), dataIndex: 'created_by_name', width: 160 },
        ]}
      />
      {starting && <StartModal onClose={(id) => { setStarting(false); load(); if (id) setOpen(id); }} />}
      {open && <CountModal id={open} onClose={() => { setOpen(null); load(); }} />}
    </>
  );
}

function StartModal({ onClose }: { onClose: (id?: string) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const useRacks = useAuth().hasFeature('pharmacy_racks');
  const [racks, setRacks] = useState<Rack[]>([]);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    form.setFieldsValue({ title: t('pharmacy.checkDefaultTitle', { date: dayjs().format('DD-MM-YYYY') }) });
    if (useRacks) api.get<Rack[]>('/racks/').then(({ data }) => setRacks(data.filter((r) => r.is_active))).catch(() => undefined);
  }, [form, t, useRacks]);
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const { data } = await api.post<StockCheck>('/stock-checks/', values);
      onClose(data.id);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal open keyboard={false} maskClosable={false} width={460} title={t('pharmacy.startCheck')} onCancel={() => onClose()} onOk={save}
      okText={t('pharmacy.startCheck')} cancelText={t('common.cancel')} confirmLoading={saving}>
      <div className="form-help">{t('pharmacy.startCheckHelp')}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="title" label={t('pharmacy.checkTitle')} rules={[{ required: true, message: t('common.required') }]}><Input maxLength={120} /></Form.Item>
        {useRacks && (
          <Form.Item name="rack" label={t('pharmacy.rack')} extra={t('pharmacy.checkRackHelp')}>
            <Select allowClear placeholder={t('pharmacy.allRacks')} options={racks.map((r) => ({ value: r.id, label: `${r.code}${r.name ? ` · ${r.name}` : ''}` }))} />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}

function CountModal({ id, onClose }: { id: string; onClose: () => void }) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const { can, hasFeature } = useAuth();
  const [check, setCheck] = useState<StockCheck | null>(null);
  const [counts, setCounts] = useState<Record<string, number | null>>({});
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState('');

  const load = useCallback(() => {
    api.get<StockCheck>(`/stock-checks/${id}/`).then(({ data }) => {
      setCheck(data);
      setCounts(Object.fromEntries((data.items ?? []).map((i) => [i.id, i.counted_quantity === null ? null : Number(i.counted_quantity)])));
    });
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const editable = check?.status === 'open' && can('pharmacy.stock');
  const saveCounts = async () => {
    setSaving(true);
    try {
      await api.post(`/stock-checks/${id}/count/`, { counts: Object.entries(counts).map(([item, v]) => ({ item, counted_quantity: v })) });
      message.success(t('common.saved'));
      load();
      return true;
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
      return false;
    } finally {
      setSaving(false);
    }
  };
  const complete = () => modal.confirm({
    title: t('pharmacy.completeCheck'), content: t('pharmacy.completeCheckHelp'), okText: t('pharmacy.completeCheck'), cancelText: t('common.cancel'),
    onOk: async () => {
      if (!(await saveCounts())) return;
      try {
        const { data } = await api.post<{ changed: number }>(`/stock-checks/${id}/complete/`);
        message.success(t('pharmacy.checkCompleted', { count: data.changed }));
        onClose();
      } catch (err) {
        message.error(errorMessage(err, t('common.saveFailed')));
      }
    },
  });

  const items = (check?.items ?? []).filter((i) => !filter || i.medicine_name.toLowerCase().includes(filter.toLowerCase()) || i.batch_no.toLowerCase() === filter.toLowerCase());

  return (
    <Modal open width={940} title={check?.title ?? ''} onCancel={onClose} keyboard={false} maskClosable={false}
      footer={editable ? (
        <Space>
          <Button onClick={onClose}>{t('common.close')}</Button>
          <Button loading={saving} onClick={saveCounts}>{t('pharmacy.saveCounts')}</Button>
          <Button type="primary" icon={<CheckOutlined />} onClick={complete}>{t('pharmacy.completeCheck')}</Button>
        </Space>
      ) : <Button onClick={onClose}>{t('common.close')}</Button>}>
      {!check ? <Spin /> : (
        <>
          <div className="section-toolbar">
            <span className="cell-sub">{editable ? t('pharmacy.countHelp') : t('pharmacy.checkDoneHelp', { date: dayjs(check.completed_at).format('DD-MM-YYYY HH:mm') })}</span>
            <Input allowClear placeholder={t('pharmacy.filterCheck')} value={filter} onChange={(e) => setFilter(e.target.value)} style={{ width: 220 }} />
          </div>
          <Table<StockCheckItem> size="small" rowKey="id" pagination={false} dataSource={items} scroll={items.length > 8 ? { y: 420 } : undefined}
            columns={[
              ...(hasFeature('pharmacy_racks') ? [{ title: t('pharmacy.location'), dataIndex: 'location', width: 90, render: (v: string) => v || '—' }] : []),
              { title: t('rx.medicine'), dataIndex: 'medicine_name' },
              { title: t('pharmacy.batch'), dataIndex: 'batch_no', width: 120, render: (b: string) => <span className="mono">{b}</span> },
              { title: t('pharmacy.expiry'), dataIndex: 'expiry_date', width: 90, render: expiryText },
              { title: t('pharmacy.system'), dataIndex: 'system_quantity', width: 90, align: 'right' as const, render: (v: string) => <span className="num">{qty(v)}</span> },
              {
                title: t('pharmacy.counted'), key: 'c', width: 110,
                render: (_: unknown, i: StockCheckItem) => (
                  <InputNumber size="small" min={0} style={{ width: 90 }} disabled={!editable} value={counts[i.id] ?? undefined}
                    onChange={(v) => setCounts((c) => ({ ...c, [i.id]: v === null ? null : Number(v) }))} />
                ),
              },
              {
                title: t('pharmacy.difference'), key: 'd', width: 100, align: 'right' as const,
                render: (_: unknown, i: StockCheckItem) => {
                  const c = counts[i.id];
                  if (c === null || c === undefined) return <span className="cell-sub">—</span>;
                  const diff = c - Number(i.system_quantity);
                  return <b className={`num ${diff < 0 ? 'text-out' : diff > 0 ? 'text-in' : ''}`}>{diff > 0 ? '+' : ''}{qty(diff)}</b>;
                },
              },
            ]} />
        </>
      )}
    </Modal>
  );
}
