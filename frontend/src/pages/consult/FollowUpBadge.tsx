// The follow-up (next visit) date, made easy to see. Used in the check-up header and on the Follow-up section.
// SAFE TO EDIT: the colours are in src/styles.css (.followup-badge); the words in src/i18n/*.json under "consult".
import { CalendarOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { followUpInfo } from './followUp';

export function FollowUpBadge({ date, big }: { date: string | null | undefined; big?: boolean }) {
  const { t } = useTranslation();
  const info = followUpInfo(date, dayjs().format('YYYY-MM-DD'));
  if (!info || !date) return null;
  const when = info.tone === 'today' ? t('consult.followUpWhen.today')
    : info.tone === 'past' ? t('consult.followUpWhen.past', { n: Math.abs(info.days) })
      : info.days === 1 ? t('consult.followUpWhen.tomorrow') : t('consult.followUpWhen.days', { n: info.days });
  return (
    <span className={`followup-badge followup-${info.tone}${big ? ' big' : ''}`} role="status">
      <CalendarOutlined aria-hidden="true" />
      <span>{t('consult.nextVisitOn', { date: dayjs(date).format('ddd, DD-MM-YYYY') })}</span>
      <span className="followup-when">{when}</span>
    </span>
  );
}
