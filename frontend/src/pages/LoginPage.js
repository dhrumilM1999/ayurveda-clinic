import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Login screen: username + password, then an OTP for doctors and admins.
import { ArrowLeftOutlined, LockOutlined, SafetyOutlined, UserOutlined } from '@ant-design/icons';
import { Alert, Button, Form, Input, Segmented } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { LeafArt } from '../components/LeafArt';
import { clinicConfig } from '../config/clinic';
import { LANGUAGES, setLanguage } from '../i18n';
export default function LoginPage() {
    const { t, i18n } = useTranslation();
    const { completeLogin, logoutReason } = useAuth();
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [otpStep, setOtpStep] = useState(null);
    const submitPassword = async (values) => {
        setBusy(true);
        setError(null);
        try {
            const { data } = await api.post('/auth/login/', values);
            if (data.otp_required) {
                setOtpStep(data);
            }
            else {
                await completeLogin(data.access, data.refresh);
            }
        }
        catch (err) {
            setError(errorMessage(err, t('login.failed')));
        }
        finally {
            setBusy(false);
        }
    };
    const submitOtp = async (values) => {
        if (!otpStep)
            return;
        setBusy(true);
        setError(null);
        try {
            const { data } = await api.post('/auth/verify-otp/', { challenge_id: otpStep.challenge_id, code: values.code });
            await completeLogin(data.access, data.refresh);
        }
        catch (err) {
            setError(errorMessage(err, t('login.otpFailed')));
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs("div", { className: "login-page", children: [_jsxs("section", { className: "login-art", style: { color: '#fff' }, children: [_jsxs("div", { className: "login-art-brand", children: [_jsx("img", { src: clinicConfig.logoPath, alt: "" }), clinicConfig.appName] }), _jsx("div", { className: "login-art-quote", children: t('login.quote') }), _jsx("div", { className: "login-art-foot", children: t('login.footer') }), _jsx(LeafArt, { className: "login-art-leaf" })] }), _jsx("section", { className: "login-form-side", children: _jsxs("div", { className: "login-form", children: [_jsxs("div", { className: "login-mobile-brand", children: [_jsx("img", { src: clinicConfig.logoPath, alt: "", width: 36, height: 36 }), clinicConfig.appName] }), !otpStep ? (_jsxs(_Fragment, { children: [_jsx("h1", { className: "login-title", children: t('login.welcomeBack') }), _jsx("div", { className: "login-sub", children: t('login.signInHelp') })] })) : (_jsxs(_Fragment, { children: [_jsx("h1", { className: "login-title", children: t('login.otpTitle') }), _jsx("div", { className: "login-sub", children: t('login.otpSent', { phone: otpStep.phone_hint || '—' }) })] })), logoutReason && _jsx(Alert, { type: "info", showIcon: true, message: logoutReason, style: { marginBottom: 20 } }), error && _jsx(Alert, { type: "error", showIcon: true, message: error, style: { marginBottom: 20 } }), !otpStep ? (_jsxs(Form, { layout: "vertical", onFinish: submitPassword, requiredMark: false, size: "large", children: [_jsx(Form.Item, { name: "username", label: t('login.username'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, { prefix: _jsx(UserOutlined, { style: { opacity: 0.45 } }), autoComplete: "username", autoFocus: true }) }), _jsx(Form.Item, { name: "password", label: t('login.password'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input.Password, { prefix: _jsx(LockOutlined, { style: { opacity: 0.45 } }), autoComplete: "current-password" }) }), _jsx(Button, { type: "primary", htmlType: "submit", block: true, loading: busy, style: { marginTop: 8 }, children: t('login.submit') })] })) : (_jsxs(Form, { layout: "vertical", onFinish: submitOtp, requiredMark: false, size: "large", children: [otpStep.dev_otp && (_jsx(Alert, { type: "warning", showIcon: true, style: { marginBottom: 20 }, message: t('login.devOtp', { code: otpStep.dev_otp }) })), _jsx(Form.Item, { name: "code", label: t('login.otp'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, { className: "otp-input", prefix: _jsx(SafetyOutlined, { style: { opacity: 0.45 } }), inputMode: "numeric", autoComplete: "one-time-code", maxLength: 6, autoFocus: true }) }), _jsx(Button, { type: "primary", htmlType: "submit", block: true, loading: busy, children: t('login.verify') }), _jsx(Button, { type: "text", block: true, icon: _jsx(ArrowLeftOutlined, {}), style: { marginTop: 8 }, onClick: () => { setOtpStep(null); setError(null); }, children: t('login.back') })] })), _jsx("div", { style: { marginTop: 32, display: 'flex', justifyContent: 'center' }, children: _jsx(Segmented, { value: i18n.language, onChange: (value) => setLanguage(String(value)), options: LANGUAGES.map((l) => ({ value: l.code, label: l.label })) }) })] }) })] }));
}
