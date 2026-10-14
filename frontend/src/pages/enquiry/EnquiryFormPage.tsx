// The PUBLIC enquiry form (no login): /enquiry. The clinic website links to it, or shows it in an iframe:
//   <iframe src="https://YOUR-APP-ADDRESS/enquiry" width="100%" height="760" style="border:0"></iframe>
// Anyone can fill it, so it only asks for the basics and nothing medical beyond "what is the problem about".
// SAFE TO EDIT: the wording is in src/i18n/*.json under "enquiry".
import { CheckCircleFilled } from '@ant-design/icons';
import { Alert, Button, Card, Checkbox, DatePicker, Form, Input, Result, Segmented, Select, Spin } from 'antd';
import axios from 'axios';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BrandLogo } from '../../branding/BrandLogo';
import { useBranding } from '../../branding/BrandingContext';
import { LANGUAGES, setLanguage } from '../../i18n';

type FormInfo = {
  enabled: boolean; clinic: string; has_logo?: boolean; phone?: string; multi_branch?: boolean;
  branches?: { id: string; name: string; city: string }[]; concerns?: string[];
};

export default function EnquiryFormPage() {
  const { t, i18n } = useTranslation();
  const { appName, logoUrl } = useBranding();
  const [info, setInfo] = useState<FormInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    axios.get<FormInfo>('/api/v1/public/enquiry-form/').then(({ data }) => setInfo(data)).catch(() => setInfo({ enabled: false, clinic: '' }));
  }, []);

  const submit = async (values: Record<string, unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await axios.post('/api/v1/public/enquiries/', {
        ...values,
        preferred_date: values.preferred_date ? (values.preferred_date as dayjs.Dayjs).format('YYYY-MM-DD') : null,
        language: i18n.language,
      });
      setSent(true);
    } catch (err) {
      const data = axios.isAxiosError(err) ? err.response?.data : null;
      const first = data && typeof data === 'object' ? Object.values(data as Record<string, unknown>).flat()[0] : null;
      setError(typeof first === 'string' ? first : t('enquiry.failed'));
    } finally {
      setBusy(false);
    }
  };

  if (!info) return <div style={{ display: 'flex', justifyContent: 'center', marginTop: '30vh' }}><Spin size="large" /></div>;

  return (
    <div className="enquiry-page">
      <div className="enquiry-head">
        {logoUrl ? <BrandLogo variant="mobile" /> : <b className="enquiry-name">{appName}</b>}
        <Segmented size="small" value={i18n.language} onChange={(v) => setLanguage(String(v))}
          options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))} />
      </div>
      <Card className="enquiry-card">
        {!info.enabled ? (
          <Result status="info" title={t('enquiry.closedTitle')} subTitle={t('enquiry.closedHelp')} />
        ) : sent ? (
          <Result icon={<CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} />} title={t('enquiry.thanksTitle')}
            subTitle={t('enquiry.thanksHelp')} extra={info.phone ? <div className="cell-sub">{t('enquiry.callUs', { phone: info.phone })}</div> : null} />
        ) : (
          <>
            <h1 className="enquiry-title">{t('enquiry.title')}</h1>
            <div className="cell-sub" style={{ marginBottom: 16 }}>{t('enquiry.subtitle', { clinic: info.clinic })}</div>
            {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}
            <Form form={form} layout="vertical" onFinish={submit} requiredMark={false} initialValues={{ preferred_time: 'any' }}>
              <Form.Item name="name" label={t('enquiry.name')} rules={[{ required: true, message: t('common.required') }]}>
                <Input autoComplete="name" maxLength={120} />
              </Form.Item>
              <Form.Item name="phone" label={t('enquiry.phone')} rules={[{ required: true, message: t('common.required') },
                { pattern: /^(\+?91)?[\s-]?[6-9]\d{4}[\s-]?\d{5}$/, message: t('enquiry.phoneInvalid') }]}>
                <Input autoComplete="tel" inputMode="tel" maxLength={16} prefix="+91" />
              </Form.Item>
              <Form.Item name="email" label={t('enquiry.email')} rules={[{ type: 'email', message: t('enquiry.emailInvalid') }]}>
                <Input autoComplete="email" maxLength={100} />
              </Form.Item>
              {(info.branches?.length ?? 0) > 1 && (
                <Form.Item name="branch" label={t('enquiry.branch')}>
                  <Select allowClear options={info.branches!.map((b) => ({ value: b.id, label: `${b.name}${b.city ? ` · ${b.city}` : ''}` }))} />
                </Form.Item>
              )}
              <Form.Item name="concern" label={t('enquiry.concern')}>
                <Select allowClear showSearch options={(info.concerns ?? []).map((c) => ({ value: c, label: c }))} />
              </Form.Item>
              <Form.Item name="message" label={t('enquiry.message')} extra={t('enquiry.messageHelp')}>
                <Input.TextArea rows={3} maxLength={1000} showCount />
              </Form.Item>
              <div className="enquiry-row">
                <Form.Item name="preferred_date" label={t('enquiry.preferredDate')} style={{ flex: 1 }}>
                  <DatePicker style={{ width: '100%' }} format="DD-MM-YYYY" disabledDate={(d) => d.isBefore(dayjs(), 'day')} />
                </Form.Item>
                <Form.Item name="preferred_time" label={t('enquiry.preferredTime')} style={{ flex: 1 }}>
                  <Select options={[
                    { value: 'any', label: t('enquiry.time.any') }, { value: 'morning', label: t('enquiry.time.morning') },
                    { value: 'evening', label: t('enquiry.time.evening') }]} />
                </Form.Item>
              </div>
              {/* Hidden from people: only bots fill it */}
              <Form.Item name="website" className="enquiry-trap" label="Website"><Input tabIndex={-1} autoComplete="off" /></Form.Item>
              <Form.Item name="consent_contact" valuePropName="checked"
                rules={[{ validator: (_, v) => (v ? Promise.resolve() : Promise.reject(new Error(t('enquiry.consentRequired')))) }]}>
                <Checkbox>{t('enquiry.consent', { clinic: info.clinic })}</Checkbox>
              </Form.Item>
              <Button type="primary" htmlType="submit" size="large" block loading={busy}>{t('enquiry.send')}</Button>
              <div className="cell-sub" style={{ marginTop: 10 }}>{t('enquiry.privacy')}</div>
            </Form>
          </>
        )}
      </Card>
    </div>
  );
}
