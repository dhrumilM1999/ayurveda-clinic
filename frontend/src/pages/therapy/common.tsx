// Small pieces shared by the therapy screens.
// SAFE TO EDIT: colours of the stage / status tags. The words are in src/i18n/*.json under "therapy".
import { Tag } from 'antd';
import { useTranslation } from 'react-i18next';
import type { TherapyPlanStatus, TherapySessionStatus, TherapyStage } from '../../api/types';

export const STAGES: TherapyStage[] = ['purva', 'pradhana', 'paschat', 'other'];

export const STAGE_COLORS: Record<TherapyStage, string> = { purva: 'blue', pradhana: 'volcano', paschat: 'green', other: 'default' };
export const SESSION_COLORS: Record<TherapySessionStatus, string> = {
  scheduled: 'blue', in_progress: 'gold', done: 'green', missed: 'red', cancelled: 'default',
};
export const PLAN_COLORS: Record<TherapyPlanStatus, string> = { planned: 'blue', active: 'gold', completed: 'green', cancelled: 'default' };

/** The therapy name in the language the user chose (falls back to English). */
export function useTherapyName() {
  const { i18n } = useTranslation();
  return (x: { therapy_name?: string; therapy_name_gu?: string; therapy_name_hi?: string; name?: string; name_gu?: string; name_hi?: string }) => {
    const en = x.therapy_name ?? x.name ?? '';
    if (i18n.language === 'gu') return (x.therapy_name_gu ?? x.name_gu) || en;
    if (i18n.language === 'hi') return (x.therapy_name_hi ?? x.name_hi) || en;
    return en;
  };
}

export function StageTag({ stage }: { stage: TherapyStage }) {
  const { t } = useTranslation();
  return <Tag color={STAGE_COLORS[stage]} style={{ marginInlineEnd: 0 }}>{t(`therapy.stage.${stage}`).split(' (')[0]}</Tag>;
}

export function SessionStatusTag({ status }: { status: TherapySessionStatus }) {
  const { t } = useTranslation();
  return <Tag color={SESSION_COLORS[status]} style={{ marginInlineEnd: 0 }}>{t(`therapy.status.${status}`)}</Tag>;
}

export function PlanStatusTag({ status }: { status: TherapyPlanStatus }) {
  const { t } = useTranslation();
  return <Tag color={PLAN_COLORS[status]} style={{ marginInlineEnd: 0 }}>{t(`therapy.planStatus.${status}`)}</Tag>;
}

export const hhmm = (time: string | null | undefined) => (time ? time.slice(0, 5) : '');
