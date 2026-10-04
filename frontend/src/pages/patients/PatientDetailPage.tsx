// One patient's file: header with key facts, and tabs for details, medical, vitals, documents,
// consent and activity. Opening this page is written to the audit log.
import { AlertOutlined, ArrowLeftOutlined, CrownOutlined, EditOutlined, PhoneOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Skeleton, Space, Tabs, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { useMasterLabel } from '../../api/masters';
import type { Patient } from '../../api/types';
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
  const [patient, setPatient] = useState<Patient | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get<Patient>(`/patients/${id}/`)
      .then(({ data }) => setPatient(data))
      .catch((err) => setError(errorMessage(err, t('common.loadFailed'))));
  }, [id, t]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <Alert type="error" showIcon message={error} />;
  if (!patient) return <Skeleton active avatar paragraph={{ rows: 8 }} />;

  const canSeeVitals = can('emr.view') || can('patients.vitals');
  const canDocuments = can('emr.view') || can('patients.edit');

  const tabs = [
    { key: 'overview', label: t('patients.tabs.overview'), children: <OverviewTab patient={patient} /> },
    { key: 'medical', label: t('patients.tabs.medical'), children: <MedicalTab patient={patient} /> },
    ...(canSeeVitals ? [{ key: 'vitals', label: t('patients.tabs.vitals'), children: <VitalsTab patientId={patient.id} /> }] : []),
    ...(canDocuments ? [{ key: 'documents', label: t('patients.tabs.documents'), children: <DocumentsTab patientId={patient.id} /> }] : []),
    { key: 'consent', label: t('patients.tabs.consent'), children: <ConsentTab patient={patient} /> },
    ...(can('audit.view') ? [{ key: 'activity', label: t('patients.tabs.activity'), children: <ActivityTab patientId={patient.id} /> }] : []),
  ];

  return (
    <>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/patients')} style={{ marginBottom: 12, marginLeft: -8 }}>
        {t('patients.backToList')}
      </Button>

      <Card className="patient-header" style={{ marginBottom: 20 }}>
        <div className="patient-header-row">
          <PatientPhoto patientId={patient.id} hasPhoto={patient.has_photo} name={patient.full_name} size={88} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <Space wrap size={8}>
              <span className="patient-name">
                {patient.title ? `${masterLabel(patient.title)} ` : ''}{patient.full_name}
              </span>
              {patient.is_vip && <Tag color="gold" icon={<CrownOutlined />}>VIP</Tag>}
              {patient.is_foc && <Tag color="blue">FOC</Tag>}
            </Space>
            <div className="patient-meta">
              <Typography.Text copyable={{ text: patient.uhid }} className="uhid-chip">{patient.uhid}</Typography.Text>
              <span>{genderAge(t, patient.gender, patient.age_years)}{patient.dob_is_estimated ? ` (${t('patients.approx')})` : ''}</span>
              {patient.blood_group && <span>{t('patients.fields.blood_group')}: <b>{masterLabel(patient.blood_group)}</b></span>}
              <span><PhoneOutlined /> {patient.country_code} {patient.mobile}</span>
              {patient.city && <span>{patient.city}</span>}
            </div>
          </div>
          {can('patients.edit') && (
            <Button icon={<EditOutlined />} onClick={() => navigate(`/patients/${patient.id}/edit`)}>{t('common.edit')}</Button>
          )}
        </div>
        {patient.allergies.length > 0 && (
          <Alert
            type="error"
            showIcon
            icon={<AlertOutlined />}
            style={{ marginTop: 16 }}
            message={<b>{t('patients.allergyAlert')}</b>}
            description={patient.allergies.map((a) => `${a.allergen}${a.reaction ? ` (${a.reaction})` : ''} — ${t(`patients.severity.${a.severity}`)}`).join(' · ')}
          />
        )}
      </Card>

      <Card>
        <Tabs items={tabs} destroyInactiveTabPane />
      </Card>
    </>
  );
}
