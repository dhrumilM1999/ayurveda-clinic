import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Register a new patient, or edit one (/patients/:id/edit).
import { ArrowLeftOutlined, MinusCircleOutlined, PlusOutlined, UserSwitchOutlined } from '@ant-design/icons';
import { Alert, App, Button, Card, Checkbox, Col, DatePicker, Empty, Form, Input, InputNumber, Radio, Row, Select, Segmented, Skeleton, Space, Switch, Typography, } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { pickLang, useMasterLabel, useMasters } from '../../api/masters';
import { useAuth } from '../../auth/AuthContext';
import { MasterSelect } from '../../components/MasterSelect';
import { PhotoPicker } from '../../components/PhotoPicker';
import { LANGUAGES } from '../../i18n';
import { genderAge } from './PatientsPage';
const MASTER_FIELDS = ['title', 'blood_group', 'marital_status', 'referral_source', 'emergency_relation'];
const HISTORY_FIELDS = ['past_history', 'family_history', 'surgical_history', 'other_notes'];
const idOf = (v) => (v && typeof v === 'object' ? v.id : v ?? undefined);
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
    const [patient, setPatient] = useState(null);
    const [loading, setLoading] = useState(isEdit);
    const [saving, setSaving] = useState(false);
    const [photo, setPhoto] = useState(null);
    const [existingPhotoUrl, setExistingPhotoUrl] = useState(null);
    const [ageMode, setAgeMode] = useState('age');
    const [duplicates, setDuplicates] = useState([]);
    const [purposes, setPurposes] = useState([]);
    const [consents, setConsents] = useState({});
    const [consentMethod, setConsentMethod] = useState('signed_form');
    const [consentGivenBy, setConsentGivenBy] = useState('');
    // Medical history: anyone may enter it at registration; after that only doctors (emr.edit).
    const canEditHistory = !isEdit || can('emr.edit');
    const showHistory = !isEdit || (can('emr.view') && !patient?.medical_history_hidden);
    const mobile = Form.useWatch('mobile', form);
    const firstName = Form.useWatch('first_name', form);
    const lastName = Form.useWatch('last_name', form);
    const age = Form.useWatch('age', form);
    const dob = Form.useWatch('date_of_birth', form);
    const patientLanguage = Form.useWatch('preferred_language', form) ?? 'gu';
    const yearsOld = ageMode === 'age' ? (age ?? null) : dob ? dayjs().diff(dob, 'year') : null;
    const isChild = yearsOld !== null && yearsOld < 18;
    // --- load for edit / consent purposes for new ---
    useEffect(() => {
        if (!isEdit) {
            api.get('/consent-purposes/').then(({ data }) => {
                setPurposes(data);
                setConsents(Object.fromEntries(data.map((p) => [p.code, { granted: p.is_required }])));
            });
            form.setFieldsValue({ gender: undefined, preferred_language: 'gu', country_code: '+91', state: 'Gujarat', country: 'India', allergies: [], medications: [] });
            return;
        }
        setLoading(true);
        api.get(`/patients/${id}/`).then(({ data }) => {
            setPatient(data);
            const values = { ...data };
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
    const checkDuplicates = useCallback(async (m, first, last) => {
        const digits = (m ?? '').replace(/\D/g, '');
        if (digits.length < 10 && !(first && last)) {
            setDuplicates([]);
            return;
        }
        const { data } = await api.get('/patients/duplicates/', {
            params: { mobile: digits, first_name: first, last_name: last, exclude: id },
        });
        setDuplicates(data);
    }, [id]);
    useEffect(() => {
        const timer = window.setTimeout(() => checkDuplicates(mobile, firstName, lastName).catch(() => undefined), 400);
        return () => window.clearTimeout(timer);
    }, [mobile, firstName, lastName, checkDuplicates]);
    const conditionOptions = useMemo(() => conditionsMaster.map((c) => ({ value: c.id, label: masterLabel(c) })), [conditionsMaster, masterLabel]);
    // --- save ---
    const save = async () => {
        let values;
        try {
            values = await form.validateFields();
        }
        catch {
            message.warning(t('patients.fixErrors'));
            return;
        }
        const required = purposes.filter((p) => p.is_required && !consents[p.code]?.granted);
        if (!isEdit && required.length) {
            message.warning(t('patients.consentRequired'));
            return;
        }
        const payload = { ...values };
        if (ageMode === 'dob') {
            payload.date_of_birth = values.date_of_birth ? values.date_of_birth.format('YYYY-MM-DD') : null;
            delete payload.age;
        }
        else {
            delete payload.date_of_birth;
        }
        if (isEdit && ageMode === 'age' && patient?.dob_is_estimated && values.age === patient.age_years) {
            delete payload.age; // unchanged
        }
        const conditionIds = values.condition_ids ?? [];
        delete payload.condition_ids;
        if (canEditHistory && showHistory) {
            const existing = new Map((patient?.conditions ?? []).map((c) => [idOf(c.condition), c]));
            payload.conditions = conditionIds.map((cid) => {
                const old = existing.get(cid);
                return old ? { id: old.id, condition: cid, since: old.since, notes: old.notes } : { condition: cid };
            });
        }
        else {
            HISTORY_FIELDS.forEach((f) => delete payload[f]);
        }
        setSaving(true);
        try {
            const { data } = isEdit
                ? await api.patch(`/patients/${id}/`, payload)
                : await api.post('/patients/', payload);
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
            }
            else {
                message.success(t('common.saved'));
            }
            navigate(`/patients/${data.id}`);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    if (loading)
        return _jsx(Skeleton, { active: true, paragraph: { rows: 12 } });
    const sectionTitle = (text) => _jsx("span", { style: { fontWeight: 600 }, children: text });
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsxs(Space, { align: "center", children: [_jsx(Button, { type: "text", icon: _jsx(ArrowLeftOutlined, {}), onClick: () => navigate(isEdit ? `/patients/${id}` : '/patients'), "aria-label": t('login.back') }), _jsxs("div", { children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: isEdit ? t('patients.editTitle') : t('patients.registerTitle') }), _jsx(Typography.Text, { type: "secondary", children: isEdit ? `${patient?.full_name} · ${patient?.uhid}` : t('patients.registerHelp') })] })] }), _jsxs(Space, { children: [_jsx(Button, { onClick: () => navigate(isEdit ? `/patients/${id}` : '/patients'), children: t('common.cancel') }), _jsx(Button, { type: "primary", size: "large", loading: saving, onClick: save, children: isEdit ? t('common.save') : t('patients.registerButton') })] })] }), _jsx(Form, { form: form, layout: "vertical", scrollToFirstError: true, children: _jsxs(Row, { gutter: [20, 20], children: [_jsx(Col, { xs: 24, xl: 17, children: _jsxs(Space, { direction: "vertical", size: 20, style: { width: '100%' }, children: [_jsx(Card, { title: sectionTitle(t('patients.sections.details')), children: _jsxs(Row, { gutter: 16, children: [_jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "title", label: t('patients.fields.title'), children: _jsx(MasterSelect, { category: "title" }) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "first_name", label: t('patients.fields.first_name'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, { autoFocus: !isEdit }) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "middle_name", label: t('patients.fields.middle_name'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "last_name", label: t('patients.fields.last_name'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { label: t('patients.fields.dobOrAge'), required: true, children: _jsxs(Space.Compact, { style: { width: '100%' }, children: [_jsx(Segmented, { value: ageMode, onChange: (v) => setAgeMode(v), options: [{ value: 'age', label: t('patients.fields.age') }, { value: 'dob', label: t('patients.fields.dob') }], style: { marginRight: 8 } }), ageMode === 'age' ? (_jsx(Form.Item, { name: "age", noStyle: true, rules: [{ required: true, message: t('common.required') }], children: _jsx(InputNumber, { min: 0, max: 120, addonAfter: t('patients.years'), style: { flex: 1 } }) })) : (_jsx(Form.Item, { name: "date_of_birth", noStyle: true, rules: [{ required: true, message: t('common.required') }], children: _jsx(DatePicker, { format: "DD-MM-YYYY", disabledDate: (d) => d.isAfter(dayjs()), style: { flex: 1 } }) }))] }) }) }), _jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "gender", label: t('patients.fields.gender'), rules: [{ required: true, message: t('common.required') }], children: _jsxs(Radio.Group, { optionType: "button", buttonStyle: "solid", children: [_jsx(Radio.Button, { value: "male", children: t('patients.gender.male') }), _jsx(Radio.Button, { value: "female", children: t('patients.gender.female') }), _jsx(Radio.Button, { value: "other", children: t('patients.gender.other') })] }) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "blood_group", label: t('patients.fields.blood_group'), children: _jsx(MasterSelect, { category: "blood_group" }) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "marital_status", label: t('patients.fields.marital_status'), children: _jsx(MasterSelect, { category: "marital_status" }) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "preferred_language", label: t('patients.fields.preferred_language'), children: _jsx(Select, { options: LANGUAGES.map((l) => ({ value: l.code, label: l.label })) }) }) }), _jsx(Col, { xs: 24, md: 6, children: _jsx(Form.Item, { name: "occupation", label: t('patients.fields.occupation'), children: _jsx(Input, {}) }) }), isChild && (_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: "guardian_name", label: t('patients.fields.guardian_name'), extra: t('patients.guardianHelp'), children: _jsx(Input, {}) }) }))] }) }), _jsx(Card, { title: sectionTitle(t('patients.sections.contact')), children: _jsxs(Row, { gutter: 16, children: [_jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: "mobile", label: t('patients.fields.mobile'), rules: [
                                                            { required: true, message: t('common.required') },
                                                            { pattern: /^[\s+\-\d]{10,16}$/, message: t('patients.mobileInvalid') },
                                                        ], children: _jsx(Input, { addonBefore: "+91", inputMode: "tel", maxLength: 14 }) }) }), _jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: "alternate_mobile", label: t('patients.fields.alternate_mobile'), children: _jsx(Input, { inputMode: "tel", maxLength: 14 }) }) }), _jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: "email", label: t('patients.fields.email'), rules: [{ type: 'email', message: t('patients.emailInvalid') }], children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: "house", label: t('patients.fields.house'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: "society", label: t('patients.fields.society'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: "area", label: t('patients.fields.area'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 12, md: 6, children: _jsx(Form.Item, { name: "pincode", label: t('patients.fields.pincode'), rules: [{ pattern: /^\d{6}$/, message: t('branches.pincodeInvalid') }], children: _jsx(Input, { maxLength: 6, inputMode: "numeric" }) }) }), _jsx(Col, { xs: 12, md: 6, children: _jsx(Form.Item, { name: "city", label: t('patients.fields.city'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 12, md: 6, children: _jsx(Form.Item, { name: "state", label: t('patients.fields.state'), children: _jsx(Input, {}) }) }), _jsx(Col, { xs: 12, md: 6, children: _jsx(Form.Item, { name: "country", label: t('patients.fields.country'), children: _jsx(Input, {}) }) })] }) }), _jsxs(Row, { gutter: [20, 20], children: [_jsx(Col, { xs: 24, lg: 12, children: _jsxs(Card, { title: sectionTitle(t('patients.sections.referral')), style: { height: '100%' }, children: [_jsx(Form.Item, { name: "referral_source", label: t('patients.fields.referral_source'), children: _jsx(MasterSelect, { category: "referral_source" }) }), _jsxs(Row, { gutter: 12, children: [_jsx(Col, { span: 12, children: _jsx(Form.Item, { name: "referred_by_name", label: t('patients.fields.referred_by_name'), children: _jsx(Input, {}) }) }), _jsx(Col, { span: 12, children: _jsx(Form.Item, { name: "referred_by_phone", label: t('patients.fields.referred_by_phone'), children: _jsx(Input, { inputMode: "tel" }) }) })] })] }) }), _jsx(Col, { xs: 24, lg: 12, children: _jsxs(Card, { title: sectionTitle(t('patients.sections.emergency')), style: { height: '100%' }, children: [_jsx(Form.Item, { name: "emergency_name", label: t('patients.fields.emergency_name'), children: _jsx(Input, {}) }), _jsxs(Row, { gutter: 12, children: [_jsx(Col, { span: 12, children: _jsx(Form.Item, { name: "emergency_relation", label: t('patients.fields.emergency_relation'), children: _jsx(MasterSelect, { category: "relation" }) }) }), _jsx(Col, { span: 12, children: _jsx(Form.Item, { name: "emergency_phone", label: t('patients.fields.emergency_phone'), children: _jsx(Input, { inputMode: "tel" }) }) })] })] }) })] }), _jsxs(Card, { title: sectionTitle(t('patients.sections.medical')), children: [showHistory && (_jsx(Form.Item, { name: "condition_ids", label: t('patients.fields.conditions'), children: _jsx(Checkbox.Group, { disabled: !canEditHistory, style: { width: '100%' }, children: _jsx(Row, { gutter: [8, 8], children: conditionOptions.map((o) => (_jsx(Col, { xs: 12, md: 8, lg: 6, children: _jsx(Checkbox, { value: o.value, children: o.label }) }, o.value))) }) }) })), _jsx(Typography.Text, { strong: true, children: t('patients.fields.allergies') }), _jsx(Form.List, { name: "allergies", children: (fields, { add, remove }) => (_jsxs("div", { style: { marginTop: 8, marginBottom: 16 }, children: [fields.map((field) => (_jsxs(Row, { gutter: 8, align: "top", children: [_jsx(Form.Item, { name: [field.name, 'id'], hidden: true, children: _jsx(Input, {}) }), _jsx(Col, { xs: 24, md: 5, children: _jsx(Form.Item, { name: [field.name, 'allergy_type'], children: _jsx(MasterSelect, { category: "allergy_type", placeholder: t('patients.allergyType') }) }) }), _jsx(Col, { xs: 24, md: 7, children: _jsx(Form.Item, { name: [field.name, 'allergen'], rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, { placeholder: t('patients.allergen') }) }) }), _jsx(Col, { xs: 24, md: 5, children: _jsx(Form.Item, { name: [field.name, 'severity'], initialValue: "moderate", children: _jsx(Select, { options: ['mild', 'moderate', 'severe'].map((s) => ({ value: s, label: t(`patients.severity.${s}`) })) }) }) }), _jsx(Col, { xs: 22, md: 6, children: _jsx(Form.Item, { name: [field.name, 'reaction'], children: _jsx(Input, { placeholder: t('patients.reaction') }) }) }), _jsx(Col, { xs: 2, md: 1, children: _jsx(Button, { type: "text", danger: true, icon: _jsx(MinusCircleOutlined, {}), onClick: () => remove(field.name), "aria-label": t('common.remove') }) })] }, field.key))), _jsx(Button, { type: "dashed", icon: _jsx(PlusOutlined, {}), onClick: () => add({ severity: 'moderate' }), children: t('patients.addAllergy') })] })) }), _jsx(Typography.Text, { strong: true, children: t('patients.fields.medications') }), _jsx(Form.List, { name: "medications", children: (fields, { add, remove }) => (_jsxs("div", { style: { marginTop: 8, marginBottom: 16 }, children: [fields.map((field) => (_jsxs(Row, { gutter: 8, children: [_jsx(Form.Item, { name: [field.name, 'id'], hidden: true, children: _jsx(Input, {}) }), _jsx(Col, { xs: 24, md: 8, children: _jsx(Form.Item, { name: [field.name, 'name'], rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, { placeholder: t('patients.medicineName') }) }) }), _jsx(Col, { xs: 12, md: 5, children: _jsx(Form.Item, { name: [field.name, 'dose'], children: _jsx(Input, { placeholder: t('patients.dose') }) }) }), _jsx(Col, { xs: 12, md: 6, children: _jsx(Form.Item, { name: [field.name, 'frequency'], children: _jsx(Input, { placeholder: t('patients.frequency') }) }) }), _jsx(Col, { xs: 22, md: 4, children: _jsx(Form.Item, { name: [field.name, 'since'], children: _jsx(Input, { placeholder: t('patients.since') }) }) }), _jsx(Col, { xs: 2, md: 1, children: _jsx(Button, { type: "text", danger: true, icon: _jsx(MinusCircleOutlined, {}), onClick: () => remove(field.name), "aria-label": t('common.remove') }) })] }, field.key))), _jsx(Button, { type: "dashed", icon: _jsx(PlusOutlined, {}), onClick: () => add(), children: t('patients.addMedicine') })] })) }), showHistory && (_jsx(Row, { gutter: 16, children: HISTORY_FIELDS.map((f) => (_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { name: f, label: t(`patients.fields.${f}`), children: _jsx(Input.TextArea, { rows: 2, disabled: !canEditHistory }) }) }, f))) })), showHistory && _jsx(Typography.Text, { type: "secondary", style: { fontSize: 12 }, children: t('patients.historyPrivate') })] }), !isEdit && (_jsxs(Card, { title: sectionTitle(t('patients.sections.consent')), children: [_jsx(Typography.Paragraph, { type: "secondary", children: t('patients.consentHelp') }), _jsx(Space, { direction: "vertical", size: 12, style: { width: '100%' }, children: purposes.map((purpose) => (_jsxs("div", { className: "consent-row", children: [_jsx(Switch, { checked: !!consents[purpose.code]?.granted, onChange: (granted) => setConsents((c) => ({ ...c, [purpose.code]: { granted } })) }), _jsxs("div", { children: [_jsxs("div", { style: { fontWeight: 600 }, children: [pickLang(purpose, 'title', i18n.language), purpose.is_required && _jsx("span", { style: { color: '#c2412d' }, children: " *" })] }), _jsx("div", { className: "consent-text", children: pickLang(purpose, 'description', patientLanguage) })] })] }, purpose.code))) }), _jsxs(Row, { gutter: 16, style: { marginTop: 16 }, children: [_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { label: t('patients.consentMethod'), children: _jsx(Select, { value: consentMethod, onChange: setConsentMethod, options: ['signed_form', 'verbal', 'on_screen', 'guardian'].map((m) => ({ value: m, label: t(`patients.consentMethods.${m}`) })) }) }) }), (consentMethod === 'guardian' || isChild) && (_jsx(Col, { xs: 24, md: 12, children: _jsx(Form.Item, { label: t('patients.consentGivenBy'), children: _jsx(Input, { value: consentGivenBy, onChange: (e) => setConsentGivenBy(e.target.value) }) }) }))] }), _jsx(Typography.Text, { type: "secondary", style: { fontSize: 12 }, children: t('patients.consentLanguageNote', { language: LANGUAGES.find((l) => l.code === patientLanguage)?.label }) })] }))] }) }), _jsx(Col, { xs: 24, xl: 7, children: _jsxs("div", { className: "side-sticky", children: [_jsx(Card, { children: _jsx(PhotoPicker, { value: photo, onChange: setPhoto, existingUrl: existingPhotoUrl }) }), _jsx(Card, { title: _jsxs(Space, { children: [_jsx(UserSwitchOutlined, {}), t('patients.existingPatients')] }), children: duplicates.length === 0 ? (_jsx(Empty, { image: Empty.PRESENTED_IMAGE_SIMPLE, description: t('patients.existingHelp') })) : (_jsxs(_Fragment, { children: [_jsx(Alert, { type: "warning", showIcon: true, message: t('patients.possibleDuplicate'), style: { marginBottom: 12 } }), _jsx(Space, { direction: "vertical", style: { width: '100%' }, children: duplicates.map((d) => (_jsxs(Link, { to: `/patients/${d.id}`, className: "dup-item", children: [_jsx("div", { style: { fontWeight: 600 }, children: d.full_name }), _jsxs("div", { className: "dup-meta", children: [d.uhid, " \u00B7 ", genderAge(t, d.gender, d.age_years), " \u00B7 ", d.mobile_masked, d.city ? ` · ${d.city}` : ''] })] }, d.id))) })] })) }), _jsx(Card, { children: _jsxs(Space, { direction: "vertical", children: [_jsx(Form.Item, { name: "is_vip", valuePropName: "checked", noStyle: true, children: _jsx(Checkbox, { children: t('patients.fields.is_vip') }) }), _jsx(Form.Item, { name: "is_foc", valuePropName: "checked", noStyle: true, children: _jsx(Checkbox, { children: t('patients.fields.is_foc') }) })] }) })] }) })] }) })] }));
}
