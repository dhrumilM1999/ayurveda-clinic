// The buttons on one appointment row: the next step (Check in / Start / Done) and a "more" menu
// (Reschedule, Cancel, Did not come, WhatsApp). Used on the Appointments screen and the patient file.
import { MoreOutlined } from '@ant-design/icons';
import { App, Button, DatePicker, Dropdown, Form, Input, Modal, Space } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Appointment, PatientNotification, Slot } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { NotificationResult, SlotPicker, fmtTime } from './shared';

type Step = 'check-in' | 'start' | 'complete' | 'no-show';

export function AppointmentActions({ appointment: a, onChanged }: { appointment: Appointment; onChanged: () => void }) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const { can } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [notice, setNotice] = useState<{ title: string; notification?: PatientNotification } | null>(null);

  if (!can('appointments.manage') && !can('emr.edit')) return null;
  const isToday = a.date === dayjs().format('YYYY-MM-DD');

  const run = async (step: Step) => {
    setBusy(true);
    try {
      const { data } = await api.post<Appointment>(`/appointments/${a.id}/${step}/`);
      if (step === 'check-in') {
        setNotice({ title: t('appointments.checkedInMsg', { token: data.token_number }), notification: data.notification });
      } else {
        message.success(t('common.saved'));
      }
      onChanged();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  // Doctors: open the check-up screen for this appointment (marks it "With doctor")
  const openCheckup = async () => {
    setBusy(true);
    try {
      const { data } = await api.post<{ id: string }>('/visits/', { appointment: a.id });
      navigate(`/consult/${data.id}`);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
      setBusy(false);
    }
  };

  const whatsapp = async () => {
    try {
      const { data } = await api.post<PatientNotification>(`/appointments/${a.id}/whatsapp/`);
      setNotice({ title: t('appointments.whatsappTitle'), notification: data });
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  // The one main button for the next step
  let main: { step: Step; label: string } | null = null;
  if (a.status === 'booked' && isToday) main = { step: 'check-in', label: t('appointments.checkIn') };
  if (a.status === 'checked_in') main = { step: 'start', label: t('appointments.start') };
  if (a.status === 'in_consultation') main = { step: 'complete', label: t('appointments.complete') };

  const canCheckup = can('emr.edit') && isToday && ['booked', 'checked_in', 'in_consultation', 'completed'].includes(a.status);
  if (!can('appointments.manage')) {
    // Doctor without front-desk rights: only the check-up button
    return canCheckup ? <Button size="small" loading={busy} onClick={openCheckup}>{t('consult.openCheckup')}</Button> : null;
  }

  const menu = [
    ...(canCheckup ? [{ key: 'checkup', label: t('consult.openCheckup') }] : []),
    ...(a.status === 'booked' ? [{ key: 'reschedule', label: t('appointments.reschedule') }] : []),
    ...(a.status === 'checked_in' ? [{ key: 'complete', label: t('appointments.complete') }] : []),
    ...(a.status === 'booked' && !dayjs(a.date).isAfter(dayjs(), 'day') ? [{ key: 'no-show', label: t('appointments.markNoShow') }] : []),
    { key: 'whatsapp', label: t('appointments.whatsapp') },
    ...(['booked', 'checked_in'].includes(a.status) ? [{ key: 'cancel', label: t('appointments.cancel'), danger: true }] : []),
  ];

  const onMenu = ({ key }: { key: string }) => {
    if (key === 'checkup') openCheckup();
    else if (key === 'reschedule') setRescheduleOpen(true);
    else if (key === 'cancel') setCancelOpen(true);
    else if (key === 'whatsapp') whatsapp();
    else if (key === 'no-show') {
      modal.confirm({
        title: t('appointments.confirmNoShow'), okText: t('common.yes'), cancelText: t('common.no'),
        onOk: () => run('no-show'),
      });
    } else run(key as Step);
  };

  return (
    <>
      <Space size={4}>
        {main && (
          <Button size="small" type={main.step === 'check-in' ? 'primary' : 'default'} loading={busy} onClick={() => run(main!.step)}>
            {main.label}
          </Button>
        )}
        <Dropdown trigger={['click']} menu={{ items: menu, onClick: onMenu }}>
          <Button size="small" type="text" icon={<MoreOutlined />} aria-label={t('appointments.more')} />
        </Dropdown>
      </Space>

      {rescheduleOpen && (
        <RescheduleModal appointment={a} onClose={(notification) => {
          setRescheduleOpen(false);
          if (notification !== undefined) {
            setNotice({ title: t('appointments.rescheduledMsg'), notification: notification ?? undefined });
            onChanged();
          }
        }} />
      )}
      {cancelOpen && (
        <CancelModal appointment={a} onClose={(notification) => {
          setCancelOpen(false);
          if (notification !== undefined) {
            setNotice({ title: t('appointments.cancelledMsg'), notification: notification ?? undefined });
            onChanged();
          }
        }} />
      )}
      <Modal open={!!notice} title={notice?.title} onCancel={() => setNotice(null)} width={520}
        footer={<Button type="primary" onClick={() => setNotice(null)}>{t('common.close')}</Button>}>
        <NotificationResult notification={notice?.notification} />
      </Modal>
    </>
  );
}

/** onClose(undefined) = closed without change; onClose(notification|null) = saved. */
function RescheduleModal({ appointment: a, onClose }: {
  appointment: Appointment;
  onClose: (notification?: PatientNotification | null) => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [day, setDay] = useState<Dayjs>(dayjs(a.date).isBefore(dayjs(), 'day') ? dayjs() : dayjs(a.date));
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(false);
  const [start, setStart] = useState<string>();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setStart(undefined);
    setLoading(true);
    api.get<{ slots: Slot[] }>('/appointments/slots/', { params: { doctor: a.doctor, date: day.format('YYYY-MM-DD') } })
      .then(({ data }) => setSlots(data.slots))
      .catch(() => setSlots([]))
      .finally(() => setLoading(false));
  }, [a.doctor, day]);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post<Appointment>(`/appointments/${a.id}/reschedule/`, {
        date: day.format('YYYY-MM-DD'), start_time: start,
      });
      onClose(data.notification ?? null);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open title={t('appointments.rescheduleTitle', { name: a.patient_detail.full_name })}
      onCancel={() => onClose()} onOk={save} okButtonProps={{ disabled: !start }} confirmLoading={saving}
      okText={t('appointments.reschedule')} cancelText={t('common.cancel')} width={600} keyboard={false} maskClosable={false}>
      <div className="cell-sub" style={{ marginBottom: 12 }}>
        {t('appointments.currentlyAt', {
          doctor: a.doctor_name, date: dayjs(a.date).format('DD-MM-YYYY'), time: fmtTime(a.start_time),
        })}
      </div>
      <Form layout="vertical">
        <Form.Item label={t('appointments.date')}>
          <DatePicker value={day} onChange={(d) => d && setDay(d)} format="DD-MM-YYYY" allowClear={false}
            disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
        </Form.Item>
        <Form.Item label={t('appointments.time')} style={{ marginBottom: 8 }}>
          <SlotPicker slots={slots} loading={loading} value={start} onChange={setStart} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function CancelModal({ appointment: a, onClose }: {
  appointment: Appointment;
  onClose: (notification?: PatientNotification | null) => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post<Appointment>(`/appointments/${a.id}/cancel/`, { reason });
      onClose(data.notification ?? null);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open title={t('appointments.cancelTitle', { name: a.patient_detail.full_name })}
      onCancel={() => onClose()} onOk={save} confirmLoading={saving}
      okText={t('appointments.cancelConfirm')} okButtonProps={{ danger: true }} cancelText={t('common.close')} width={480}>
      <Form layout="vertical">
        <Form.Item label={t('appointments.cancelReason')}>
          <Input.TextArea rows={2} maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} autoFocus />
        </Form.Item>
      </Form>
    </Modal>
  );
}
