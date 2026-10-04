import { Col, Descriptions, Row } from 'antd';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { useMasterLabel } from '../../../api/masters';
import type { Patient } from '../../../api/types';
import { LANGUAGES } from '../../../i18n';

export function OverviewTab({ patient: p }: { patient: Patient }) {
  const { t } = useTranslation();
  const label = useMasterLabel();
  const dash = (v?: string | null) => v || '—';
  const address = [p.house, p.society, p.area, p.city, p.pincode, p.state].filter(Boolean).join(', ');

  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} lg={12}>
        <Descriptions title={t('patients.sections.details')} column={1} size="small" bordered>
          <Descriptions.Item label={t('patients.fields.dob')}>
            {p.date_of_birth ? dayjs(p.date_of_birth).format('DD-MM-YYYY') : '—'}{p.dob_is_estimated ? ` (${t('patients.approx')})` : ''}
          </Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.gender')}>{t(`patients.gender.${p.gender}`)}</Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.blood_group')}>{dash(label(p.blood_group))}</Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.marital_status')}>{dash(label(p.marital_status))}</Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.preferred_language')}>
            {LANGUAGES.find((l) => l.code === p.preferred_language)?.label}
          </Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.occupation')}>{dash(p.occupation)}</Descriptions.Item>
          {p.guardian_name ? <Descriptions.Item label={t('patients.fields.guardian_name')}>{p.guardian_name}</Descriptions.Item> : null}
          <Descriptions.Item label={t('patients.registered')}>
            {dayjs(p.registration_date).format('DD-MM-YYYY')} · {p.registered_branch_name}{p.created_by_name ? ` · ${p.created_by_name}` : ''}
          </Descriptions.Item>
        </Descriptions>
      </Col>
      <Col xs={24} lg={12}>
        <Descriptions title={t('patients.sections.contact')} column={1} size="small" bordered>
          <Descriptions.Item label={t('patients.fields.mobile')}>{p.country_code} {p.mobile}</Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.alternate_mobile')}>{dash(p.alternate_mobile)}</Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.email')}>{dash(p.email)}</Descriptions.Item>
          <Descriptions.Item label={t('patients.address')}>{dash(address)}</Descriptions.Item>
        </Descriptions>
        <Descriptions title={t('patients.sections.emergency')} column={1} size="small" bordered style={{ marginTop: 24 }}>
          <Descriptions.Item label={t('patients.fields.emergency_name')}>
            {p.emergency_name ? `${p.emergency_name}${p.emergency_relation ? ` (${label(p.emergency_relation)})` : ''}` : '—'}
          </Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.emergency_phone')}>{dash(p.emergency_phone)}</Descriptions.Item>
        </Descriptions>
        <Descriptions title={t('patients.sections.referral')} column={1} size="small" bordered style={{ marginTop: 24 }}>
          <Descriptions.Item label={t('patients.fields.referral_source')}>{dash(label(p.referral_source))}</Descriptions.Item>
          <Descriptions.Item label={t('patients.fields.referred_by_name')}>
            {p.referred_by_name ? `${p.referred_by_name}${p.referred_by_phone ? ` · ${p.referred_by_phone}` : ''}` : '—'}
          </Descriptions.Item>
        </Descriptions>
      </Col>
    </Row>
  );
}
