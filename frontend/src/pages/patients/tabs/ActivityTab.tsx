// Who opened or changed this patient's file (from the audit log).
import { Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../../api/client';
import type { AuditLogEntry } from '../../../api/types';

const COLORS: Record<string, string> = { view: 'default', create: 'green', update: 'blue', delete: 'red', export: 'purple', print: 'purple' };

export function ActivityTab({ patientId }: { patientId: string }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<AuditLogEntry[]>(`/patients/${patientId}/activity/`)
      .then(({ data }) => setRows(data))
      .finally(() => setLoading(false));
  }, [patientId]);

  return (
    <>
      <Typography.Paragraph type="secondary">{t('patients.activityHelp')}</Typography.Paragraph>
      <Table<AuditLogEntry>
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        pagination={{ pageSize: 15, hideOnSinglePage: true }}
        scroll={{ x: true }}
        columns={[
          { title: t('audit.when'), dataIndex: 'created_at', render: (v: string) => dayjs(v).format('DD-MM-YYYY HH:mm:ss') },
          { title: t('audit.user'), dataIndex: 'username' },
          { title: t('audit.action'), dataIndex: 'action', render: (a: string) => <Tag color={COLORS[a]}>{t(`auditActions.${a}`, { defaultValue: a })}</Tag> },
          { title: t('audit.what'), dataIndex: 'object_type', render: (v: string) => t(`patients.objectTypes.${v.replace('.', '_')}`, { defaultValue: v }) },
          { title: t('layout.branch'), dataIndex: 'branch_name' },
          { title: t('audit.ip'), dataIndex: 'ip_address' },
        ]}
      />
    </>
  );
}
