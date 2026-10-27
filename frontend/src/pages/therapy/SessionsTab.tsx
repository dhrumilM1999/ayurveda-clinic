// The day's therapy sessions: who comes when, with which therapist and room. The therapist starts a session and records
// the oil used and how the patient felt. SAFE TO EDIT: the words are in src/i18n/*.json under "therapy".
import { CheckOutlined, CloseOutlined, LeftOutlined, PlayCircleOutlined, ReloadOutlined, RightOutlined, UndoOutlined, UserDeleteOutlined } from '@ant-design/icons';
import { App, Button, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Table, Tag, TimePicker, Tooltip, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { TherapyOptions, TherapySession } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { PatientCell } from '../appointments/shared';
import { SessionStatusTag, StageTag, hhmm, useTherapyName } from './common';

export default function SessionsTab() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const canManage = can('therapy.manage');
  const name = useTherapyName();
  const [day, setDay] = useState(dayjs());
  const [therapist, setTherapist] = useState<string>();
  const [room, setRoom] = useState<string>();
  const [rows, setRows] = useState<TherapySession[]>([]);
  const [options, setOptions] = useState<TherapyOptions>({ therapists: [], rooms: [] });
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState<TherapySession | null>(null);
  const [moving, setMoving] = useState<TherapySession | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<TherapySession[]>('/therapy-sessions/', {
        params: { date: day.format('YYYY-MM-DD'), therapist, room, ordering: 'start_time' },
      });
      setRows(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [day, therapist, room, message, t]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api.get<TherapyOptions>('/therapy-sessions/options/').then(({ data }) => setOptions(data)).catch(() => undefined);
  }, []);

  const act = async (row: TherapySession, what: 'start' | 'missed' | 'cancel' | 'undo') => {
    try {
      await api.post(`/therapy-sessions/${row.id}/${what}/`);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  // Booked, but the day or time has gone by and it was never started: it must be moved or cancelled
  const timePassed = (r: TherapySession) => r.status === 'scheduled'
    && dayjs(`${r.date} ${r.end_time}`).isBefore(dayjs());

  const openRecord = (row: TherapySession) => {
    setRecording(row);
    form.setFieldsValue({ material_used: row.material_used, quantity_ml: row.quantity_ml, patient_response: row.patient_response, notes: row.notes });
  };

  const saveRecord = async () => {
    if (!recording) return;
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post(`/therapy-sessions/${recording.id}/complete/`, { ...values, quantity_ml: values.quantity_ml ?? '' });
      message.success(t('common.saved'));
      setRecording(null);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Button icon={<LeftOutlined />} onClick={() => setDay(day.subtract(1, 'day'))} />
        <DatePicker allowClear={false} value={day} format="DD-MM-YYYY" onChange={(d) => d && setDay(d)} />
        <Button icon={<RightOutlined />} onClick={() => setDay(day.add(1, 'day'))} />
        <Button onClick={() => setDay(dayjs())}>{t('appointments.today')}</Button>
        <Select allowClear style={{ width: 190 }} placeholder={t('therapy.allTherapists')} value={therapist} onChange={setTherapist}
          options={options.therapists.map((x) => ({ value: x.id, label: x.name }))} />
        <Select allowClear style={{ width: 170 }} placeholder={t('therapy.allRooms')} value={room} onChange={setRoom}
          options={options.rooms.map((x) => ({ value: x.id, label: x.name }))} />
        <Button icon={<ReloadOutlined />} onClick={load} />
      </Space>
      <Table<TherapySession>
        rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} scroll={{ x: 'max-content' }}
        locale={{ emptyText: t('therapy.noSessions') }}
        columns={[
          { title: t('appointments.time'), width: 110, render: (_, r) => <b>{hhmm(r.start_time)}-{hhmm(r.end_time)}</b> },
          { title: t('therapy.plan.patient'), render: (_, r) => <PatientCell patient={r.patient_detail} /> },
          {
            title: t('therapy.plan.therapy'),
            render: (_, r) => (
              <div style={{ lineHeight: 1.35 }}>
                <Typography.Text strong>{name(r)}</Typography.Text> <StageTag stage={r.stage} />
                <div className="cell-sub">{r.plan_title} · {t('therapy.sessionNo', { n: r.session_no ?? '-', total: r.sessions_planned })}</div>
                {r.status === 'done' && (r.material_used || r.quantity_ml) ? (
                  <div className="cell-sub">{[r.material_used, r.quantity_ml ? `${r.quantity_ml} ml` : ''].filter(Boolean).join(' · ')}</div>
                ) : null}
              </div>
            ),
          },
          { title: t('therapy.book.therapist'), dataIndex: 'therapist_name', render: (v) => v || <span className="cell-sub">{t('therapy.anyone')}</span> },
          { title: t('therapy.book.room'), dataIndex: 'room_name', render: (v) => v || <span className="cell-sub">{t('therapy.noRoom')}</span> },
          { title: t('common.status'), width: 130, render: (_, r) => <SessionStatusTag status={r.status} /> },
          {
            title: '', width: 330, align: 'right',
            render: (_, r) => canManage && (r.status === 'scheduled' || r.status === 'in_progress' || r.status === 'missed' || r.undo_to) ? (
              <Space size={4} style={{ justifyContent: 'flex-end' }}>
                {timePassed(r) && <Tag color="orange" style={{ marginInlineEnd: 0 }}>{t('therapy.timePassed')}</Tag>}
                {(r.status === 'missed' || timePassed(r)) && (
                  <>
                    <Button size="small" type="primary" ghost onClick={() => setMoving(r)}>{t('therapy.reschedule')}</Button>
                    {r.status === 'missed' && (
                      <Popconfirm title={t('therapy.cancelAsk')} onConfirm={() => act(r, 'cancel')}>
                        <Button size="small" danger>{t('therapy.cancel')}</Button>
                      </Popconfirm>
                    )}
                  </>
                )}
                {r.undo_to && (
                  <Tooltip title={t('undo.to', { status: t(`therapy.status.${r.undo_to}`) })}>
                    <Button size="small" icon={<UndoOutlined />} onClick={() => act(r, 'undo')}>{t('undo.button')}</Button>
                  </Tooltip>
                )}
                {r.status === 'scheduled' && !dayjs(r.date).isAfter(dayjs(), 'day') && <Button size="small" icon={<PlayCircleOutlined />} onClick={() => act(r, 'start')}>{t('therapy.start')}</Button>}
                {(r.status === 'scheduled' || r.status === 'in_progress') && !dayjs(r.date).isAfter(dayjs(), 'day') && (
                  <Button size="small" type="primary" icon={<CheckOutlined />} onClick={() => openRecord(r)}>{t('therapy.finish')}</Button>
                )}
                {(r.status === 'scheduled' || r.status === 'in_progress') && (
                  <Popconfirm title={t('therapy.cancelAsk')} onConfirm={() => act(r, 'cancel')}>
                    <Button size="small" icon={<CloseOutlined />} title={t('therapy.cancel')} />
                  </Popconfirm>
                )}
                {r.status === 'scheduled' && (
                  <Button size="small" icon={<UserDeleteOutlined />} title={t('therapy.missed')} onClick={() => act(r, 'missed')} />
                )}
              </Space>
            ) : null,
          },
        ]}
      />

      <MoveModal session={moving} options={options} onClose={() => setMoving(null)} onMoved={() => { setMoving(null); load(); }} />

      <Modal open={!!recording} title={t('therapy.record.title')} onCancel={() => setRecording(null)} onOk={saveRecord}
        okText={t('therapy.record.save')} confirmLoading={saving} destroyOnHidden>
        {recording && (
          <>
            <div style={{ marginBottom: 12 }}><b>{recording.patient_detail.full_name}</b> · {name(recording)}</div>
            <Form form={form} layout="vertical">
              <Space align="start" style={{ width: '100%' }} styles={{ item: { flex: 1 } }}>
                <Form.Item name="material_used" label={t('therapy.record.material')} style={{ flex: 1, minWidth: 220 }}>
                  <Input maxLength={150} />
                </Form.Item>
                <Form.Item name="quantity_ml" label={t('therapy.record.quantity')}>
                  <InputNumber min={0} max={100000} style={{ width: 130 }} />
                </Form.Item>
              </Space>
              <Form.Item name="patient_response" label={t('therapy.record.response')} extra={t('therapy.record.help')}>
                <Input.TextArea rows={3} maxLength={1000} />
              </Form.Item>
              <Form.Item name="notes" label={t('therapy.record.notes')}><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </>
  );
}

/** Move a session that was not done to a new day and time (same therapist and room unless changed). */
function MoveModal({ session, options, onClose, onMoved }: {
  session: TherapySession | null; options: TherapyOptions; onClose: () => void; onMoved: () => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const name = useTherapyName();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!session) return;
    const today = dayjs();
    form.setFieldsValue({
      date: dayjs(session.date).isBefore(today, 'day') ? today : dayjs(session.date),
      start_time: dayjs(session.start_time, 'HH:mm'),
      therapist: session.therapist ?? undefined, room: session.room ?? undefined,
    });
  }, [session, form]);

  const save = async () => {
    if (!session) return;
    const v = await form.validateFields();
    setSaving(true);
    try {
      await api.post(`/therapy-sessions/${session.id}/reschedule/`, {
        date: v.date.format('YYYY-MM-DD'), start_time: v.start_time.format('HH:mm'),
        therapist: v.therapist ?? null, room: v.room ?? null,
      });
      message.success(t('therapy.rescheduled'));
      onMoved();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={!!session} title={session ? t('therapy.rescheduleTitle', { name: name(session) }) : ''} onCancel={onClose} onOk={save}
      okText={t('therapy.reschedule')} confirmLoading={saving} destroyOnHidden>
      {session && <div className="cell-sub" style={{ marginBottom: 12 }}><b>{session.patient_detail.full_name}</b> · {t('therapy.rescheduleHelp')}</div>}
      <Form form={form} layout="vertical">
        <Space align="start" wrap>
          <Form.Item name="date" label={t('appointments.date')} rules={[{ required: true, message: t('common.required') }]}>
            <DatePicker format="DD-MM-YYYY" allowClear={false} disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
          </Form.Item>
          <Form.Item name="start_time" label={t('therapy.book.time')} rules={[{ required: true, message: t('common.required') }]}>
            <TimePicker format="HH:mm" minuteStep={5} allowClear={false} />
          </Form.Item>
        </Space>
        <Form.Item name="therapist" label={t('therapy.book.therapist')}>
          <Select allowClear placeholder={t('therapy.anyone')} options={options.therapists.map((x) => ({ value: x.id, label: x.name }))} />
        </Form.Item>
        <Form.Item name="room" label={t('therapy.book.room')}>
          <Select allowClear placeholder={t('therapy.noRoom')} options={options.rooms.map((x) => ({ value: x.id, label: x.name }))} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
