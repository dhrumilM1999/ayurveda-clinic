import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Rooms of the current branch, plus the room-type dropdown list.
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useList } from '../api/useList';
import { useAuth } from '../auth/AuthContext';
export default function RoomsPage() {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can, branch } = useAuth();
    const { rows, loading, reload, pagination } = useList('/rooms/');
    const [roomTypes, setRoomTypes] = useState([]);
    const [editing, setEditing] = useState(null);
    const [typesOpen, setTypesOpen] = useState(false);
    const [newType, setNewType] = useState('');
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const canManage = can('rooms.manage');
    const loadTypes = useCallback(async () => {
        const { data } = await api.get('/room-types/');
        setRoomTypes(data);
    }, []);
    useEffect(() => {
        loadTypes().catch(() => undefined);
    }, [loadTypes]);
    const open = (room) => {
        setEditing(room ?? {});
        form.setFieldsValue(room ?? { capacity: 1, is_active: true });
    };
    const save = async () => {
        const values = await form.validateFields();
        setSaving(true);
        try {
            if (editing?.id)
                await api.patch(`/rooms/${editing.id}/`, values);
            else
                await api.post('/rooms/', values);
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
    const remove = async (room) => {
        try {
            await api.delete(`/rooms/${room.id}/`);
            message.success(t('common.removed'));
            reload();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
    };
    const addType = async () => {
        if (!newType.trim())
            return;
        try {
            await api.post('/room-types/', { name: newType.trim(), sort_order: roomTypes.length });
            setNewType('');
            loadTypes();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
    };
    const toggleType = async (type) => {
        await api.patch(`/room-types/${type.id}/`, { is_active: !type.is_active });
        loadTypes();
    };
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('rooms.title', { branch: branch?.name }) }), canManage && (_jsxs(Space, { children: [_jsx(Button, { onClick: () => setTypesOpen(true), children: t('rooms.manageTypes') }), _jsx(Button, { type: "primary", icon: _jsx(PlusOutlined, {}), onClick: () => open(), children: t('rooms.add') })] }))] }), _jsx(Table, { rowKey: "id", loading: loading, dataSource: rows, pagination: pagination, scroll: { x: true }, columns: [
                    { title: t('rooms.name'), dataIndex: 'name' },
                    { title: t('rooms.type'), dataIndex: 'room_type_name' },
                    { title: t('rooms.capacity'), dataIndex: 'capacity', width: 100 },
                    { title: t('rooms.notes'), dataIndex: 'notes' },
                    {
                        title: t('common.status'), dataIndex: 'is_active',
                        render: (active) => active ? _jsx(Tag, { color: "green", children: t('common.active') }) : _jsx(Tag, { children: t('common.inactive') }),
                    },
                    ...(canManage ? [{
                            title: '', key: 'actions', width: 160,
                            render: (_, room) => (_jsxs(Space, { children: [_jsx(Button, { size: "small", onClick: () => open(room), children: t('common.edit') }), _jsx(Popconfirm, { title: t('rooms.confirmRemove'), onConfirm: () => remove(room), okText: t('common.yes'), cancelText: t('common.no'), children: _jsx(Button, { size: "small", danger: true, icon: _jsx(DeleteOutlined, {}), "aria-label": t('common.remove') }) })] })),
                        }] : []),
                ] }), _jsx(Modal, { open: !!editing, title: editing?.id ? t('rooms.edit') : t('rooms.add'), onCancel: () => setEditing(null), onOk: save, confirmLoading: saving, okText: t('common.save'), cancelText: t('common.cancel'), destroyOnClose: true, children: _jsxs(Form, { form: form, layout: "vertical", children: [_jsx(Form.Item, { name: "name", label: t('rooms.name'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "room_type", label: t('rooms.type'), children: _jsx(Select, { allowClear: true, options: roomTypes.filter((rt) => rt.is_active).map((rt) => ({ value: rt.id, label: rt.name })) }) }), _jsx(Form.Item, { name: "capacity", label: t('rooms.capacity'), children: _jsx(InputNumber, { min: 1, max: 100 }) }), _jsx(Form.Item, { name: "notes", label: t('rooms.notes'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "is_active", label: t('common.active'), valuePropName: "checked", children: _jsx(Switch, {}) })] }) }), _jsxs(Modal, { open: typesOpen, title: t('rooms.manageTypes'), onCancel: () => setTypesOpen(false), footer: null, children: [_jsxs(Space.Compact, { style: { width: '100%', marginBottom: 12 }, children: [_jsx(Input, { value: newType, onChange: (e) => setNewType(e.target.value), placeholder: t('rooms.newType'), onPressEnter: addType }), _jsx(Button, { type: "primary", onClick: addType, children: t('common.add') })] }), _jsx(Table, { rowKey: "id", size: "small", pagination: false, dataSource: roomTypes, columns: [
                            { title: t('rooms.type'), dataIndex: 'name' },
                            {
                                title: t('common.active'), dataIndex: 'is_active', width: 90,
                                render: (_, rt) => _jsx(Switch, { size: "small", checked: rt.is_active, onChange: () => toggleType(rt) }),
                            },
                        ] })] })] }));
}
