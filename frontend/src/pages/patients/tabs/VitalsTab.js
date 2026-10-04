import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Vitals history and "Record vitals". BMI is calculated by the server.
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Table, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import { useAuth } from '../../../auth/AuthContext';
export function bmiCategory(bmi) {
    if (bmi < 18.5)
        return { key: 'under', color: '#d48a0c' };
    if (bmi < 23)
        return { key: 'normal', color: '#2f8a57' }; // Asian cut-offs
    if (bmi < 25)
        return { key: 'over', color: '#d48a0c' };
    return { key: 'obese', color: '#c2412d' };
}
export function VitalsTab({ patientId }) {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can } = useAuth();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const weight = Form.useWatch('weight_kg', form);
    const height = Form.useWatch('height_cm', form);
    const liveBmi = weight && height ? Math.round((weight / ((height / 100) ** 2)) * 10) / 10 : null;
    const load = useCallback(async () => {
        setLoading(true);
        try {
            const { data } = await api.get('/patient-vitals/', { params: { patient: patientId } });
            setRows(data);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
        finally {
            setLoading(false);
        }
    }, [patientId, message, t]);
    useEffect(() => {
        load();
    }, [load]);
    const save = async () => {
        const values = await form.validateFields();
        setSaving(true);
        try {
            await api.post('/patient-vitals/', { ...values, patient: patientId });
            message.success(t('common.saved'));
            setOpen(false);
            load();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    const latest = rows[0];
    const tiles = latest
        ? [
            { label: t('vitals.bp'), value: latest.bp_systolic ? `${latest.bp_systolic}/${latest.bp_diastolic ?? '—'}` : '—', unit: 'mmHg' },
            { label: t('vitals.pulse'), value: latest.pulse ?? '—', unit: '/min' },
            { label: t('vitals.weight'), value: latest.weight_kg ?? '—', unit: 'kg' },
            { label: 'BMI', value: latest.bmi ?? '—', unit: latest.bmi ? t(`vitals.bmi.${bmiCategory(Number(latest.bmi)).key}`) : '' },
            { label: t('vitals.spo2'), value: latest.spo2 ?? '—', unit: '%' },
            { label: t('vitals.temperature'), value: latest.temperature_f ?? '—', unit: '°F' },
        ]
        : [];
    const num = (name, label, min, max, addon, step = 1) => (_jsx(Col, { xs: 12, md: 8, children: _jsx(Form.Item, { name: name, label: label, children: _jsx(InputNumber, { min: min, max: max, step: step, addonAfter: addon, style: { width: '100%' } }) }) }));
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", style: { marginBottom: 12 }, children: [_jsx(Typography.Text, { type: "secondary", children: latest ? t('vitals.latest', { date: dayjs(latest.recorded_at).format('DD-MM-YYYY HH:mm') }) : t('vitals.none') }), can('patients.vitals') && (_jsx(Button, { type: "primary", icon: _jsx(PlusOutlined, {}), onClick: () => { form.resetFields(); setOpen(true); }, children: t('vitals.record') }))] }), latest && (_jsx("div", { className: "vital-tiles", children: tiles.map((tile) => (_jsxs("div", { className: "vital-tile", children: [_jsx("div", { className: "vital-label", children: tile.label }), _jsx("div", { className: "vital-value", children: tile.value }), _jsx("div", { className: "vital-unit", children: tile.unit })] }, tile.label))) })), _jsx(Table, { rowKey: "id", size: "small", loading: loading, dataSource: rows, pagination: { pageSize: 10, hideOnSinglePage: true }, scroll: { x: true }, columns: [
                    { title: t('vitals.when'), dataIndex: 'recorded_at', render: (v) => dayjs(v).format('DD-MM-YYYY HH:mm') },
                    { title: t('vitals.bp'), key: 'bp', render: (_, v) => (v.bp_systolic ? `${v.bp_systolic}/${v.bp_diastolic ?? '—'}` : '—') },
                    { title: t('vitals.pulse'), dataIndex: 'pulse' },
                    { title: t('vitals.weight'), dataIndex: 'weight_kg' },
                    { title: t('vitals.height'), dataIndex: 'height_cm' },
                    {
                        title: 'BMI', dataIndex: 'bmi',
                        render: (b) => b ? _jsx("span", { style: { color: bmiCategory(Number(b)).color, fontWeight: 600 }, children: b }) : '—',
                    },
                    { title: t('vitals.spo2'), dataIndex: 'spo2' },
                    { title: t('vitals.temperature'), dataIndex: 'temperature_f' },
                    { title: t('vitals.by'), key: 'by', render: (_, v) => `${v.recorded_by_name} · ${v.branch_name}` },
                    ...(can('patients.vitals') || can('emr.edit') ? [{
                            title: '', key: 'del', width: 50,
                            render: (_, v) => (_jsx(Popconfirm, { title: t('vitals.confirmRemove'), okText: t('common.yes'), cancelText: t('common.no'), onConfirm: () => api.delete(`/patient-vitals/${v.id}/`).then(load), children: _jsx(Button, { size: "small", type: "text", danger: true, icon: _jsx(DeleteOutlined, {}), "aria-label": t('common.remove') }) })),
                        }] : []),
                ] }), _jsx(Modal, { open: open, title: t('vitals.record'), onCancel: () => setOpen(false), onOk: save, confirmLoading: saving, okText: t('common.save'), cancelText: t('common.cancel'), width: 640, destroyOnClose: true, children: _jsx(Form, { form: form, layout: "vertical", children: _jsxs(Row, { gutter: 12, children: [num('bp_systolic', t('vitals.systolic'), 50, 260, 'mmHg'), num('bp_diastolic', t('vitals.diastolic'), 30, 160, 'mmHg'), num('pulse', t('vitals.pulse'), 25, 250, '/min'), num('weight_kg', t('vitals.weight'), 0.5, 300, 'kg', 0.1), num('height_cm', t('vitals.height'), 30, 250, 'cm', 0.5), _jsx(Col, { xs: 12, md: 8, children: _jsx(Form.Item, { label: "BMI", children: _jsxs("div", { className: "bmi-live", style: { color: liveBmi ? bmiCategory(liveBmi).color : undefined }, children: [liveBmi ?? '—', " ", liveBmi ? _jsx("small", { children: t(`vitals.bmi.${bmiCategory(liveBmi).key}`) }) : null] }) }) }), num('spo2', t('vitals.spo2'), 50, 100, '%'), num('temperature_f', t('vitals.temperature'), 90, 110, '°F', 0.1), num('respiratory_rate', t('vitals.respiratory'), 5, 60, '/min'), _jsx(Col, { span: 24, children: _jsx(Form.Item, { name: "notes", label: t('rooms.notes'), children: _jsx(Input, {}) }) })] }) }) })] }));
}
