// Fees & services: each doctor's OPD consultation fee (this branch) and the "Services & charges" list
// that can be added to an OPD bill (procedures, Panchakarma, certificates...).
import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Col, Form, Input, InputNumber, Modal, Row, Space, Switch, Table, Tag, Tooltip, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { ConsultationFeeRow, MasterRef, ServiceCharge } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { useMasterLabel } from '../api/masters';
import { MasterSelect } from '../components/MasterSelect';
import { money } from './medicines/shared';

export default function FeesServicesPage() {
  const { t } = useTranslation();
  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('fees.title')}</Typography.Title>
          <div className="cell-sub">{t('fees.subtitle')}</div>
        </div>
      </div>
      <ConsultationFees />
      <Services />
    </>
  );
}

type Draft = { new_case_fee: number | null; follow_up_fee: number | null; follow_up_days: number };

function ConsultationFees() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { branch, can } = useAuth();
  const canEdit = can('billing.manage');
  const [rows, setRows] = useState<ConsultationFeeRow[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<ConsultationFeeRow[]>('/consultation-fees/');
      setRows(data);
      setDrafts(Object.fromEntries(data.map((r) => [r.doctor, {
        new_case_fee: r.new_case_fee === null ? null : Number(r.new_case_fee),
        follow_up_fee: r.follow_up_fee === null ? null : Number(r.follow_up_fee),
        follow_up_days: r.follow_up_days,
      }])));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const changed = (r: ConsultationFeeRow) => {
    const d = drafts[r.doctor];
    if (!d) return false;
    return !r.is_set || d.new_case_fee !== Number(r.new_case_fee) || d.follow_up_fee !== Number(r.follow_up_fee) || d.follow_up_days !== r.follow_up_days;
  };
  const set = (doctor: string, patch: Partial<Draft>) => setDrafts((all) => ({ ...all, [doctor]: { ...all[doctor]!, ...patch } }));

  const save = async (r: ConsultationFeeRow) => {
    const d = drafts[r.doctor]!;
    if (d.new_case_fee === null || d.follow_up_fee === null) {
      message.warning(t('fees.enterBoth'));
      return;
    }
    setSaving(r.doctor);
    try {
      await api.post('/consultation-fees/set/', { doctor: r.doctor, ...d });
      message.success(t('common.saved'));
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(null);
    }
  };

  return (
    <Card title={t('fees.consultationTitle', { branch: branch?.name })} style={{ marginBottom: 12 }}>
      <div className="form-help">{t('fees.consultationHelp')}</div>
      <Table<ConsultationFeeRow>
        rowKey="doctor"
        size="middle"
        loading={loading}
        dataSource={rows}
        pagination={false}
        locale={{ emptyText: t('fees.noDoctors') }}
        columns={[
          {
            title: t('appointments.doctor'), dataIndex: 'doctor_name',
            render: (v: string, r: ConsultationFeeRow) => <Space size={8}><b>{v}</b>{!r.is_set && <Tag color="orange" className="tag-tight">{t('fees.notSet')}</Tag>}</Space>,
          },
          {
            title: t('fees.newCase'), key: 'new', width: 170,
            render: (_: unknown, r: ConsultationFeeRow) => (
              <InputNumber min={0} precision={0} prefix="₹" style={{ width: 130 }} disabled={!canEdit}
                value={drafts[r.doctor]?.new_case_fee ?? undefined} onChange={(v) => set(r.doctor, { new_case_fee: v ?? null })} />
            ),
          },
          {
            title: t('fees.followUp'), key: 'fu', width: 170,
            render: (_: unknown, r: ConsultationFeeRow) => (
              <InputNumber min={0} precision={0} prefix="₹" style={{ width: 130 }} disabled={!canEdit}
                value={drafts[r.doctor]?.follow_up_fee ?? undefined} onChange={(v) => set(r.doctor, { follow_up_fee: v ?? null })} />
            ),
          },
          {
            title: <Tooltip title={t('fees.followUpDaysHelp')}>{t('fees.followUpDays')}</Tooltip>, key: 'days', width: 170,
            render: (_: unknown, r: ConsultationFeeRow) => (
              <InputNumber min={0} max={365} precision={0} suffix={t('fees.days')} style={{ width: 130 }} disabled={!canEdit}
                value={drafts[r.doctor]?.follow_up_days} onChange={(v) => set(r.doctor, { follow_up_days: Number(v ?? 0) })} />
            ),
          },
          {
            title: '', key: 'save', width: 100, align: 'right' as const,
            render: (_: unknown, r: ConsultationFeeRow) => canEdit ? (
              <Button size="small" type={changed(r) ? 'primary' : 'default'} disabled={!changed(r)} loading={saving === r.doctor} onClick={() => save(r)}>
                {t('common.save')}
              </Button>
            ) : null,
          },
        ]}
      />
    </Card>
  );
}

