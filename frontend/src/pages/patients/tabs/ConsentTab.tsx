// Purpose-wise consent (DPDP): current status, give / withdraw, and full history.
import { CheckCircleFilled, CloseCircleFilled, ExclamationCircleFilled, MinusCircleOutlined } from '@ant-design/icons';
import { App, Button, Card, Col, Form, Input, Modal, Row, Segmented, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import { pickLang } from '../../../api/masters';
import type { ConsentPurpose, ConsentRecord, ConsentStatus, Patient } from '../../../api/types';
import { useAuth } from '../../../auth/AuthContext';
import { LANGUAGES } from '../../../i18n';

export function ConsentTab({ patient }: { patient: Patient }) {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [status, setStatus] = useState<ConsentStatus[]>([]);
  const [history, setHistory] = useState<ConsentRecord[]>([]);
  const [dialog, setDialog] = useState<{ purpose: ConsentPurpose; granted: boolean } | null>(null);
  const [language, setLanguage] = useState(patient.preferred_language || 'gu');
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const canRecord = can('patients.create') || can('patients.edit');

  const load = useCallback(async () => {
    try {
      const [s, h] = await Promise.all([
        api.get<ConsentStatus[]>('/patient-consents/status/', { params: { patient: patient.id } }),
        api.get<ConsentRecord[]>('/patient-consents/', { params: { patient: patient.id } }),
      ]);
      setStatus(s.data);
      setHistory(h.data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  }, [patient.id, message, t]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!dialog) return;
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/patient-consents/', {
        patient: patient.id, purpose: dialog.purpose.id, granted: dialog.granted, language, ...values,
      });
      message.success(t('consent.recorded'));
      setDialog(null);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const statusBadge = (row: ConsentStatus) => {
    if (row.granted === null) return <Tag icon={<MinusCircleOutlined />}>{t('consent.notAsked')}</Tag>;
    if (row.outdated) return <Tag color="orange" icon={<ExclamationCircleFilled />}>{t('consent.outdated')}</Tag>;
    return row.granted
      ? <Tag color="green" icon={<CheckCircleFilled />}>{t('consent.given')}</Tag>
      : <Tag color="red" icon={<CloseCircleFilled />}>{t('consent.withdrawn')}</Tag>;
  };

  return (
    <>
      <Typography.Paragraph type="secondary">{t('consent.help')}</Typography.Paragraph>
      <Row gutter={[16, 16]}>
        {status.map((row) => (
          <Col xs={24} md={12} key={row.purpose.code}>
            <Card size="small" className="consent-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>
                    {pickLang(row.purpose, 'title', i18n.language)}
                    {row.purpose.is_required && <Tag color="volcano" style={{ marginLeft: 8 }}>{t('consent.required')}</Tag>}
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {row.since ? t('consent.since', { date: dayjs(row.since).format('DD-MM-YYYY') }) : ''}
                  </Typography.Text>
                </div>
                {statusBadge(row)}
              </div>
              {canRecord && (
                <Space style={{ marginTop: 12 }}>
                  {row.granted !== true || row.outdated ? (
                    <Button size="small" type="primary" onClick={() => { form.resetFields(); setDialog({ purpose: row.purpose, granted: true }); }}>
                      {t('consent.give')}
                    </Button>
                  ) : null}
                  {row.granted === true && (
                    <Button size="small" danger onClick={() => { form.resetFields(); setDialog({ purpose: row.purpose, granted: false }); }}>
                      {t('consent.withdraw')}
                    </Button>
                  )}
                </Space>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <Typography.Title level={5} style={{ marginTop: 28 }}>{t('consent.history')}</Typography.Title>
      <Table<ConsentRecord>
        rowKey="id"
        size="small"
        dataSource={history}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        scroll={{ x: true }}
        columns={[
          { title: t('audit.when'), dataIndex: 'created_at', render: (v: string) => dayjs(v).format('DD-MM-YYYY HH:mm') },
          { title: t('consent.purpose'), dataIndex: 'purpose_title' },
          {
            title: t('consent.decision'), dataIndex: 'granted',
            render: (g: boolean) => (g ? <Tag color="green">{t('consent.given')}</Tag> : <Tag color="red">{t('consent.notGiven')}</Tag>),
          },
          { title: t('patients.consentMethod'), dataIndex: 'method', render: (m: string) => t(`patients.consentMethods.${m}`) },
          { title: t('layout.language'), dataIndex: 'language', render: (l: string) => LANGUAGES.find((x) => x.code === l)?.label },
          { title: t('consent.version'), dataIndex: 'purpose_version', width: 80 },
          { title: t('vitals.by'), key: 'by', render: (_: unknown, r: ConsentRecord) => `${r.recorded_by_name} · ${r.branch_name}` },
          { title: t('patients.consentGivenBy'), dataIndex: 'given_by' },
        ]}
      />

      <Modal
        open={!!dialog}
        title={dialog ? `${dialog.granted ? t('consent.give') : t('consent.withdraw')}: ${pickLang(dialog.purpose, 'title', i18n.language)}` : ''}
        onCancel={() => setDialog(null)}
        onOk={save}
        confirmLoading={saving}
        okText={dialog?.granted ? t('consent.confirmGive') : t('consent.confirmWithdraw')}
        okButtonProps={{ danger: dialog ? !dialog.granted : false }}
        cancelText={t('common.cancel')}
        width={620}
        destroyOnClose
      >
        {dialog && (
          <>
            <Segmented
              value={language}
              onChange={(v) => setLanguage(String(v))}
              options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))}
              style={{ marginBottom: 12 }}
            />
            <div className="consent-text consent-text-box">{pickLang(dialog.purpose, 'description', language)}</div>
            {!dialog.granted && dialog.purpose.is_required && (
              <Typography.Paragraph type="danger" style={{ marginTop: 12 }}>{t('consent.withdrawRequiredWarning')}</Typography.Paragraph>
            )}
            <Form form={form} layout="vertical" style={{ marginTop: 16 }} initialValues={{ method: 'signed_form' }}>
              <Form.Item name="method" label={t('patients.consentMethod')}>
                <Select options={['signed_form', 'verbal', 'on_screen', 'guardian'].map((m) => ({ value: m, label: t(`patients.consentMethods.${m}`) }))} />
              </Form.Item>
              <Form.Item name="given_by" label={t('patients.consentGivenBy')}><Input /></Form.Item>
              <Form.Item name="notes" label={t('rooms.notes')}><Input /></Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </>
  );
}
