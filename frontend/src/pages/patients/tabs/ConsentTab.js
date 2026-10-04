import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Purpose-wise consent (DPDP): current status, give / withdraw, and full history.
import { CheckCircleFilled, CloseCircleFilled, ExclamationCircleFilled, MinusCircleOutlined } from '@ant-design/icons';
import { App, Button, Card, Col, Form, Input, Modal, Row, Segmented, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import { pickLang } from '../../../api/masters';
import { useAuth } from '../../../auth/AuthContext';
import { LANGUAGES } from '../../../i18n';
export function ConsentTab({ patient }) {
    const { t, i18n } = useTranslation();
    const { message } = App.useApp();
    const { can } = useAuth();
    const [status, setStatus] = useState([]);
    const [history, setHistory] = useState([]);
    const [dialog, setDialog] = useState(null);
    const [language, setLanguage] = useState(patient.preferred_language || 'gu');
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const canRecord = can('patients.create') || can('patients.edit');
    const load = useCallback(async () => {
        try {
            const [s, h] = await Promise.all([
                api.get('/patient-consents/status/', { params: { patient: patient.id } }),
                api.get('/patient-consents/', { params: { patient: patient.id } }),
            ]);
            setStatus(s.data);
            setHistory(h.data);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
    }, [patient.id, message, t]);
    useEffect(() => {
        load();
    }, [load]);
    const save = async () => {
        if (!dialog)
            return;
        const values = await form.validateFields();
        setSaving(true);
        try {
            await api.post('/patient-consents/', {
                patient: patient.id, purpose: dialog.purpose.id, granted: dialog.granted, language, ...values,
            });
            message.success(t('consent.recorded'));
            setDialog(null);
            load();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    const statusBadge = (row) => {
        if (row.granted === null)
            return _jsx(Tag, { icon: _jsx(MinusCircleOutlined, {}), children: t('consent.notAsked') });
        if (row.outdated)
            return _jsx(Tag, { color: "orange", icon: _jsx(ExclamationCircleFilled, {}), children: t('consent.outdated') });
        return row.granted
            ? _jsx(Tag, { color: "green", icon: _jsx(CheckCircleFilled, {}), children: t('consent.given') })
            : _jsx(Tag, { color: "red", icon: _jsx(CloseCircleFilled, {}), children: t('consent.withdrawn') });
    };
    return (_jsxs(_Fragment, { children: [_jsx(Typography.Paragraph, { type: "secondary", children: t('consent.help') }), _jsx(Row, { gutter: [16, 16], children: status.map((row) => (_jsx(Col, { xs: 24, md: 12, children: _jsxs(Card, { size: "small", className: "consent-card", children: [_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start' }, children: [_jsxs("div", { children: [_jsxs("div", { style: { fontWeight: 600 }, children: [pickLang(row.purpose, 'title', i18n.language), row.purpose.is_required && _jsx(Tag, { color: "volcano", style: { marginLeft: 8 }, children: t('consent.required') })] }), _jsx(Typography.Text, { type: "secondary", style: { fontSize: 12 }, children: row.since ? t('consent.since', { date: dayjs(row.since).format('DD-MM-YYYY') }) : '' })] }), statusBadge(row)] }), canRecord && (_jsxs(Space, { style: { marginTop: 12 }, children: [row.granted !== true || row.outdated ? (_jsx(Button, { size: "small", type: "primary", onClick: () => { form.resetFields(); setDialog({ purpose: row.purpose, granted: true }); }, children: t('consent.give') })) : null, row.granted === true && (_jsx(Button, { size: "small", danger: true, onClick: () => { form.resetFields(); setDialog({ purpose: row.purpose, granted: false }); }, children: t('consent.withdraw') }))] }))] }) }, row.purpose.code))) }), _jsx(Typography.Title, { level: 5, style: { marginTop: 28 }, children: t('consent.history') }), _jsx(Table, { rowKey: "id", size: "small", dataSource: history, pagination: { pageSize: 10, hideOnSinglePage: true }, scroll: { x: true }, columns: [
                    { title: t('audit.when'), dataIndex: 'created_at', render: (v) => dayjs(v).format('DD-MM-YYYY HH:mm') },
                    { title: t('consent.purpose'), dataIndex: 'purpose_title' },
                    {
                        title: t('consent.decision'), dataIndex: 'granted',
                        render: (g) => (g ? _jsx(Tag, { color: "green", children: t('consent.given') }) : _jsx(Tag, { color: "red", children: t('consent.notGiven') })),
                    },
                    { title: t('patients.consentMethod'), dataIndex: 'method', render: (m) => t(`patients.consentMethods.${m}`) },
                    { title: t('layout.language'), dataIndex: 'language', render: (l) => LANGUAGES.find((x) => x.code === l)?.label },
                    { title: t('consent.version'), dataIndex: 'purpose_version', width: 80 },
                    { title: t('vitals.by'), key: 'by', render: (_, r) => `${r.recorded_by_name} · ${r.branch_name}` },
                    { title: t('patients.consentGivenBy'), dataIndex: 'given_by' },
                ] }), _jsx(Modal, { open: !!dialog, title: dialog ? `${dialog.granted ? t('consent.give') : t('consent.withdraw')}: ${pickLang(dialog.purpose, 'title', i18n.language)}` : '', onCancel: () => setDialog(null), onOk: save, confirmLoading: saving, okText: dialog?.granted ? t('consent.confirmGive') : t('consent.confirmWithdraw'), okButtonProps: { danger: dialog ? !dialog.granted : false }, cancelText: t('common.cancel'), width: 620, destroyOnClose: true, children: dialog && (_jsxs(_Fragment, { children: [_jsx(Segmented, { value: language, onChange: (v) => setLanguage(String(v)), options: LANGUAGES.map((l) => ({ value: l.code, label: l.label })), style: { marginBottom: 12 } }), _jsx("div", { className: "consent-text consent-text-box", children: pickLang(dialog.purpose, 'description', language) }), !dialog.granted && dialog.purpose.is_required && (_jsx(Typography.Paragraph, { type: "danger", style: { marginTop: 12 }, children: t('consent.withdrawRequiredWarning') })), _jsxs(Form, { form: form, layout: "vertical", style: { marginTop: 16 }, initialValues: { method: 'signed_form' }, children: [_jsx(Form.Item, { name: "method", label: t('patients.consentMethod'), children: _jsx(Select, { options: ['signed_form', 'verbal', 'on_screen', 'guardian'].map((m) => ({ value: m, label: t(`patients.consentMethods.${m}`) })) }) }), _jsx(Form.Item, { name: "given_by", label: t('patients.consentGivenBy'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "notes", label: t('rooms.notes'), children: _jsx(Input, {}) })] })] })) })] }));
}
