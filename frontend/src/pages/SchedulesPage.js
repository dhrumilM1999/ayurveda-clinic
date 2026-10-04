import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Doctor schedules for the current branch (which days and times each doctor sits here).
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, Tag, TimePicker, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];
export default function SchedulesPage() {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can, branch } = useAuth();
    const [rows, setRows] = useState([]);
    const [doctors, setDoctors] = useState([]);
    const [doctorFilter, setDoctorFilter] = useState();
    const [loading, setLoading] = useState(false);
    const [editing, setEditing] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const canManage = can('schedules.manage');
    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [schedules, docs] = await Promise.all([
                api.get('/doctor-schedules/', { params: { doctor: doctorFilter } }),
                api.get('/doctor-schedules/doctors/'),
            ]);
            setRows(schedules.data);
            setDoctors(docs.data);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
        finally {
            setLoading(false);
        }
    }, [doctorFilter, message, t]);
    useEffect(() => {
        load();
    }, [load]);
    const open = (s) => {
        setEditing(s ?? {});
        form.resetFields();
        form.setFieldsValue(s
            ? { ...s, start_time: dayjs(s.start_time, 'HH:mm:ss'), end_time: dayjs(s.end_time, 'HH:mm:ss') }
            : { slot_minutes: 15, is_active: true });
    };
    const save = async () => {
        const values = await form.validateFields();
        const payload = {
            ...values,
            start_time: values.start_time.format('HH:mm'),
            end_time: values.end_time.format('HH:mm'),
        };
        setSaving(true);
        try {
            if (editing?.id)
                await api.patch(`/doctor-schedules/${editing.id}/`, payload);
            else
                await api.post('/doctor-schedules/', payload);
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
    const remove = async (s) => {
        try {
            await api.delete(`/doctor-schedules/${s.id}/`);
            load();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
    };
    const time = (value) => value.slice(0, 5);
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('schedules.title', { branch: branch?.name }) }), _jsxs(Space, { children: [_jsx(Select, { allowClear: true, placeholder: t('schedules.allDoctors'), style: { width: 220 }, value: doctorFilter, onChange: setDoctorFilter, options: doctors.map((d) => ({ value: d.id, label: d.full_name })) }), canManage && _jsx(Button, { type: "primary", icon: _jsx(PlusOutlined, {}), onClick: () => open(), children: t('schedules.add') })] })] }), doctors.length === 0 && !loading && _jsx(Typography.Paragraph, { type: "secondary", children: t('schedules.noDoctors') }), _jsx(Table, { rowKey: "id", loading: loading, dataSource: rows, pagination: false, scroll: { x: true }, columns: [
                    { title: t('schedules.doctor'), dataIndex: 'doctor_name' },
                    { title: t('schedules.day'), dataIndex: 'weekday', render: (d) => t(`weekdays.${d}`) },
                    { title: t('schedules.time'), key: 'time', render: (_, s) => `${time(s.start_time)} – ${time(s.end_time)}` },
                    { title: t('schedules.slot'), dataIndex: 'slot_minutes', render: (m) => t('schedules.minutes', { n: m }) },
                    {
                        title: t('common.status'), dataIndex: 'is_active',
                        render: (active) => active ? _jsx(Tag, { color: "green", children: t('common.active') }) : _jsx(Tag, { children: t('common.inactive') }),
                    },
                    ...(canManage ? [{
                            title: '', key: 'actions', width: 140,
                            render: (_, s) => (_jsxs(Space, { children: [_jsx(Button, { size: "small", onClick: () => open(s), children: t('common.edit') }), _jsx(Popconfirm, { title: t('schedules.confirmRemove'), onConfirm: () => remove(s), okText: t('common.yes'), cancelText: t('common.no'), children: _jsx(Button, { size: "small", danger: true, icon: _jsx(DeleteOutlined, {}), "aria-label": t('common.remove') }) })] })),
                        }] : []),
                ] }), _jsx(Modal, { open: !!editing, title: editing?.id ? t('schedules.edit') : t('schedules.add'), onCancel: () => setEditing(null), onOk: save, confirmLoading: saving, okText: t('common.save'), cancelText: t('common.cancel'), destroyOnClose: true, children: _jsxs(Form, { form: form, layout: "vertical", children: [_jsx(Form.Item, { name: "doctor", label: t('schedules.doctor'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Select, { options: doctors.map((d) => ({ value: d.id, label: d.full_name })) }) }), _jsx(Form.Item, { name: "weekday", label: t('schedules.day'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Select, { options: WEEKDAYS.map((d) => ({ value: d, label: t(`weekdays.${d}`) })) }) }), _jsxs(Space, { wrap: true, children: [_jsx(Form.Item, { name: "start_time", label: t('schedules.start'), rules: [{ required: true, message: t('common.required') }], children: _jsx(TimePicker, { format: "HH:mm", minuteStep: 5 }) }), _jsx(Form.Item, { name: "end_time", label: t('schedules.end'), rules: [{ required: true, message: t('common.required') }], children: _jsx(TimePicker, { format: "HH:mm", minuteStep: 5 }) }), _jsx(Form.Item, { name: "slot_minutes", label: t('schedules.slot'), children: _jsx(InputNumber, { min: 5, max: 120, step: 5, addonAfter: t('schedules.min') }) })] }), _jsx(Form.Item, { name: "is_active", label: t('common.active'), valuePropName: "checked", children: _jsx(Switch, {}) })] }) })] }));
}
