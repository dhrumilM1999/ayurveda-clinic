// Today's final prescriptions of this branch: give the medicines and reduce stock.
import { LeftOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons';
import { App, Button, Checkbox, DatePicker, InputNumber, Modal, Segmented, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { DispenseDetail, DispenseLine, DispenseQueueRow, DispenseStatus } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { PatientCell } from '../appointments/shared';
import { money } from '../medicines/shared';

const REFRESH_SECONDS = 30;
const STATUS_COLORS: Record<DispenseStatus, string> = { pending: 'gold', partly: 'blue', done: 'green' };

export function DispenseStatusTag({ status }: { status: DispenseStatus }) {
  const { t } = useTranslation();
  return <Tag color={STATUS_COLORS[status]} className="tag-tight">{t(`pharmacy.status.${status}`)}</Tag>;
}

export function expiryText(date: string | null) {
  return date ? dayjs(date).format('MM-YYYY') : '—';
}

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
            render: (_: unknown, r: DispenseQueueRow) => (
              <Button size="small" type={r.status === 'done' || !can('pharmacy.dispense') ? 'default' : 'primary'} onClick={() => setOpen(r.id)}>
                {r.status === 'done' || !can('pharmacy.dispense') ? t('common.view') : t('pharmacy.dispense')}
              </Button>
            ),
          },
        ]}
      />
      {open && <DispenseModal prescriptionId={open} onClose={(done) => { setOpen(null); if (done) load(); }} />}
    </>
  );
}

type Choice = { give: boolean; batch?: string; quantity: number };

