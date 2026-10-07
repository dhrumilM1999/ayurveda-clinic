// The doctor's check-up screen: today's patients on the left, the open check-up on the right.
import { LeftOutlined, PlusOutlined, ReloadOutlined, RightOutlined, SearchOutlined } from '@ant-design/icons';
import { App, Button, DatePicker, Empty, Input, Modal, Select, Spin, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import type { Appointment, AppointmentDoctor, Page, Visit } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { PatientPicker, StatusTag, fmtTime } from '../appointments/shared';
import { VisitWorkspace } from './VisitWorkspace';

const REFRESH_SECONDS = 30;

export default function ConsultPage() {
  const { visitId } = useParams();
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { me, can, features } = useAuth();
  const withAppointments = can('appointments.view') && features.appointments !== false;
  const [doctors, setDoctors] = useState<AppointmentDoctor[]>([]);
  const [doctor, setDoctor] = useState<string | undefined>(me?.user.is_doctor ? me.user.id : undefined);
  const [rows, setRows] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState<string | null>(null);
  // Which appointment belongs to the open check-up (highlighted in the list)
  const [currentAppointment, setCurrentAppointment] = useState<string | null>(null);
  const [pickOpen, setPickOpen] = useState(false);
  const [picked, setPicked] = useState<string>();

  const today = dayjs().format('YYYY-MM-DD');
  // The day shown in the list (today by default), a quick filter and a search box
  const [day, setDay] = useState(today);
  const [filter, setFilter] = useState<'all' | 'checked_in' | 'in_consultation' | 'booked' | 'completed'>('all');
  const [search, setSearch] = useState('');
  const moveDay = (delta: number) => setDay(dayjs(day).add(delta, 'day').format('YYYY-MM-DD'));

  const loadList = useCallback(async () => {
    if (!withAppointments) return;
    setLoading(true);
    try {
      const { data } = await api.get<Page<Appointment>>('/appointments/', {
        params: { date: day, doctor, page_size: 200, ordering: 'start_time' },
      });
      setRows(data.results.filter((a) => !['cancelled', 'no_show'].includes(a.status)));
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [withAppointments, day, doctor]);

  useEffect(() => {
    loadList();
    const timer = window.setInterval(loadList, REFRESH_SECONDS * 1000);
    return () => window.clearInterval(timer);
  }, [loadList]);

  useEffect(() => {
    if (!withAppointments) return;
    api.get<AppointmentDoctor[]>('/appointments/doctors/', { params: { date: day } })
      .then(({ data }) => setDoctors(data)).catch(() => setDoctors([]));
  }, [withAppointments, day]);

  const open = async (payload: { appointment?: string; patient?: string }, key: string) => {
    setOpening(key);
    try {
      const { data } = await api.post<Visit>('/visits/', payload);
      navigate(`/consult/${data.id}`);
      loadList();
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setOpening(null);
    }
  };

  // Waiting / with doctor first, then booked (not arrived), then done
  const order = { in_consultation: 0, checked_in: 1, booked: 2, completed: 3 } as Record<string, number>;
  const sorted = [...rows].sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9)
    || (a.token_number ?? 999) - (b.token_number ?? 999) || (a.start_time ?? '').localeCompare(b.start_time ?? ''));

  const count = (status: string) => rows.filter((a) => a.status === status).length;
  const needle = search.trim().toLowerCase();
  const shown = sorted.filter((a) => (filter === 'all' || a.status === filter)
    && (!needle || `${a.patient_detail.full_name} ${a.patient_detail.uhid} ${a.reason}`.toLowerCase().includes(needle)));

  return (
    <div className="consult">
      <aside className="consult-list">
        <div className="consult-list-head">
          <div className="section-title" style={{ margin: 0 }}>{t('consult.appointmentsTitle')}</div>
          <Button size="small" type="text" icon={<ReloadOutlined />} onClick={loadList} aria-label={t('appointments.refresh')} />
        </div>
        <div className="consult-day">
          <Button size="small" icon={<LeftOutlined />} onClick={() => moveDay(-1)} aria-label={t('consult.previousDay')} />
          <DatePicker size="small" allowClear={false} format="DD-MM-YYYY" value={dayjs(day)} onChange={(d) => d && setDay(d.format('YYYY-MM-DD'))} style={{ flex: 1 }} />
          <Button size="small" icon={<RightOutlined />} onClick={() => moveDay(1)} aria-label={t('consult.nextDay')} />
          {day !== today && <Button size="small" type="link" onClick={() => setDay(today)}>{t('consult.today')}</Button>}
        </div>
        {withAppointments && doctors.length > 1 && (
          <Select size="small" allowClear placeholder={t('appointments.allDoctors')} value={doctor} onChange={setDoctor}
            options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} style={{ width: '100%' }} />
        )}
        <Input size="small" allowClear prefix={<SearchOutlined />} placeholder={t('consult.searchList')} value={search}
          onChange={(e) => setSearch(e.target.value)} />
        <div className="consult-filters">
          {([['all', rows.length], ['checked_in', count('checked_in')], ['in_consultation', count('in_consultation')],
            ['booked', count('booked')], ['completed', count('completed')]] as [typeof filter, number][]).map(([value, n]) => (
            <Tag.CheckableTag key={value} checked={filter === value} onChange={() => setFilter(value)}>
              {t(`consult.filter.${{ all: 'all', checked_in: 'waiting', in_consultation: 'withDoctor', booked: 'booked', completed: 'done' }[value]}`)} {n}
            </Tag.CheckableTag>
          ))}
        </div>
        {me?.user.is_doctor && can('emr.edit') && (
          <Button size="small" block icon={<PlusOutlined />} onClick={() => { setPicked(undefined); setPickOpen(true); }}>
            {t('consult.withoutAppointment')}
          </Button>
        )}
        <div className="consult-items">
          {loading && !rows.length && <Spin size="small" />}
          {!loading && !shown.length && <div className="cell-sub">{withAppointments ? (rows.length ? t('consult.noMatch') : t('consult.noPatientsToday')) : t('consult.appointmentsOff')}</div>}
          {shown.map((a) => {
            const due = a.opd_bill ? Number(a.opd_bill.balance) : 0;
            const waiting = a.status === 'checked_in' && a.checked_in_at ? Math.max(0, dayjs().diff(dayjs(a.checked_in_at), 'minute')) : null;
            return (
              <button type="button" key={a.id} disabled={!!opening}
                className={`consult-item${currentAppointment === a.id ? ' active' : ''} status-${a.status}`}
                onClick={() => open({ appointment: a.id }, a.id)}>
                <div className="consult-item-top">
                  <b className="consult-item-name">{a.patient_detail.full_name}</b>
                  <span className="cell-sub">{a.token_number ? `#${a.token_number}` : fmtTime(a.start_time)}{a.token_number && a.start_time ? ` · ${fmtTime(a.start_time)}` : ''}</span>
                </div>
                <div className="consult-item-sub">
                  <span className="cell-sub mono">{a.patient_detail.uhid}</span>
                  <StatusTag status={a.status} />
                </div>
                <div className="consult-item-tags">
                  <Tag color={(a.previous_visits ?? 0) > 0 ? 'cyan' : 'blue'} bordered={false}>
                    {(a.previous_visits ?? 0) > 0 ? t('consult.followUpTag') : t('consult.newTag')}
                  </Tag>
                  <Tag bordered={false}>{a.kind === 'walk_in' ? t('consult.walkInTag') : t('consult.bookedTag')}</Tag>
                  {waiting !== null && <Tag color="gold" bordered={false}>{t('consult.waitingMin', { n: waiting })}</Tag>}
                  {due > 0 && <Tag color="red" bordered={false}>{t('consult.dueTag', { amount: money(due) })}</Tag>}
                </div>
                {a.reason && <div className="cell-sub consult-item-reason">{a.reason}</div>}
                {opening === a.id && <Spin size="small" />}
              </button>
            );
          })}
        </div>
      </aside>

      <section className="consult-main">
        {visitId ? (
          <VisitWorkspace key={visitId} visitId={visitId} onChanged={loadList}
            onLoaded={(v) => setCurrentAppointment(v.appointment)} />
        ) : (
          <div className="consult-empty">
            <Empty description={t('consult.choosePatient')} />
          </div>
        )}
      </section>

      <Modal open={pickOpen} title={t('consult.withoutAppointment')} onCancel={() => setPickOpen(false)}
        okText={t('consult.startCheckup')} cancelText={t('common.cancel')} okButtonProps={{ disabled: !picked }}
        confirmLoading={opening === 'picker'} onOk={async () => { await open({ patient: picked }, 'picker'); setPickOpen(false); }}>
        <div className="cell-sub" style={{ marginBottom: 8 }}>{t('consult.withoutAppointmentHelp')}</div>
        <PatientPicker value={picked} onChange={setPicked} />
      </Modal>
    </div>
  );
}
