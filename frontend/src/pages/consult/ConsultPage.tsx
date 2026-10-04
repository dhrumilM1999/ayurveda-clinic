// The doctor's check-up screen: today's patients on the left, the open check-up on the right.
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { App, Button, Empty, Modal, Select, Spin } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import type { Appointment, AppointmentDoctor, Page, Visit } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
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

  const loadList = useCallback(async () => {
    if (!withAppointments) return;
    setLoading(true);
    try {
      const { data } = await api.get<Page<Appointment>>('/appointments/', {
        params: { date: today, doctor, page_size: 200, ordering: 'start_time' },
      });
      setRows(data.results.filter((a) => !['cancelled', 'no_show'].includes(a.status)));
    } catch {
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [withAppointments, today, doctor]);

  useEffect(() => {
    loadList();
    const timer = window.setInterval(loadList, REFRESH_SECONDS * 1000);
    return () => window.clearInterval(timer);
  }, [loadList]);

  useEffect(() => {
    if (!withAppointments) return;
    api.get<AppointmentDoctor[]>('/appointments/doctors/', { params: { date: today } })
      .then(({ data }) => setDoctors(data)).catch(() => setDoctors([]));
  }, [withAppointments, today]);

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

  return (
    <div className="consult">
      <aside className="consult-list">
        <div className="consult-list-head">
          <div className="section-title" style={{ margin: 0 }}>{t('consult.todayPatients', { n: rows.length })}</div>
          <Button size="small" type="text" icon={<ReloadOutlined />} onClick={loadList} aria-label={t('appointments.refresh')} />
        </div>
        {withAppointments && (
          <Select size="small" allowClear placeholder={t('appointments.allDoctors')} value={doctor} onChange={setDoctor}
            options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} style={{ width: '100%' }} />
        )}
        {me?.user.is_doctor && can('emr.edit') && (
          <Button size="small" block icon={<PlusOutlined />} onClick={() => { setPicked(undefined); setPickOpen(true); }}>
            {t('consult.withoutAppointment')}
          </Button>
        )}
        <div className="consult-items">
          {loading && !rows.length && <Spin size="small" />}
          {!loading && !rows.length && <div className="cell-sub">{withAppointments ? t('consult.noPatientsToday') : t('consult.appointmentsOff')}</div>}
          {sorted.map((a) => (
            <button type="button" key={a.id} disabled={!!opening}
              className={`consult-item${currentAppointment === a.id ? ' active' : ''} status-${a.status}`}
              onClick={() => open({ appointment: a.id }, a.id)}>
              <div className="consult-item-top">
                <b className="consult-item-name">{a.patient_detail.full_name}</b>
                <span className="cell-sub">{a.token_number ? `#${a.token_number}` : fmtTime(a.start_time)}</span>
              </div>
              <div className="consult-item-sub">
                <span className="cell-sub">{a.patient_detail.uhid}</span>
                <StatusTag status={a.status} />
              </div>
              {opening === a.id && <Spin size="small" />}
            </button>
          ))}
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
