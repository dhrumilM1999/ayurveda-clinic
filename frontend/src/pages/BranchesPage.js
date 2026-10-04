import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Branches: list, add and edit. Branches are switched off (not deleted).
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, Modal, Switch, Table, Tag, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useList } from '../api/useList';
import { useAuth } from '../auth/AuthContext';
export default function BranchesPage() {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can } = useAuth();
    const [search, setSearch] = useState('');
    const { rows, loading, reload, pagination } = useList('/branches/', { search });
    const [editing, setEditing] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const canManage = can('branches.manage');
    const open = (branch) => {
        setEditing(branch ?? {});
        form.setFieldsValue(branch ?? { state: 'Gujarat', is_active: true });
    };
    const save = async () => {
        const values = await form.validateFields();
        setSaving(true);
        try {
            if (editing?.id)
                await api.patch(`/branches/${editing.id}/`, values);
            else
                await api.post('/branches/', values);
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
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('branches.title') }), _jsxs("div", { style: { display: 'flex', gap: 8 }, children: [_jsx(Input.Search, { placeholder: t('common.search'), allowClear: true, onSearch: setSearch, style: { width: 220 } }), canManage && _jsx(Button, { type: "primary", icon: _jsx(PlusOutlined, {}), onClick: () => open(), children: t('branches.add') })] })] }), !canManage && _jsx(Typography.Paragraph, { type: "secondary", children: t('branches.onlyOrgAdmin') }), _jsx(Table, { rowKey: "id", loading: loading, dataSource: rows, pagination: pagination, scroll: { x: true }, onRow: (record) => ({ onClick: () => canManage && open(record), style: { cursor: canManage ? 'pointer' : 'default' } }), columns: [
                    { title: t('branches.code'), dataIndex: 'code', width: 90 },
                    { title: t('branches.name'), dataIndex: 'name' },
                    { title: t('branches.city'), dataIndex: 'city' },
                    { title: t('branches.phone'), dataIndex: 'phone' },
                    { title: t('branches.gstin'), dataIndex: 'gstin' },
                    {
                        title: t('common.status'), dataIndex: 'is_active',
                        render: (active) => active ? _jsx(Tag, { color: "green", children: t('common.active') }) : _jsx(Tag, { children: t('common.inactive') }),
                    },
                ] }), _jsx(Modal, { open: !!editing, title: editing?.id ? t('branches.edit') : t('branches.add'), onCancel: () => setEditing(null), onOk: save, confirmLoading: saving, okText: t('common.save'), cancelText: t('common.cancel'), destroyOnClose: true, children: _jsxs(Form, { form: form, layout: "vertical", children: [_jsx(Form.Item, { name: "name", label: t('branches.name'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "code", label: t('branches.code'), extra: t('branches.codeHelp'), rules: [{ required: true, message: t('common.required') }, { max: 20 }], children: _jsx(Input, { style: { textTransform: 'uppercase' } }) }), _jsx(Form.Item, { name: "address", label: t('branches.address'), children: _jsx(Input.TextArea, { rows: 2 }) }), _jsx(Form.Item, { name: "city", label: t('branches.city'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "state", label: t('branches.state'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "pincode", label: t('branches.pincode'), rules: [{ pattern: /^\d{6}$/, message: t('branches.pincodeInvalid') }], children: _jsx(Input, { maxLength: 6 }) }), _jsx(Form.Item, { name: "phone", label: t('branches.phone'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "email", label: t('branches.email'), rules: [{ type: 'email' }], children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "gstin", label: t('branches.gstin'), rules: [{ len: 15, message: t('branches.gstinInvalid') }], children: _jsx(Input, { maxLength: 15, style: { textTransform: 'uppercase' } }) }), _jsx(Form.Item, { name: "is_active", label: t('common.active'), valuePropName: "checked", children: _jsx(Switch, {}) })] }) })] }));
}
