// Appointments of one day in the current branch: book, walk-in, check in, reschedule, cancel.
import { LeftOutlined, PlusOutlined, ReloadOutlined, RightOutlined, UserAddOutlined } from '@ant-design/icons';
import { Button, DatePicker, Input, Segmented, Select, Space, Table, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import type { Appointment, AppointmentDoctor, AppointmentStatus } from '../../api/types';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { AppointmentActions } from './AppointmentActions';
import { BookAppointmentModal } from './BookAppointmentModal';
import { PatientCell, StatusTag, fmtTime } from './shared';

type Filter = 'all' | 'booked' | 'waiting' | 'done' | 'cancelled';

const FILTER_STATUSES: Record<Filter, AppointmentStatus[] | null> = {
  all: null,
  booked: ['booked'],
  waiting: ['checked_in', 'in_consultation'],
  done: ['completed'],
  cancelled: ['cancelled', 'no_show'],
};

export default function AppointmentsPage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [day, setDay] = useState<Dayjs>(dayjs());
  const [doctor, setDoctor] = useState<string>();
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [doctors, setDoctors] = useState<AppointmentDoctor[]>([]);
  const [booking, setBooking] = useState<'booked' | 'walk_in' | null>(null);
  const dayKey = day.format('YYYY-MM-DD');

  const { rows, loading, reload } = useList<Appointment>('/appointments/', {
    date: dayKey, doctor, q: query || undefined, ordering: 'start_time',
  }, 200); // one day fits on one page

  useEffect(() => {
    api.get<AppointmentDoctor[]>('/appointments/doctors/', { params: { date: dayKey } })
      .then(({ data }) => setDoctors(data))
      .catch(() => setDoctors([]));
  }, [dayKey]);

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: rows.length, booked: 0, waiting: 0, done: 0, cancelled: 0 };
    for (const row of rows) {
      for (const key of ['booked', 'waiting', 'done', 'cancelled'] as Filter[]) {
        if (FILTER_STATUSES[key]!.includes(row.status)) c[key] += 1;
      }
    }
    return c;
  }, [rows]);

  const shown = FILTER_STATUSES[filter] ? rows.filter((r) => FILTER_STATUSES[filter]!.includes(r.status)) : rows;
  // Booked times first (in time order), then walk-ins (in token order)
  const sorted = [...shown].sort((x, y) =>
    (x.start_time ?? '99').localeCompare(y.start_time ?? '99') || (x.token_number ?? 999) - (y.token_number ?? 999));

  const isToday = day.isSame(dayjs(), 'day');

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('appointments.title')}</Typography.Title>
          <div className="cell-sub">{t('appointments.subtitle', { n: counts.all })}</div>
        </div>
        <Space wrap>
          {can('appointments.manage') && (
            <>
              <Button icon={<UserAddOutlined />} onClick={() => setBooking('walk_in')}>{t('appointments.walkIn')}</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setBooking('booked')}>{t('appointments.book')}</Button>
            </>
          )}
        </Space>
      </div>

      <div className="filter-bar">
        <Space.Compact>
          <Button icon={<LeftOutlined />} onClick={() => setDay(day.subtract(1, 'day'))} aria-label={t('appointments.prevDay')} />
          <DatePicker value={day} onChange={(d) => d && setDay(d)} format="ddd, DD-MM-YYYY" allowClear={false} style={{ width: 170 }} />
          <Button icon={<RightOutlined />} onClick={() => setDay(day.add(1, 'day'))} aria-label={t('appointments.nextDay')} />
        </Space.Compact>
        {!isToday && <Button onClick={() => setDay(dayjs())}>{t('appointments.today')}</Button>}
        <Select
          allowClear
          placeholder={t('appointments.allDoctors')}
          value={doctor}
          onChange={setDoctor}
          style={{ minWidth: 200 }}
          options={doctors.map((d) => ({ value: d.id, label: d.full_name }))}
        />
        <Input.Search
          allowClear
          placeholder={t('appointments.searchPlaceholder')}
          value={search}
          onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }}
          onSearch={(v) => setQuery(v.trim())}
          style={{ width: 240 }}
        />
        <Button icon={<ReloadOutlined />} onClick={reload} aria-label={t('appointments.refresh')} />
      </div>

      <Segmented
        className="status-filter"
        value={filter}
        onChange={(v) => setFilter(v as Filter)}
        options={(Object.keys(FILTER_STATUSES) as Filter[]).map((key) => ({
          value: key, label: `${t(`appointments.filters.${key}`)} (${counts[key]})`,
        }))}
      />

      <Table<Appointment>
        rowKey="id"
        size="middle"
        loading={loading}
        dataSource={sorted}
        pagination={false}
        scroll={{ x: 900 }}
        rowClassName={(r) => (['cancelled', 'no_show'].includes(r.status) ? 'row-muted' : '')}
        locale={{ emptyText: t('appointments.empty') }}
        columns={[
          {
            title: t('appointments.time'), key: 'time', width: 120,
            render: (_: unknown, r: Appointment) => (
              <div style={{ lineHeight: 1.35 }}>
                <b>{r.start_time ? fmtTime(r.start_time) : t('appointments.walkInShort')}</b>
                {r.token_number && <div><span className="token-chip">#{r.token_number}</span></div>}
              </div>
            ),
          },
          {
            title: t('appointments.patient'), key: 'patient',
            render: (_: unknown, r: Appointment) => (
              <Link to={`/patients/${r.patient}`} style={{ color: 'inherit' }}><PatientCell patient={r.patient_detail} /></Link>
            ),
          },
          { title: t('appointments.doctor'), dataIndex: 'doctor_name' },
          {
            title: t('appointments.reason'), dataIndex: 'reason', ellipsis: true,
            render: (v: string, r: Appointment) => (
              <>
                {v || <span className="cell-sub">—</span>}
                {r.reschedule_count > 0 && <div className="cell-sub">{t('appointments.movedTimes', { n: r.reschedule_count })}</div>}
                {r.cancel_reason && <div className="cell-sub">{r.cancel_reason}</div>}
              </>
            ),
          },
          { title: t('common.status'), dataIndex: 'status', width: 120, render: (s: AppointmentStatus) => <StatusTag status={s} /> },
          {
            title: '', key: 'actions', width: 150, align: 'right' as const,
            render: (_: unknown, r: Appointment) => <AppointmentActions appointment={r} onChanged={reload} />,
          },
        ]}
      />

      <BookAppointmentModal
        open={booking !== null}
        kind={booking ?? 'booked'}
        defaultDate={day}
        defaultDoctor={doctor}
        onClose={(changed) => { setBooking(null); if (changed) reload(); }}
      />
    </>
  );
}
