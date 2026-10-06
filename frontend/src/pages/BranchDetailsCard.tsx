// Details of the current branch that are printed on bills: address, phone, GSTIN, drug licence, UPI ID.
import { App, Button, Card, Col, Form, Input, Row } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { Branch } from '../api/types';
import { useAuth } from '../auth/AuthContext';

export function BranchDetailsCard() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { branch, can } = useAuth();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const canEdit = can('branches.manage');

  useEffect(() => {
    if (!branch) return;
    api.get<Branch>(`/branches/${branch.id}/`).then(({ data }) => form.setFieldsValue(data)).catch(() => undefined);
  }, [branch, form]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.patch(`/branches/${branch!.id}/`, values);
      message.success(t('common.saved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title={t('settings.branchDetails', { branch: branch?.name })}>
      <div className="form-help">{t('settings.branchDetailsHelp')}</div>
      <Form form={form} layout="vertical" requiredMark={false} disabled={!canEdit}>
        <Row gutter={12}>
          <Col xs={24} md={12}><Form.Item name="name" label={t('settings.branchName')} rules={[{ required: true, message: t('common.required') }]}><Input maxLength={200} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="phone" label={t('branches.phone')}><Input maxLength={20} /></Form.Item></Col>
          <Col span={24}><Form.Item name="address" label={t('branches.address')}><Input.TextArea autoSize={{ minRows: 2, maxRows: 3 }} /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="city" label={t('branches.city')}><Input maxLength={100} /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="state" label={t('pharmacy.state')}><Input maxLength={100} /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="pincode" label={t('branches.pincode')}><Input maxLength={10} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="gstin" label={t('branches.gstin')}><Input maxLength={15} style={{ textTransform: 'uppercase' }} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="drug_licence_no" label={t('pharmacy.drugLicence')}><Input maxLength={100} /></Form.Item></Col>
          <Col span={24}>
            <Form.Item name="letterhead_footer" label={t('settings.letterheadFooter')} extra={t('settings.letterheadFooterHelp')}>
              <Input maxLength={300} placeholder={t('settings.letterheadFooterPlaceholder')} />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="upi_vpa" label={t('settings.upiId')} extra={t('settings.upiIdHelp')}><Input maxLength={100} placeholder="clinic@okbank" /></Form.Item>
          </Col>
        </Row>
        {canEdit && <Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>}
      </Form>
    </Card>
  );
}
