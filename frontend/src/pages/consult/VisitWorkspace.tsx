// One patient's check-up: header, section buttons (Healthray style), the open section, previous visits.
// - Autosave: changes save by themselves a moment after typing stops (and on "Save"). If saving fails
//   (e.g. no network) it tries again, and nothing typed is lost.
// - Undo / Redo: buttons at the top, or Ctrl+Z / Ctrl+Y (Ctrl+Shift+Z) while the check-up is open.
// SAFE TO EDIT: AUTOSAVE_MS, RETRY_MS, UNDO_STEPS below.
import {
  AlertOutlined, CheckCircleOutlined, CloudSyncOutlined, FileSearchOutlined, RedoOutlined, SaveOutlined, UndoOutlined,
} from '@ant-design/icons';
import { Alert, App, Button, Card, Modal, Skeleton, Space, Tag, Tooltip } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import { useMasterLabel } from '../../api/masters';
import type {
  ExamField, ExamTemplate, Page, Patient, Prescription, RxLine, RxWarning, Visit, VisitExam, VisitListItem,
} from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { genderAge } from '../patients/PatientsPage';
import { VitalsTab } from '../patients/tabs/VitalsTab';
import {
  AdviceSection, ComplaintsSection, DiagnosisSection, FollowUpSection, NotesSection, SummarySection,
  TemplateSection, type VisitDraft,
} from './sections';
import { PhotosSection, ProgressSection } from './extraSections';
import { RxSection, type RxDraft } from './RxSection';
import { usePrakritiName, useTemplateName } from './shared';

const AUTOSAVE_MS = 1500; // save this long after the last change
const RETRY_MS = 8000; // if saving failed, try again after this long
const UNDO_STEPS = 100; // how many changes Undo remembers
const GROUP_MS = 1000; // typing in one box within this time = one Undo step

type Doc = { draft: VisitDraft; exams: Record<string, Record<string, unknown>>; rx: RxDraft };
const EMPTY_RX: RxDraft = { items: [], notes: '' };

/** Lines as the API wants them (without screen-only fields). */
function rxPayload(items: RxLine[]) {
  return items.map(({ medicine_flags: _f, medicine_kind: _k, medicine_version: _v, ...line }) => line);
}

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

/** Questions of exams filled with an older template version (so old answers show correctly). */
function toExamFields(exams: VisitExam[], templates: ExamTemplate[]): Record<string, ExamField[]> {
  const current = Object.fromEntries(templates.map((tpl) => [tpl.code, tpl.version]));
  return Object.fromEntries(exams.filter((e) => e.template_version !== current[e.template_code])
    .map((e) => [e.template_code, e.template_fields]));
}

