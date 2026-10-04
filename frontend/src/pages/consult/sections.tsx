// The parts of the check-up screen. Each one edits a piece of the visit; the workspace saves it.
import { CloseOutlined } from '@ant-design/icons';
import { Button, DatePicker, Descriptions, Empty, Input, InputNumber, Radio, Segmented, Select, Space, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import type { Complaint, Diagnosis, ExamField, ExamTemplate, Visit } from '../../api/types';
import { ChipPicker, PrakritiBars, scorePrakriti, useLang3, usePrakritiName, useTemplateName } from './shared';

export type VisitDraft = Pick<Visit,
  'complaints' | 'history_notes' | 'examination_notes' | 'diagnoses' | 'advice' | 'advice_notes'
  | 'follow_up_date' | 'follow_up_notes'>;

interface SectionProps {
  draft: VisitDraft;
  onChange: (patch: Partial<VisitDraft>) => void;
  readOnly?: boolean;
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="section-title">{children}</div>;
}

// --- Complaints -------------------------------------------------------------------
export function ComplaintsSection({ draft, onChange, readOnly }: SectionProps) {
  const { t } = useTranslation();
  const list = draft.complaints;
  const update = (i: number, patch: Partial<Complaint>) =>
    onChange({ complaints: list.map((c, j) => (j === i ? { ...c, ...patch } : c)) });

  return (
    <>
      <SectionTitle>{t('consult.sections.complaints')}</SectionTitle>
      {!readOnly && (
        <ChipPicker category="complaint" selected={list.map((c) => c.label)} placeholder={t('consult.searchComplaints')}
          onAdd={(label, code) => onChange({ complaints: [...list, { label, code, duration: null, duration_unit: 'days', severity: '' }] })} />
      )}
      {list.length === 0 && <div className="cell-sub" style={{ marginTop: 8 }}>{t('consult.noneAdded')}</div>}
      <div className="item-rows">
        {list.map((c, i) => (
          <div className="item-row" key={`${c.label}-${i}`}>
            <b className="item-label">{c.label}</b>
            <Space.Compact size="small">
              <InputNumber size="small" min={0} max={999} placeholder={t('consult.since')} value={c.duration ?? undefined}
                disabled={readOnly} onChange={(v) => update(i, { duration: v ?? null })} style={{ width: 80 }} />
              <Select size="small" value={c.duration_unit ?? 'days'} disabled={readOnly} style={{ width: 92 }}
                onChange={(v) => update(i, { duration_unit: v })}
                options={['days', 'weeks', 'months', 'years'].map((u) => ({ value: u, label: t(`consult.units.${u}`) }))} />
            </Space.Compact>
            <Segmented size="small" value={c.severity || ''} disabled={readOnly}
              onChange={(v) => update(i, { severity: v as Complaint['severity'] })}
              options={[
                { value: '', label: '—' },
                ...['mild', 'moderate', 'severe'].map((s) => ({ value: s, label: t(`consult.severity.${s}`) })),
              ]} />
            <InputNumber size="small" min={0} max={10} precision={0} disabled={readOnly} style={{ width: 92 }}
              placeholder="0-10" addonBefore={t('consult.score')} value={c.score ?? undefined}
              title={t('consult.scoreHelp')} onChange={(v) => update(i, { score: v ?? null })} />
            <Input size="small" placeholder={t('consult.notes')} value={c.notes} disabled={readOnly} maxLength={500}
              onChange={(e) => update(i, { notes: e.target.value })} className="item-notes" />
            {!readOnly && (
              <Button size="small" type="text" icon={<CloseOutlined />} aria-label={t('common.remove')}
                onClick={() => onChange({ complaints: list.filter((_, j) => j !== i) })} />
            )}
          </div>
        ))}
      </div>
    </>
  );
}

// --- History & examination notes ------------------------------------------------------
export function NotesSection({ draft, onChange, readOnly }: SectionProps) {
  const { t } = useTranslation();
  return (
    <>
      <SectionTitle>{t('consult.sections.history')}</SectionTitle>
      <Input.TextArea autoSize={{ minRows: 4, maxRows: 14 }} value={draft.history_notes} disabled={readOnly}
        placeholder={t('consult.historyPlaceholder')} onChange={(e) => onChange({ history_notes: e.target.value })} />
      <SectionTitle>{t('consult.examination')}</SectionTitle>
      <Input.TextArea autoSize={{ minRows: 3, maxRows: 12 }} value={draft.examination_notes} disabled={readOnly}
        placeholder={t('consult.examinationPlaceholder')} onChange={(e) => onChange({ examination_notes: e.target.value })} />
    </>
  );
}

// --- Diagnosis --------------------------------------------------------------------------
export function DiagnosisSection({ draft, onChange, readOnly }: SectionProps) {
  const { t } = useTranslation();
  const list = draft.diagnoses;
  const update = (i: number, patch: Partial<Diagnosis>) =>
    onChange({ diagnoses: list.map((d, j) => (j === i ? { ...d, ...patch } : d)) });

  return (
    <>
      <SectionTitle>{t('consult.sections.diagnosis')}</SectionTitle>
      {!readOnly && (
        <ChipPicker category="diagnosis" selected={list.map((d) => d.label)} placeholder={t('consult.searchDiagnosis')}
          onAdd={(label, code) => onChange({ diagnoses: [...list, { label, master: code, kind: 'provisional', system: '', code: '' }] })} />
      )}
      {list.length === 0 && <div className="cell-sub" style={{ marginTop: 8 }}>{t('consult.noneAdded')}</div>}
      <div className="item-rows">
        {list.map((d, i) => (
          <div className="item-row" key={`${d.label}-${i}`}>
            <b className="item-label">{d.label}</b>
            <Segmented size="small" value={d.kind} disabled={readOnly}
              onChange={(v) => update(i, { kind: v as Diagnosis['kind'] })}
              options={[
                { value: 'provisional', label: t('consult.provisional') },
                { value: 'final', label: t('consult.final') },
              ]} />
            <Space.Compact size="small">
              <Select size="small" value={d.system ?? ''} disabled={readOnly} style={{ width: 104 }}
                onChange={(v) => update(i, { system: v })}
                options={[
                  { value: '', label: t('consult.noCode') },
                  { value: 'namaste', label: 'NAMASTE' },
                  { value: 'icd10', label: 'ICD-10' },
                  { value: 'icd11', label: 'ICD-11' },
                ]} />
              <Input size="small" placeholder={t('consult.code')} value={d.code} maxLength={30} style={{ width: 100 }}
                disabled={readOnly || !d.system} onChange={(e) => update(i, { code: e.target.value })} />
            </Space.Compact>
            <span style={{ flex: 1 }} />
            {!readOnly && (
              <Button size="small" type="text" icon={<CloseOutlined />} aria-label={t('common.remove')}
                onClick={() => onChange({ diagnoses: list.filter((_, j) => j !== i) })} />
            )}
          </div>
        ))}
      </div>
    </>
  );
}

// --- Advice (diet & lifestyle) ----------------------------------------------------------------
export function AdviceSection({ draft, onChange, readOnly }: SectionProps) {
  const { t } = useTranslation();
  return (
    <>
      <SectionTitle>{t('consult.sections.advice')}</SectionTitle>
      {!readOnly && (
        <ChipPicker category="advice" selected={draft.advice} placeholder={t('consult.searchAdvice')}
          onAdd={(label) => onChange({ advice: [...draft.advice, label] })} />
      )}
      <div className="chosen-tags">
        {draft.advice.map((a, i) => (
          <Tag key={`${a}-${i}`} color="green" closable={!readOnly}
            onClose={() => onChange({ advice: draft.advice.filter((_, j) => j !== i) })}>{a}</Tag>
        ))}
      </div>
      <SectionTitle>{t('consult.adviceNotes')}</SectionTitle>
      <Input.TextArea autoSize={{ minRows: 3, maxRows: 10 }} value={draft.advice_notes} disabled={readOnly}
        placeholder={t('consult.adviceNotesPlaceholder')} onChange={(e) => onChange({ advice_notes: e.target.value })} />
    </>
  );
}

// --- Follow-up -------------------------------------------------------------------------------
export function FollowUpSection({ draft, onChange, readOnly }: SectionProps) {
  const { t } = useTranslation();
  const set = (days: number) => onChange({ follow_up_date: dayjs().add(days, 'day').format('YYYY-MM-DD') });
  return (
    <>
      <SectionTitle>{t('consult.sections.followUp')}</SectionTitle>
      <Space wrap size={6}>
        {[7, 15, 30, 45].map((d) => (
          <Button key={d} size="small" disabled={readOnly} onClick={() => set(d)}>{t('consult.afterDays', { n: d })}</Button>
        ))}
        <DatePicker size="small" format="DD-MM-YYYY" disabled={readOnly}
          value={draft.follow_up_date ? dayjs(draft.follow_up_date) : null}
          disabledDate={(d) => d.isBefore(dayjs(), 'day')}
          onChange={(d) => onChange({ follow_up_date: d ? d.format('YYYY-MM-DD') : null })} />
      </Space>
      {draft.follow_up_date && (
        <div className="cell-sub" style={{ marginTop: 6 }}>
          {t('consult.followUpOn', { date: dayjs(draft.follow_up_date).format('dddd, DD-MM-YYYY') })}
        </div>
      )}
      <SectionTitle>{t('consult.notes')}</SectionTitle>
      <Input value={draft.follow_up_notes} maxLength={300} disabled={readOnly}
        placeholder={t('consult.followUpNotesPlaceholder')} onChange={(e) => onChange({ follow_up_notes: e.target.value })} />
    </>
  );
}

// --- Ayurveda templates (Ashtavidha, Dashavidha, Prakriti...) -----------------------------------
export function TemplateSection({ template, values, onChange, readOnly }: {
  template: ExamTemplate;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  readOnly?: boolean;
}) {
  const { t } = useTranslation();
  const lang = useLang3();
  const name = useTemplateName();
  const prakritiName = usePrakritiName();
  const set = (key: string, value: unknown) => onChange({ ...values, [key]: value });
  const score = template.kind === 'questionnaire' ? scorePrakriti(template.fields, values) : null;

  const renderField = (field: ExamField) => {
    const value = values[field.key];
    switch (field.type) {
      case 'choice':
        return (
          <Radio.Group size="small" optionType="button" buttonStyle="solid" disabled={readOnly}
            value={value} onChange={(e) => set(field.key, e.target.value)}
            options={(field.options ?? []).map((o) => ({ value: o.value, label: lang(o.label) }))} />
        );
      case 'multi': {
        const chosen = Array.isArray(value) ? (value as string[]) : [];
        return (
          <div className="chip-list">
            {(field.options ?? []).map((o) => (
              <Tag.CheckableTag key={o.value} checked={chosen.includes(o.value)} className="check-chip"
                onChange={(on) => !readOnly && set(field.key, on ? [...chosen, o.value] : chosen.filter((v) => v !== o.value))}>
                {lang(o.label)}
              </Tag.CheckableTag>
            ))}
          </div>
        );
      }
      case 'number':
        return (
          <InputNumber size="small" min={field.min} max={field.max} disabled={readOnly} style={{ width: 150 }}
            value={typeof value === 'number' ? value : undefined} addonAfter={field.unit}
            onChange={(v) => set(field.key, v ?? null)} />
        );
      default:
        return (
          <Input.TextArea autoSize={{ minRows: 2, maxRows: 8 }} disabled={readOnly} value={(value as string) ?? ''}
            onChange={(e) => set(field.key, e.target.value)} />
        );
    }
  };

  return (
    <>
      <div className="template-head">
        <div>
          <SectionTitle>{name(template)}</SectionTitle>
          {template.description && <div className="cell-sub">{lang(template.description)}</div>}
        </div>
        {!readOnly && Object.keys(values).length > 0 && (
          <Button size="small" type="link" onClick={() => onChange({})}>{t('consult.clearAll')}</Button>
        )}
      </div>
      <div className={template.kind === 'questionnaire' ? 'questionnaire' : ''}>
        <div className="template-fields">
          {template.fields.map((field, i) => (
            <div className="template-field" key={field.key}>
              <div className="template-label">
                {template.kind === 'questionnaire' && <span className="q-num">{i + 1}.</span>} {lang(field.label)}
              </div>
              {renderField(field)}
            </div>
          ))}
        </div>
        {template.kind === 'questionnaire' && (
          <div className="score-card">
            <div className="section-title" style={{ marginTop: 0 }}>{t('consult.prakritiScore')}</div>
            {score ? (
              <>
                <div className="score-type">{prakritiName(score.type)}</div>
                <PrakritiBars result={score} />
                <div className="cell-sub">{t('consult.answered', { n: score.answered, total: score.total })}</div>
              </>
            ) : <div className="cell-sub">{t('consult.answerToScore')}</div>}
          </div>
        )}
      </div>
    </>
  );
}

// --- Summary of everything filled in ---------------------------------------------------------
export function SummarySection({ draft, templates, exams, examFields = {} }: {
  draft: VisitDraft;
  templates: ExamTemplate[];
  exams: Record<string, Record<string, unknown>>;
  /** Questions of older template versions, for check-ups filled before a template changed */
  examFields?: Record<string, ExamField[]>;
}) {
  const { t } = useTranslation();
  const lang = useLang3();
  const name = useTemplateName();
  const prakritiName = usePrakritiName();

  const filledTemplates = templates
    .filter((tpl) => Object.keys(exams[tpl.code] ?? {}).length > 0)
    .map((tpl) => (examFields[tpl.code] ? { ...tpl, fields: examFields[tpl.code]! } : tpl));
  const nothing = !draft.complaints.length && !draft.diagnoses.length && !draft.advice.length && !draft.history_notes
    && !filledTemplates.length && !draft.follow_up_date;
  if (nothing) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('consult.summaryEmpty')} />;

  const answerText = (tpl: ExamTemplate, field: ExamField) => {
    const value = exams[tpl.code]?.[field.key];
    if (value === undefined || value === null || value === '') return null;
    const optionLabel = (v: unknown) => lang(field.options?.find((o) => o.value === v)?.label) || String(v);
    if (Array.isArray(value)) return value.map(optionLabel).join(', ');
    if (field.type === 'number') return `${value} ${field.unit ?? ''}`;
    return field.options ? optionLabel(value) : String(value);
  };

  return (
    <div className="summary">
      {draft.complaints.length > 0 && (
        <>
          <SectionTitle>{t('consult.sections.complaints')}</SectionTitle>
          <ul className="summary-list">
            {draft.complaints.map((c, i) => (
              <li key={i}>
                <b>{c.label}</b>
                {c.duration ? ` — ${c.duration} ${t(`consult.units.${c.duration_unit ?? 'days'}`)}` : ''}
                {c.severity ? ` · ${t(`consult.severity.${c.severity}`)}` : ''}
                {c.score !== null && c.score !== undefined ? ` · ${t('consult.score')} ${c.score}/10` : ''}
                {c.notes ? ` · ${c.notes}` : ''}
              </li>
            ))}
          </ul>
        </>
      )}
      {draft.history_notes && (
        <>
          <SectionTitle>{t('consult.sections.history')}</SectionTitle>
          <Typography.Paragraph className="pre-line">{draft.history_notes}</Typography.Paragraph>
        </>
      )}
      {draft.examination_notes && (
        <>
          <SectionTitle>{t('consult.examination')}</SectionTitle>
          <Typography.Paragraph className="pre-line">{draft.examination_notes}</Typography.Paragraph>
        </>
      )}
      {filledTemplates.map((tpl) => (
        <div key={tpl.code}>
          <SectionTitle>{name(tpl)}</SectionTitle>
          {tpl.kind === 'questionnaire' ? (() => {
            const score = scorePrakriti(tpl.fields, exams[tpl.code] ?? {});
            return score ? (
              <div style={{ maxWidth: 360 }}>
                <b>{prakritiName(score.type)}</b>
                <PrakritiBars result={score} />
              </div>
            ) : null;
          })() : (
            <Descriptions size="small" column={{ xs: 1, md: 2 }} bordered
              items={tpl.fields.map((f) => ({ key: f.key, label: lang(f.label), children: answerText(tpl, f) }))
                .filter((item) => item.children)} />
          )}
        </div>
      ))}
      {draft.diagnoses.length > 0 && (
        <>
          <SectionTitle>{t('consult.sections.diagnosis')}</SectionTitle>
          <ul className="summary-list">
            {draft.diagnoses.map((d, i) => (
              <li key={i}>
                <b>{d.label}</b> · {t(`consult.${d.kind}`)}
                {d.system && d.code ? ` · ${d.system.toUpperCase()} ${d.code}` : ''}
              </li>
            ))}
          </ul>
        </>
      )}
      {(draft.advice.length > 0 || draft.advice_notes) && (
        <>
          <SectionTitle>{t('consult.sections.advice')}</SectionTitle>
          <ul className="summary-list">{draft.advice.map((a, i) => <li key={i}>{a}</li>)}</ul>
          {draft.advice_notes && <Typography.Paragraph className="pre-line">{draft.advice_notes}</Typography.Paragraph>}
        </>
      )}
      {draft.follow_up_date && (
        <>
          <SectionTitle>{t('consult.sections.followUp')}</SectionTitle>
          <div>{dayjs(draft.follow_up_date).format('dddd, DD-MM-YYYY')}{draft.follow_up_notes ? ` · ${draft.follow_up_notes}` : ''}</div>
        </>
      )}
    </div>
  );
}
