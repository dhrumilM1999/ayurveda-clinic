import { LockOutlined } from '@ant-design/icons';
import { Alert, Col, Empty, Row, Table, Tag, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useMasterLabel } from '../../../api/masters';
import type { MasterRef, Patient, PatientAllergy, PatientMedication } from '../../../api/types';

const SEVERITY_COLOR = { mild: 'green', moderate: 'orange', severe: 'red' } as const;

export function MedicalTab({ patient: p }: { patient: Patient }) {
  const { t } = useTranslation();
  const label = useMasterLabel();

  return (
    <Row gutter={[12, 12]}>
      <Col span={24}>
        <Typography.Title level={5}>{t('patients.fields.conditions')}</Typography.Title>
        {p.medical_history_hidden ? (
          <Alert type="info" showIcon icon={<LockOutlined />} message={t('patients.historyHidden')} />
        ) : p.conditions && p.conditions.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {p.conditions.map((c) => (
              <Tag key={c.id} color="purple" style={{ padding: '4px 10px', fontSize: 13 }}>
                {label(c.condition as MasterRef)}{c.since ? ` · ${c.since}` : ''}
              </Tag>
            ))}
          </div>
        ) : (
          <Typography.Text type="secondary">{t('patients.noneRecorded')}</Typography.Text>
        )}
      </Col>

      <Col xs={24} lg={12}>
        <Typography.Title level={5}>{t('patients.fields.allergies')}</Typography.Title>
        <Table<PatientAllergy>
          rowKey="id" size="small" pagination={false} dataSource={p.allergies}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('patients.noAllergies')} /> }}
          columns={[
            { title: t('patients.allergen'), dataIndex: 'allergen' },
            { title: t('patients.allergyType'), dataIndex: 'allergy_type', render: (v: MasterRef | null) => label(v) },
            { title: t('patients.severityLabel'), dataIndex: 'severity', render: (s: 'mild') => <Tag color={SEVERITY_COLOR[s]}>{t(`patients.severity.${s}`)}</Tag> },
            { title: t('patients.reaction'), dataIndex: 'reaction' },
          ]}
        />
      </Col>
      <Col xs={24} lg={12}>
        <Typography.Title level={5}>{t('patients.fields.medications')}</Typography.Title>
        <Table<PatientMedication>
          rowKey="id" size="small" pagination={false} dataSource={p.medications}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('patients.noneRecorded')} /> }}
          columns={[
            { title: t('patients.medicineName'), dataIndex: 'name' },
            { title: t('patients.dose'), dataIndex: 'dose' },
            { title: t('patients.frequency'), dataIndex: 'frequency' },
            { title: t('patients.since'), dataIndex: 'since' },
          ]}
        />
      </Col>

      {!p.medical_history_hidden && (
        <Col span={24}>
          <Row gutter={[12, 12]}>
            {(['past_history', 'family_history', 'surgical_history', 'other_notes'] as const).map((f) => (
              <Col xs={24} md={12} key={f}>
                <div className="history-box">
                  <div className="history-label">{t(`patients.fields.${f}`)}</div>
                  <div className="history-text">{p[f] || <Typography.Text type="secondary">—</Typography.Text>}</div>
                </div>
              </Col>
            ))}
          </Row>
        </Col>
      )}
    </Row>
  );
}
