// "Plan therapy" button on the doctor's check-up screen: opens the therapy plan form for this patient and check-up.
// Shown only when Panchakarma and therapy is switched on and the user may manage therapy.
import { HeartOutlined } from '@ant-design/icons';
import { App, Button } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { Page, TherapyType } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { PlanForm } from './PlansTab';

export function PlanTherapyButton({ patientId, patientName, visitId }: { patientId: string; patientName: string; visitId: string }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can, hasFeature } = useAuth();
  const [open, setOpen] = useState(false);
  const [therapies, setTherapies] = useState<TherapyType[]>([]);
  if (!hasFeature('panchakarma') || !can('therapy.manage')) return null;

  const show = async () => {
    const { data } = await api.get<Page<TherapyType> | TherapyType[]>('/therapies/');
    setTherapies(Array.isArray(data) ? data : data.results);
    setOpen(true);
  };

  return (
    <>
      <Button size="small" icon={<HeartOutlined />} onClick={() => show().catch(() => undefined)}>{t('therapy.plan.planTherapy')}</Button>
      <PlanForm open={open} therapies={therapies} patient={{ id: patientId, label: patientName }} visit={visitId}
        onClose={() => setOpen(false)} onSaved={() => { setOpen(false); message.success(t('therapy.plan.planned')); }} />
    </>
  );
}
