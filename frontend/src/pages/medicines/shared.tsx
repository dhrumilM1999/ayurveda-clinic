// Small pieces used by the medicine and prescription screens.
import { Tag, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import type { Medicine, MedicineFlag } from '../../api/types';

export const FLAG_COLORS: Record<MedicineFlag, string> = {
  schedule_e1: 'red',
  contains_metals: 'volcano',
  pregnancy_caution: 'magenta',
  child_caution: 'purple',
};
export const FLAGS = Object.keys(FLAG_COLORS) as MedicineFlag[];

/** "₹ 120.00" (or — when there is no price) */
export function money(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '—';
  return `₹ ${Number(value).toFixed(2)}`;
}

/** The medicine's name in the screen language (falls back to English). */
export function useMedicineName() {
  const { i18n } = useTranslation();
  return (m: Pick<Medicine, 'name' | 'name_gu' | 'name_hi'>) =>
    (i18n.language === 'gu' && m.name_gu) || (i18n.language === 'hi' && m.name_hi) || m.name;
}

/** Small coloured tags for Schedule E1, metals, pregnancy and child caution. */
export function MedicineFlags({ medicine, flags }: { medicine?: Medicine; flags?: MedicineFlag[] }) {
  const { t } = useTranslation();
  const list = flags ?? FLAGS.filter((f) => medicine?.[f]);
  if (!list.length) return null;
  return (
    <span className="flag-tags">
      {list.map((f) => (
        <Tooltip key={f} title={t(`medicines.flagHelp.${f}`)}>
          <Tag color={FLAG_COLORS[f]} className="tag-tight">{t(`medicines.flagShort.${f}`)}</Tag>
        </Tooltip>
      ))}
    </span>
  );
}
