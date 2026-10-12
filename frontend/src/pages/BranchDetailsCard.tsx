// Details of the current branch that are printed on bills: address, phone, GSTIN, drug licence, UPI ID,
// and the pre-printed prescription pad (blank space at the top / bottom of prescriptions).
import { App, Button, Card, Col, Form, Input, InputNumber, Row, Segmented, Switch } from 'antd';
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
  const onPad: boolean = Form.useWatch('print_on_pad', form) ?? false;
  const design: string = Form.useWatch('prescription_design', form) ?? 'standard';

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
        {/* Pre-printed prescription pad: the paper already has the logo, clinic, doctor and reg. no. at the top */}
        <div className="section-title" style={{ marginTop: 4 }}>{t('settings.designTitle')}</div>
        <Form.Item name="prescription_design" extra={t('settings.designHelp')} style={{ marginBottom: 8 }}>
          <Segmented options={(['standard', 'ayurveda_pad'] as const).map((v) => ({ value: v, label: t(`settings.design.${v}`) }))} />
        </Form.Item>
        {design === 'ayurveda_pad' && (
          <Row gutter={12}>
            <Col xs={24} md={12}><Form.Item name="print_subtitle" label={t('settings.printSubtitle')}><Input maxLength={200} placeholder={t('settings.printSubtitlePlaceholder')} /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="print_closed_note" label={t('settings.printClosed')}><Input maxLength={100} placeholder={t('settings.printClosedPlaceholder')} /></Form.Item></Col>
            <Col span={24}><Form.Item name="print_services" label={t('settings.printServices')} extra={t('settings.printServicesHelp')}><Input maxLength={200} /></Form.Item></Col>
            <Col span={24}><Form.Item name="print_quote" label={t('settings.printQuote')}><Input maxLength={300} /></Form.Item></Col>
          </Row>
        )}
        <div className="section-title" style={{ marginTop: 4 }}>{t('settings.padTitle')}</div>
        <Form.Item name="print_on_pad" valuePropName="checked" extra={t('settings.padHelp')} style={{ marginBottom: 8 }}>
          <Switch checkedChildren={t('settings.padOn')} unCheckedChildren={t('settings.padOff')} />
        </Form.Item>
        <Row gutter={12}>
          <Col xs={12} md={8}>
            <Form.Item name="pad_top_mm" label={t('settings.padTop')}>
              <InputNumber min={0} max={120} addonAfter="mm" style={{ width: '100%' }} disabled={!onPad} />
            </Form.Item>
          </Col>
          <Col xs={12} md={8}>
            <Form.Item name="pad_bottom_mm" label={t('settings.padBottom')}>
              <InputNumber min={0} max={80} addonAfter="mm" style={{ width: '100%' }} disabled={!onPad} />
            </Form.Item>
          </Col>
        </Row>
        {canEdit && <Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>}
      </Form>
    </Card>
  );
}