function DispenseModal({ prescriptionId, onClose }: { prescriptionId: string; onClose: (done: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [detail, setDetail] = useState<DispenseDetail | null>(null);
  const [choices, setChoices] = useState<Record<string, Choice>>({});
  const [saving, setSaving] = useState(false);
  const canDispense = can('pharmacy.dispense');

  useEffect(() => {
    api.get<DispenseDetail>(`/dispensing/${prescriptionId}/`).then(({ data }) => {
      setDetail(data);
      // Suggest: earliest-expiry batch, 1 pack, for lines not given yet
      setChoices(Object.fromEntries(data.lines.map((l) => [l.id, {
        give: !!l.batches.length && !l.given, batch: l.batches[0]?.id, quantity: 1,
      }])));
    }).catch((err) => { message.error(errorMessage(err, t('common.loadFailed'))); onClose(false); });
  // Load once per prescription (the list behind refreshes every 30 s; that must not reset the choices)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prescriptionId]);

  const set = (id: string, patch: Partial<Choice>) => setChoices((c) => ({ ...c, [id]: { ...c[id]!, ...patch } }));
  const batchOf = (l: DispenseLine) => l.batches.find((b) => b.id === choices[l.id]?.batch);
  const total = detail?.lines.reduce((sum, l) => {
    const c = choices[l.id];
    const b = batchOf(l);
    return c?.give && b ? sum + Number(b.mrp) * (c.quantity || 0) : sum;
  }, 0) ?? 0;
  const selected = detail?.lines.filter((l) => choices[l.id]?.give && choices[l.id]?.batch) ?? [];

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post<{ total_amount: string }>(`/dispensing/${prescriptionId}/dispense/`, {
        items: selected.map((l) => ({ prescription_item: l.id, batch: choices[l.id]!.batch, quantity: choices[l.id]!.quantity })),
      });
      message.success(t('pharmacy.dispensedMsg', { amount: money(data.total_amount) }));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const rxText = (l: DispenseLine) => [
    `${l.dose} ${l.dose_unit}`.trim(), l.frequency, l.timing, l.anupana,
    l.duration ? `${l.duration} ${t(`consult.units.${l.duration_unit}`)}` : '',
  ].filter(Boolean).join(' · ');

  return (
    <Modal open width={940} keyboard={false} maskClosable={false} onCancel={() => onClose(false)}
      title={detail ? t('pharmacy.dispenseTitle', { name: detail.patient_detail.full_name }) : t('pharmacy.dispense')}
      footer={(
        <div className="modal-footer-split">
          <span className="total-text">{t('pharmacy.total')}: <b className="num">{money(total)}</b></span>
          <Space>
            <Button onClick={() => onClose(false)}>{t('common.close')}</Button>
            {canDispense && (
              <Button type="primary" loading={saving} disabled={!selected.length} onClick={save}>
                {t('pharmacy.dispenseButton', { count: selected.length })}
              </Button>
            )}
          </Space>
        </div>
      )}>
      {!detail ? <Spin /> : (
        <>
          <div className="cell-sub" style={{ marginBottom: 12 }}>
            {detail.patient_detail.uhid} · {t('pharmacy.byDoctor', { name: detail.doctor_name })}
          </div>
          <Table<DispenseLine>
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={detail.lines}
            columns={[
              {
                title: '', key: 'give', width: 36,
                render: (_: unknown, l: DispenseLine) => (
                  <Checkbox checked={!!choices[l.id]?.give} disabled={!l.batches.length || !canDispense}
                    onChange={(e) => set(l.id, { give: e.target.checked })} aria-label={t('pharmacy.give')} />
                ),
              },
              {
                title: t('rx.medicine'), key: 'medicine',
                render: (_: unknown, l: DispenseLine) => (
                  <div style={{ lineHeight: 1.35 }}>
                    <b>{l.medicine_name}</b> <span className="cell-sub">{l.pack_size}</span>
                    <div className="cell-sub">{rxText(l)}</div>
                    {l.instructions && <div className="cell-sub">{l.instructions}</div>}
                    {l.given && <Tag color="green" className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.alreadyGiven', { n: Number(l.given) })}</Tag>}
                  </div>
                ),
              },
              {
                title: t('pharmacy.batch'), key: 'batch', width: 230,
                render: (_: unknown, l: DispenseLine) => {
                  if (!l.medicine) return <Tag className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.notFromStock')}</Tag>;
                  if (!l.batches.length) return <Tag color="red" className="tag-tight" style={{ marginInlineStart: 0 }}>{t('pharmacy.outOfStock')}</Tag>;
                  return (
                    <Select size="small" style={{ width: '100%' }} value={choices[l.id]?.batch} disabled={!canDispense}
                      onChange={(v) => set(l.id, { batch: v })}
                      options={l.batches.map((b) => ({
                        value: b.id,
                        label: `${b.batch_no} · ${t('pharmacy.exp')} ${expiryText(b.expiry_date)} · ${Number(b.quantity)} ${t('pharmacy.left')}`,
                      }))} />
                  );
                },
              },
              {
                title: t('pharmacy.qty'), key: 'qty', width: 90,
                render: (_: unknown, l: DispenseLine) => l.batches.length ? (
                  <InputNumber size="small" min={0.01} max={Number(batchOf(l)?.quantity ?? 0) || undefined} style={{ width: 72 }}
                    value={choices[l.id]?.quantity} disabled={!canDispense || !choices[l.id]?.give}
                    onChange={(v) => set(l.id, { quantity: Number(v ?? 0) })} />
                ) : null,
              },
              {
                title: t('pharmacy.amount'), key: 'amount', width: 100, align: 'right' as const,
                render: (_: unknown, l: DispenseLine) => {
                  const b = batchOf(l);
                  const c = choices[l.id];
                  return b && c?.give ? <span className="num">{money(Number(b.mrp) * (c.quantity || 0))}</span> : <span className="cell-sub">—</span>;
                },
              },
            ]}
          />
          {detail.notes && <Typography.Paragraph className="pre-line cell-sub" style={{ marginTop: 12, marginBottom: 0 }}>{detail.notes}</Typography.Paragraph>}
        </>
      )}
    </Modal>
  );
}
