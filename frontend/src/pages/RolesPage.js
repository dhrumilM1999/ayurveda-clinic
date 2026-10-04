import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Roles: tick which permissions each role has.
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Checkbox, Col, Form, Input, Modal, Popconfirm, Row, Space, Switch, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
export default function RolesPage() {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can } = useAuth();
    const [roles, setRoles] = useState([]);
    const [catalog, setCatalog] = useState([]);
    const [loading, setLoading] = useState(false);
    const [editing, setEditing] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const canManage = can('roles.manage');
    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [rolesRes, catalogRes] = await Promise.all([
                api.get('/roles/'),
                api.get('/roles/catalog/'),
            ]);
            setRoles(rolesRes.data);
            setCatalog(catalogRes.data);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
        finally {
            setLoading(false);
        }
    }, [message, t]);
    useEffect(() => {
        load();
    }, [load]);
    // Group permissions by module: { patients: [...], billing: [...] }
    const groups = useMemo(() => {
        const result = {};
        catalog.forEach((p) => (result[p.group] = [...(result[p.group] ?? []), p]));
        return result;
    }, [catalog]);
    const permLabel = (p) => t(`permissions.${p.code.replace('.', '_')}`, { defaultValue: p.label });
    const open = (role) => {
        setEditing(role ?? {});
        form.resetFields();
        form.setFieldsValue(role ?? { permissions: ['dashboard.view'], requires_2fa: false });
    };
    const save = async () => {
        const values = await form.validateFields();
        setSaving(true);
        try {
            if (editing?.id)
                await api.patch(`/roles/${editing.id}/`, values);
            else
                await api.post('/roles/', values);
            message.success(t('common.saved'));
            setEditing(null);
            load();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    const remove = async (role) => {
        try {
            await api.delete(`/roles/${role.id}/`);
            message.success(t('common.removed'));
            load();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
    };
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('roles.title') }), canManage && _jsx(Button, { type: "primary", icon: _jsx(PlusOutlined, {}), onClick: () => open(), children: t('roles.add') })] }), _jsx(Typography.Paragraph, { type: "secondary", children: t('roles.help') }), _jsx(Table, { rowKey: "id", loading: loading, dataSource: roles, pagination: false, scroll: { x: true }, columns: [
                    {
                        title: t('roles.name'), dataIndex: 'name',
                        render: (name, r) => _jsxs(Space, { children: [name, r.is_system && _jsx(Tag, { children: t('roles.builtIn') })] }),
                    },
                    { title: t('roles.description'), dataIndex: 'description' },
                    { title: t('roles.permissionCount'), dataIndex: 'permissions', render: (p) => p.length, width: 120 },
                    { title: t('roles.users'), dataIndex: 'user_count', width: 90 },
                    { title: t('roles.otp'), dataIndex: 'requires_2fa', width: 90, render: (v) => (v ? t('common.yes') : t('common.no')) },
                    {
                        title: '', key: 'actions', width: 170,
                        render: (_, role) => (_jsxs(Space, { children: [_jsx(Button, { size: "small", onClick: () => open(role), children: canManage ? t('common.edit') : t('common.view') }), canManage && !role.is_system && (_jsx(Popconfirm, { title: t('roles.confirmRemove'), onConfirm: () => remove(role), okText: t('common.yes'), cancelText: t('common.no'), children: _jsx(Button, { size: "small", danger: true, children: t('common.remove') }) }))] })),
                    },
                ] }), _jsx(Modal, { open: !!editing, title: editing?.id ? editing.name : t('roles.add'), onCancel: () => setEditing(null), onOk: canManage ? save : () => setEditing(null), confirmLoading: saving, okText: canManage ? t('common.save') : t('common.close'), cancelText: t('common.cancel'), width: 860, destroyOnClose: true, children: _jsxs(Form, { form: form, layout: "vertical", disabled: !canManage, children: [_jsxs(Row, { gutter: 12, children: [_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "name", label: t('roles.name'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "description", label: t('roles.description'), children: _jsx(Input, {}) }) })] }), _jsx(Form.Item, { name: "requires_2fa", label: t('roles.otp'), valuePropName: "checked", extra: t('roles.otpHelp'), children: _jsx(Switch, {}) }), _jsx(Form.Item, { name: "permissions", label: t('roles.permissions'), children: _jsx(Checkbox.Group, { style: { width: '100%' }, children: _jsx(Row, { gutter: [12, 12], children: Object.entries(groups).map(([group, perms]) => (_jsx(Col, { xs: 24, md: 12, lg: 8, children: _jsx(Card, { size: "small", title: t(`permissionGroups.${group}`, { defaultValue: group }), children: _jsx(Space, { direction: "vertical", children: perms.map((p) => _jsx(Checkbox, { value: p.code, children: permLabel(p) }, p.code)) }) }) }, group))) }) }) })] }) })] }));
}
