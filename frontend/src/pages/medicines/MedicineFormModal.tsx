// Add or edit a medicine. Every saved change gets a new version (see "History").
// Extra fields follow Additional settings: product details, barcode, loose sale.
import { App, Checkbox, Col, Form, Input, InputNumber, Modal, Row, Segmented, Select, Switch } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { MasterRef, Medicine, MedicineKind, Page } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { MasterSelect } from '../../components/MasterSelect';
import { quickDosage } from '../../utils/dosage';
import { FLAGS } from './shared';

const MASTER_FIELDS = ['dosage_form', 'dose_unit', 'default_timing', 'default_anupana', 'category', 'pack_type'] as const;

export function MedicineFormModal({ medicine, onClose }: { medicine: Medicine | null; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const { hasFeature } = useAuth();
  const extra = hasFeature('medicine_extra_details');
  const barcode = hasFeature('pharmacy_barcode');
  const loose = hasFeature('pharmacy_loose_sale');
  const [saving, setSaving] = useState(false);
  const [classicals, setClassicals] = useState<{ value: string; label: string }[]>([]);
  const kind: MedicineKind = Form.useWatch('kind', form) ?? medicine?.kind ?? 'classical';

  useEffect(() => {
    if (medicine) {
      const values: Record<string, unknown> = { ...medicine };
      MASTER_FIELDS.forEach((f) => (values[f] = (medicine[f] as MasterRef | null)?.id));
      values.mrp = medicine.mrp === null ? undefined : Number(medicine.mrp);
      values.selling_price = medicine.selling_price === null ? undefined : Number(medicine.selling_price);
      values.units_per_pack = medicine.units_per_pack === null ? undefined : Number(medicine.units_per_pack);
      values.gst_rate = Number(medicine.gst_rate);
      form.setFieldsValue(values);
    } else {
      form.setFieldsValue({ kind: 'classical', gst_rate: 12, hsn_code: '3004' });
    }
  }, [medicine, form]);

  useEffect(() => {
    if (kind !== 'proprietary') return;
    api.get<Page<Medicine>>('/medicines/', { params: { kind: 'classical', page_size: 200 } })
      .then(({ data }) => setClassicals(data.results.map((m) => ({ value: m.id, label: m.name }))))
      .catch(() => setClassicals([]));
  }, [kind]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      // Hidden fields (switched off in Additional settings) are not sent, so their saved values stay
      const payload = {
        ...values, mrp: values.mrp ?? null, classical_equivalent: values.classical_equivalent ?? null,
        ...(extra ? { selling_price: values.selling_price ?? null } : {}),
        ...(loose ? { units_per_pack: values.units_per_pack ?? null } : {}),
      };
      if (medicine) await api.patch(`/medicines/${medicine.id}/`, payload);
      else await api.post('/medicines/', payload);
      message.success(t('common.saved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const required = [{ required: true, message: t('common.required') }];

  return (
    <Modal open width={820} title={medicine ? t('medicines.editTitle', { name: medicine.name }) : t('medicines.add')}
      onCancel={() => onClose(false)} onOk={save} okText={t('common.save')} cancelText={t('common.cancel')}
      confirmLoading={saving} keyboard={false} maskClosable={false} destroyOnHidden>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="kind" style={{ marginBottom: 12 }}>
          <Segmented options={[
            { value: 'classical', label: t('medicines.kinds.classical') },
            { value: 'proprietary', label: t('medicines.kinds.proprietary') },
          ]} />
        </Form.Item>
        <div className="form-help">{kind === 'classical' ? t('medicines.classicalHelp') : t('medicines.proprietaryHelp')}</div>

        <div className="section-title">{t('medicines.sections.name')}</div>
        <Row gutter={12}>
          <Col xs={24} md={12}>
            <Form.Item name="name" label={kind === 'classical' ? t('medicines.officialName') : t('medicines.brandName')} rules={required}>
              <Input maxLength={200} />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item name="dosage_form" label={t('medicines.form')}><MasterSelect category="dosage_form" /></Form.Item>
          </Col>
          {extra && (
            <>
              <Col xs={24} md={12}><Form.Item name="generic_name" label={t('medicines.genericName')}><Input maxLength={200} /></Form.Item></Col>
              <Col xs={24} md={12}><Form.Item name="category" label={t('medicines.category')}><MasterSelect category="product_category" /></Form.Item></Col>
            </>
          )}
          <Col xs={24} md={12}><Form.Item name="name_gu" label={t('medicines.nameGu')}><Input maxLength={200} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="name_hi" label={t('medicines.nameHi')}><Input maxLength={200} /></Form.Item></Col>
          <Col span={24}>
            <Form.Item name="synonyms" label={t('medicines.synonyms')} extra={t('medicines.synonymsHelp')}>
              <Input placeholder="Triphala, Three fruits, ત્રિફળા, त्रिफला" />
            </Form.Item>
          </Col>
        </Row>

        <div className="section-title">{t('medicines.sections.details')}</div>
        <Row gutter={12}>
          <Col span={24}><Form.Item name="composition" label={t('medicines.composition')}><Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} /></Form.Item></Col>
          {kind === 'classical' ? (
            <Col xs={24} md={12}>
              <Form.Item name="reference" label={t('medicines.reference')}><Input placeholder="AFI Part I, 4:12" maxLength={300} /></Form.Item>
            </Col>
          ) : (
            <>
              <Col xs={24} md={12}><Form.Item name="manufacturer" label={t('medicines.manufacturer')}><Input maxLength={200} /></Form.Item></Col>
              <Col xs={24} md={12}>
                <Form.Item name="classical_equivalent" label={t('medicines.classicalEquivalent')}>
                  <Select allowClear showSearch optionFilterProp="label" options={classicals} />
                </Form.Item>
              </Col>
            </>
          )}
          <Col xs={24} md={12}><Form.Item name="ayush_licence_no" label={t('medicines.licence')}><Input maxLength={60} /></Form.Item></Col>
          {barcode && <Col xs={24} md={12}><Form.Item name="barcode" label={t('medicines.barcode')} extra={t('medicines.barcodeHelp')}><Input maxLength={64} /></Form.Item></Col>}
        </Row>

        <div className="section-title">{t('medicines.sections.pack')}</div>
        <Row gutter={12}>
          {extra && <Col xs={12} md={6}><Form.Item name="pack_type" label={t('medicines.packType')}><MasterSelect category="pack_type" /></Form.Item></Col>}
          <Col xs={12} md={6}><Form.Item name="pack_size" label={t('medicines.packSize')}><Input placeholder="100 g, 60 tablets" maxLength={60} /></Form.Item></Col>
          {loose && (
            <>
              <Col xs={12} md={6}>
                <Form.Item name="units_per_pack" label={t('medicines.unitsPerPack')} extra={t('medicines.unitsPerPackHelp')}>
                  <InputNumber min={1} style={{ width: '100%' }} placeholder="60" />
                </Form.Item>
              </Col>
              <Col xs={12} md={6}>
                <Form.Item name="allow_loose" label={t('medicines.allowLoose')} valuePropName="checked" extra={t('medicines.allowLooseHelp')}>
                  <Switch />
                </Form.Item>
              </Col>
            </>
          )}
        </Row>

        <div className="section-title">{t('medicines.sections.dose')}</div>
        <Row gutter={12}>
          <Col xs={12} md={4}><Form.Item name="default_dose" label={t('medicines.dose')}><Input maxLength={20} placeholder="2" /></Form.Item></Col>
          <Col xs={12} md={5}><Form.Item name="dose_unit" label={t('medicines.unit')}><MasterSelect category="dose_unit" /></Form.Item></Col>
          <Col xs={12} md={5}><Form.Item name="default_frequency" label={t('medicines.frequency')} getValueFromEvent={(e) => quickDosage(e.target.value)}><Input maxLength={20} placeholder="1-0-1 / 101" /></Form.Item></Col>
          <Col xs={12} md={5}><Form.Item name="default_timing" label={t('medicines.timing')}><MasterSelect category="medicine_timing" /></Form.Item></Col>
          <Col xs={24} md={5}><Form.Item name="default_anupana" label={t('medicines.anupana')}><MasterSelect category="anupana" /></Form.Item></Col>
        </Row>

        <div className="section-title">{t('medicines.sections.price')}</div>
        <Row gutter={12}>
          <Col xs={12} md={6}>
            <Form.Item name="mrp" label={t('medicines.mrp')}><InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }} /></Form.Item>
          </Col>
          {extra && (
            <Col xs={12} md={6}>
              <Form.Item name="selling_price" label={t('medicines.sellingPrice')} extra={t('medicines.sellingPriceHelp')}>
                <InputNumber min={0} precision={2} prefix="₹" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          )}
          <Col xs={12} md={6}>
            <Form.Item name="gst_rate" label={t('medicines.gst')} extra={t('medicines.gstHelp')} rules={required}>
              <InputNumber min={0} max={40} precision={2} suffix="%" style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col xs={12} md={6}><Form.Item name="hsn_code" label={t('medicines.hsn')}><Input maxLength={10} /></Form.Item></Col>
        </Row>

        <div className="section-title">{t('medicines.sections.safety')}</div>
        <div className="check-grid">
          {FLAGS.map((f) => (
            <Form.Item key={f} name={f} valuePropName="checked" noStyle>
              <Checkbox>
                <b>{t(`medicines.flagLabel.${f}`)}</b>
                <div className="cell-sub">{t(`medicines.flagHelp.${f}`)}</div>
              </Checkbox>
            </Form.Item>
          ))}
        </div>
        <Form.Item name="safety_notes" label={t('medicines.safetyNotes')} style={{ marginTop: 12 }}>
          <Input maxLength={300} placeholder={t('medicines.safetyNotesPlaceholder')} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
