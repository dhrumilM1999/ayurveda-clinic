// Panchakarma and therapy: the day's sessions, therapy plans, and the list of therapies.
// SAFE TO EDIT: the words are in src/i18n/*.json under "therapy".
import { Alert, Tabs } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { Page, TherapyType } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import PlansTab from './PlansTab';
import SessionsTab from './SessionsTab';
import TherapiesTab from './TherapiesTab';

export default function TherapyPage() {
  const { t } = useTranslation();
  const { hasFeature } = useAuth();
  const [therapies, setTherapies] = useState<TherapyType[]>([]);

  const loadTherapies = useCallback(async () => {
    const { data } = await api.get<Page<TherapyType> | TherapyType[]>('/therapies/');
    setTherapies(Array.isArray(data) ? data : data.results);
  }, []);
  useEffect(() => { loadTherapies().catch(() => undefined); }, [loadTherapies]);

  if (!hasFeature('panchakarma')) return <Alert type="info" showIcon message={t('therapy.off')} />;
  return (
    <div>
      <div className="page-toolbar">
        <div>
          <div className="page-title">{t('therapy.title')}</div>
          <div className="cell-sub">{t('therapy.subtitle')}</div>
        </div>
      </div>
      <Tabs destroyOnHidden
        items={[
          { key: 'sessions', label: t('therapy.tabs.sessions'), children: <SessionsTab /> },
          { key: 'plans', label: t('therapy.tabs.plans'), children: <PlansTab therapies={therapies} /> },
          { key: 'list', label: t('therapy.tabs.list'), children: <TherapiesTab rows={therapies} reload={loadTherapies} /> },
        ]}
      />
    </div>
  );
}
