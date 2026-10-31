// The doctor's check-up screen: today's patients on the left, the open check-up on the right.
import { shownStatus } from '../appointments/status';
import { LeftOutlined, PlusOutlined, ReloadOutlined, RightOutlined, SearchOutlined } from '@ant-design/icons';
import { App, Button, DatePicker, Empty, Input, Modal, Select, Spin, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { useLiveRefresh } from '../../api/useLiveRefresh';
import type { Appointment, AppointmentDoctor, Page, Visit } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { PatientPicker, StatusTag, fmtTime } from '../appointments/shared';
import { VisitWorkspace } from './VisitWorkspace';

const REFRESH_SECONDS = 5; // the waiting list updates by itself (new patient arrives, a check-up is completed)

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
  const [filter, setFilter] = useState<'all' | 'checked_in' | 'booked' | 'completed'>('all');
  const [search, setSearch] = useState('');
  const moveDay = (delta: number) => setDay(dayjs(day).add(delta, 'day').format('YYYY-MM-DD'));

  // quiet = the automatic refresh: no spinner, and if the server does not answer the list on the screen stays as it was
  const fetchList = useCallback(async (quiet: boolean) => {
    if (!withAppointments) return;
    if (!quiet) setLoading(true);
    try {
      const { data } = await api.get<Page<Appointment>>('/appointments/', {
        params: { date: day, doctor, page_size: 200, ordering: 'start_time' },
      });
      setRows(data.results.filter((a) => !['cancelled', 'no_show'].includes(a.status)));
    } catch {
      if (!quiet) setRows([]);
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [withAppointments, day, doctor]);
  const loadList = useCallback(() => fetchList(false), [fetchList]);

  useEffect(() => { loadList(); }, [loadList]);
  useLiveRefresh(() => fetchList(true), REFRESH_SECONDS);

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
  const order = { checked_in: 0, booked: 1, completed: 2 } as Record<string, number>;
  const sorted = [...rows].sort((a, b) => (order[shownStatus(a.status)] ?? 9) - (order[shownStatus(b.status)] ?? 9)
    || (a.token_number ?? 999) - (b.token_number ?? 999) || (a.start_time ?? '').localeCompare(b.start_time ?? ''));

  const count = (status: string) => rows.filter((a) => shownStatus(a.status) === status).length;
  const needle = search.trim().toLowerCase();
  const shown = sorted.filter((a) => (filter === 'all' || shownStatus(a.status) === filter)
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
        <div className="consult-counts-title">{day === today ? t('consult.todaysAppointments') : t('consult.appointmentsOf', { date: dayjs(day).format('DD-MM-YYYY') })}</div>
        <div className="consult-counts">
          {([['all', rows.length], ['checked_in', count('checked_in')],
            ['booked', count('booked')], ['completed', count('completed')]] as [typeof filter, number][]).map(([value, n]) => (
            <button type="button" key={value} className={`consult-count count-${value}${filter === value ? ' on' : ''}`} onClick={() => setFilter(value)}
              aria-pressed={filter === value}>
              <span className="consult-count-n">{n}</span>
              <span className="consult-count-l">{t(`consult.filter.${{ all: 'all', checked_in: 'waiting', booked: 'booked', completed: 'done' }[value]}`)}</span>
            </button>
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
                  <span className="cell-sub">{a.token_number ? t('consult.tokenLabel', { n: a.token_number }) : fmtTime(a.start_time)}{a.token_number && a.start_time ? ` · ${fmtTime(a.start_time)}` : ''}</span>
                </div>
                <div className="consult-item-sub">
                  <span className="cell-sub mono">{t('consult.idLabel', { id: a.patient_detail.uhid })}</span>
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
            onLoaded={(v) => setCurrentAppointment(v.appointment)}
            reason={rows.find((a) => a.id === currentAppointment)?.reason || undefined}
            nextPatient={(() => {
              // the next one who is already waiting (the longest first), not the one on screen
              const next = sorted.find((a) => a.status === 'checked_in' && a.id !== currentAppointment);
              return next ? { name: next.patient_detail.full_name, token: next.token_number, open: () => open({ appointment: next.id }, next.id) } : null;
            })()} />
        ) : (
          <div className="consult-empty">
            <Empty description={t('consult.choosePatient')} />
            <ol className="how-steps">
              <li>{t('consult.step1')}</li>
              <li>{t('consult.step2')}</li>
              <li>{t('consult.step3')}</li>
              <li>{t('consult.step4')}</li>
            </ol>
            <div className="cell-sub how-note">{t('consult.manyPatients')}</div>
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
