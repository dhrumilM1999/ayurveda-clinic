// A patient's check-ups from all branches (newest first). Click one to open it.
import { Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { VisitListItem } from '../../../api/types';
import { useList } from '../../../api/useList';

export function VisitsTab({ patientId }: { patientId: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { rows, loading, pagination } = useList<VisitListItem>('/visits/', { patient: patientId }, 10);

  return (
    <>
      <Typography.Paragraph type="secondary">{t('consult.visitsTabHelp')}</Typography.Paragraph>
      <Table<VisitListItem>
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        pagination={{ ...pagination, hideOnSinglePage: true }}
        scroll={{ x: true }}
        locale={{ emptyText: t('consult.noVisits') }}
        onRow={(v) => ({ onClick: () => navigate(`/consult/${v.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('appointments.date'), dataIndex: 'visit_date', render: (d: string) => <b>{dayjs(d).format('DD-MM-YYYY')}</b> },
          { title: t('appointments.doctor'), key: 'doc', render: (_: unknown, v: VisitListItem) => `${v.doctor_name} · ${v.branch_name}` },
          { title: t('consult.sections.complaints'), dataIndex: 'complaints', render: (c: string[]) => c.join(', ') || '—' },
          { title: t('consult.sections.diagnosis'), dataIndex: 'diagnoses', render: (d: string[]) => d.join(', ') || '—' },
          {
            title: t('common.status'), dataIndex: 'status',
            render: (s: string) => <Tag color={s === 'completed' ? 'green' : 'gold'}>{t(`consult.status.${s}`)}</Tag>,
          },
        ]}
      />
    </>
  );
}
