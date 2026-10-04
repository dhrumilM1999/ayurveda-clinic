// Patient list with search (by name, mobile number or patient ID). Phone numbers are masked.
import { AlertOutlined, CrownOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Input, Segmented, Space, Table, Tag, Tooltip, Typography } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useMasterLabel } from '../../api/masters';
import type { PatientListItem } from '../../api/types';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { PatientPhoto } from '../../components/PatientPhoto';

export function genderAge(t: (key: string) => string, gender: string, age: number | null) {
  const g = t(`patients.genderShort.${gender}`);
  return age === null ? g : `${age} ${t('patients.yearsShort')} · ${g}`;
}

export default function PatientsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { can } = useAuth();
  const masterLabel = useMasterLabel();
  const [search, setSearch] = useState('');
  const [gender, setGender] = useState<string>('all');
  const { rows, loading, pagination, total } = useList<PatientListItem>('/patients/', {
    q: search || undefined,
    gender: gender === 'all' ? undefined : gender,
  });

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('patients.title')}</Typography.Title>
          <Typography.Text type="secondary">{t('patients.count', { n: total })}</Typography.Text>
        </div>
        {can('patients.create') && (
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => navigate('/patients/new')}>
            {t('patients.register')}
          </Button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <Input.Search
          size="large"
          allowClear
          prefix={<SearchOutlined style={{ opacity: 0.45 }} />}
          placeholder={t('patients.searchPlaceholder')}
          onSearch={(value) => setSearch(value.trim())}
          style={{ maxWidth: 520, flex: 1 }}
          enterButton={t('common.search')}
        />
        <Segmented
          size="large"
          value={gender}
          onChange={(v) => setGender(String(v))}
          options={[
            { value: 'all', label: t('patients.all') },
            { value: 'male', label: t('patients.gender.male') },
            { value: 'female', label: t('patients.gender.female') },
          ]}
        />
      </div>

      <Table<PatientListItem>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        scroll={{ x: true }}
        onRow={(record) => ({ onClick: () => navigate(`/patients/${record.id}`), style: { cursor: 'pointer' } })}
        locale={{ emptyText: search ? t('patients.noResults') : t('patients.empty') }}
        columns={[
          {
            title: t('patients.patient'),
            key: 'name',
            render: (_: unknown, p: PatientListItem) => (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <PatientPhoto patientId={p.id} hasPhoto={p.has_photo} name={p.full_name} size={42} />
                <div>
                  <div style={{ fontWeight: 600 }}>
                    {p.title ? `${masterLabel(p.title)} ` : ''}{p.full_name}
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 12, fontFamily: 'monospace' }}>{p.uhid}</Typography.Text>
                </div>
              </div>
            ),
          },
          { title: t('patients.ageGender'), key: 'age', render: (_: unknown, p: PatientListItem) => genderAge(t, p.gender, p.age_years) },
          { title: t('patients.mobile'), dataIndex: 'mobile_masked', render: (m: string) => <span style={{ fontFamily: 'monospace' }}>{m}</span> },
          { title: t('patients.city'), dataIndex: 'city' },
          {
            title: t('patients.registered'), dataIndex: 'registration_date',
            render: (d: string, p: PatientListItem) => (
              <div>
                <div>{dayjs(d).format('DD-MM-YYYY')}</div>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>{p.registered_branch_name}</Typography.Text>
              </div>
            ),
          },
          {
            title: '', key: 'flags',
            render: (_: unknown, p: PatientListItem) => (
              <Space size={4}>
                {p.allergy_count > 0 && (
                  <Tooltip title={t('patients.hasAllergies')}><Tag color="red" icon={<AlertOutlined />}>{t('patients.allergyShort')}</Tag></Tooltip>
                )}
                {p.is_vip && <Tag color="gold" icon={<CrownOutlined />}>VIP</Tag>}
                {p.is_foc && <Tag color="blue">FOC</Tag>}
              </Space>
            ),
          },
        ]}
      />
    </>
  );
}
