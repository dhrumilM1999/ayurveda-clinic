// Pharmacy set-up: racks / shelves and suppliers.
import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Col, Form, Input, InputNumber, Modal, Row, Segmented, Switch, Table } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Rack, Supplier } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';

export function SetupTab() {
  const { t } = useTranslation();
  const { hasFeature } = useAuth();
  const [view, setView] = useState<'racks' | 'suppliers'>('racks');
  // Racks and suppliers each have a switch in Additional settings
  if (!hasFeature('pharmacy_racks')) return <Suppliers />;
  if (!hasFeature('pharmacy_suppliers')) return <Racks />;
  return (
    <>
      <div className="filter-bar">
        <Segmented value={view} onChange={(v) => setView(v as typeof view)}
          options={[{ value: 'racks', label: t('pharmacy.racks') }, { value: 'suppliers', label: t('pharmacy.tabs.suppliers') }]} />
      </div>
      {view === 'racks' ? <Racks /> : <Suppliers />}
    </>
  );
}

function Racks() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [rows, setRows] = useState<Rack[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<Rack | 'new' | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows((await api.get<Rack[]>('/racks/')).data);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  const toggle = async (r: Rack, on: boolean) => {
    try {
      await api.patch(`/racks/${r.id}/`, { is_active: on });
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };
  return (
    <>
      <div className="section-toolbar">
        <span className="cell-sub">{t('pharmacy.racksHelp')}</span>
        {can('pharmacy.stock') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>{t('pharmacy.addRack')}</Button>}
      </div>
      <Table<Rack> rowKey="id" loading={loading} dataSource={rows} pagination={false} rowClassName={(r) => (r.is_active ? '' : 'row-muted')}
        locale={{ emptyText: t('pharmacy.noRacks') }}
        columns={[
          { title: t('pharmacy.rack'), dataIndex: 'code', width: 90, render: (v: string) => <b className="mono">{v}</b> },
          { title: t('pharmacy.rackName'), dataIndex: 'name', render: (v: string) => v || '—' },
          { title: t('pharmacy.shelves'), dataIndex: 'shelves', width: 90, align: 'center' as const },
          { title: t('pharmacy.products'), dataIndex: 'product_count', width: 110, align: 'center' as const },
          { title: t('common.active'), dataIndex: 'is_active', width: 90, render: (on: boolean, r: Rack) => <Switch size="small" checked={on} disabled={!can('pharmacy.stock')} onChange={(v) => toggle(r, v)} /> },
          {
            title: '', key: 'e', width: 60, align: 'right' as const,
            render: (_: unknown, r: Rack) => can('pharmacy.stock') ? <Button size="small" type="text" icon={<EditOutlined />} onClick={() => setEditing(r)} aria-label={t('common.edit')} /> : null,
          },
        ]} />
      {editing && <RackModal rack={editing === 'new' ? null : editing} onClose={(saved) => { setEditing(null); if (saved) load(); }} />}
    </>
  );
}

function RackModal({ rack, onClose }: { rack: Rack | null; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  useEffect(() => { form.setFieldsValue(rack ?? { shelves: 5 }); }, [rack, form]);
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (rack) await api.patch(`/racks/${rack.id}/`, values);
      else await api.post('/racks/', values);
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal open keyboard={false} maskClosable={false} width={460} title={rack ? t('pharmacy.editRack') : t('pharmacy.addRack')} onCancel={() => onClose(false)} onOk={save}
      okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving} destroyOnHidden>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Row gutter={12}>
          <Col span={8}><Form.Item name="code" label={t('pharmacy.rackCode')} rules={[{ required: true, message: t('common.required') }]}><Input maxLength={20} style={{ textTransform: 'uppercase' }} placeholder="A" /></Form.Item></Col>
          <Col span={16}><Form.Item name="shelves" label={t('pharmacy.shelves')}><InputNumber min={1} max={50} style={{ width: '100%' }} /></Form.Item></Col>
        </Row>
        <Form.Item name="name" label={t('pharmacy.rackName')}><Input maxLength={100} placeholder={t('pharmacy.rackNamePlaceholder')} /></Form.Item>
      </Form>
    </Modal>
  );
}