function Services() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const canEdit = can('billing.manage');
  const masterLabel = useMasterLabel();
  const [rows, setRows] = useState<ServiceCharge[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<ServiceCharge | 'new' | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows((await api.get<ServiceCharge[]>('/services/')).data);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = async (s: ServiceCharge, on: boolean) => {
    try {
      await api.patch(`/services/${s.id}/`, { is_active: on });
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <Card title={t('fees.servicesTitle')}
      extra={canEdit && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>{t('fees.addService')}</Button>}>
      <div className="form-help">{t('fees.servicesHelp')}</div>
      <Table<ServiceCharge>
        rowKey="id"
        size="middle"
        loading={loading}
        dataSource={rows}
        pagination={false}
        rowClassName={(r) => (r.is_active ? '' : 'row-muted')}
        locale={{ emptyText: t('fees.noServices') }}
        columns={[
          {
            title: t('fees.service'), dataIndex: 'name',
            render: (v: string, r: ServiceCharge) => (
              <div style={{ lineHeight: 1.35 }}>
                <b>{v}</b> {r.is_sample && <Tag color="orange" className="tag-tight">{t('medicines.sample')}</Tag>}
                <div className="cell-sub">{[r.name_gu, r.name_hi].filter(Boolean).join(' · ')}</div>
              </div>
            ),
          },
          { title: t('fees.category'), dataIndex: 'category', width: 180, render: (c: MasterRef | null) => (c ? masterLabel(c) : '—') },
          {
            title: t('fees.price'), key: 'price', width: 150, align: 'right' as const,
            render: (_: unknown, r: ServiceCharge) => (
              <div style={{ lineHeight: 1.35 }}>
                <b className="num">{money(r.effective_price ?? r.price)}</b>
                {r.branch_price !== null && <div className="cell-sub">{t('fees.branchPrice')}</div>}
              </div>
            ),
          },
          { title: 'GST', dataIndex: 'gst_rate', width: 80, align: 'right' as const, render: (v: string) => `${Number(v)}%` },
          { title: 'SAC', dataIndex: 'sac_code', width: 100 },
          {
            title: t('common.active'), dataIndex: 'is_active', width: 90,
            render: (on: boolean, r: ServiceCharge) => <Switch size="small" checked={on} disabled={!canEdit} onChange={(v) => toggle(r, v)} />,
          },
          {
            title: '', key: 'edit', width: 50, align: 'right' as const,
            render: (_: unknown, r: ServiceCharge) => canEdit ? <Button size="small" type="text" icon={<EditOutlined />} onClick={() => setEditing(r)} aria-label={t('common.edit')} /> : null,
          },
        ]}
      />
      {editing && <ServiceModal service={editing === 'new' ? null : editing} onClose={(saved) => { setEditing(null); if (saved) load(); }} />}
    </Card>
  );
}

function ServiceModal({ service, onClose }: { service: ServiceCharge | null; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { branch } = useAuth();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const initial = service ? {
    ...service, category: service.category?.id, price: Number(service.price), gst_rate: Number(service.gst_rate),
    branch_price: service.branch_price === null ? undefined : Number(service.branch_price),
  } : { gst_rate: 0, sac_code: '999312' };

  const save = async () => {
    const { branch_price, ...values } = await form.validateFields();
    setSaving(true);
    try {
      const { data } = service ? await api.patch<ServiceCharge>(`/services/${service.id}/`, values) : await api.post<ServiceCharge>('/services/', values);
      const ownPrice = branch_price ?? null;
      if (ownPrice !== (service?.branch_price === null || !service ? null : Number(service.branch_price))) {
        await api.post(`/services/${data.id}/branch-price/`, { price: ownPrice, is_active: true });
      }
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const required = [{ required: true, message: t('common.required') }];
  return (
    <Modal open width={640} title={service ? t('fees.editService') : t('fees.addService')} onCancel={() => onClose(false)} onOk={save}
      okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving} keyboard={false} maskClosable={false} destroyOnHidden>
      <Form form={form} layout="vertical" requiredMark={false} initialValues={initial}>
        <Row gutter={12}>
          <Col xs={24} md={14}><Form.Item name="name" label={t('fees.serviceName')} rules={required}><Input maxLength={150} placeholder="Agnikarma" /></Form.Item></Col>
          <Col xs={24} md={10}><Form.Item name="category" label={t('fees.category')}><MasterSelect category="service_category" /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="name_gu" label={t('medicines.nameGu')}><Input maxLength={150} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="name_hi" label={t('medicines.nameHi')}><Input maxLength={150} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="price" label={t('fees.price')} rules={required}><InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}>
            <Form.Item name="branch_price" label={t('fees.branchPriceLabel', { branch: branch?.name })} extra={t('fees.branchPriceHelp')}>
              <InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col xs={12} md={6}><Form.Item name="gst_rate" label="GST %" extra={t('fees.gstHelp')}><InputNumber min={0} max={40} precision={2} suffix="%" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="sac_code" label="SAC"><Input maxLength={10} /></Form.Item></Col>
        </Row>
      </Form>
    </Modal>
  );
}
