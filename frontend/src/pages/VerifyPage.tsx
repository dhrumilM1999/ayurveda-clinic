// Public page opened by the QR code on a prescription / certificate: "Is this document genuine?"
// Works without logging in and shows no medical details (only number, date, clinic, doctor, patient initials).
import { CheckCircleFilled, CloseCircleFilled, WarningFilled } from '@ant-design/icons';
import { Card, Result, Spin } from 'antd';
import axios from 'axios';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { clinicConfig } from '../config/clinic';

type Check = {
  valid: boolean; cancelled?: boolean; kind?: string; number?: string; issued_on?: string;
  clinic?: string; branch?: string; doctor?: string; patient_initials?: string;
};

export default function VerifyPage() {
  const { t } = useTranslation();
  const { token } = useParams();
  const [check, setCheck] = useState<Check | null>(null);

  useEffect(() => {
    // Plain request without login
    axios.get<Check>(`/api/v1/verify/${token}/`).then(({ data }) => setCheck(data)).catch(() => setCheck({ valid: false }));
  }, [token]);

  if (!check) return <div style={{ display: 'flex', justifyContent: 'center', marginTop: '30vh' }}><Spin size="large" /></div>;

  const found = !!check.number || !!check.issued_on;
  return (
    <div className="verify-page">
      <div className="verify-brand">{clinicConfig.appName}</div>
      <Card className="verify-card">
        <Result
          icon={check.valid ? <CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} />
            : check.cancelled ? <WarningFilled style={{ color: '#d48806' }} /> : <CloseCircleFilled style={{ color: '#c0392b' }} />}
          title={check.valid ? t('verify.genuine') : check.cancelled ? t('verify.cancelled') : t('verify.notFound')}
          subTitle={found ? t('verify.subtitle') : t('verify.notFoundHelp')}
        />
        {found && (
          <dl className="verify-list">
            <dt>{t('verify.document')}</dt><dd>{t(`verify.kinds.${check.kind}`, { defaultValue: check.kind })}</dd>
            <dt>{t('verify.number')}</dt><dd>{check.number || '—'}</dd>
            <dt>{t('verify.date')}</dt><dd>{check.issued_on ? dayjs(check.issued_on).format('DD-MM-YYYY') : '—'}</dd>
            <dt>{t('verify.clinic')}</dt><dd>{check.clinic} · {check.branch}</dd>
            <dt>{t('verify.doctor')}</dt><dd>{check.doctor || '—'}</dd>
            <dt>{t('verify.patient')}</dt><dd>{check.patient_initials || '—'}</dd>
          </dl>
        )}
      </Card>
    </div>
  );
}
