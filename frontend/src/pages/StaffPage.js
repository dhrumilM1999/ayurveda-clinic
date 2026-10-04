import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Staff: add users, give them a role in each branch, reset passwords.
import { KeyOutlined, MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Checkbox, Col, Divider, Form, Input, Modal, Row, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useList } from '../api/useList';
import { useAuth } from '../auth/AuthContext';
import { LANGUAGES } from '../i18n';
export default function StaffPage() {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can, me } = useAuth();
    const [search, setSearch] = useState('');
    const { rows, loading, reload, pagination } = useList('/staff/', { search });
    const [roles, setRoles] = useState([]);
    const [editing, setEditing] = useState(null);
    const [passwordFor, setPasswordFor] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const [passwordForm] = Form.useForm();
    const canManage = can('staff.manage');
    const isOrgAdmin = !!me?.user.is_org_admin;
    useEffect(() => {
        if (can('roles.view'))
            api.get('/roles/').then(({ data }) => setRoles(data)).catch(() => undefined);
    }, [can]);
    const open = (staff) => {
        setEditing(staff ?? {});
        form.resetFields();
        form.setFieldsValue(staff
            ? { ...staff, branch_roles: staff.branch_roles.map((br) => ({ branch: br.branch, role: br.role })) }
            : { is_active: true, preferred_language: 'en', branch_roles: [{}] });
    };
    const save = async () => {
        const values = await form.validateFields();
        values.branch_roles = (values.branch_roles ?? []).filter((br) => br?.branch && br?.role);
        if (!values.password)
            delete values.password;
        setSaving(true);
        try {
            if (editing?.id)
                await api.patch(`/staff/${editing.id}/`, values);
            else
                await api.post('/staff/', values);
            message.success(t('common.saved'));
            setEditing(null);
            reload();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    const savePassword = async () => {
        const values = await passwordForm.validateFields();
        try {
            await api.post(`/staff/${passwordFor.id}/set-password/`, { password: values.password });
            message.success(t('staff.passwordChanged'));
            setPasswordFor(null);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
    };
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('staff.title') }), _jsxs(Space, { children: [_jsx(Input.Search, { placeholder: t('common.search'), allowClear: true, onSearch: setSearch, style: { width: 220 } }), canManage && _jsx(Button, { type: "primary", icon: _jsx(PlusOutlined, {}), onClick: () => open(), children: t('staff.add') })] })] }), _jsx(Table, { rowKey: "id", loading: loading, dataSource: rows, pagination: pagination, scroll: { x: true }, columns: [
                    {
                        title: t('staff.fullName'), dataIndex: 'full_name',
                        render: (name, s) => (_jsxs(Space, { children: [name, s.is_doctor && _jsx(Tag, { color: "blue", children: t('staff.doctor') }), s.is_org_admin && _jsx(Tag, { color: "gold", children: t('layout.orgAdmin') })] })),
                    },
                    { title: t('staff.username'), dataIndex: 'username' },
                    {
                        title: t('staff.branchRoles'), dataIndex: 'branch_roles',
                        render: (list) => list.map((br) => _jsxs(Tag, { children: [br.branch_name, ": ", br.role_name] }, br.branch)),
                    },
                    {
                        title: t('staff.lastLogin'), dataIndex: 'last_login',
                        render: (value) => (value ? dayjs(value).format('DD-MM-YYYY HH:mm') : '—'),
                    },
                    {
                        title: t('common.status'), dataIndex: 'is_active',
                        render: (active) => active ? _jsx(Tag, { color: "green", children: t('common.active') }) : _jsx(Tag, { children: t('common.inactive') }),
                    },
                    ...(canManage ? [{
                            title: '', key: 'actions', width: 170,
                            render: (_, s) => (_jsxs(Space, { children: [_jsx(Button, { size: "small", onClick: () => open(s), children: t('common.edit') }), _jsx(Button, { size: "small", icon: _jsx(KeyOutlined, {}), onClick: () => { passwordForm.resetFields(); setPasswordFor(s); }, children: t('staff.password') })] })),
                        }] : []),
                ] }), _jsx(Modal, { open: !!editing, title: editing?.id ? t('staff.edit') : t('staff.add'), onCancel: () => setEditing(null), onOk: save, confirmLoading: saving, okText: t('common.save'), cancelText: t('common.cancel'), width: 720, destroyOnClose: true, children: _jsxs(Form, { form: form, layout: "vertical", children: [_jsxs(Row, { gutter: 12, children: [_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "full_name", label: t('staff.fullName'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "username", label: t('staff.username'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, { autoComplete: "off" }) }) }), !editing?.id && (_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "password", label: t('staff.password'), extra: t('staff.passwordRules'), rules: [{ required: true, message: t('common.required') }, { min: 10 }], children: _jsx(Input.Password, { autoComplete: "new-password" }) }) })), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "phone", label: t('staff.phone'), extra: t('staff.phoneHelp'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "email", label: t('staff.email'), rules: [{ type: 'email' }], children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "designation", label: t('staff.designation'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "preferred_language", label: t('layout.language'), children: _jsx(Select, { options: LANGUAGES.map((l) => ({ value: l.code, label: l.label })) }) }) })] }), _jsxs(Space, { size: "large", wrap: true, children: [_jsx(Form.Item, { name: "is_doctor", valuePropName: "checked", children: _jsx(Checkbox, { children: t('staff.isDoctor') }) }), isOrgAdmin && (_jsx(Form.Item, { name: "is_org_admin", valuePropName: "checked", children: _jsx(Checkbox, { children: t('staff.isOrgAdmin') }) })), _jsx(Form.Item, { name: "is_active", label: t('common.active'), valuePropName: "checked", children: _jsx(Switch, {}) })] }), _jsx(Form.Item, { noStyle: true, shouldUpdate: (a, b) => a.is_doctor !== b.is_doctor, children: ({ getFieldValue }) => getFieldValue('is_doctor') && (_jsxs(Row, { gutter: 12, children: [_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "qualification", label: t('staff.qualification'), children: _jsx(Input, { placeholder: "BAMS, MD (Ayu)" }) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "registration_number", label: t('staff.registrationNumber'), children: _jsx(Input, {}) }) })] })) }), _jsx(Divider, { orientation: "left", children: t('staff.branchRoles') }), _jsx(Typography.Paragraph, { type: "secondary", children: t('staff.branchRolesHelp') }), _jsx(Form.List, { name: "branch_roles", children: (fields, { add, remove }) => (_jsxs(_Fragment, { children: [fields.map((field) => (_jsxs(Space, { align: "baseline", wrap: true, children: [_jsx(Form.Item, { name: [field.name, 'branch'], rules: [{ required: true, message: t('common.required') }], children: _jsx(Select, { style: { width: 240 }, placeholder: t('layout.branch'), options: me?.branches.map((b) => ({ value: b.id, label: b.name })) }) }), _jsx(Form.Item, { name: [field.name, 'role'], rules: [{ required: true, message: t('common.required') }], children: _jsx(Select, { style: { width: 200 }, placeholder: t('staff.role'), options: roles.map((r) => ({ value: r.id, label: r.name })) }) }), _jsx(MinusCircleOutlined, { onClick: () => remove(field.name), "aria-label": t('common.remove') })] }, field.key))), _jsx(Button, { type: "dashed", onClick: () => add(), icon: _jsx(PlusOutlined, {}), children: t('staff.addBranchRole') })] })) })] }) }), _jsx(Modal, { open: !!passwordFor, title: t('staff.setPasswordFor', { name: passwordFor?.full_name }), onCancel: () => setPasswordFor(null), onOk: savePassword, okText: t('common.save'), cancelText: t('common.cancel'), destroyOnClose: true, children: _jsx(Form, { form: passwordForm, layout: "vertical", children: _jsx(Form.Item, { name: "password", label: t('staff.newPassword'), extra: t('staff.passwordRules'), rules: [{ required: true, message: t('common.required') }, { min: 10 }], children: _jsx(Input.Password, { autoComplete: "new-password" }) }) }) })] }));
}
