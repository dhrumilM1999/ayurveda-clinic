// Popup to book an appointment (pick doctor, date and time) or add a walk-in (gets a token now).
// After saving it shows the confirmation message and the WhatsApp button.
import { CheckCircleFilled } from '@ant-design/icons';
import { App, Button, Col, DatePicker, Form, Input, Modal, Result, Row, Select } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Appointment, AppointmentDoctor, Slot } from '../../api/types';
import { NotificationResult, PatientPicker, SlotPicker, fmtTime } from './shared';

export interface BookProps {
  open: boolean;
  kind: 'booked' | 'walk_in';
  patient?: { id: string; label: string };
  defaultDate?: Dayjs;
  defaultDoctor?: string;
  onClose: (changed: boolean) => void;
}

export function BookAppointmentModal({ open, kind, patient, defaultDate, defaultDoctor, onClose }: BookProps) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [doctors, setDoctors] = useState<AppointmentDoctor[]>([]);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<Appointment | null>(null);
  const walkIn = kind === 'walk_in';
  const doctor: string | undefined = Form.useWatch('doctor', form);
  const date: Dayjs | undefined = Form.useWatch('date', form);
  const start: string | undefined = Form.useWatch('start_time', form);

  // Fresh form every time the popup opens
  useEffect(() => {
    if (!open) return;
    setResult(null);
    setSlots([]);
    form.resetFields();
    const today = dayjs();
    const day = walkIn ? today : defaultDate && !defaultDate.isBefore(today, 'day') ? defaultDate : today;
    form.setFieldsValue({ patient: patient?.id, doctor: defaultDoctor, date: day });
  }, [open, walkIn, patient, defaultDate, defaultDoctor, form]);

  // Doctors of this branch for the chosen day (who sits, how busy)
  const dayKey = (date ?? dayjs()).format('YYYY-MM-DD');
  useEffect(() => {
    if (!open) return;
    api.get<AppointmentDoctor[]>('/appointments/doctors/', { params: { date: dayKey } })
      .then(({ data }) => {
        setDoctors(data);
        // Only one doctor: choose them automatically
        if (!form.getFieldValue('doctor') && data.length === 1) form.setFieldValue('doctor', data[0]!.id);
      })
      .catch(() => setDoctors([]));
  }, [open, dayKey, form]);

  // Time slots of the chosen doctor and day
  useEffect(() => {
    if (!open || walkIn || !doctor) {
      setSlots([]);
      return;
    }
    form.setFieldValue('start_time', undefined);
    setSlotsLoading(true);
    api.get<{ slots: Slot[] }>('/appointments/slots/', { params: { doctor, date: dayKey } })
      .then(({ data }) => setSlots(data.slots))
      .catch(() => setSlots([]))
      .finally(() => setSlotsLoading(false));
  }, [open, walkIn, doctor, dayKey, form]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload = {
        patient: values.patient,
        doctor: values.doctor,
        kind,
        reason: values.reason ?? '',
        notes: values.notes ?? '',
        ...(walkIn ? {} : { date: values.date.format('YYYY-MM-DD'), start_time: values.start_time }),
      };
      const { data } = await api.post<Appointment>('/appointments/', payload);
      setResult(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  if (result) {
    const title = result.kind === 'walk_in'
      ? t('appointments.walkInDone', { token: result.token_number })
      : t('appointments.bookedDone', { date: dayjs(result.date).format('DD-MM-YYYY'), time: fmtTime(result.start_time) });
    return (
      <Modal open={open} title={walkIn ? t('appointments.walkIn') : t('appointments.book')} onCancel={() => onClose(true)}
        footer={<Button type="primary" onClick={() => onClose(true)}>{t('common.close')}</Button>} width={560}>
        <Result
          className="compact-result"
          icon={<CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} />}
          title={title}
          subTitle={`${result.patient_detail.full_name} · ${result.doctor_name}`}
        />
        <NotificationResult notification={result.notification} />
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      title={walkIn ? t('appointments.walkIn') : t('appointments.book')}
      onCancel={() => onClose(false)}
      onOk={save}
      okText={walkIn ? t('appointments.giveToken') : t('appointments.confirmBooking')}
      cancelText={t('common.cancel')}
      okButtonProps={{ disabled: !walkIn && !start }}
      confirmLoading={saving}
      width={680}
      destroyOnHidden
      // Don't lose a half-filled booking by pressing Esc or clicking outside
      keyboard={false}
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="patient" label={t('appointments.patient')} rules={[{ required: true, message: t('common.required') }]}
          extra={!patient ? t('appointments.patientHelp') : undefined}>
          <PatientPicker initial={patient} />
        </Form.Item>
        <Row gutter={12}>
          <Col xs={24} md={walkIn ? 24 : 14}>
            <Form.Item name="doctor" label={t('appointments.doctor')} rules={[{ required: true, message: t('common.required') }]}>
              <Select
                placeholder={t('appointments.chooseDoctor')}
                options={doctors.map((d) => ({
                  value: d.id,
                  label: (
                    <span>
                      {d.full_name}{' '}
                      <span className="cell-sub">
                        · {d.sits ? d.timings.join(', ') : t('appointments.notSitting')}
                        {d.active_count ? ` · ${t('appointments.activeCount', { n: d.active_count })}` : ''}
                      </span>
                    </span>
                  ),
                }))}
                notFoundContent={t('appointments.noDoctors')}
              />
            </Form.Item>
          </Col>
          {!walkIn && (
            <Col xs={24} md={10}>
              <Form.Item name="date" label={t('appointments.date')} rules={[{ required: true, message: t('common.required') }]}>
                <DatePicker format="DD-MM-YYYY" allowClear={false} style={{ width: '100%' }}
                  disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
              </Form.Item>
            </Col>
          )}
        </Row>
        {!walkIn && (
          <Form.Item name="start_time" label={t('appointments.time')} rules={[{ required: true, message: t('appointments.chooseTime') }]}>
            <SlotPicker slots={slots} loading={slotsLoading}
              emptyText={doctor ? t('appointments.noSlots') : t('appointments.chooseDoctorFirst')} />
          </Form.Item>
        )}
        <Row gutter={12}>
          <Col xs={24} md={12}>
            <Form.Item name="reason" label={t('appointments.reason')}>
              <Input maxLength={200} placeholder={t('appointments.reasonPlaceholder')} />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="notes" label={t('appointments.notes')}>
              <Input maxLength={500} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
}
