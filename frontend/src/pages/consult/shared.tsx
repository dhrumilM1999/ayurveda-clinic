// Small pieces used by the check-up screen.
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { Input } from 'antd';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMasterLabel, useMasters } from '../../api/masters';
import type { ExamField, ExamTemplate, Lang3, PrakritiResult } from '../../api/types';

/** Text of a {en, gu, hi} label in the current screen language. */
export function useLang3() {
  const { i18n } = useTranslation();
  return (label: Partial<Lang3> | undefined) =>
    (label && ((label as Record<string, string>)[i18n.language] || label.en)) || '';
}

export function useTemplateName() {
  const { i18n } = useTranslation();
  return (tpl: ExamTemplate) =>
    (i18n.language === 'gu' && tpl.name_gu) || (i18n.language === 'hi' && tpl.name_hi) || tpl.name;
}

const DOSHAS = ['vata', 'pitta', 'kapha'] as const;

/** Same scoring as the server (apps/emr/services.py), so the score shows while answering. */
export function scorePrakriti(fields: ExamField[], values: Record<string, unknown>): PrakritiResult | null {
  const counts = { vata: 0, pitta: 0, kapha: 0 };
  for (const field of fields) {
    const answer = values[field.key];
    if (answer === 'vata' || answer === 'pitta' || answer === 'kapha') counts[answer] += 1;
  }
  const answered = counts.vata + counts.pitta + counts.kapha;
  if (!answered) return null;
  const pct = Object.fromEntries(DOSHAS.map((d) => [d, Math.round((counts[d] * 100) / answered)])) as Record<string, number>;
  const ranked = [...DOSHAS].sort((a, b) => pct[b]! - pct[a]!);
  const [top, second, third] = ranked as [string, string, string];
  let type: string;
  if (pct[top]! - pct[third]! <= 10) type = 'sama';
  else if (pct[top]! >= 50 && pct[top]! - pct[second]! > 15) type = top;
  else type = DOSHAS.filter((d) => d === top || d === second).join('_');
  return { ...pct, type, answered, total: fields.length };
}

/** "vata_pitta" -> "Vata-Pitta" in the screen language. */
export function usePrakritiName() {
  const { t } = useTranslation();
  return (type?: string) => (type ? type.split('_').map((d) => t(`consult.dosha.${d}`)).join('-') : '');
}

/** Three labelled bars: Vata / Pitta / Kapha share in percent. */
export function PrakritiBars({ result }: { result: PrakritiResult }) {
  const { t } = useTranslation();
  return (
    <div className="dosha-bars" role="table" aria-label={t('consult.prakritiScore')}>
      {DOSHAS.map((d) => (
        <div className="dosha-row" role="row" key={d} title={`${t(`consult.dosha.${d}`)}: ${result[d] ?? 0}%`}>
          <span className="dosha-name" role="cell">{t(`consult.dosha.${d}`)}</span>
          <span className="dosha-track" role="cell">
            <span className={`dosha-fill dosha-${d}`} style={{ width: `${result[d] ?? 0}%` }} />
          </span>
          <span className="dosha-pct" role="cell">{result[d] ?? 0}%</span>
        </div>
      ))}
    </div>
  );
}

/**
 * Search box + quick-pick chips from a dropdown list (Healthray style).
 * Click a chip to add it; type something new and press Enter to add your own words.
 */
export function ChipPicker({ category, selected, onAdd, placeholder }: {
  category: string;
  selected: string[];
  onAdd: (label: string, code: string) => void;
  placeholder: string;
}) {
  const { t } = useTranslation();
  const values = useMasters(category);
  const label = useMasterLabel();
  const [search, setSearch] = useState('');

  const chips = useMemo(() => {
    const q = search.trim().toLowerCase();
    return values.filter((v) => {
      const text = label(v);
      if (selected.includes(text)) return false;
      return !q || [v.label, v.label_gu, v.label_hi].some((s) => s?.toLowerCase().includes(q));
    });
  }, [values, search, selected, label]);

  const addTyped = () => {
    const text = search.trim();
    if (!text) return;
    const match = values.find((v) => label(v).toLowerCase() === text.toLowerCase());
    onAdd(match ? label(match) : text, match?.code ?? '');
    setSearch('');
  };

  return (
    <div className="chip-picker">
      <Input
        allowClear
        size="small"
        prefix={<SearchOutlined />}
        placeholder={placeholder}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onPressEnter={addTyped}
        suffix={search.trim() ? <a onClick={addTyped}><PlusOutlined /> {t('consult.addTyped')}</a> : null}
      />
      <div className="chip-list">
        {chips.map((v) => (
          <button type="button" className="pick-chip" key={v.id} onClick={() => { onAdd(label(v), v.code); setSearch(''); }}>
            {label(v)}
          </button>
        ))}
        {!chips.length && search.trim() && <span className="cell-sub">{t('consult.pressEnterToAdd')}</span>}
      </div>
    </div>
  );
}
