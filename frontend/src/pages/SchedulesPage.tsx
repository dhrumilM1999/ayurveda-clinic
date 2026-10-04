// Doctor schedules for the current branch (which days and times each doctor sits here).
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, Tag, TimePicker, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { DoctorSchedule } from '../api/types';
import { useAuth } from '../auth/AuthContext';

interface DoctorOption {
  id: string;
  full_name: string;
}

const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];

export default function SchedulesPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can, branch } = useAuth();
  const [rows, setRows] = useState<DoctorSchedule[]>([]);
  const [doctors, setDoctors] = useState<DoctorOption[]>([]);
  const [doctorFilter, setDoctorFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<Partial<DoctorSchedule> | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const canManage = can('schedules.manage');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [schedules, docs] = await Promise.all([
        api.get<DoctorSchedule[]>('/doctor-schedules/', { params: { doctor: doctorFilter } }),
        api.get<DoctorOption[]>('/doctor-schedules/doctors/'),
      ]);
      setRows(schedules.data);
      setDoctors(docs.data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [doctorFilter, message, t]);

  useEffect(() => {
    load();
  }, [load]);

  const open = (s?: DoctorSchedule) => {
    setEditing(s ?? {});
    form.resetFields();
    form.setFieldsValue(
      s
        ? { ...s, start_time: dayjs(s.start_time, 'HH:mm:ss'), end_time: dayjs(s.end_time, 'HH:mm:ss') }
        : { slot_minutes: 15, is_active: true },
    );
  };

  const save = async () => {
    const values = await form.validateFields();
    const payload = {
      ...values,
      start_time: values.start_time.format('HH:mm'),
      end_time: values.end_time.format('HH:mm'),
    };
    setSaving(true);
    try {
      if (editing?.id) await api.patch(`/doctor-schedules/${editing.id}/`, payload);
      else await api.post('/doctor-schedules/', payload);
      message.success(t('common.saved'));
      setEditing(null);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (s: DoctorSchedule) => {
    try {
      await api.delete(`/doctor-schedules/${s.id}/`);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const time = (value: string) => value.slice(0, 5);

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('schedules.title', { branch: branch?.name })}</Typography.Title>
        <Space>
          <Select allowClear placeholder={t('schedules.allDoctors')} style={{ width: 220 }} value={doctorFilter}
            onChange={setDoctorFilter} options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} />
          {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('schedules.add')}</Button>}
        </Space>
      </div>
      {doctors.length === 0 && !loading && <Typography.Paragraph type="secondary">{t('schedules.noDoctors')}</Typography.Paragraph>}
      <Table<DoctorSchedule>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        scroll={{ x: true }}
        columns={[
          { title: t('schedules.doctor'), dataIndex: 'doctor_name' },
          { title: t('schedules.day'), dataIndex: 'weekday', render: (d: number) => t(`weekdays.${d}`) },
          { title: t('schedules.time'), key: 'time', render: (_: unknown, s: DoctorSchedule) => `${time(s.start_time)} – ${time(s.end_time)}` },
          { title: t('schedules.slot'), dataIndex: 'slot_minutes', render: (m: number) => t('schedules.minutes', { n: m }) },
          {
            title: t('common.status'), dataIndex: 'is_active',
            render: (active: boolean) => active ? <Tag color="green">{t('common.active')}</Tag> : <Tag>{t('common.inactive')}</Tag>,
          },
          ...(canManage ? [{
            title: '', key: 'actions', width: 140,
            render: (_: unknown, s: DoctorSchedule) => (
              <Space>
                <Button size="small" onClick={() => open(s)}>{t('common.edit')}</Button>
                <Popconfirm title={t('schedules.confirmRemove')} onConfirm={() => remove(s)} okText={t('common.yes')} cancelText={t('common.no')}>
                  <Button size="small" danger icon={<DeleteOutlined />} aria-label={t('common.remove')} />
                </Popconfirm>
              </Space>
            ),
          }] : []),
        ]}
      />
      <Modal
        open={!!editing}
        title={editing?.id ? t('schedules.edit') : t('schedules.add')}
        onCancel={() => setEditing(null)}
        onOk={save}
        confirmLoading={saving}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="doctor" label={t('schedules.doctor')} rules={[{ required: true, message: t('common.required') }]}>
            <Select options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} />
          </Form.Item>
          <Form.Item name="weekday" label={t('schedules.day')} rules={[{ required: true, message: t('common.required') }]}>
            <Select options={WEEKDAYS.map((d) => ({ value: d, label: t(`weekdays.${d}`) }))} />
          </Form.Item>
          <Space wrap>
            <Form.Item name="start_time" label={t('schedules.start')} rules={[{ required: true, message: t('common.required') }]}>
              <TimePicker format="HH:mm" minuteStep={5} />
            </Form.Item>
            <Form.Item name="end_time" label={t('schedules.end')} rules={[{ required: true, message: t('common.required') }]}>
              <TimePicker format="HH:mm" minuteStep={5} />
            </Form.Item>
            <Form.Item name="slot_minutes" label={t('schedules.slot')}>
              <InputNumber min={5} max={120} step={5} addonAfter={t('schedules.min')} />
            </Form.Item>
          </Space>
          <Form.Item name="is_active" label={t('common.active')} valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
