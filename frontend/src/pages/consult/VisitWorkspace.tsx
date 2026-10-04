// One patient's check-up: header, section buttons (Healthray style), the open section, previous visits.
// Changes save by themselves a moment after typing stops (and on "Save").
import { AlertOutlined, CheckCircleOutlined, CloudSyncOutlined, FileSearchOutlined, SaveOutlined } from '@ant-design/icons';
import { Alert, App, Button, Card, Modal, Skeleton, Space, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { useMasterLabel } from '../../api/masters';
import type { ExamTemplate, Patient, Visit, VisitExam, VisitListItem } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { genderAge } from '../patients/PatientsPage';
import { VitalsTab } from '../patients/tabs/VitalsTab';
import {
  AdviceSection, ComplaintsSection, DiagnosisSection, FollowUpSection, NotesSection, SummarySection,
  TemplateSection, type VisitDraft,
} from './sections';
import { usePrakritiName, useTemplateName } from './shared';

const AUTOSAVE_MS = 1500;

function toDraft(v: Visit): VisitDraft {
  return {
    complaints: v.complaints, history_notes: v.history_notes, examination_notes: v.examination_notes,
    diagnoses: v.diagnoses, advice: v.advice, advice_notes: v.advice_notes,
    follow_up_date: v.follow_up_date, follow_up_notes: v.follow_up_notes,
  };
}

function toExams(exams: VisitExam[]) {
  return Object.fromEntries(exams.map((e) => [e.template_code, e.values]));
}

let templatesCache: Promise<ExamTemplate[]> | null = null;
function loadTemplates() {
  templatesCache ??= api.get<ExamTemplate[]>('/exam-templates/').then((r) => r.data)
    .catch((e) => { templatesCache = null; throw e; });
  return templatesCache;
}

export function VisitWorkspace({ visitId, onChanged, onLoaded }: {
  visitId: string;
  onChanged: () => void;
  onLoaded?: (visit: Visit) => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const templateName = useTemplateName();
  const prakritiName = usePrakritiName();
  const masterLabel = useMasterLabel();
  const [visit, setVisit] = useState<Visit | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [templates, setTemplates] = useState<ExamTemplate[]>([]);
  const [draft, setDraft] = useState<VisitDraft | null>(null);
  const [exams, setExams] = useState<Record<string, Record<string, unknown>>>({});
  const [section, setSection] = useState('complaints');
  const [saveState, setSaveState] = useState<'saved' | 'dirty' | 'saving' | 'error'>('saved');
  const [error, setError] = useState<string | null>(null);
  const readOnly = !can('emr.edit');

  // What still needs saving (kept in refs so the timer always sees the latest values)
  const dirtyDraft = useRef(false);
  const dirtyExams = useRef(new Set<string>());
  const latest = useRef<{ draft: VisitDraft | null; exams: Record<string, Record<string, unknown>> }>({ draft: null, exams: {} });
  latest.current = { draft, exams };
  const timer = useRef<number>();

  useEffect(() => {
    setVisit(null);
    setError(null);
    setSection('complaints');
    dirtyDraft.current = false;
    dirtyExams.current.clear();
    Promise.all([api.get<Visit>(`/visits/${visitId}/`), loadTemplates()])
      .then(([{ data }, tpls]) => {
        setVisit(data);
        onLoaded?.(data);
        setDraft(toDraft(data));
        setExams(toExams(data.exams));
        setTemplates(tpls);
        setSaveState('saved');
        return api.get<Patient>(`/patients/${data.patient}/`).then((p) => setPatient(p.data));
      })
      .catch((err) => setError(errorMessage(err, t('common.loadFailed'))));
  // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per visit
  }, [visitId, t]);

  const save = useCallback(async () => {
    window.clearTimeout(timer.current);
    const { draft: d, exams: ex } = latest.current;
    if (!d || (!dirtyDraft.current && dirtyExams.current.size === 0)) return true;
    setSaveState('saving');
    try {
      if (dirtyDraft.current) {
        dirtyDraft.current = false;
        await api.patch<Visit>(`/visits/${visitId}/`, d);
      }
      for (const code of [...dirtyExams.current]) {
        dirtyExams.current.delete(code);
        await api.put(`/visits/${visitId}/exams/${code}/`, { values: ex[code] ?? {} });
      }
      setSaveState(dirtyDraft.current || dirtyExams.current.size ? 'dirty' : 'saved');
      return true;
    } catch (err) {
      setSaveState('error');
      message.error(errorMessage(err, t('common.saveFailed')));
      return false;
    }
  }, [visitId, message, t]);

  // Save a moment after the last change; also save when leaving this visit.
  const scheduleSave = () => {
    setSaveState('dirty');
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(save, AUTOSAVE_MS);
  };
  useEffect(() => () => { save(); }, [save]);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirtyDraft.current || dirtyExams.current.size) e.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  const changeDraft = (patch: Partial<VisitDraft>) => {
    setDraft((d) => (d ? { ...d, ...patch } : d));
    dirtyDraft.current = true;
    scheduleSave();
  };
  const changeExam = (code: string, values: Record<string, unknown>) => {
    setExams((e) => ({ ...e, [code]: values }));
    dirtyExams.current.add(code);
    scheduleSave();
  };

  const complete = async () => {
    if (!(await save())) return;
    try {
      const { data } = await api.post<Visit>(`/visits/${visitId}/complete/`);
      setVisit(data);
      message.success(t('consult.completedMsg'));
      onChanged();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  if (error) return <Alert type="error" showIcon message={error} />;
  if (!visit || !draft) return <Card><Skeleton active paragraph={{ rows: 8 }} /></Card>;

  const filled: Record<string, boolean> = {
    complaints: draft.complaints.length > 0,
    history: !!(draft.history_notes || draft.examination_notes),
    diagnosis: draft.diagnoses.length > 0,
    advice: draft.advice.length > 0 || !!draft.advice_notes,
    followUp: !!draft.follow_up_date,
    ...Object.fromEntries(templates.map((tpl) => [`tpl:${tpl.code}`, Object.keys(exams[tpl.code] ?? {}).length > 0])),
  };
  const sections = [
    { key: 'summary', label: t('consult.sections.summary') },
    { key: 'complaints', label: t('consult.sections.complaints') },
    { key: 'history', label: t('consult.sections.history') },
    ...(can('patients.vitals') || can('emr.view') ? [{ key: 'vitals', label: t('consult.sections.vitals') }] : []),
    ...templates.map((tpl) => ({ key: `tpl:${tpl.code}`, label: templateName(tpl) })),
    { key: 'diagnosis', label: t('consult.sections.diagnosis') },
    { key: 'advice', label: t('consult.sections.advice') },
    { key: 'followUp', label: t('consult.sections.followUp') },
  ];
  const openTemplate = section.startsWith('tpl:') ? templates.find((tpl) => `tpl:${tpl.code}` === section) : undefined;
  const p = visit.patient_detail;
  const props = { draft, onChange: changeDraft, readOnly };

  return (
    <div className="workspace">
      <div className="workspace-main">
        <Card className="visit-head" size="small">
          <div className="visit-head-row">
            <div style={{ minWidth: 0 }}>
              <Space size={8} wrap>
                <Link to={`/patients/${p.id}`} className="visit-patient">{p.full_name}</Link>
                <span className="uhid-chip">{p.uhid}</span>
                <span className="cell-sub">{genderAge(t, p.gender, p.age_years)}</span>
                {visit.token_number && <span className="token-chip">#{visit.token_number}</span>}
                {visit.prakriti?.type && (
                  <Tag color="purple">{t('consult.prakritiTag', { type: prakritiName(visit.prakriti.type) })}</Tag>
                )}
                {visit.status === 'completed' && <Tag color="green" icon={<CheckCircleOutlined />}>{t('consult.completed')}</Tag>}
              </Space>
              <div className="cell-sub">
                {dayjs(visit.visit_date).format('DD-MM-YYYY')} · {visit.doctor_name} · {visit.branch_name}
              </div>
            </div>
            <Space size={8}>
              <span className={`save-state save-${saveState}`}>
                <CloudSyncOutlined /> {t(`consult.save.${saveState}`)}
              </span>
              {!readOnly && <Button size="small" icon={<SaveOutlined />} onClick={save}>{t('common.save')}</Button>}
              {!readOnly && visit.status !== 'completed' && (
                <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={complete}>{t('consult.complete')}</Button>
              )}
            </Space>
          </div>
          {patient && patient.allergies.length > 0 && (
            <Alert type="error" showIcon icon={<AlertOutlined />} className="visit-allergy"
              message={<><b>{t('patients.allergyAlert')}:</b> {patient.allergies.map((a) => a.allergen).join(', ')}</>} />
          )}
          {patient && (patient.conditions?.length ?? 0) > 0 && (
            <div className="cell-sub" style={{ marginTop: 6 }}>
              {t('consult.knownConditions')}:{' '}
              {patient.conditions!.map((c) => (typeof c.condition === 'string' ? '' : masterLabel(c.condition))).filter(Boolean).join(', ')}
            </div>
          )}
        </Card>

        <div className="section-nav">
          {sections.map((s) => (
            <button type="button" key={s.key} className={`section-btn${section === s.key ? ' active' : ''}`}
              onClick={() => setSection(s.key)}>
              {filled[s.key] && <span className="filled-dot" aria-label={t('consult.filled')} />}
              {s.label}
            </button>
          ))}
        </div>

        <Card size="small" className="section-card">
          {section === 'summary' && <SummarySection draft={draft} templates={templates} exams={exams} />}
          {section === 'complaints' && <ComplaintsSection {...props} />}
          {section === 'history' && <NotesSection {...props} />}
          {section === 'vitals' && <VitalsTab patientId={visit.patient} />}
          {openTemplate && (
            <TemplateSection template={openTemplate} values={exams[openTemplate.code] ?? {}} readOnly={readOnly}
              onChange={(values) => changeExam(openTemplate.code, values)} />
          )}
          {section === 'diagnosis' && <DiagnosisSection {...props} />}
          {section === 'advice' && <AdviceSection {...props} />}
          {section === 'followUp' && <FollowUpSection {...props} />}
        </Card>
      </div>

      <PreviousVisits patientId={visit.patient} currentId={visit.id} templates={templates} />
    </div>
  );
}

/** Right panel: the patient's earlier check-ups (all branches). Click one to read it. */
function PreviousVisits({ patientId, currentId, templates }: { patientId: string; currentId: string; templates: ExamTemplate[] }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<VisitListItem[]>([]);
  const [open, setOpen] = useState<Visit | null>(null);

  useEffect(() => {
    api.get<{ results: VisitListItem[] }>('/visits/', { params: { patient: patientId, page_size: 30 } })
      .then(({ data }) => setRows(data.results.filter((v) => v.id !== currentId)))
      .catch(() => setRows([]));
  }, [patientId, currentId]);

  return (
    <aside className="workspace-side">
      <div className="section-title" style={{ marginTop: 0 }}><FileSearchOutlined /> {t('consult.previousVisits')}</div>
      {rows.length === 0 && <div className="cell-sub">{t('consult.firstVisit')}</div>}
      {rows.map((v) => (
        <button type="button" className="prev-visit" key={v.id}
          onClick={() => api.get<Visit>(`/visits/${v.id}/`).then(({ data }) => setOpen(data))}>
          <div className="prev-visit-date">{dayjs(v.visit_date).format('DD-MM-YYYY')}</div>
          <div className="cell-sub">{v.doctor_name} · {v.branch_name}</div>
          {v.diagnoses.length > 0 && <div className="prev-visit-dx">{v.diagnoses.join(', ')}</div>}
          {v.complaints.length > 0 && <div className="cell-sub">{v.complaints.join(', ')}</div>}
        </button>
      ))}
      <Modal open={!!open} width={760} title={open ? t('consult.visitOf', { date: dayjs(open.visit_date).format('DD-MM-YYYY') }) : ''}
        onCancel={() => setOpen(null)} footer={<Button onClick={() => setOpen(null)}>{t('common.close')}</Button>}>
        {open && (
          <>
            <div className="cell-sub" style={{ marginBottom: 8 }}>{open.doctor_name} · {open.branch_name}</div>
            <SummarySection draft={toDraft(open)} templates={templates} exams={toExams(open.exams)} />
          </>
        )}
      </Modal>
    </aside>
  );
}