function Suppliers() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [rows, setRows] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<Supplier | 'new' | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows((await api.get<Supplier[]>('/suppliers/')).data);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  const toggle = async (s: Supplier, on: boolean) => {
    try {
      await api.patch(`/suppliers/${s.id}/`, { is_active: on });
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };
  return (
    <>
      <div className="section-toolbar">
        <span className="cell-sub">{t('pharmacy.suppliersHelp')}</span>
        {can('pharmacy.stock') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>{t('pharmacy.addSupplier')}</Button>}
      </div>
      <Table<Supplier> rowKey="id" loading={loading} dataSource={rows} pagination={false} rowClassName={(s) => (s.is_active ? '' : 'row-muted')}
        locale={{ emptyText: t('pharmacy.noSuppliers') }} scroll={{ x: 800 }}
        columns={[
          { title: t('pharmacy.supplier'), dataIndex: 'name', render: (v: string, s: Supplier) => <div style={{ lineHeight: 1.35 }}><b>{v}</b><div className="cell-sub">{s.state}</div></div> },
          { title: t('pharmacy.contact'), key: 'c', render: (_: unknown, s: Supplier) => [s.contact_person, s.phone, s.email].filter(Boolean).join(' · ') || '—' },
          { title: 'GSTIN', dataIndex: 'gstin', render: (v: string) => (v ? <span className="mono">{v}</span> : '—') },
          { title: t('pharmacy.drugLicence'), dataIndex: 'drug_licence_no', render: (v: string) => v || '—' },
          { title: t('pharmacy.paymentTerms'), dataIndex: 'payment_terms_days', width: 120, render: (v: number | null) => (v ? t('pharmacy.daysN', { n: v }) : '—') },
          { title: t('common.active'), dataIndex: 'is_active', width: 90, render: (on: boolean, s: Supplier) => <Switch size="small" checked={on} disabled={!can('pharmacy.stock')} onChange={(v) => toggle(s, v)} /> },
          {
            title: '', key: 'edit', width: 60, align: 'right' as const,
            render: (_: unknown, s: Supplier) => can('pharmacy.stock') ? <Button size="small" type="text" icon={<EditOutlined />} onClick={() => setEditing(s)} aria-label={t('common.edit')} /> : null,
          },
        ]} />
      {editing && <SupplierModal supplier={editing === 'new' ? null : editing} onClose={(saved) => { setEditing(null); if (saved) load(); }} />}
    </>
  );
}

function SupplierModal({ supplier, onClose }: { supplier: Supplier | null; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  useEffect(() => { form.setFieldsValue(supplier ?? { state: 'Gujarat' }); }, [supplier, form]);
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (supplier) await api.patch(`/suppliers/${supplier.id}/`, values);
      else await api.post('/suppliers/', values);
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Modal open keyboard={false} maskClosable={false} width={640} title={supplier ? t('pharmacy.editSupplier') : t('pharmacy.addSupplier')} onCancel={() => onClose(false)}
      onOk={save} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving} destroyOnHidden>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="name" label={t('pharmacy.supplier')} rules={[{ required: true, message: t('common.required') }]}><Input maxLength={200} /></Form.Item>
        <Row gutter={12}>
          <Col xs={24} md={12}><Form.Item name="contact_person" label={t('pharmacy.contactPerson')}><Input maxLength={120} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="phone" label={t('branches.phone')}><Input maxLength={20} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="email" label={t('branches.email')} rules={[{ type: 'email', message: t('patients.emailInvalid') }]}><Input maxLength={120} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="gstin" label="GSTIN"><Input maxLength={15} style={{ textTransform: 'uppercase' }} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="drug_licence_no" label={t('pharmacy.drugLicence')}><Input maxLength={100} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="state" label={t('pharmacy.state')}><Input maxLength={100} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="payment_terms_days" label={t('pharmacy.paymentTerms')}><InputNumber min={0} max={365} suffix={t('pharmacy.days')} style={{ width: '100%' }} /></Form.Item></Col>
        </Row>
        <Form.Item name="address" label={t('branches.address')}><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} /></Form.Item>
      </Form>
    </Modal>
  );
}
