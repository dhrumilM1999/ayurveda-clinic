// Suppliers (who medicines are bought from). Shared by all branches. Switch off instead of deleting.
import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Col, Form, Input, Modal, Row, Switch, Table } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Supplier } from '../../api/types';

export function SuppliersTab() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [rows, setRows] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<Supplier | 'new' | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Supplier[]>('/suppliers/');
      setRows(data);
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
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>{t('pharmacy.addSupplier')}</Button>
      </div>
      <Table<Supplier>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        rowClassName={(s) => (s.is_active ? '' : 'row-muted')}
        locale={{ emptyText: t('pharmacy.noSuppliers') }}
        columns={[
          { title: t('pharmacy.supplier'), dataIndex: 'name', render: (v: string) => <b>{v}</b> },
          { title: t('pharmacy.contact'), key: 'c', render: (_: unknown, s: Supplier) => [s.contact_person, s.phone].filter(Boolean).join(' · ') || '—' },
          { title: 'GSTIN', dataIndex: 'gstin', render: (v: string) => (v ? <span className="mono">{v}</span> : '—') },
          { title: t('common.active'), dataIndex: 'is_active', width: 90, render: (on: boolean, s: Supplier) => <Switch size="small" checked={on} onChange={(v) => toggle(s, v)} /> },
          {
            title: '', key: 'edit', width: 60, align: 'right' as const,
            render: (_: unknown, s: Supplier) => <Button size="small" type="text" icon={<EditOutlined />} onClick={() => setEditing(s)} aria-label={t('common.edit')} />,
          },
        ]}
      />
      {editing && <SupplierModal supplier={editing === 'new' ? null : editing} onClose={(saved) => { setEditing(null); if (saved) load(); }} />}
    </>
  );
}

function SupplierModal({ supplier, onClose }: { supplier: Supplier | null; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (supplier) form.setFieldsValue(supplier); }, [supplier, form]);

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
    <Modal open width={560} title={supplier ? t('pharmacy.editSupplier') : t('pharmacy.addSupplier')} onCancel={() => onClose(false)}
      onOk={save} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving} destroyOnHidden>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="name" label={t('pharmacy.supplier')} rules={[{ required: true, message: t('common.required') }]}><Input maxLength={200} /></Form.Item>
        <Row gutter={12}>
          <Col xs={24} md={12}><Form.Item name="contact_person" label={t('pharmacy.contactPerson')}><Input maxLength={120} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="phone" label={t('branches.phone')}><Input maxLength={20} /></Form.Item></Col>
        </Row>
        <Form.Item name="gstin" label="GSTIN"><Input maxLength={15} style={{ textTransform: 'uppercase' }} /></Form.Item>
        <Form.Item name="address" label={t('branches.address')}><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} /></Form.Item>
      </Form>
    </Modal>
  );
}
