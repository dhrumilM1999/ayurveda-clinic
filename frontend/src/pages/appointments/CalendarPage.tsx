// Calendar: see at a glance which days have free time. A month view with, for every day, how many times are free and how
// many patients are booked; click a day to see its time slots (free or booked, and who) and book a free one.
// SAFE TO EDIT: the words are in src/i18n/*.json under "calendar".
import { LeftOutlined, PlusOutlined, RightOutlined } from '@ant-design/icons';
import { Button, Calendar, DatePicker, Empty, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { Appointment, AppointmentDoctor, Slot } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { BookAppointmentModal } from './BookAppointmentModal';
import { StatusTag, fmtTime } from './shared';

interface DaySummary { date: string; sits: boolean; free: number; past: number; slots: number; booked: number; walk_in: number }

export default function CalendarPage() {
  const { t } = useTranslation();
  const { can, multiDoctor } = useAuth();
  const [month, setMonth] = useState<Dayjs>(dayjs().startOf('month'));
  const [selected, setSelected] = useState<Dayjs>(dayjs());
  const [doctors, setDoctors] = useState<AppointmentDoctor[]>([]);
  const [doctor, setDoctor] = useState<string | undefined>();
  const [days, setDays] = useState<Record<string, DaySummary>>({});
  const [loading, setLoading] = useState(false);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [booked, setBooked] = useState<Appointment[]>([]);
  const [dayLoading, setDayLoading] = useState(false);
  const [booking, setBooking] = useState<{ start?: string } | null>(null);
  const [version, setVersion] = useState(0);

  // The month grid shows leading / trailing days of the neighbouring months too
  const from = month.startOf('month').startOf('week');
  const to = month.endOf('month').endOf('week');

  useEffect(() => {
    api.get<AppointmentDoctor[]>('/appointments/doctors/', { params: { date: selected.format('YYYY-MM-DD') } })
      .then(({ data }) => { setDoctors(data); if (data.length === 1) setDoctor(data[0]!.id); })
      .catch(() => setDoctors([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let current = true; // an older, slower answer must not replace the newest one
    setLoading(true);
    api.get<{ days: DaySummary[] }>('/appointments/calendar/', {
      params: { from: from.format('YYYY-MM-DD'), to: to.format('YYYY-MM-DD'), doctor },
    }).then(({ data }) => { if (current) setDays(Object.fromEntries(data.days.map((d) => [d.date, d]))); })
      .catch(() => { if (current) setDays({}); }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month, doctor, version]);

  const monthsAway = month.diff(dayjs().startOf('month'), 'month');
  const key = selected.format('YYYY-MM-DD');
  useEffect(() => {
    let current = true;
    setDayLoading(true);
    const slotCall = doctor
      ? api.get<{ slots: Slot[] }>('/appointments/slots/', { params: { doctor, date: key } }).then(({ data }) => data.slots)
      : Promise.resolve([] as Slot[]);
    Promise.all([
      slotCall,
      api.get<{ results: Appointment[] }>('/appointments/', { params: { date: key, doctor, page_size: 200, ordering: 'start_time' } })
        .then(({ data }) => data.results),
    ]).then(([s, a]) => { if (current) { setSlots(s); setBooked(a.filter((x) => x.status !== 'cancelled')); } })
      .catch(() => { if (current) { setSlots([]); setBooked([]); } }).finally(() => { if (current) setDayLoading(false); });
    return () => { current = false; };
  }, [key, doctor, version]);

  const byTime = useMemo(() => Object.fromEntries(booked.filter((a) => a.start_time).map((a) => [a.start_time!.slice(0, 5), a])), [booked]);
  const walkIns = booked.filter((a) => a.kind === 'walk_in');
  const summary = days[key];

  const cell = (date: Dayjs) => {
    const d = days[date.format('YYYY-MM-DD')];
    if (!d || !date.isSame(month, 'month')) return null;
    if (!d.sits && !d.booked && !d.walk_in) return <div className="cal-cell cal-closed">{t('calendar.closed')}</div>;
    return (
      <div className="cal-cell">
        {d.slots > 0 && !date.isBefore(dayjs(), 'day') && <span className={`cal-free${d.free === 0 ? ' none' : ''}`}>{t('calendar.free', { n: d.free })}</span>}
        {(d.booked > 0 || d.walk_in > 0) && <span className="cal-booked">{t('calendar.patients', { count: d.booked + d.walk_in })}</span>}
      </div>
    );
  };

  const rows = slots.map((s) => ({ ...s, appointment: byTime[s.start] as Appointment | undefined }));

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('calendar.title')}</Typography.Title>
          <div className="cell-sub">{t('calendar.subtitle')}</div>
        </div>
        <Space wrap>
          {multiDoctor && (
            <Select allowClear placeholder={t('appointments.allDoctors')} value={doctor} onChange={setDoctor} style={{ minWidth: 200 }}
              options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} />
          )}
          <Button onClick={() => { setMonth(dayjs().startOf('month')); setSelected(dayjs()); }} disabled={month.isSame(dayjs(), 'month') && selected.isSame(dayjs(), 'day')}>{t('calendar.today')}</Button>
        </Space>
      </div>

      {/* Which month is this? A big title, and how far from now it is, so going forward or back is never confusing */}
      <div className="cal-monthbar">
        <Button size="large" icon={<LeftOutlined />} onClick={() => setMonth(month.subtract(1, 'month'))}>{month.subtract(1, 'month').format('MMM')}</Button>
        <div className="cal-monthtitle">
          <DatePicker picker="month" allowClear={false} value={month} format="MMMM YYYY" variant="borderless" className="cal-monthpicker"
            onChange={(d) => d && setMonth(d.startOf('month'))} suffixIcon={null} inputReadOnly />
          <Tag color={monthsAway === 0 ? 'blue' : monthsAway > 0 ? 'purple' : 'default'} bordered={false}>
            {monthsAway === 0 ? t('calendar.thisMonth') : monthsAway === 1 ? t('calendar.nextMonth') : monthsAway === -1 ? t('calendar.lastMonth')
              : monthsAway > 0 ? t('calendar.monthsAhead', { n: monthsAway }) : t('calendar.monthsAgo', { n: -monthsAway })}
          </Tag>
        </div>
        <Button size="large" onClick={() => setMonth(month.add(1, 'month'))}>{month.add(1, 'month').format('MMM')} <RightOutlined /></Button>
      </div>

      <div className="cal-layout">
        <Spin spinning={loading}>
          {/* The grid shows the chosen month (value={month}); the selected day is drawn by our own cell */}
          <Calendar className="cal-grid" value={month} fullscreen headerRender={() => null}
            onSelect={(d, meta) => { if (meta.source === 'date' && d.isSame(month, 'month')) setSelected(d); }}
            fullCellRender={(date, info) => {
              if (info.type !== 'date') return info.originNode;
              const inMonth = date.isSame(month, 'month');
              return (
                <div className={`cal-daycell${inMonth ? '' : ' cal-out'}${date.isSame(selected, 'day') ? ' cal-picked' : ''}${date.isSame(dayjs(), 'day') ? ' cal-today' : ''}`}>
                  <div className="cal-daynum">{date.date()}</div>
                  {inMonth && cell(date)}
                </div>
              );
            }} />
        </Spin>

        <div className="cal-day">
          <div className="cal-day-head">
            <div>
              <Typography.Title level={5} style={{ margin: 0 }}>{selected.format('dddd, DD-MM-YYYY')}</Typography.Title>
              {summary && (
                <div className="cell-sub">
                  {summary.sits ? t('calendar.dayLine', { free: summary.free, booked: summary.booked, walk: summary.walk_in }) : t('calendar.closed')}
                </div>
              )}
            </div>
            {can('appointments.manage') && !selected.isBefore(dayjs(), 'day') && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setBooking({})}>{t('appointments.book')}</Button>
            )}
          </div>
          {multiDoctor && !doctor && <div className="cell-sub" style={{ margin: '8px 0' }}>{t('calendar.pickDoctor')}</div>}
          <Table<(typeof rows)[number]>
            size="small" rowKey="start" loading={dayLoading} dataSource={rows} pagination={false}
            locale={{ emptyText: doctor || !multiDoctor ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('calendar.noSlots')} /> : t('calendar.pickDoctor') }}
            columns={[
              { title: t('appointments.time'), dataIndex: 'start', width: 90, render: (v: string) => <b>{fmtTime(v)}</b> },
              {
                title: t('common.status'), key: 'st',
                render: (_: unknown, r) => r.appointment ? (
                  <Space size={6} wrap><b>{r.appointment.patient_detail.full_name}</b><StatusTag status={r.appointment.status} /></Space>
                ) : r.status === 'past' ? <Tag bordered={false}>{t('calendar.past')}</Tag> : <Tag color="green" bordered={false}>{t('calendar.freeTag')}</Tag>,
              },
              {
                title: '', key: 'a', width: 90, align: 'right' as const,
                render: (_: unknown, r) => (!r.appointment && r.status === 'free' && can('appointments.manage')
                  ? <Button size="small" onClick={() => setBooking({ start: r.start })}>{t('calendar.bookThis')}</Button> : null),
              },
            ]}
          />
          {walkIns.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div className="cell-sub">{t('calendar.walkIns')}</div>
              <Space size={[6, 6]} wrap>{walkIns.map((a) => <Tag key={a.id}>{a.patient_detail.full_name} <StatusTag status={a.status} /></Tag>)}</Space>
            </div>
          )}
        </div>
      </div>

      <BookAppointmentModal open={booking !== null} kind="booked" defaultDate={selected} defaultDoctor={doctor} defaultStart={booking?.start}
        onClose={(changed) => { setBooking(null); if (changed) setVersion((v) => v + 1); }} />
    </>
  );
}
