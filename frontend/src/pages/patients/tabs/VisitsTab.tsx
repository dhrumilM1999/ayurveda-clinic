// A patient's check-ups from all branches (newest first). Click one to open it.
import { Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../../auth/AuthContext';
import { useNavigate } from 'react-router-dom';
import type { VisitListItem } from '../../../api/types';
import { useList } from '../../../api/useList';
import { ListEmpty } from '../../../components/ListEmpty';

export function VisitsTab({ patientId }: { patientId: string }) {
  const { multiBranch, multiDoctor } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { rows, loading, pagination, failed, reload } = useList<VisitListItem>('/visits/', { patient: patientId }, 10);

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
        locale={{ emptyText: <ListEmpty failed={failed} onRetry={reload} text={t('consult.noVisits')} /> }}
        onRow={(v) => ({ onClick: () => navigate(`/consult/${v.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('appointments.date'), dataIndex: 'visit_date', render: (d: string) => <b>{dayjs(d).format('DD-MM-YYYY')}</b> },
          { title: t('appointments.doctor'), key: 'doc', render: (_: unknown, v: VisitListItem) => [multiDoctor ? v.doctor_name : '', multiBranch ? v.branch_name : ''].filter(Boolean).join(' · ') || v.doctor_name },
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
