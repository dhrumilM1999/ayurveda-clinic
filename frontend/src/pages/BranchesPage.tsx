// Branches: list, add and edit. Branches are switched off (not deleted).
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, Modal, Switch, Table, Tag, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { Branch } from '../api/types';
import { useList } from '../api/useList';
import { useAuth } from '../auth/AuthContext';

export default function BranchesPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [search, setSearch] = useState('');
  const { rows, loading, reload, pagination } = useList<Branch>('/branches/', { search });
  const [editing, setEditing] = useState<Partial<Branch> | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const canManage = can('branches.manage');

  const open = (branch?: Branch) => {
    setEditing(branch ?? {});
    form.setFieldsValue(branch ?? { state: 'Gujarat', is_active: true });
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing?.id) await api.patch(`/branches/${editing.id}/`, values);
      else await api.post('/branches/', values);
      message.success(t('common.saved'));
      setEditing(null);
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('branches.title')}</Typography.Title>
        <div style={{ display: 'flex', gap: 8 }}>
          <Input.Search placeholder={t('common.search')} allowClear onSearch={setSearch} style={{ width: 220 }} />
          {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('branches.add')}</Button>}
        </div>
      </div>
      {!canManage && <Typography.Paragraph type="secondary">{t('branches.onlyOrgAdmin')}</Typography.Paragraph>}
      <Table<Branch>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        scroll={{ x: true }}
        onRow={(record) => ({ onClick: () => canManage && open(record), style: { cursor: canManage ? 'pointer' : 'default' } })}
        columns={[
          { title: t('branches.code'), dataIndex: 'code', width: 90 },
          { title: t('branches.name'), dataIndex: 'name' },
          { title: t('branches.city'), dataIndex: 'city' },
          { title: t('branches.phone'), dataIndex: 'phone' },
          { title: t('branches.gstin'), dataIndex: 'gstin' },
          {
            title: t('common.status'), dataIndex: 'is_active',
            render: (active: boolean) => active ? <Tag color="green">{t('common.active')}</Tag> : <Tag>{t('common.inactive')}</Tag>,
          },
        ]}
      />
      <Modal
        open={!!editing}
        title={editing?.id ? t('branches.edit') : t('branches.add')}
        onCancel={() => setEditing(null)}
        onOk={save}
        confirmLoading={saving}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('branches.name')} rules={[{ required: true, message: t('common.required') }]}>
            <Input />
          </Form.Item>
          <Form.Item name="code" label={t('branches.code')} extra={t('branches.codeHelp')}
            rules={[{ required: true, message: t('common.required') }, { max: 20 }]}>
            <Input style={{ textTransform: 'uppercase' }} />
          </Form.Item>
          <Form.Item name="address" label={t('branches.address')}><Input.TextArea rows={2} /></Form.Item>
          <Form.Item name="city" label={t('branches.city')}><Input /></Form.Item>
          <Form.Item name="state" label={t('branches.state')}><Input /></Form.Item>
          <Form.Item name="pincode" label={t('branches.pincode')} rules={[{ pattern: /^\d{6}$/, message: t('branches.pincodeInvalid') }]}>
            <Input maxLength={6} />
          </Form.Item>
          <Form.Item name="phone" label={t('branches.phone')}><Input /></Form.Item>
          <Form.Item name="email" label={t('branches.email')} rules={[{ type: 'email' }]}><Input /></Form.Item>
          <Form.Item name="gstin" label={t('branches.gstin')} rules={[{ len: 15, message: t('branches.gstinInvalid') }]}>
            <Input maxLength={15} style={{ textTransform: 'uppercase' }} />
          </Form.Item>
          <Form.Item name="is_active" label={t('common.active')} valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
