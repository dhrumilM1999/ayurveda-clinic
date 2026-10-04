// Audit log: who did what and when. Read-only.
import { DatePicker, Input, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { AuditLogEntry } from '../api/types';
import { useList } from '../api/useList';

const ACTIONS = [
  'view', 'create', 'update', 'delete', 'print', 'export', 'share',
  'login', 'login_failed', 'otp_sent', 'otp_failed', 'logout', 'password_change',
];

const ACTION_COLORS: Record<string, string> = {
  create: 'green', update: 'blue', delete: 'red', login_failed: 'volcano', otp_failed: 'volcano', print: 'purple',
};

export default function AuditLogPage() {
  const { t } = useTranslation();
  const [action, setAction] = useState<string | undefined>();
  const [search, setSearch] = useState('');
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  const { rows, loading, pagination } = useList<AuditLogEntry>('/audit-logs/', {
    action,
    search,
    date_from: range?.[0]?.format('YYYY-MM-DD'),
    date_to: range?.[1]?.format('YYYY-MM-DD'),
  });

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('audit.title')}</Typography.Title>
        <Space wrap>
          <Select allowClear placeholder={t('audit.action')} style={{ width: 180 }} value={action} onChange={setAction}
            options={ACTIONS.map((a) => ({ value: a, label: t(`auditActions.${a}`) }))} />
          <DatePicker.RangePicker value={range} onChange={(v) => setRange(v)} format="DD-MM-YYYY" />
          <Input.Search placeholder={t('common.search')} allowClear onSearch={setSearch} style={{ width: 200 }} />
        </Space>
      </div>
      <Typography.Paragraph type="secondary">{t('audit.help')}</Typography.Paragraph>
      <Table<AuditLogEntry>
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        scroll={{ x: true }}
        expandable={{
          rowExpandable: (r) => Object.keys(r.changes ?? {}).length > 0,
          expandedRowRender: (r) => <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(r.changes, null, 2)}</pre>,
        }}
        columns={[
          { title: t('audit.when'), dataIndex: 'created_at', width: 160, render: (v: string) => dayjs(v).format('DD-MM-YYYY HH:mm:ss') },
          { title: t('audit.user'), dataIndex: 'username' },
          { title: t('audit.action'), dataIndex: 'action', render: (a: string) => <Tag color={ACTION_COLORS[a]}>{t(`auditActions.${a}`, { defaultValue: a })}</Tag> },
          { title: t('audit.what'), dataIndex: 'object_type' },
          { title: t('audit.record'), dataIndex: 'object_repr' },
          { title: t('layout.branch'), dataIndex: 'branch_name' },
          { title: t('audit.ip'), dataIndex: 'ip_address' },
        ]}
      />
    </>
  );
}
