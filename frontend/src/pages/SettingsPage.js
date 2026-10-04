import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Settings: clinic details and module on/off switches for the current branch.
import { App, Button, Card, Col, Form, Input, List, Row, Select, Switch, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { LANGUAGES } from '../i18n';
export default function SettingsPage() {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { branch } = useAuth();
    const [flags, setFlags] = useState([]);
    const [saving, setSaving] = useState(false);
    const [form] = Form.useForm();
    const load = useCallback(async () => {
        try {
            const [org, features] = await Promise.all([api.get('/organization/'), api.get('/feature-flags/')]);
            form.setFieldsValue(org.data);
            setFlags(features.data);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
    }, [form, message, t]);
    useEffect(() => {
        load();
    }, [load]);
    const saveOrg = async () => {
        const values = await form.validateFields();
        setSaving(true);
        try {
            await api.patch('/organization/', values);
            message.success(t('common.saved'));
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    const toggle = async (flag, enabled) => {
        try {
            await api.patch(`/feature-flags/${flag.code}/`, { enabled });
            setFlags((list) => list.map((f) => (f.code === flag.code ? { ...f, enabled } : f)));
            message.success(t('common.saved'));
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
    };
    return (_jsxs(_Fragment, { children: [_jsx(Typography.Title, { level: 3, children: t('settings.title') }), _jsxs(Row, { gutter: [16, 16], children: [_jsx(Col, { xs: 24, lg: 12, children: _jsx(Card, { title: t('settings.clinic'), children: _jsxs(Form, { form: form, layout: "vertical", children: [_jsx(Form.Item, { name: "name", label: t('settings.clinicName'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "short_name", label: t('settings.shortName'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "legal_name", label: t('settings.legalName'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "gstin", label: t('branches.gstin'), children: _jsx(Input, { maxLength: 15 }) }), _jsx(Form.Item, { name: "phone", label: t('branches.phone'), children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "email", label: t('branches.email'), rules: [{ type: 'email' }], children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "address", label: t('branches.address'), children: _jsx(Input.TextArea, { rows: 2 }) }), _jsx(Form.Item, { name: "uhid_prefix", label: t('settings.uhidPrefix'), extra: t('settings.uhidPrefixHelp'), rules: [{ required: true, message: t('common.required') }, { pattern: /^[A-Za-z0-9]{1,6}$/, message: t('settings.uhidPrefixInvalid') }], children: _jsx(Input, { maxLength: 6, style: { textTransform: 'uppercase', width: 140 } }) }), _jsx(Form.Item, { name: "default_language", label: t('settings.defaultLanguage'), children: _jsx(Select, { options: LANGUAGES.map((l) => ({ value: l.code, label: l.label })) }) }), _jsx(Button, { type: "primary", onClick: saveOrg, loading: saving, children: t('common.save') })] }) }) }), _jsx(Col, { xs: 24, lg: 12, children: _jsxs(Card, { title: t('settings.features', { branch: branch?.name }), children: [_jsx(Typography.Paragraph, { type: "secondary", children: t('settings.featuresHelp') }), _jsx(List, { dataSource: flags, renderItem: (flag) => (_jsx(List.Item, { actions: [_jsx(Switch, { checked: flag.enabled, onChange: (v) => toggle(flag, v) }, "s")], children: t(`features.${flag.code}`, { defaultValue: flag.label }) })) })] }) })] })] }));
}
