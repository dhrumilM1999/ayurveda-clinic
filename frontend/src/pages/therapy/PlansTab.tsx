// Therapy plans: what the doctor advised for a patient (e.g. a Virechana course), how many sessions of each
// therapy, and booking the sessions with a therapist and a room. SAFE TO EDIT: the words are in src/i18n/*.json under "therapy".
import { CalendarOutlined, MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Checkbox, DatePicker, Descriptions, Drawer, Form, Input, InputNumber, Modal, Popconfirm, Progress, Select, Space, Table, TimePicker, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { TherapyOptions, TherapyPlan, TherapyPlanItem, TherapyType } from '../../api/types';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { PatientCell, PatientPicker } from '../appointments/shared';
import { PlanStatusTag, STAGES, StageTag, useTherapyName } from './common';

const STATUS_FILTERS = ['planned', 'active', 'completed', 'cancelled'] as const;

export default function PlansTab({ therapies }: { therapies: TherapyType[] }) {
  const { t } = useTranslation();
  const { can } = useAuth();
  const canManage = can('therapy.manage');
  const [status, setStatus] = useState<string>();
  const [search, setSearch] = useState('');
  const { rows, loading, reload, pagination } = useList<TherapyPlan>('/therapy-plans/', { status, search: search || undefined });
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search allowClear placeholder={t('common.search')} style={{ width: 240 }} onSearch={setSearch} />
        <Select allowClear style={{ width: 170 }} placeholder={t('common.status')} value={status} onChange={setStatus}
          options={STATUS_FILTERS.map((s) => ({ value: s, label: t(`therapy.planStatus.${s}`) }))} />
        {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>{t('therapy.plan.new')}</Button>}
      </Space>
      <Table<TherapyPlan>
        rowKey="id" size="small" loading={loading} dataSource={rows} pagination={pagination} scroll={{ x: 'max-content' }}
        locale={{ emptyText: t('therapy.noPlans') }}
        onRow={(r) => ({ onClick: () => setOpenId(r.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('therapy.plan.patient'), render: (_, r) => <PatientCell patient={r.patient_detail} /> },
          { title: t('therapy.plan.title'), render: (_, r) => <div><b>{r.title}</b><div className="cell-sub">{r.doctor_name}</div></div> },
          { title: t('therapy.plan.startDate'), dataIndex: 'start_date', render: (v) => dayjs(v).format('DD-MM-YYYY') },
          {
            title: t('therapy.plan.sessionsPlanned'), width: 190,
            render: (_, r) => (
              <div>
                <Progress percent={r.sessions_planned ? Math.round((100 * r.sessions_done) / r.sessions_planned) : 0} size="small" showInfo={false} />
                <div className="cell-sub">{t('therapy.plan.progress', { done: r.sessions_done, total: r.sessions_planned })}</div>
              </div>
            ),
          },
          { title: t('common.status'), width: 110, render: (_, r) => <PlanStatusTag status={r.status} /> },
        ]}
      />
      <PlanForm open={creating} therapies={therapies} onClose={() => setCreating(false)}
        onSaved={(plan) => { setCreating(false); reload(); setOpenId(plan.id); }} />
      <PlanDrawer id={openId} therapies={therapies} onClose={() => setOpenId(null)} onChanged={reload} canManage={canManage} />
    </>
  );
}

/** New plan: patient, name, start date, the therapies and how many sessions of each. */
function PlanForm({ open, therapies, onClose, onSaved }: {
  open: boolean; therapies: TherapyType[]; onClose: () => void; onSaved: (plan: TherapyPlan) => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const name = useTherapyName();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) form.setFieldsValue({ patient: undefined, title: '', start_date: dayjs(), items: [{}], consent_taken: false, notes: '' });
  }, [open, form]);

  const options = therapies.filter((x) => x.is_active).map((x) => ({ value: x.id, label: name(x) }));
  const onTherapyChange = (index: number, id: string) => {
    const found = therapies.find((x) => x.id === id);
    const items = form.getFieldValue('items') as Partial<TherapyPlanItem>[];
    items[index] = { ...items[index], therapy: id, stage: found?.stage ?? 'other', sessions_planned: items[index]?.sessions_planned ?? 1 };
    form.setFieldsValue({ items: [...items] });
  };

  const save = async () => {
    const v = await form.validateFields();
    const items = (v.items as Partial<TherapyPlanItem>[]).filter((i) => i.therapy);
    if (!items.length) { message.error(t('therapy.plan.needItem')); return; }
    setSaving(true);
    try {
      const { data } = await api.post<TherapyPlan>('/therapy-plans/', {
        patient: v.patient, title: v.title, start_date: (v.start_date as Dayjs).format('YYYY-MM-DD'),
        notes: v.notes || '', consent_taken: !!v.consent_taken, items,
      });
      message.success(t('common.saved'));
      onSaved(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} title={t('therapy.plan.new')} onCancel={onClose} onOk={save} confirmLoading={saving} width={720} destroyOnHidden
      okText={t('common.save')}>
      <Form form={form} layout="vertical">
        <Form.Item name="patient" label={t('therapy.plan.patient')} rules={[{ required: true, message: t('common.required') }]}>
          <PatientPicker />
        </Form.Item>
        <Space align="start" wrap style={{ width: '100%' }}>
          <Form.Item name="title" label={t('therapy.plan.title')} rules={[{ required: true, message: t('common.required') }]} style={{ minWidth: 340 }}>
            <Input maxLength={150} placeholder={t('therapy.plan.titlePlaceholder')} />
          </Form.Item>
          <Form.Item name="start_date" label={t('therapy.plan.startDate')} rules={[{ required: true, message: t('common.required') }]}>
            <DatePicker format="DD-MM-YYYY" allowClear={false} />
          </Form.Item>
        </Space>
        <Typography.Text strong>{t('therapy.plan.items')}</Typography.Text>
        <Form.List name="items">
          {(fields, { add, remove }) => (
            <div style={{ marginTop: 8 }}>
              {fields.map((field) => (
                <Space key={field.key} align="start" wrap style={{ display: 'flex', marginBottom: 4 }}>
                  <Form.Item name={[field.name, 'therapy']} rules={[{ required: true, message: t('common.required') }]} style={{ marginBottom: 8 }}>
                    <Select showSearch optionFilterProp="label" style={{ width: 320 }} placeholder={t('therapy.plan.therapy')} options={options}
                      onChange={(id) => onTherapyChange(field.name, id)} />
                  </Form.Item>
                  <Form.Item name={[field.name, 'stage']} style={{ marginBottom: 8 }}>
                    <Select style={{ width: 200 }} options={STAGES.map((s) => ({ value: s, label: t(`therapy.stage.${s}`) }))} />
                  </Form.Item>
                  <Form.Item name={[field.name, 'sessions_planned']} initialValue={1} style={{ marginBottom: 8 }}>
                    <InputNumber min={1} max={60} placeholder={t('therapy.plan.sessionsPlanned')} style={{ width: 110 }} />
                  </Form.Item>
                  {fields.length > 1 && <Button type="text" icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} />}
                </Space>
              ))}
              <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ sessions_planned: 1, stage: 'pradhana' })}>{t('therapy.plan.addTherapy')}</Button>
            </div>
          )}
        </Form.List>
        <Form.Item name="notes" label={t('therapy.plan.notes')} style={{ marginTop: 16 }}><Input.TextArea rows={2} maxLength={1000} /></Form.Item>
        <Form.Item name="consent_taken" valuePropName="checked"><Checkbox>{t('therapy.plan.consent')}</Checkbox></Form.Item>
      </Form>
    </Modal>
  );
}

