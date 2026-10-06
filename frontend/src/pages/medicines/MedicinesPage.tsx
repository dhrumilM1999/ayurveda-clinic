// The medicine list: classical medicines and patent & proprietary brands, with this branch's price.
import { EditOutlined, HistoryOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';
import { App, Button, Input, Segmented, Space, Switch, Table, Tag, Tooltip, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import { useMasterLabel } from '../../api/masters';
import type { Medicine, MedicineKind } from '../../api/types';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { MasterSelect } from '../../components/MasterSelect';
import { ImportModal } from './ImportModal';
import { MedicineFormModal } from './MedicineFormModal';
import { VersionsDrawer } from './VersionsDrawer';
import { FLAGS, MedicineFlags, money, useMedicineName } from './shared';

export default function MedicinesPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const masterLabel = useMasterLabel();
  const medicineName = useMedicineName();
  const manage = can('medicines.manage');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<'all' | MedicineKind>('all');
  const [form, setForm] = useState<string>();
  const [editing, setEditing] = useState<Medicine | 'new' | null>(null);
  const [history, setHistory] = useState<Medicine | null>(null);
  const [importing, setImporting] = useState(false);

  const { rows, total, loading, reload, pagination } = useList<Medicine>('/medicines/', {
    q: query || undefined, kind: kind === 'all' ? undefined : kind, dosage_form: form,
  }, 50);

  const toggle = async (m: Medicine, on: boolean) => {
    try {
      await api.patch(`/medicines/${m.id}/branch/`, { is_active: on });
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('medicines.title')}</Typography.Title>
          <div className="cell-sub">{t('medicines.subtitle', { n: total })}</div>
        </div>
        {manage && (
          <Space>
            <Button icon={<UploadOutlined />} onClick={() => setImporting(true)}>{t('medicines.import')}</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>{t('medicines.add')}</Button>
          </Space>
        )}
      </div>

      <div className="filter-bar">
        <Input.Search
          allowClear
          placeholder={t('medicines.searchPlaceholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }}
          onSearch={(v) => setQuery(v.trim())}
          style={{ width: 280 }}
        />
        <Segmented
          value={kind}
          onChange={(v) => setKind(v as typeof kind)}
          options={[
            { value: 'all', label: t('medicines.kinds.all') },
            { value: 'classical', label: t('medicines.kinds.classical') },
            { value: 'proprietary', label: t('medicines.kinds.proprietary') },
          ]}
        />
        <MasterSelect category="dosage_form" placeholder={t('medicines.allForms')} value={form} onChange={setForm} style={{ width: 200 }} />
      </div>

      <Table<Medicine>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        scroll={{ x: 1100 }}
        rowClassName={(m) => (!m.is_active || !m.branch_active ? 'row-muted' : '')}
        locale={{ emptyText: t('medicines.empty') }}
        columns={[
          {
            title: t('medicines.name'), key: 'name',
            render: (_: unknown, m: Medicine) => (
              <div style={{ lineHeight: 1.35 }}>
                <Typography.Text strong>{medicineName(m)}</Typography.Text>
                {m.is_sample && <Tag color="orange" className="tag-tight">{t('medicines.sample')}</Tag>}
                <div className="cell-sub">
                  {[m.kind === 'proprietary' ? m.manufacturer : m.reference, m.pack_size].filter(Boolean).join(' · ')}
                  {m.classical_equivalent_name && ` · = ${m.classical_equivalent_name}`}
                </div>
              </div>
            ),
          },
          {
            title: t('medicines.kind'), dataIndex: 'kind', width: 120,
            render: (k: MedicineKind) => <Tag color={k === 'classical' ? 'green' : 'blue'} className="tag-tight">{t(`medicines.kinds.${k}`)}</Tag>,
          },
          { title: t('medicines.form'), key: 'form', width: 200, ellipsis: true, render: (_: unknown, m: Medicine) => [masterLabel(m.dosage_form), m.strength].filter(Boolean).join(' · ') || '—' },
          { title: t('medicines.safety'), key: 'flags', width: 250, render: (_: unknown, m: Medicine) => (FLAGS.some((f) => m[f]) ? <MedicineFlags medicine={m} /> : <span className="cell-sub">—</span>) },
          {
            title: t('medicines.price'), key: 'price', width: 110, align: 'right' as const,
            render: (_: unknown, m: Medicine) => (
              <Tooltip title={m.branch_price !== m.mrp ? t('medicines.branchPriceHelp', { mrp: money(m.mrp) }) : undefined}>
                <span className="num">{money(m.branch_price)}</span>
                {m.branch_price !== m.mrp && <span className="price-dot" />}
              </Tooltip>
            ),
          },
          { title: 'GST', dataIndex: 'gst_rate', width: 70, align: 'right' as const, render: (g: string) => <span className="num">{Number(g)}%</span> },
          {
            title: t('medicines.inUse'), key: 'active', width: 90, align: 'center' as const,
            render: (_: unknown, m: Medicine) => (
              <Tooltip title={t('medicines.inUseHelp')}>
                <Switch size="small" checked={m.is_active && m.branch_active} disabled={!manage || !m.is_active}
                  onChange={(on) => toggle(m, on)} />
              </Tooltip>
            ),
          },
          {
            title: '', key: 'actions', width: 84, align: 'right' as const, fixed: 'right' as const,
            render: (_: unknown, m: Medicine) => (
              <Space size={4}>
                <Tooltip title={t('medicines.history')}>
                  <Button size="small" type="text" icon={<HistoryOutlined />} onClick={() => setHistory(m)} aria-label={t('medicines.history')} />
                </Tooltip>
                {manage && (
                  <Tooltip title={t('common.edit')}>
                    <Button size="small" type="text" icon={<EditOutlined />} onClick={() => setEditing(m)} aria-label={t('common.edit')} />
                  </Tooltip>
                )}
              </Space>
            ),
          },
        ]}
      />

      {editing && (
        <MedicineFormModal medicine={editing === 'new' ? null : editing}
          onClose={(saved) => { setEditing(null); if (saved) reload(); }} />
      )}
      {history && <VersionsDrawer medicine={history} onClose={() => setHistory(null)} />}
      {importing && <ImportModal onClose={(done) => { setImporting(false); if (done) reload(); }} />}
    </>
  );
}
