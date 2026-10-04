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

interface OtpStep {
  challenge_id: string;
  phone_hint: string;
  dev_otp?: string;
}

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const { completeLogin, logoutReason } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [otpStep, setOtpStep] = useState<OtpStep | null>(null);

  const submitPassword = async (values: { username: string; password: string }) => {
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post('/auth/login/', values);
      if (data.otp_required) {
        setOtpStep(data);
      } else {
        await completeLogin(data.access, data.refresh);
      }
    } catch (err) {
      setError(errorMessage(err, t('login.failed')));
    } finally {
      setBusy(false);
    }
  };

  const submitOtp = async (values: { code: string }) => {
    if (!otpStep) return;
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post('/auth/verify-otp/', { challenge_id: otpStep.challenge_id, code: values.code });
      await completeLogin(data.access, data.refresh);
    } catch (err) {
      setError(errorMessage(err, t('login.otpFailed')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-art" style={{ color: '#fff' }}>
        <div className="login-art-brand">
          <img src={clinicConfig.logoPath} alt="" />
          {clinicConfig.appName}
        </div>
        <div className="login-art-quote">{t('login.quote')}</div>
        <div className="login-art-foot">{t('login.footer')}</div>
        <LeafArt className="login-art-leaf" />
      </section>

      <section className="login-form-side">
        <div className="login-form">
          <div className="login-mobile-brand">
            <img src={clinicConfig.logoPath} alt="" width={36} height={36} />
            {clinicConfig.appName}
          </div>

          {!otpStep ? (
            <>
              <h1 className="login-title">{t('login.welcomeBack')}</h1>
              <div className="login-sub">{t('login.signInHelp')}</div>
            </>
          ) : (
            <>
              <h1 className="login-title">{t('login.otpTitle')}</h1>
              <div className="login-sub">{t('login.otpSent', { phone: otpStep.phone_hint || '—' })}</div>
            </>
          )}

          {logoutReason && <Alert type="info" showIcon message={logoutReason} style={{ marginBottom: 20 }} />}
          {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 20 }} />}

          {!otpStep ? (
            <Form layout="vertical" onFinish={submitPassword} requiredMark={false} size="large">
              <Form.Item name="username" label={t('login.username')} rules={[{ required: true, message: t('common.required') }]}>
                <Input prefix={<UserOutlined style={{ opacity: 0.45 }} />} autoComplete="username" autoFocus />
              </Form.Item>
              <Form.Item name="password" label={t('login.password')} rules={[{ required: true, message: t('common.required') }]}>
                <Input.Password prefix={<LockOutlined style={{ opacity: 0.45 }} />} autoComplete="current-password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" block loading={busy} style={{ marginTop: 8 }}>
                {t('login.submit')}
              </Button>
            </Form>
          ) : (
            <Form layout="vertical" onFinish={submitOtp} requiredMark={false} size="large">
              {otpStep.dev_otp && (
                <Alert type="warning" showIcon style={{ marginBottom: 20 }} message={t('login.devOtp', { code: otpStep.dev_otp })} />
              )}
              <Form.Item name="code" label={t('login.otp')} rules={[{ required: true, message: t('common.required') }]}>
                <Input className="otp-input" prefix={<SafetyOutlined style={{ opacity: 0.45 }} />} inputMode="numeric"
                  autoComplete="one-time-code" maxLength={6} autoFocus />
              </Form.Item>
              <Button type="primary" htmlType="submit" block loading={busy}>{t('login.verify')}</Button>
              <Button type="text" block icon={<ArrowLeftOutlined />} style={{ marginTop: 8 }}
                onClick={() => { setOtpStep(null); setError(null); }}>
                {t('login.back')}
              </Button>
            </Form>
          )}

          <div style={{ marginTop: 32, display: 'flex', justifyContent: 'center' }}>
            <Segmented
              value={i18n.language}
              onChange={(value) => setLanguage(String(value))}
              options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
