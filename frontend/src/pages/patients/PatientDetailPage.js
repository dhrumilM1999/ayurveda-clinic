import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// One patient's file: header with key facts, and tabs for details, medical, vitals, documents,
// consent and activity. Opening this page is written to the audit log.
import { AlertOutlined, ArrowLeftOutlined, CrownOutlined, EditOutlined, PhoneOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Skeleton, Space, Tabs, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { useMasterLabel } from '../../api/masters';
import { useAuth } from '../../auth/AuthContext';
import { PatientPhoto } from '../../components/PatientPhoto';
import { genderAge } from './PatientsPage';
import { ActivityTab } from './tabs/ActivityTab';
import { ConsentTab } from './tabs/ConsentTab';
import { DocumentsTab } from './tabs/DocumentsTab';
import { MedicalTab } from './tabs/MedicalTab';
import { OverviewTab } from './tabs/OverviewTab';
import { VitalsTab } from './tabs/VitalsTab';
export default function PatientDetailPage() {
    const { id } = useParams();
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { can } = useAuth();
    const masterLabel = useMasterLabel();
    const [patient, setPatient] = useState(null);
    const [error, setError] = useState(null);
    const load = useCallback(() => {
        api.get(`/patients/${id}/`)
            .then(({ data }) => setPatient(data))
            .catch((err) => setError(errorMessage(err, t('common.loadFailed'))));
    }, [id, t]);
    useEffect(() => {
        load();
    }, [load]);
    if (error)
        return _jsx(Alert, { type: "error", showIcon: true, message: error });
    if (!patient)
        return _jsx(Skeleton, { active: true, avatar: true, paragraph: { rows: 8 } });
    const canSeeVitals = can('emr.view') || can('patients.vitals');
    const canDocuments = can('emr.view') || can('patients.edit');
    const tabs = [
        { key: 'overview', label: t('patients.tabs.overview'), children: _jsx(OverviewTab, { patient: patient }) },
        { key: 'medical', label: t('patients.tabs.medical'), children: _jsx(MedicalTab, { patient: patient }) },
        ...(canSeeVitals ? [{ key: 'vitals', label: t('patients.tabs.vitals'), children: _jsx(VitalsTab, { patientId: patient.id }) }] : []),
        ...(canDocuments ? [{ key: 'documents', label: t('patients.tabs.documents'), children: _jsx(DocumentsTab, { patientId: patient.id }) }] : []),
        { key: 'consent', label: t('patients.tabs.consent'), children: _jsx(ConsentTab, { patient: patient }) },
        ...(can('audit.view') ? [{ key: 'activity', label: t('patients.tabs.activity'), children: _jsx(ActivityTab, { patientId: patient.id }) }] : []),
    ];
    return (_jsxs(_Fragment, { children: [_jsx(Button, { type: "text", icon: _jsx(ArrowLeftOutlined, {}), onClick: () => navigate('/patients'), style: { marginBottom: 12, marginLeft: -8 }, children: t('patients.backToList') }), _jsxs(Card, { className: "patient-header", style: { marginBottom: 20 }, children: [_jsxs("div", { className: "patient-header-row", children: [_jsx(PatientPhoto, { patientId: patient.id, hasPhoto: patient.has_photo, name: patient.full_name, size: 88 }), _jsxs("div", { style: { flex: 1, minWidth: 0 }, children: [_jsxs(Space, { wrap: true, size: 8, children: [_jsxs("span", { className: "patient-name", children: [patient.title ? `${masterLabel(patient.title)} ` : '', patient.full_name] }), patient.is_vip && _jsx(Tag, { color: "gold", icon: _jsx(CrownOutlined, {}), children: "VIP" }), patient.is_foc && _jsx(Tag, { color: "blue", children: "FOC" })] }), _jsxs("div", { className: "patient-meta", children: [_jsx(Typography.Text, { copyable: { text: patient.uhid }, className: "uhid-chip", children: patient.uhid }), _jsxs("span", { children: [genderAge(t, patient.gender, patient.age_years), patient.dob_is_estimated ? ` (${t('patients.approx')})` : ''] }), patient.blood_group && _jsxs("span", { children: [t('patients.fields.blood_group'), ": ", _jsx("b", { children: masterLabel(patient.blood_group) })] }), _jsxs("span", { children: [_jsx(PhoneOutlined, {}), " ", patient.country_code, " ", patient.mobile] }), patient.city && _jsx("span", { children: patient.city })] })] }), can('patients.edit') && (_jsx(Button, { icon: _jsx(EditOutlined, {}), onClick: () => navigate(`/patients/${patient.id}/edit`), children: t('common.edit') }))] }), patient.allergies.length > 0 && (_jsx(Alert, { type: "error", showIcon: true, icon: _jsx(AlertOutlined, {}), style: { marginTop: 16 }, message: _jsx("b", { children: t('patients.allergyAlert') }), description: patient.allergies.map((a) => `${a.allergen}${a.reaction ? ` (${a.reaction})` : ''} — ${t(`patients.severity.${a.severity}`)}`).join(' · ') }))] }), _jsx(Card, { children: _jsx(Tabs, { items: tabs, destroyInactiveTabPane: true }) })] }));
}
