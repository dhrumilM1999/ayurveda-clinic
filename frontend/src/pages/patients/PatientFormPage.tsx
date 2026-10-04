// Register a new patient, or edit one (/patients/:id/edit).
import { ArrowLeftOutlined, MinusCircleOutlined, PlusOutlined, UserSwitchOutlined } from '@ant-design/icons';
import {
  Alert, App, Button, Card, Checkbox, Col, DatePicker, Empty, Form, Input, InputNumber, Radio, Row, Select,
  Segmented, Skeleton, Space, Switch, Typography,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { pickLang, useMasterLabel, useMasters } from '../../api/masters';
import type { ConsentPurpose, DuplicatePatient, MasterRef, Patient } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { MasterSelect } from '../../components/MasterSelect';
import { PhotoPicker } from '../../components/PhotoPicker';
import { LANGUAGES } from '../../i18n';
import { genderAge } from './PatientsPage';

const MASTER_FIELDS = ['title', 'blood_group', 'marital_status', 'referral_source', 'emergency_relation'] as const;
const HISTORY_FIELDS = ['past_history', 'family_history', 'surgical_history', 'other_notes'] as const;
const idOf = (v: MasterRef | string | null | undefined) => (v && typeof v === 'object' ? v.id : v ?? undefined);

interface ConsentChoice {
  granted: boolean;
}

export default function PatientFormPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { can } = useAuth();
  const masterLabel = useMasterLabel();
  const [form] = Form.useForm();
  const conditionsMaster = useMasters('medical_condition');

  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [existingPhotoUrl, setExistingPhotoUrl] = useState<string | null>(null);
  const [ageMode, setAgeMode] = useState<'dob' | 'age'>('age');
  const [duplicates, setDuplicates] = useState<DuplicatePatient[]>([]);
  const [purposes, setPurposes] = useState<ConsentPurpose[]>([]);
  const [consents, setConsents] = useState<Record<string, ConsentChoice>>({});
  const [consentMethod, setConsentMethod] = useState('signed_form');
  const [consentGivenBy, setConsentGivenBy] = useState('');

  // Medical history: anyone may enter it at registration; after that only doctors (emr.edit).
  const canEditHistory = !isEdit || can('emr.edit');
  const showHistory = !isEdit || (can('emr.view') && !patient?.medical_history_hidden);

  const mobile = Form.useWatch('mobile', form);
  const firstName = Form.useWatch('first_name', form);
  const lastName = Form.useWatch('last_name', form);
  const age = Form.useWatch('age', form);
  const dob = Form.useWatch('date_of_birth', form) as Dayjs | undefined;
  const patientLanguage = Form.useWatch('preferred_language', form) ?? 'gu';
  const yearsOld: number | null = ageMode === 'age' ? (age ?? null) : dob ? dayjs().diff(dob, 'year') : null;
  const isChild = yearsOld !== null && yearsOld < 18;

  // --- load for edit / consent purposes for new ---
  useEffect(() => {
    if (!isEdit) {
      api.get<ConsentPurpose[]>('/consent-purposes/').then(({ data }) => {
        setPurposes(data);
        setConsents(Object.fromEntries(data.map((p) => [p.code, { granted: p.is_required }])));
      });
      form.setFieldsValue({ gender: undefined, preferred_language: 'gu', country_code: '+91', state: 'Gujarat', country: 'India', allergies: [], medications: [] });
      return;
    }
    setLoading(true);
    api.get<Patient>(`/patients/${id}/`).then(({ data }) => {
      setPatient(data);
      const values: Record<string, unknown> = { ...data };
      MASTER_FIELDS.forEach((f) => (values[f] = idOf(data[f])));
      values.date_of_birth = data.date_of_birth ? dayjs(data.date_of_birth) : undefined;
      values.age = data.age_years;
      values.condition_ids = (data.conditions ?? []).map((c) => idOf(c.condition));
      values.allergies = data.allergies.map((a) => ({ ...a, allergy_type: idOf(a.allergy_type) }));
      setAgeMode(data.dob_is_estimated ? 'age' : 'dob');
      form.setFieldsValue(values);
      if (data.has_photo) {
        api.get(`/patients/${id}/photo/`, { responseType: 'blob' }).then((r) => setExistingPhotoUrl(URL.createObjectURL(r.data)));
      }
    }).catch((err) => message.error(errorMessage(err, t('common.loadFailed'))))
      .finally(() => setLoading(false));
  }, [id, isEdit, form, message, t]);

  // --- "existing patients" check while typing ---
  const checkDuplicates = useCallback(async (m?: string, first?: string, last?: string) => {
    const digits = (m ?? '').replace(/\D/g, '');
    if (digits.length < 10 && !(first && last)) {
      setDuplicates([]);
      return;
    }
    const { data } = await api.get<DuplicatePatient[]>('/patients/duplicates/', {
      params: { mobile: digits, first_name: first, last_name: last, exclude: id },
    });
    setDuplicates(data);
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => checkDuplicates(mobile, firstName, lastName).catch(() => undefined), 400);
    return () => window.clearTimeout(timer);
  }, [mobile, firstName, lastName, checkDuplicates]);

  const conditionOptions = useMemo(
    () => conditionsMaster.map((c) => ({ value: c.id, label: masterLabel(c) })),
    [conditionsMaster, masterLabel],
  );

  // --- save ---
  const save = async () => {
    let values: Record<string, unknown>;
    try {
      values = await form.validateFields();
    } catch {
      message.warning(t('patients.fixErrors'));
      return;
    }
    const required = purposes.filter((p) => p.is_required && !consents[p.code]?.granted);
    if (!isEdit && required.length) {
      message.warning(t('patients.consentRequired'));
      return;
    }

    const payload: Record<string, unknown> = { ...values };
    if (ageMode === 'dob') {
      payload.date_of_birth = values.date_of_birth ? (values.date_of_birth as Dayjs).format('YYYY-MM-DD') : null;
      delete payload.age;
    } else {
      delete payload.date_of_birth;
    }
    if (isEdit && ageMode === 'age' && patient?.dob_is_estimated && values.age === patient.age_years) {
      delete payload.age; // unchanged
    }
    const conditionIds = (values.condition_ids as string[] | undefined) ?? [];
    delete payload.condition_ids;
    if (canEditHistory && showHistory) {
      const existing = new Map((patient?.conditions ?? []).map((c) => [idOf(c.condition), c]));
      payload.conditions = conditionIds.map((cid) => {
        const old = existing.get(cid);
        return old ? { id: old.id, condition: cid, since: old.since, notes: old.notes } : { condition: cid };
      });
    } else {
      HISTORY_FIELDS.forEach((f) => delete payload[f]);
    }

    setSaving(true);
    try {
      const { data } = isEdit
        ? await api.patch<Patient>(`/patients/${id}/`, payload)
        : await api.post<Patient>('/patients/', payload);
      if (photo) {
        const body = new FormData();
        body.append('file', photo, 'photo.jpg');
        await api.post(`/patients/${data.id}/photo/`, body);
      }
      if (!isEdit) {
        for (const purpose of purposes) {
          await api.post('/patient-consents/', {
            patient: data.id, purpose: purpose.id, granted: !!consents[purpose.code]?.granted,
            method: consentMethod, language: patientLanguage, given_by: consentGivenBy,
          });
        }
        message.success(t('patients.registeredMsg', { uhid: data.uhid }));
      } else {
        message.success(t('common.saved'));
      }
      navigate(`/patients/${data.id}`);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Skeleton active paragraph={{ rows: 12 }} />;

  const sectionTitle = (text: string) => <span style={{ fontWeight: 600 }}>{text}</span>;

  return (
    <>
      <div className="page-toolbar">
        <Space align="center">
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate(isEdit ? `/patients/${id}` : '/patients')} aria-label={t('login.back')} />
          <div>
            <Typography.Title level={3} style={{ margin: 0 }}>
              {isEdit ? t('patients.editTitle') : t('patients.registerTitle')}
            </Typography.Title>
            <Typography.Text type="secondary">
              {isEdit ? `${patient?.full_name} · ${patient?.uhid}` : t('patients.registerHelp')}
            </Typography.Text>
          </div>
        </Space>
        <Space>
          <Button onClick={() => navigate(isEdit ? `/patients/${id}` : '/patients')}>{t('common.cancel')}</Button>
          <Button type="primary" size="large" loading={saving} onClick={save}>
            {isEdit ? t('common.save') : t('patients.registerButton')}
          </Button>
        </Space>
      </div>

      <Form form={form} layout="vertical" scrollToFirstError>
        <Row gutter={[20, 20]}>
          <Col xs={24} xl={17}>
            <Space direction="vertical" size={20} style={{ width: '100%' }}>
              {/* ---------- Patient details ---------- */}
              <Card title={sectionTitle(t('patients.sections.details'))}>
                <Row gutter={16}>
                  <Col xs={24} md={6}>
                    <Form.Item name="title" label={t('patients.fields.title')}><MasterSelect category="title" /></Form.Item>
                  </Col>
                  <Col xs={24} md={6}>
                    <Form.Item name="first_name" label={t('patients.fields.first_name')} rules={[{ required: true, message: t('common.required') }]}>
                      <Input autoFocus={!isEdit} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={6}>
                    <Form.Item name="middle_name" label={t('patients.fields.middle_name')}><Input /></Form.Item>
                  </Col>
                  <Col xs={24} md={6}>
                    <Form.Item name="last_name" label={t('patients.fields.last_name')}><Input /></Form.Item>
                  </Col>

                  <Col xs={24} md={12}>
                    <Form.Item label={t('patients.fields.dobOrAge')} required>
                      <Space.Compact style={{ width: '100%' }}>
                        <Segmented
                          value={ageMode}
                          onChange={(v) => setAgeMode(v as 'dob' | 'age')}
                          options={[{ value: 'age', label: t('patients.fields.age') }, { value: 'dob', label: t('patients.fields.dob') }]}
                          style={{ marginRight: 8 }}
                        />
                        {ageMode === 'age' ? (
                          <Form.Item name="age" noStyle rules={[{ required: true, message: t('common.required') }]}>
                            <InputNumber min={0} max={120} addonAfter={t('patients.years')} style={{ flex: 1 }} />
                          </Form.Item>
                        ) : (
                          <Form.Item name="date_of_birth" noStyle rules={[{ required: true, message: t('common.required') }]}>
                            <DatePicker format="DD-MM-YYYY" disabledDate={(d) => d.isAfter(dayjs())} style={{ flex: 1 }} />
                          </Form.Item>
                        )}
                      </Space.Compact>
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item name="gender" label={t('patients.fields.gender')} rules={[{ required: true, message: t('common.required') }]}>
                      <Radio.Group optionType="button" buttonStyle="solid">
                        <Radio.Button value="male">{t('patients.gender.male')}</Radio.Button>
                        <Radio.Button value="female">{t('patients.gender.female')}</Radio.Button>
                        <Radio.Button value="other">{t('patients.gender.other')}</Radio.Button>
                      </Radio.Group>
                    </Form.Item>
                  </Col>

                  <Col xs={24} md={6}>
                    <Form.Item name="blood_group" label={t('patients.fields.blood_group')}><MasterSelect category="blood_group" /></Form.Item>
                  </Col>
                  <Col xs={24} md={6}>
                    <Form.Item name="marital_status" label={t('patients.fields.marital_status')}><MasterSelect category="marital_status" /></Form.Item>
                  </Col>
                  <Col xs={24} md={6}>
                    <Form.Item name="preferred_language" label={t('patients.fields.preferred_language')}>
                      <Select options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={6}>
                    <Form.Item name="occupation" label={t('patients.fields.occupation')}><Input /></Form.Item>
                  </Col>
                  {isChild && (
                    <Col xs={24} md={12}>
                      <Form.Item name="guardian_name" label={t('patients.fields.guardian_name')} extra={t('patients.guardianHelp')}>
                        <Input />
                      </Form.Item>
                    </Col>
                  )}
                </Row>
              </Card>

              {/* ---------- Contact ---------- */}
              <Card title={sectionTitle(t('patients.sections.contact'))}>
                <Row gutter={16}>
                  <Col xs={24} md={8}>
                    <Form.Item
                      name="mobile"
                      label={t('patients.fields.mobile')}
                      rules={[
                        { required: true, message: t('common.required') },
                        { pattern: /^[\s+\-\d]{10,16}$/, message: t('patients.mobileInvalid') },
                      ]}
                    >
                      <Input addonBefore="+91" inputMode="tel" maxLength={14} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={8}>
                    <Form.Item name="alternate_mobile" label={t('patients.fields.alternate_mobile')}><Input inputMode="tel" maxLength={14} /></Form.Item>
                  </Col>
                  <Col xs={24} md={8}>
                    <Form.Item name="email" label={t('patients.fields.email')} rules={[{ type: 'email', message: t('patients.emailInvalid') }]}><Input /></Form.Item>
                  </Col>
                  <Col xs={24} md={8}>
                    <Form.Item name="house" label={t('patients.fields.house')}><Input /></Form.Item>
                  </Col>
                  <Col xs={24} md={8}>
                    <Form.Item name="society" label={t('patients.fields.society')}><Input /></Form.Item>
                  </Col>
                  <Col xs={24} md={8}>
                    <Form.Item name="area" label={t('patients.fields.area')}><Input /></Form.Item>
                  </Col>
                  <Col xs={12} md={6}>
                    <Form.Item name="pincode" label={t('patients.fields.pincode')} rules={[{ pattern: /^\d{6}$/, message: t('branches.pincodeInvalid') }]}>
                      <Input maxLength={6} inputMode="numeric" />
                    </Form.Item>
                  </Col>
                  <Col xs={12} md={6}>
                    <Form.Item name="city" label={t('patients.fields.city')}><Input /></Form.Item>
                  </Col>
                  <Col xs={12} md={6}>
                    <Form.Item name="state" label={t('patients.fields.state')}><Input /></Form.Item>
                  </Col>
                  <Col xs={12} md={6}>
                    <Form.Item name="country" label={t('patients.fields.country')}><Input /></Form.Item>
                  </Col>
                </Row>
              </Card>

              {/* ---------- Referred by + emergency ---------- */}
              <Row gutter={[20, 20]}>
                <Col xs={24} lg={12}>
                  <Card title={sectionTitle(t('patients.sections.referral'))} style={{ height: '100%' }}>
                    <Form.Item name="referral_source" label={t('patients.fields.referral_source')}><MasterSelect category="referral_source" /></Form.Item>
                    <Row gutter={12}>
                      <Col span={12}><Form.Item name="referred_by_name" label={t('patients.fields.referred_by_name')}><Input /></Form.Item></Col>
                      <Col span={12}><Form.Item name="referred_by_phone" label={t('patients.fields.referred_by_phone')}><Input inputMode="tel" /></Form.Item></Col>
                    </Row>
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card title={sectionTitle(t('patients.sections.emergency'))} style={{ height: '100%' }}>
                    <Form.Item name="emergency_name" label={t('patients.fields.emergency_name')}><Input /></Form.Item>
                    <Row gutter={12}>
                      <Col span={12}><Form.Item name="emergency_relation" label={t('patients.fields.emergency_relation')}><MasterSelect category="relation" /></Form.Item></Col>
                      <Col span={12}><Form.Item name="emergency_phone" label={t('patients.fields.emergency_phone')}><Input inputMode="tel" /></Form.Item></Col>
                    </Row>
                  </Card>
                </Col>
              </Row>

              {/* ---------- Medical ---------- */}
              <Card title={sectionTitle(t('patients.sections.medical'))}>
                {showHistory && (
                  <Form.Item name="condition_ids" label={t('patients.fields.conditions')}>
                    <Checkbox.Group disabled={!canEditHistory} style={{ width: '100%' }}>
                      <Row gutter={[8, 8]}>
                        {conditionOptions.map((o) => (
                          <Col xs={12} md={8} lg={6} key={o.value}><Checkbox value={o.value}>{o.label}</Checkbox></Col>
                        ))}
                      </Row>
                    </Checkbox.Group>
                  </Form.Item>
                )}

                <Typography.Text strong>{t('patients.fields.allergies')}</Typography.Text>
                <Form.List name="allergies">
                  {(fields, { add, remove }) => (
                    <div style={{ marginTop: 8, marginBottom: 16 }}>
                      {fields.map((field) => (
                        <Row gutter={8} key={field.key} align="top">
                          <Form.Item name={[field.name, 'id']} hidden><Input /></Form.Item>
                          <Col xs={24} md={5}><Form.Item name={[field.name, 'allergy_type']}><MasterSelect category="allergy_type" placeholder={t('patients.allergyType')} /></Form.Item></Col>
                          <Col xs={24} md={7}><Form.Item name={[field.name, 'allergen']} rules={[{ required: true, message: t('common.required') }]}><Input placeholder={t('patients.allergen')} /></Form.Item></Col>
                          <Col xs={24} md={5}>
                            <Form.Item name={[field.name, 'severity']} initialValue="moderate">
                              <Select options={['mild', 'moderate', 'severe'].map((s) => ({ value: s, label: t(`patients.severity.${s}`) }))} />
                            </Form.Item>
                          </Col>
                          <Col xs={22} md={6}><Form.Item name={[field.name, 'reaction']}><Input placeholder={t('patients.reaction')} /></Form.Item></Col>
                          <Col xs={2} md={1}><Button type="text" danger icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} aria-label={t('common.remove')} /></Col>
                        </Row>
                      ))}
                      <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ severity: 'moderate' })}>{t('patients.addAllergy')}</Button>
                    </div>
                  )}
                </Form.List>

                <Typography.Text strong>{t('patients.fields.medications')}</Typography.Text>
                <Form.List name="medications">
                  {(fields, { add, remove }) => (
                    <div style={{ marginTop: 8, marginBottom: 16 }}>
                      {fields.map((field) => (
                        <Row gutter={8} key={field.key}>
                          <Form.Item name={[field.name, 'id']} hidden><Input /></Form.Item>
                          <Col xs={24} md={8}><Form.Item name={[field.name, 'name']} rules={[{ required: true, message: t('common.required') }]}><Input placeholder={t('patients.medicineName')} /></Form.Item></Col>
                          <Col xs={12} md={5}><Form.Item name={[field.name, 'dose']}><Input placeholder={t('patients.dose')} /></Form.Item></Col>
                          <Col xs={12} md={6}><Form.Item name={[field.name, 'frequency']}><Input placeholder={t('patients.frequency')} /></Form.Item></Col>
                          <Col xs={22} md={4}><Form.Item name={[field.name, 'since']}><Input placeholder={t('patients.since')} /></Form.Item></Col>
                          <Col xs={2} md={1}><Button type="text" danger icon={<MinusCircleOutlined />} onClick={() => remove(field.name)} aria-label={t('common.remove')} /></Col>
                        </Row>
                      ))}
                      <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()}>{t('patients.addMedicine')}</Button>
                    </div>
                  )}
                </Form.List>

                {showHistory && (
                  <Row gutter={16}>
                    {HISTORY_FIELDS.map((f) => (
                      <Col xs={24} md={12} key={f}>
                        <Form.Item name={f} label={t(`patients.fields.${f}`)}>
                          <Input.TextArea rows={2} disabled={!canEditHistory} />
                        </Form.Item>
                      </Col>
                    ))}
                  </Row>
                )}
                {showHistory && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('patients.historyPrivate')}</Typography.Text>}
              </Card>

              {/* ---------- Consent (new patients) ---------- */}
              {!isEdit && (
                <Card title={sectionTitle(t('patients.sections.consent'))}>
                  <Typography.Paragraph type="secondary">{t('patients.consentHelp')}</Typography.Paragraph>
                  <Space direction="vertical" size={12} style={{ width: '100%' }}>
                    {purposes.map((purpose) => (
                      <div key={purpose.code} className="consent-row">
                        <Switch
                          checked={!!consents[purpose.code]?.granted}
                          onChange={(granted) => setConsents((c) => ({ ...c, [purpose.code]: { granted } }))}
                        />
                        <div>
                          <div style={{ fontWeight: 600 }}>
                            {pickLang(purpose, 'title', i18n.language)}
                            {purpose.is_required && <span style={{ color: '#c2412d' }}> *</span>}
                          </div>
                          <div className="consent-text">{pickLang(purpose, 'description', patientLanguage)}</div>
                        </div>
                      </div>
                    ))}
                  </Space>
                  <Row gutter={16} style={{ marginTop: 16 }}>
                    <Col xs={24} md={12}>
                      <Form.Item label={t('patients.consentMethod')}>
                        <Select value={consentMethod} onChange={setConsentMethod}
                          options={['signed_form', 'verbal', 'on_screen', 'guardian'].map((m) => ({ value: m, label: t(`patients.consentMethods.${m}`) }))} />
                      </Form.Item>
                    </Col>
                    {(consentMethod === 'guardian' || isChild) && (
                      <Col xs={24} md={12}>
                        <Form.Item label={t('patients.consentGivenBy')}>
                          <Input value={consentGivenBy} onChange={(e) => setConsentGivenBy(e.target.value)} />
                        </Form.Item>
                      </Col>
                    )}
                  </Row>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {t('patients.consentLanguageNote', { language: LANGUAGES.find((l) => l.code === patientLanguage)?.label })}
                  </Typography.Text>
                </Card>
              )}
            </Space>
          </Col>

          {/* ---------- Right side ---------- */}
          <Col xs={24} xl={7}>
            <div className="side-sticky">
              <Card>
                <PhotoPicker value={photo} onChange={setPhoto} existingUrl={existingPhotoUrl} />
              </Card>
              <Card title={<Space><UserSwitchOutlined />{t('patients.existingPatients')}</Space>}>
                {duplicates.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('patients.existingHelp')} />
                ) : (
                  <>
                    <Alert type="warning" showIcon message={t('patients.possibleDuplicate')} style={{ marginBottom: 12 }} />
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {duplicates.map((d) => (
                        <Link key={d.id} to={`/patients/${d.id}`} className="dup-item">
                          <div style={{ fontWeight: 600 }}>{d.full_name}</div>
                          <div className="dup-meta">{d.uhid} · {genderAge(t, d.gender, d.age_years)} · {d.mobile_masked}{d.city ? ` · ${d.city}` : ''}</div>
                        </Link>
                      ))}
                    </Space>
                  </>
                )}
              </Card>
              <Card>
                <Space direction="vertical">
                  <Form.Item name="is_vip" valuePropName="checked" noStyle><Checkbox>{t('patients.fields.is_vip')}</Checkbox></Form.Item>
                  <Form.Item name="is_foc" valuePropName="checked" noStyle><Checkbox>{t('patients.fields.is_foc')}</Checkbox></Form.Item>
                </Space>
              </Card>
            </div>
          </Col>
        </Row>
      </Form>
    </>
  );
}