let templatesCache: Promise<ExamTemplate[]> | null = null;
/** Call after templates were edited, so the next check-up loads the new questions. */
export function clearTemplatesCache() {
  templatesCache = null;
}
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
  const [rx, setRx] = useState<RxDraft>(EMPTY_RX);
  const [rxWarnings, setRxWarnings] = useState<RxWarning[]>([]);
  const [section, setSection] = useState('complaints');
  const [saveState, setSaveState] = useState<'saved' | 'dirty' | 'saving' | 'error'>('saved');
  const [error, setError] = useState<string | null>(null);
  const readOnly = !can('emr.edit');
  const canSeeRx = can('prescriptions.view');
  const rxReadOnly = !can('prescriptions.create');

  // What still needs saving (kept in refs so the timer always sees the latest values)
  const dirtyDraft = useRef(false);
  const dirtyExams = useRef(new Set<string>());
  const dirtyRx = useRef(false);
  const latest = useRef<{ draft: VisitDraft | null; exams: Record<string, Record<string, unknown>>; rx: RxDraft }>(
    { draft: null, exams: {}, rx: EMPTY_RX });
  latest.current = { draft, exams, rx };
  const timer = useRef<number>();
  const inFlight = useRef<Promise<boolean> | null>(null);

  // Undo / redo history
  const past = useRef<Doc[]>([]);
  const future = useRef<Doc[]>([]);
  const lastEdit = useRef({ at: 0, key: '' });
  const [, setHistoryVersion] = useState(0);
  const workspaceRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVisit(null);
    setError(null);
    setSection('complaints');
    dirtyDraft.current = false;
    dirtyExams.current.clear();
    dirtyRx.current = false;
    setRx(EMPTY_RX);
    setRxWarnings([]);
    past.current = [];
    future.current = [];
    Promise.all([api.get<Visit>(`/visits/${visitId}/`), loadTemplates()])
      .then(([{ data }, tpls]) => {
        setVisit(data);
        onLoaded?.(data);
        setDraft(toDraft(data));
        setExams(toExams(data.exams));
        setTemplates(tpls);
        setSaveState('saved');
        if (canSeeRx) {
          api.get<Page<Prescription>>('/prescriptions/', { params: { visit: data.id } }).then(({ data: page }) => {
            const found = page.results[0];
            if (found) {
              setRx({ id: found.id, items: found.items, notes: found.notes, status: found.status });
              setRxWarnings(found.warnings);
            }
          }).catch(() => undefined);
        }
        return api.get<Patient>(`/patients/${data.patient}/`).then((p) => setPatient(p.data));
      })
      .catch((err) => setError(errorMessage(err, t('common.loadFailed'))));
  // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per visit
  }, [visitId, t]);

  const hasUnsaved = () => dirtyDraft.current || dirtyExams.current.size > 0 || dirtyRx.current;

  const save = useCallback(async (): Promise<boolean> => {
    window.clearTimeout(timer.current);
    // Never run two saves at the same time: wait for the running one, then save what is left.
    if (inFlight.current) await inFlight.current;
    if (!latest.current.draft || !(dirtyDraft.current || dirtyExams.current.size || dirtyRx.current)) return true;

    const run = (async () => {
      const { draft: d, exams: ex, rx: r } = latest.current;
      const sendDraft = dirtyDraft.current;
      const codes = [...dirtyExams.current];
      const sendRx = dirtyRx.current;
      dirtyDraft.current = false;
      dirtyExams.current.clear();
      dirtyRx.current = false;
      setSaveState('saving');
      try {
        if (sendDraft) await api.patch<Visit>(`/visits/${visitId}/`, d);
        for (const code of codes) {
          const { data } = await api.put<VisitExam>(`/visits/${visitId}/exams/${code}/`, { values: ex[code] ?? {} });
          if (data.template_code === 'prakriti' && 'answered' in data.result && data.result.answered) {
            // Show the new Prakriti in the header straight away
            setVisit((v) => (v ? { ...v, prakriti: { ...data.result, visit_date: v.visit_date } as Visit['prakriti'] } : v));
          }
        }
        if (sendRx) {
          const sent = r.items;
          const body = { items: rxPayload(sent), notes: r.notes };
          const { data } = r.id
            ? await api.patch<Prescription>(`/prescriptions/${r.id}/`, body)
            : await api.post<Prescription>('/prescriptions/', { ...body, visit: visitId });
          // New lines get their id from the server (matched by the line objects that were sent)
          setRx((cur) => ({
            ...cur, id: data.id, status: data.status,
            items: cur.items.map((line) => {
              const index = sent.indexOf(line);
              return index >= 0 && !line.id ? { ...line, id: data.items[index]?.id } : line;
            }),
          }));
          setRxWarnings(data.warnings);
        }
        setSaveState(dirtyDraft.current || dirtyExams.current.size || dirtyRx.current ? 'dirty' : 'saved');
        return true;
      } catch (err) {
        // Keep the changes marked as unsaved and try again a little later
        if (sendDraft) dirtyDraft.current = true;
        if (sendRx) dirtyRx.current = true;
        codes.forEach((c) => dirtyExams.current.add(c));
        setSaveState('error');
        message.error(errorMessage(err, t('common.saveFailed')));
        window.clearTimeout(timer.current);
        timer.current = window.setTimeout(() => { save(); }, RETRY_MS);
        return false;
      }
    })();
    inFlight.current = run;
    const ok = await run;
    inFlight.current = null;
    return ok;
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
      if (hasUnsaved()) e.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, []);

  /** Remember the state before a change, so Undo can go back to it. */
  const remember = (key: string) => {
    const current = latest.current;
    if (!current.draft) return;
    const now = Date.now();
    // Typing in the same box without a pause counts as one change
    if (now - lastEdit.current.at > GROUP_MS || lastEdit.current.key !== key) {
      past.current.push({ draft: current.draft, exams: current.exams, rx: current.rx });
      if (past.current.length > UNDO_STEPS) past.current.shift();
    }
    lastEdit.current = { at: now, key };
    future.current = [];
    setHistoryVersion((n) => n + 1);
  };

  const changeDraft = (patch: Partial<VisitDraft>) => {
    remember(`draft:${Object.keys(patch).join(',')}`);
    setDraft((d) => (d ? { ...d, ...patch } : d));
    dirtyDraft.current = true;
    scheduleSave();
  };
  const changeRx = (patch: Partial<RxDraft>) => {
    remember(`rx:${Object.keys(patch).join(',')}`);
    setRx((r) => ({ ...r, ...patch }));
    dirtyRx.current = true;
    scheduleSave();
  };
  const changeExam = (code: string, values: Record<string, unknown>) => {
    remember(`exam:${code}`);
    setExams((e) => ({ ...e, [code]: values }));
    dirtyExams.current.add(code);
    scheduleSave();
  };

  /** Put back an earlier state and save it. */
  const restore = (doc: Doc) => {
    const current = latest.current;
    if (doc.draft !== current.draft) dirtyDraft.current = true;
    if (doc.rx !== current.rx) dirtyRx.current = true;
    for (const code of new Set([...Object.keys(doc.exams), ...Object.keys(current.exams)])) {
      if (doc.exams[code] !== current.exams[code]) dirtyExams.current.add(code);
    }
    setDraft(doc.draft);
    setExams(doc.exams);
    // Keep the prescription's server id even when going back to before it was first saved
    const restoredRx = { ...doc.rx, id: doc.rx.id ?? current.rx.id };
    setRx(restoredRx);
    latest.current = { ...doc, rx: restoredRx };
    lastEdit.current = { at: 0, key: '' };
    setHistoryVersion((n) => n + 1);
    scheduleSave();
  };
  const undo = () => {
    const previous = past.current.pop();
    const current = latest.current;
    if (!previous || !current.draft) return;
    future.current.push({ draft: current.draft, exams: current.exams, rx: current.rx });
    restore(previous);
  };
  const redo = () => {
    const next = future.current.pop();
    const current = latest.current;
    if (!next || !current.draft) return;
    past.current.push({ draft: current.draft, exams: current.exams, rx: current.rx });
    restore(next);
  };

  // Keyboard: Ctrl+Z = undo, Ctrl+Y or Ctrl+Shift+Z = redo (only while this check-up is in use)
  const keys = useRef({ undo, redo });
  keys.current = { undo, redo };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || readOnly) return;
      const active = document.activeElement;
      const inside = !active || active === document.body || workspaceRef.current?.contains(active);
      if (!inside || document.querySelector('.ant-modal-wrap:not([style*="display: none"])')) return;
      const key = e.key.toLowerCase();
      if (key === 'z' && !e.shiftKey) { e.preventDefault(); keys.current.undo(); }
      else if (key === 'y' || (key === 'z' && e.shiftKey)) { e.preventDefault(); keys.current.redo(); }
      else if (key === 's') { e.preventDefault(); save(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [readOnly, save]);

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
    progress: draft.complaints.some((c) => c.score !== null && c.score !== undefined),
    photos: visit.photos.length > 0,
    rx: rx.items.length > 0,
    ...Object.fromEntries(templates.map((tpl) => [`tpl:${tpl.code}`, Object.keys(exams[tpl.code] ?? {}).length > 0])),
  };
  const sections = [
    { key: 'summary', label: t('consult.sections.summary') },
    { key: 'complaints', label: t('consult.sections.complaints') },
    { key: 'history', label: t('consult.sections.history') },
    ...(can('patients.vitals') || can('emr.view') ? [{ key: 'vitals', label: t('consult.sections.vitals') }] : []),
    ...templates.map((tpl) => ({ key: `tpl:${tpl.code}`, label: templateName(tpl) })),
    { key: 'progress', label: t('consult.sections.progress') },
    { key: 'photos', label: t('consult.sections.photos') },
    { key: 'diagnosis', label: t('consult.sections.diagnosis') },
    ...(canSeeRx ? [{ key: 'rx', label: t('consult.sections.rx') }] : []),
    { key: 'advice', label: t('consult.sections.advice') },
    { key: 'followUp', label: t('consult.sections.followUp') },
  ];
  const openTemplate = section.startsWith('tpl:') ? templates.find((tpl) => `tpl:${tpl.code}` === section) : undefined;
  const p = visit.patient_detail;
  const props = { draft, onChange: changeDraft, readOnly };

  return (
    <div className="workspace" ref={workspaceRef}>
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
              {!readOnly && (
                <>
                  <Tooltip title={t('consult.undoHelp')}>
                    <Button size="small" icon={<UndoOutlined />} disabled={!past.current.length} onClick={undo} aria-label={t('consult.undo')} />
                  </Tooltip>
                  <Tooltip title={t('consult.redoHelp')}>
                    <Button size="small" icon={<RedoOutlined />} disabled={!future.current.length} onClick={redo} aria-label={t('consult.redo')} />
                  </Tooltip>
                  <Button size="small" icon={<SaveOutlined />} onClick={() => save()}>{t('common.save')}</Button>
                </>
              )}
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
              {s.key === 'rx' && rxWarnings.some((w) => w.level === 'danger') && <span className="danger-dot" aria-label={t('rx.hasDanger')} />}
            </button>
          ))}
        </div>

        <Card size="small" className="section-card">
          {section === 'summary' && (
            <SummarySection draft={draft} templates={templates} exams={exams} examFields={toExamFields(visit.exams, templates)}
              rxItems={rx.items} rxNotes={rx.notes} />
          )}
          {section === 'progress' && (
            <ProgressSection patientId={visit.patient} visitId={visit.id} visitDate={visit.visit_date} complaints={draft.complaints} />
          )}
          {section === 'photos' && <PhotosSection visitId={visit.id} patientId={visit.patient} readOnly={readOnly} />}
          {section === 'complaints' && <ComplaintsSection {...props} />}
          {section === 'history' && <NotesSection {...props} />}
          {section === 'vitals' && <VitalsTab patientId={visit.patient} />}
          {openTemplate && (
            <TemplateSection template={openTemplate} values={exams[openTemplate.code] ?? {}} readOnly={readOnly}
              onChange={(values) => changeExam(openTemplate.code, values)} />
          )}
          {section === 'diagnosis' && <DiagnosisSection {...props} />}
          {section === 'rx' && (
            <RxSection rx={rx} onChange={changeRx} warnings={rxWarnings} diagnoses={draft.diagnoses} readOnly={rxReadOnly} />
          )}
          {section === 'advice' && <AdviceSection {...props} />}
          {section === 'followUp' && <FollowUpSection {...props} />}
        </Card>
      </div>

      <PreviousVisits patientId={visit.patient} currentId={visit.id} templates={templates}
        onRepeat={!rxReadOnly ? (lines) => { changeRx({ items: [...rx.items, ...lines] }); setSection('rx'); } : undefined} />
    </div>
  );
}

