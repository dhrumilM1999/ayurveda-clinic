// Roles: tick which permissions each role has.
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Checkbox, Col, Form, Input, Modal, Popconfirm, Row, Space, Switch, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { PermissionInfo, Role } from '../api/types';
import { useAuth } from '../auth/AuthContext';

export default function RolesPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [roles, setRoles] = useState<Role[]>([]);
  const [catalog, setCatalog] = useState<PermissionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<Partial<Role> | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const canManage = can('roles.manage');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rolesRes, catalogRes] = await Promise.all([
        api.get<Role[]>('/roles/'),
        api.get<PermissionInfo[]>('/roles/catalog/'),
      ]);
      setRoles(rolesRes.data);
      setCatalog(catalogRes.data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [message, t]);

  useEffect(() => {
    load();
  }, [load]);

  // Group permissions by module: { patients: [...], billing: [...] }
  const groups = useMemo(() => {
    const result: Record<string, PermissionInfo[]> = {};
    catalog.forEach((p) => (result[p.group] = [...(result[p.group] ?? []), p]));
    return result;
  }, [catalog]);

  const permLabel = (p: PermissionInfo) => t(`permissions.${p.code.replace('.', '_')}`, { defaultValue: p.label });

  const open = (role?: Role) => {
    setEditing(role ?? {});
    form.resetFields();
    form.setFieldsValue(role ?? { permissions: ['dashboard.view'], requires_2fa: false });
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing?.id) await api.patch(`/roles/${editing.id}/`, values);
      else await api.post('/roles/', values);
      message.success(t('common.saved'));
      setEditing(null);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (role: Role) => {
    try {
      await api.delete(`/roles/${role.id}/`);
      message.success(t('common.removed'));
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('roles.title')}</Typography.Title>
        {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('roles.add')}</Button>}
      </div>
      <Typography.Paragraph type="secondary">{t('roles.help')}</Typography.Paragraph>
      <Table<Role>
        rowKey="id"
        loading={loading}
        dataSource={roles}
        pagination={false}
        scroll={{ x: true }}
        columns={[
          {
            title: t('roles.name'), dataIndex: 'name',
            render: (name: string, r: Role) => <Space>{name}{r.is_system && <Tag>{t('roles.builtIn')}</Tag>}</Space>,
          },
          { title: t('roles.description'), dataIndex: 'description' },
          { title: t('roles.permissionCount'), dataIndex: 'permissions', render: (p: string[]) => p.length, width: 120 },
          { title: t('roles.users'), dataIndex: 'user_count', width: 90 },
          { title: t('roles.otp'), dataIndex: 'requires_2fa', width: 90, render: (v: boolean) => (v ? t('common.yes') : t('common.no')) },
          {
            title: '', key: 'actions', width: 170,
            render: (_: unknown, role: Role) => (
              <Space>
                <Button size="small" onClick={() => open(role)}>{canManage ? t('common.edit') : t('common.view')}</Button>
                {canManage && !role.is_system && (
                  <Popconfirm title={t('roles.confirmRemove')} onConfirm={() => remove(role)} okText={t('common.yes')} cancelText={t('common.no')}>
                    <Button size="small" danger>{t('common.remove')}</Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={!!editing}
        title={editing?.id ? editing.name : t('roles.add')}
        onCancel={() => setEditing(null)}
        onOk={canManage ? save : () => setEditing(null)}
        confirmLoading={saving}
        okText={canManage ? t('common.save') : t('common.close')}
        cancelText={t('common.cancel')}
        width={860}
        destroyOnClose
      >
        <Form form={form} layout="vertical" disabled={!canManage}>
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item name="name" label={t('roles.name')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="description" label={t('roles.description')}><Input /></Form.Item>
            </Col>
          </Row>
          <Form.Item name="requires_2fa" label={t('roles.otp')} valuePropName="checked" extra={t('roles.otpHelp')}><Switch /></Form.Item>
          <Form.Item name="permissions" label={t('roles.permissions')}>
            <Checkbox.Group style={{ width: '100%' }}>
              <Row gutter={[12, 12]}>
                {Object.entries(groups).map(([group, perms]) => (
                  <Col xs={24} md={12} lg={8} key={group}>
                    <Card size="small" title={t(`permissionGroups.${group}`, { defaultValue: group })}>
                      <Space direction="vertical">
                        {perms.map((p) => <Checkbox key={p.code} value={p.code}>{permLabel(p)}</Checkbox>)}
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
