// Settings: clinic details and module on/off switches for the current branch.
import { App, Button, Card, Col, Form, Input, List, Row, Select, Switch, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { FeatureFlag } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { LANGUAGES } from '../i18n';
import { BranchDetailsCard } from './BranchDetailsCard';

export default function SettingsPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { branch, me } = useAuth();
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    try {
      const [org, features] = await Promise.all([api.get('/organization/'), api.get<FeatureFlag[]>('/feature-flags/')]);
      form.setFieldsValue(org.data);
      setFlags(features.data);
    } catch (err) {
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
      // The branch switch changes the menu and top bar: reload the app to apply it.
      if (me && values.multi_branch !== undefined && values.multi_branch !== me.organization?.multi_branch) {
        window.location.reload();
      }
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (flag: FeatureFlag, enabled: boolean) => {
    try {
      await api.patch(`/feature-flags/${flag.code}/`, { enabled });
      setFlags((list) => list.map((f) => (f.code === flag.code ? { ...f, enabled } : f)));
      message.success(t('common.saved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <>
      <div className="page-toolbar"><Typography.Title level={3} style={{ margin: 0 }}>{t('settings.title')}</Typography.Title></div>
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={12}>
          <Card title={t('settings.clinic')}>
            <Form form={form} layout="vertical">
              <Form.Item name="name" label={t('settings.clinicName')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
              <Form.Item name="short_name" label={t('settings.shortName')}><Input /></Form.Item>
              <Form.Item name="legal_name" label={t('settings.legalName')}><Input /></Form.Item>
              <Form.Item name="gstin" label={t('branches.gstin')}><Input maxLength={15} /></Form.Item>
              <Form.Item name="phone" label={t('branches.phone')}><Input /></Form.Item>
              <Form.Item name="email" label={t('branches.email')} rules={[{ type: 'email' }]}><Input /></Form.Item>
              <Form.Item name="address" label={t('branches.address')}><Input.TextArea rows={2} /></Form.Item>
              <Form.Item name="uhid_prefix" label={t('settings.uhidPrefix')} extra={t('settings.uhidPrefixHelp')}
                rules={[{ required: true, message: t('common.required') }, { pattern: /^[A-Za-z0-9]{1,6}$/, message: t('settings.uhidPrefixInvalid') }]}>
                <Input maxLength={6} style={{ textTransform: 'uppercase', width: 140 }} />
              </Form.Item>
              {me?.user.is_org_admin && (
                <Form.Item name="multi_branch" label={t('settings.multiBranch')} valuePropName="checked"
                  extra={t('settings.multiBranchHelp')}>
                  <Switch />
                </Form.Item>
              )}
              <Form.Item name="default_language" label={t('settings.defaultLanguage')}>
                <Select options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))} />
              </Form.Item>
              <Button type="primary" onClick={saveOrg} loading={saving}>{t('common.save')}</Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <BranchDetailsCard />
          <Card title={t('settings.features', { branch: branch?.name })} style={{ marginTop: 12 }}>
            <Typography.Paragraph type="secondary">{t('settings.featuresHelp')}</Typography.Paragraph>
            <List
              dataSource={flags}
              renderItem={(flag) => (
                <List.Item actions={[<Switch key="s" checked={flag.enabled} onChange={(v) => toggle(flag, v)} />]}>
                  {t(`features.${flag.code}`, { defaultValue: flag.label })}
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </>
  );
}