/** Right panel: the patient's earlier check-ups (all branches). Click one to read it. */
function PreviousVisits({ patientId, currentId, templates, onRepeat }: {
  patientId: string;
  currentId: string;
  templates: ExamTemplate[];
  onRepeat?: (lines: RxLine[]) => void;
}) {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [rows, setRows] = useState<VisitListItem[]>([]);
  const [open, setOpen] = useState<Visit | null>(null);
  const [openRx, setOpenRx] = useState<Prescription | null>(null);

  const openVisit = async (id: string) => {
    const { data } = await api.get<Visit>(`/visits/${id}/`);
    setOpen(data);
    setOpenRx(null);
    if (can('prescriptions.view')) {
      api.get<Page<Prescription>>('/prescriptions/', { params: { visit: id } })
        .then(({ data: page }) => setOpenRx(page.results[0] ?? null)).catch(() => undefined);
    }
  };

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
          onClick={() => openVisit(v.id)}>
          <div className="prev-visit-date">{dayjs(v.visit_date).format('DD-MM-YYYY')}</div>
          <div className="cell-sub">{v.doctor_name} · {v.branch_name}</div>
          {v.diagnoses.length > 0 && <div className="prev-visit-dx">{v.diagnoses.join(', ')}</div>}
          {v.complaints.length > 0 && <div className="cell-sub">{v.complaints.join(', ')}</div>}
        </button>
      ))}
      <Modal open={!!open} width={760} title={open ? t('consult.visitOf', { date: dayjs(open.visit_date).format('DD-MM-YYYY') }) : ''}
        onCancel={() => setOpen(null)} footer={(
          <Space>
            {onRepeat && openRx && openRx.items.length > 0 && (
              <Button onClick={() => {
                onRepeat(openRx.items.map(({ id: _id, ...line }) => line));
                setOpen(null);
              }}>{t('rx.repeat', { n: openRx.items.length })}</Button>
            )}
            <Button type="primary" onClick={() => setOpen(null)}>{t('common.close')}</Button>
          </Space>
        )}>
        {open && (
          <>
            <div className="cell-sub" style={{ marginBottom: 8 }}>{open.doctor_name} · {open.branch_name}</div>
            <SummarySection draft={toDraft(open)} templates={templates} exams={toExams(open.exams)}
              examFields={toExamFields(open.exams, templates)} rxItems={openRx?.items} rxNotes={openRx?.notes} />
          </>
        )}
      </Modal>
    </aside>
  );
}