/** One plan: its therapies with progress, booking, consent, cancel. */
function PlanDrawer({ id, therapies, onClose, onChanged, canManage }: {
  id: string | null; therapies: TherapyType[]; onClose: () => void; onChanged: () => void; canManage: boolean;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const name = useTherapyName();
  const [plan, setPlan] = useState<TherapyPlan | null>(null);
  const [booking, setBooking] = useState<TherapyPlanItem | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    const { data } = await api.get<TherapyPlan>(`/therapy-plans/${id}/`);
    setPlan(data);
  }, [id]);
  useEffect(() => { setPlan(null); load().catch(() => undefined); }, [load]);

  const cancelPlan = async () => {
    if (!plan) return;
    try {
      await api.post(`/therapy-plans/${plan.id}/cancel/`);
      await load();
      onChanged();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const closed = !plan || plan.status === 'completed' || plan.status === 'cancelled';
  return (
    <Drawer open={!!id} onClose={onClose} width={640} title={plan?.title ?? t('therapy.plan.edit')} destroyOnHidden
      extra={plan && canManage && plan.status !== 'cancelled' && plan.status !== 'completed' ? (
        <Popconfirm title={t('therapy.plan.cancelAsk')} onConfirm={cancelPlan}><Button danger>{t('therapy.plan.cancelPlan')}</Button></Popconfirm>
      ) : null}>
      {plan && (
        <>
          <Descriptions size="small" column={1} style={{ marginBottom: 12 }}>
            <Descriptions.Item label={t('therapy.plan.patient')}><PatientCell patient={plan.patient_detail} /></Descriptions.Item>
            <Descriptions.Item label={t('common.status')}><PlanStatusTag status={plan.status} /></Descriptions.Item>
            <Descriptions.Item label={t('therapy.plan.startDate')}>{dayjs(plan.start_date).format('DD-MM-YYYY')}</Descriptions.Item>
            {plan.doctor_name && <Descriptions.Item label={t('therapy.plan.doctor')}>{plan.doctor_name}</Descriptions.Item>}
            <Descriptions.Item label={t('therapy.plan.consent')}>
              {plan.consent_taken ? t('therapy.plan.consentOn', { date: plan.consent_on ? dayjs(plan.consent_on).format('DD-MM-YYYY') : '' }) : t('common.no')}
            </Descriptions.Item>
            {Number(plan.estimate) > 0 && <Descriptions.Item label={t('therapy.plan.estimate', { amount: '' }).replace(/[:\s]+$/, '')}>₹{plan.estimate}</Descriptions.Item>}
            {plan.notes && <Descriptions.Item label={t('therapy.plan.notes')}>{plan.notes}</Descriptions.Item>}
          </Descriptions>
          <Table<TherapyPlanItem>
            rowKey="id" size="small" pagination={false} dataSource={plan.items}
            columns={[
              { title: t('therapy.plan.therapy'), render: (_, r) => <div><b>{name(r)}</b> <StageTag stage={r.stage} /></div> },
              {
                title: t('therapy.plan.sessionsPlanned'),
                render: (_, r) => <span>{t('therapy.plan.booked', { booked: r.sessions_booked ?? 0, total: r.sessions_planned, done: r.sessions_done ?? 0 })}</span>,
              },
              {
                title: '', align: 'right', width: 130,
                render: (_, r) => canManage && !closed && (r.sessions_booked ?? 0) < r.sessions_planned ? (
                  <Button size="small" icon={<CalendarOutlined />} onClick={() => setBooking(r)}>{t('therapy.plan.book')}</Button>
                ) : null,
              },
            ]}
          />
          <BookModal plan={plan} item={booking} therapies={therapies} onClose={() => setBooking(null)}
            onBooked={() => { setBooking(null); load(); onChanged(); }} />
        </>
      )}
    </Drawer>
  );
}

/** Book several sessions of one therapy: pick the days, the time, a therapist and a room. */
function BookModal({ plan, item, onClose, onBooked }: {
  plan: TherapyPlan; item: TherapyPlanItem | null; therapies: TherapyType[]; onClose: () => void; onBooked: () => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const name = useTherapyName();
  const [form] = Form.useForm();
  const [options, setOptions] = useState<TherapyOptions>({ therapists: [], rooms: [] });
  const [saving, setSaving] = useState(false);
  const left = item ? item.sessions_planned - (item.sessions_booked ?? 0) : 0;

  useEffect(() => {
    if (!item) return;
    form.setFieldsValue({ dates: [], start_time: dayjs('09:00', 'HH:mm'), therapist: undefined, room: undefined });
    api.get<TherapyOptions>('/therapy-sessions/options/').then(({ data }) => setOptions(data)).catch(() => undefined);
  }, [item, form]);

  const save = async () => {
    if (!item?.id) return;
    const v = await form.validateFields();
    setSaving(true);
    try {
      await api.post(`/therapy-plans/${plan.id}/schedule/`, {
        item: item.id, dates: (v.dates as Dayjs[]).map((d) => d.format('YYYY-MM-DD')), start_time: (v.start_time as Dayjs).format('HH:mm'),
        therapist: v.therapist ?? null, room: v.room ?? null,
      });
      message.success(t('therapy.book.done', { n: (v.dates as Dayjs[]).length }));
      onBooked();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={!!item} title={item ? t('therapy.book.title', { name: name(item) }) : ''} onCancel={onClose} onOk={save}
      okText={t('therapy.book.save')} confirmLoading={saving} destroyOnHidden>
      <div className="cell-sub" style={{ marginBottom: 12 }}>{left > 0 ? t('therapy.book.left', { n: left }) : t('therapy.book.none')}</div>
      <Form form={form} layout="vertical">
        <Form.Item name="dates" label={t('therapy.book.dates')} extra={t('therapy.book.datesHelp')}
          rules={[{ required: true, type: 'array', min: 1, message: t('common.required') }]}>
          <DatePicker multiple maxTagCount="responsive" format="DD-MM-YYYY" style={{ width: '100%' }} minDate={dayjs()} />
        </Form.Item>
        <Form.Item name="start_time" label={t('therapy.book.time')} rules={[{ required: true, message: t('common.required') }]}>
          <TimePicker format="HH:mm" minuteStep={5} allowClear={false} />
        </Form.Item>
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
