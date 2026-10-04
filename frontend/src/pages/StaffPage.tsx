// Staff: add users, give them a role in each branch, reset passwords.
import { KeyOutlined, MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Checkbox, Col, Divider, Form, Input, Modal, Row, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { Role, Staff } from '../api/types';
import { useList } from '../api/useList';
import { useAuth } from '../auth/AuthContext';
import { LANGUAGES } from '../i18n';

export default function StaffPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can, me } = useAuth();
  const [search, setSearch] = useState('');
  const { rows, loading, reload, pagination } = useList<Staff>('/staff/', { search });
  const [roles, setRoles] = useState<Role[]>([]);
  const [editing, setEditing] = useState<Partial<Staff> | null>(null);
  const [passwordFor, setPasswordFor] = useState<Staff | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const canManage = can('staff.manage');
  const isOrgAdmin = !!me?.user.is_org_admin;

  useEffect(() => {
    if (can('roles.view')) api.get<Role[]>('/roles/').then(({ data }) => setRoles(data)).catch(() => undefined);
  }, [can]);

  const open = (staff?: Staff) => {
    setEditing(staff ?? {});
    form.resetFields();
    form.setFieldsValue(
      staff
        ? { ...staff, branch_roles: staff.branch_roles.map((br) => ({ branch: br.branch, role: br.role })) }
        : { is_active: true, preferred_language: 'en', branch_roles: [{}] },
    );
  };

  const save = async () => {
    const values = await form.validateFields();
    values.branch_roles = (values.branch_roles ?? []).filter((br: { branch?: string; role?: string }) => br?.branch && br?.role);
    if (!values.password) delete values.password;
    setSaving(true);
    try {
      if (editing?.id) await api.patch(`/staff/${editing.id}/`, values);
      else await api.post('/staff/', values);
      message.success(t('common.saved'));
      setEditing(null);
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const savePassword = async () => {
    const values = await passwordForm.validateFields();
    try {
      await api.post(`/staff/${passwordFor!.id}/set-password/`, { password: values.password });
      message.success(t('staff.passwordChanged'));
      setPasswordFor(null);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('staff.title')}</Typography.Title>
        <Space>
          <Input.Search placeholder={t('common.search')} allowClear onSearch={setSearch} style={{ width: 220 }} />
          {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('staff.add')}</Button>}
        </Space>
      </div>
      <Table<Staff>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        scroll={{ x: true }}
        columns={[
          {
            title: t('staff.fullName'), dataIndex: 'full_name',
            render: (name: string, s: Staff) => (
              <Space>
                {name}
                {s.is_doctor && <Tag color="blue">{t('staff.doctor')}</Tag>}
                {s.is_org_admin && <Tag color="gold">{t('layout.orgAdmin')}</Tag>}
              </Space>
            ),
          },
          { title: t('staff.username'), dataIndex: 'username' },
          {
            title: t('staff.branchRoles'), dataIndex: 'branch_roles',
            render: (list: Staff['branch_roles']) => list.map((br) => <Tag key={br.branch}>{br.branch_name}: {br.role_name}</Tag>),
          },
          {
            title: t('staff.lastLogin'), dataIndex: 'last_login',
            render: (value: string | null) => (value ? dayjs(value).format('DD-MM-YYYY HH:mm') : '—'),
          },
          {
            title: t('common.status'), dataIndex: 'is_active',
            render: (active: boolean) => active ? <Tag color="green">{t('common.active')}</Tag> : <Tag>{t('common.inactive')}</Tag>,
          },
          ...(canManage ? [{
            title: '', key: 'actions', width: 170,
            render: (_: unknown, s: Staff) => (
              <Space>
                <Button size="small" onClick={() => open(s)}>{t('common.edit')}</Button>
                <Button size="small" icon={<KeyOutlined />} onClick={() => { passwordForm.resetFields(); setPasswordFor(s); }}>
                  {t('staff.password')}
                </Button>
              </Space>
            ),
          }] : []),
        ]}
      />

      <Modal
        open={!!editing}
        title={editing?.id ? t('staff.edit') : t('staff.add')}
        onCancel={() => setEditing(null)}
        onOk={save}
        confirmLoading={saving}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        width={720}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item name="full_name" label={t('staff.fullName')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="username" label={t('staff.username')} rules={[{ required: true, message: t('common.required') }]}><Input autoComplete="off" /></Form.Item>
            </Col>
            {!editing?.id && (
              <Col xs={24} md={12}>
                <Form.Item name="password" label={t('staff.password')} extra={t('staff.passwordRules')} rules={[{ required: true, message: t('common.required') }, { min: 10 }]}>
                  <Input.Password autoComplete="new-password" />
                </Form.Item>
              </Col>
            )}
            <Col xs={24} md={12}>
              <Form.Item name="phone" label={t('staff.phone')} extra={t('staff.phoneHelp')}><Input /></Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="email" label={t('staff.email')} rules={[{ type: 'email' }]}><Input /></Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="designation" label={t('staff.designation')}><Input /></Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="preferred_language" label={t('layout.language')}>
                <Select options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))} />
              </Form.Item>
            </Col>
          </Row>
          <Space size={12} wrap>
            <Form.Item name="is_doctor" valuePropName="checked"><Checkbox>{t('staff.isDoctor')}</Checkbox></Form.Item>
            {isOrgAdmin && (
              <Form.Item name="is_org_admin" valuePropName="checked"><Checkbox>{t('staff.isOrgAdmin')}</Checkbox></Form.Item>
            )}
            <Form.Item name="is_active" label={t('common.active')} valuePropName="checked"><Switch /></Form.Item>
          </Space>
          <Form.Item noStyle shouldUpdate={(a, b) => a.is_doctor !== b.is_doctor}>
            {({ getFieldValue }) => getFieldValue('is_doctor') && (
              <Row gutter={12}>
                <Col xs={24} md={12}><Form.Item name="qualification" label={t('staff.qualification')}><Input placeholder="BAMS, MD (Ayu)" /></Form.Item></Col>
                <Col xs={24} md={12}><Form.Item name="registration_number" label={t('staff.registrationNumber')}><Input /></Form.Item></Col>
              </Row>
            )}
          </Form.Item>

          <Divider orientation="left">{t('staff.branchRoles')}</Divider>
          <Typography.Paragraph type="secondary">{t('staff.branchRolesHelp')}</Typography.Paragraph>
          <Form.List name="branch_roles">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} align="baseline" wrap>
                    <Form.Item name={[field.name, 'branch']} rules={[{ required: true, message: t('common.required') }]}>
                      <Select style={{ width: 240 }} placeholder={t('layout.branch')}
                        options={me?.branches.map((b) => ({ value: b.id, label: b.name }))} />
                    </Form.Item>
                    <Form.Item name={[field.name, 'role']} rules={[{ required: true, message: t('common.required') }]}>
                      <Select style={{ width: 200 }} placeholder={t('staff.role')}
                        options={roles.map((r) => ({ value: r.id, label: r.name }))} />
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(field.name)} aria-label={t('common.remove')} />
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />}>{t('staff.addBranchRole')}</Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      <Modal
        open={!!passwordFor}
        title={t('staff.setPasswordFor', { name: passwordFor?.full_name })}
        onCancel={() => setPasswordFor(null)}
        onOk={savePassword}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        destroyOnHidden
      >
        <Form form={passwordForm} layout="vertical">
          <Form.Item name="password" label={t('staff.newPassword')} extra={t('staff.passwordRules')}
            rules={[{ required: true, message: t('common.required') }, { min: 10 }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
