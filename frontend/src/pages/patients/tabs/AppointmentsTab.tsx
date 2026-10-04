// A patient's appointments in the current branch, with "Book appointment".
import { PlusOutlined } from '@ant-design/icons';
import { Button, Table, Typography } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Appointment, AppointmentStatus, Patient } from '../../../api/types';
import { useList } from '../../../api/useList';
import { useAuth } from '../../../auth/AuthContext';
import { AppointmentActions } from '../../appointments/AppointmentActions';
import { BookAppointmentModal } from '../../appointments/BookAppointmentModal';
import { StatusTag, fmtTime } from '../../appointments/shared';

export function AppointmentsTab({ patient }: { patient: Patient }) {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [booking, setBooking] = useState(false);
  const { rows, loading, reload, pagination } = useList<Appointment>('/appointments/', {
    patient: patient.id, ordering: '-date',
  }, 10);

  return (
    <>
      <div className="section-toolbar">
        <Typography.Text type="secondary">{t('appointments.patientTabHelp')}</Typography.Text>
        {can('appointments.manage') && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setBooking(true)}>{t('appointments.book')}</Button>
        )}
      </div>
      <Table<Appointment>
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        pagination={{ ...pagination, hideOnSinglePage: true }}
        scroll={{ x: true }}
        locale={{ emptyText: t('appointments.noneForPatient') }}
        columns={[
          {
            title: t('appointments.date'), key: 'date',
            render: (_: unknown, r: Appointment) => (
              <>
                <b>{dayjs(r.date).format('DD-MM-YYYY')}</b>{' '}
                {r.start_time ? fmtTime(r.start_time) : t('appointments.walkInShort')}
                {r.token_number && <span className="token-chip" style={{ marginInlineStart: 6 }}>#{r.token_number}</span>}
              </>
            ),
          },
          { title: t('appointments.doctor'), dataIndex: 'doctor_name' },
          { title: t('appointments.reason'), dataIndex: 'reason', render: (v: string) => v || '—' },
          { title: t('common.status'), dataIndex: 'status', render: (s: AppointmentStatus) => <StatusTag status={s} /> },
          {
            title: '', key: 'actions', align: 'right' as const,
            render: (_: unknown, r: Appointment) => <AppointmentActions appointment={r} onChanged={reload} />,
          },
        ]}
      />
      <BookAppointmentModal
        open={booking}
        kind="booked"
        patient={{ id: patient.id, label: `${patient.full_name} · ${patient.uhid}` }}
        onClose={(changed) => { setBooking(false); if (changed) reload(); }}
      />
    </>
  );
}
