// The prescription (Rx) part of the check-up: search medicines, dose / frequency / timing / anupana /
// duration / quantity, safety warnings (fixed rules), disease-wise templates, medicine days, and the
// patient's last prescription to continue.
// Quick dosage: type 222 in "M-N-N" and it becomes 2-2-2. The quantity is worked out (e.g. 180 tablets)
// until the doctor types their own.
import { CloseOutlined, ExclamationCircleFilled, SaveOutlined, WarningFilled } from '@ant-design/icons';
import { App, AutoComplete, Button, Empty, Form, Input, InputNumber, Modal, Select, Space, Spin, Tag, Tooltip } from 'antd';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import { useMasterLabel, useMasters } from '../../api/masters';
import type { Diagnosis, Medicine, Page, Prescription, PrescriptionTemplate, RxLine, RxWarning } from '../../api/types';
import { autoQuantity, quickDosage } from '../../utils/dosage';
import { MasterSelect } from '../../components/MasterSelect';
import { MedicineFlags, money } from '../medicines/shared';

export type RxDraft = { id?: string; items: RxLine[]; notes: string; status?: 'draft' | 'final'; medicine_days?: number | null };

/** Keep the worked-out quantity up to date, unless the doctor typed their own. */
export function withQuantity(before: RxLine | null, after: RxLine): RxLine {
  const typedOwn = before && before.quantity && before.quantity !== autoQuantity(before);
  if (typedOwn) return after;
  return { ...after, quantity: autoQuantity(after) };
}

const FREQUENCIES = ['1-0-1', '1-1-1', '1-0-0', '0-0-1', '0-1-0', '1-1-0', '0-1-1'];

/** A new prescription line from a medicine's defaults. */
function lineFromMedicine(m: Medicine): RxLine {
  return {
    medicine: m.id,
    medicine_name: m.name,
    dosage_form: m.dosage_form?.label ?? '',
    dose: m.default_dose,
    dose_unit: m.dose_unit?.label ?? '',
    frequency: m.default_frequency,
    timing: m.default_timing?.label ?? '',
    anupana: m.default_anupana?.label ?? '',
    duration: null,
    duration_unit: 'days',
    quantity: '',
    instructions: '',
    medicine_flags: (['schedule_e1', 'contains_metals', 'pregnancy_caution', 'child_caution'] as const).filter((f) => m[f]),
  };
}

/** Dropdown that stores the English label (prescriptions keep plain words) but shows the screen language. */
function LabelSelect({ category, value, onChange, disabled, width }: {
  category: string; value: string; onChange: (v: string) => void; disabled?: boolean; width: number;
}) {
  const values = useMasters(category);
  const label = useMasterLabel();
  return (
    <Select size="small" allowClear showSearch optionFilterProp="label" disabled={disabled} style={{ width }}
      value={value || undefined} onChange={(v) => onChange(v ?? '')}
      options={values.map((m) => ({ value: m.label, label: label(m) }))} />
  );
}

export function RxSection({ rx, onChange, warnings, diagnoses, readOnly, daysBar, patientId, visitId }: {
  rx: RxDraft;
  onChange: (patch: Partial<RxDraft>) => void;
  warnings: RxWarning[];
  diagnoses: Diagnosis[];
  readOnly?: boolean;
  /** Medicine days / follow-up days row (from the check-up screen) */
  daysBar?: ReactNode;
  /** To show the patient's last prescription */
  patientId?: string;
  visitId?: string;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [options, setOptions] = useState<Medicine[]>([]);
  const [searching, setSearching] = useState(false);
  const [search, setSearch] = useState('');
  const [templates, setTemplates] = useState<PrescriptionTemplate[]>([]);
  const [saveOpen, setSaveOpen] = useState(false);
  const timer = useRef<number>();

  const loadTemplates = () => {
    api.get<PrescriptionTemplate[]>('/prescription-templates/').then(({ data }) => setTemplates(data)).catch(() => setTemplates([]));
  };
  useEffect(loadTemplates, []);

  const doSearch = (text: string) => {
    setSearch(text);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await api.get<Page<Medicine>>('/medicines/', { params: { for_rx: 1, q: text.trim() || undefined, page_size: 20 } });
        setOptions(data.results);
      } finally {
        setSearching(false);
      }
    }, 250);
  };
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const items = rx.items;
  const setItems = (next: RxLine[]) => onChange({ items: next });
  const update = (i: number, patch: Partial<RxLine>) =>
    setItems(items.map((l, j) => (j === i ? ('quantity' in patch ? { ...l, ...patch } : withQuantity(l, { ...l, ...patch })) : l)));
  // New lines take the prescription's medicine days when they have none
  const withDays = (line: RxLine): RxLine => withQuantity(null, rx.medicine_days && !line.duration
    ? { ...line, duration: rx.medicine_days, duration_unit: 'days' } : line);

  const addMedicine = (id: string) => {
    if (id.startsWith('free:')) {
      const name = id.slice(5);
      setItems([...items, withDays({
        medicine: null, medicine_name: name, dosage_form: '', dose: '', dose_unit: '', frequency: '', timing: '',
        anupana: '', duration: null, duration_unit: 'days', quantity: '', instructions: '', medicine_flags: [],
      })]);
    } else {
      const medicine = options.find((m) => m.id === id);
      if (medicine) setItems([...items, withDays(lineFromMedicine(medicine))]);
    }
    setSearch('');
  };

  // Templates that match this check-up's diagnoses come first
  const dxCodes = new Set(diagnoses.map((d) => d.master).filter(Boolean));
  const sortedTemplates = useMemo(
    () => [...templates].sort((a, b) => Number(dxCodes.has(b.diagnosis?.code ?? '')) - Number(dxCodes.has(a.diagnosis?.code ?? ''))),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [templates, diagnoses],
  );
  const applyTemplate = (id: string) => {
    const tpl = templates.find((x) => x.id === id);
    if (!tpl) return;
    const added = tpl.items.map((l) => withDays({ ...l, id: undefined }));
    // One change (one Undo step): the lines, and the template's notes if there are none yet
    onChange({ items: [...items, ...added], ...(tpl.notes && !rx.notes ? { notes: tpl.notes } : {}) });
    message.success(t('rx.templateApplied', { name: tpl.name }));
  };

  const searchOptions = [
    ...options.map((m) => ({
      value: m.id,
      label: (
        <div className="rx-option">
          <span><b>{m.name}</b> <span className="cell-sub">{m.dosage_form?.label}</span></span>
          <span className="rx-option-meta"><MedicineFlags medicine={m} /> <span className="cell-sub num">{money(m.branch_price)}</span></span>
        </div>
      ),
    })),
    ...(search.trim().length >= 2 && !options.some((m) => m.name.toLowerCase() === search.trim().toLowerCase())
      ? [{ value: `free:${search.trim()}`, label: <span className="cell-sub">{t('rx.addFreeText', { name: search.trim() })}</span> }]
      : []),
  ];

  return (
    <>
      <div className="section-toolbar">
        <div className="section-title" style={{ margin: 0 }}>{t('rx.title')}</div>
        {!readOnly && (
          <Space size={8}>
            <Select size="small" placeholder={t('rx.applyTemplate')} style={{ width: 220 }} value={null} onChange={applyTemplate}
              notFoundContent={t('rx.noTemplates')} showSearch optionFilterProp="label"
              options={sortedTemplates.map((tpl) => ({
                value: tpl.id,
                label: `${dxCodes.has(tpl.diagnosis?.code ?? '') ? '★ ' : ''}${tpl.name}`,
              }))} />
            <Button size="small" icon={<SaveOutlined />} disabled={!items.length} onClick={() => setSaveOpen(true)}>{t('rx.saveTemplate')}</Button>
          </Space>
        )}
      </div>

      {daysBar}

      {!readOnly && patientId && (
        <LastPrescription patientId={patientId} visitId={visitId} current={items}
          onContinue={(lines) => {
            onChange({ items: [...items, ...lines.map(({ id: _id, ...l }) => withDays(l))] });
            message.success(t('rx.continued', { count: lines.length }));
          }} />
      )}

      {warnings.length > 0 && (
        <div className="rx-warnings">
          {warnings.map((w, i) => (
            <div key={i} className={`rx-warning rx-${w.level}`}>
              {w.level === 'danger' ? <ExclamationCircleFilled /> : <WarningFilled />}
              <b>{w.medicine}:</b> <span>{w.message}</span>
            </div>
          ))}
        </div>
      )}

      {!readOnly && (
        <Select
          showSearch
          className="rx-search"
          value={null}
          placeholder={t('rx.searchMedicine')}
          filterOption={false}
          searchValue={search}
          onSearch={doSearch}
          onFocus={() => !options.length && doSearch('')}
          onChange={addMedicine}
          options={searchOptions}
          notFoundContent={searching ? <Spin size="small" /> : t('rx.noMedicine')}
          popupMatchSelectWidth
        />
      )}

      {items.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('rx.empty')} />
      ) : (
        <div className="rx-lines">
          {items.map((l, i) => (
            <div className="rx-line" key={l.id ?? `new-${i}`}>
              <div className="rx-line-top">
                <span className="rx-num">{i + 1}</span>
                <div className="rx-med">
                  <b>{l.medicine_name}</b>
                  {l.dosage_form && <span className="cell-sub">{l.dosage_form}</span>}
                  {l.medicine === null && <Tag className="tag-tight">{t('rx.freeText')}</Tag>}
                  <MedicineFlags flags={l.medicine_flags} />
                </div>
                {!readOnly && (
                  <Button size="small" type="text" icon={<CloseOutlined />} aria-label={t('common.remove')}
                    onClick={() => setItems(items.filter((_, j) => j !== i))} />
                )}
              </div>
              <div className="rx-controls">
                <div className="rx-field">
                  <span>{t('rx.dose')}</span>
                  <Space.Compact size="small">
                    <Input size="small" value={l.dose} maxLength={20} disabled={readOnly} style={{ width: 52 }} placeholder="2"
                      onChange={(e) => update(i, { dose: e.target.value })} />
                    <LabelSelect category="dose_unit" value={l.dose_unit} disabled={readOnly} width={96} onChange={(v) => update(i, { dose_unit: v })} />
                  </Space.Compact>
                </div>
                <div className="rx-field">
                  <Tooltip title={t('rx.frequencyHelp')}><span>{t('rx.frequency')}</span></Tooltip>
                  <AutoComplete size="small" value={l.frequency} disabled={readOnly} style={{ width: 84 }} placeholder="1-0-1"
                    filterOption={false}
                    options={FREQUENCIES.filter((f) => !l.frequency || (f.startsWith(l.frequency) && f !== l.frequency)).map((f) => ({ value: f }))}
                    onChange={(v) => update(i, { frequency: quickDosage(v).slice(0, 20) })} />
                </div>
                <div className="rx-field">
                  <span>{t('rx.timing')}</span>
                  <LabelSelect category="medicine_timing" value={l.timing} disabled={readOnly} width={136} onChange={(v) => update(i, { timing: v })} />
                </div>
                <div className="rx-field">
                  <span>{t('rx.anupana')}</span>
                  <LabelSelect category="anupana" value={l.anupana} disabled={readOnly} width={124} onChange={(v) => update(i, { anupana: v })} />
                </div>
                <div className="rx-field">
                  <span>{t('rx.duration')}</span>
                  <Space.Compact size="small">
                    <InputNumber size="small" min={0} max={365} value={l.duration ?? undefined} disabled={readOnly} style={{ width: 56 }}
                      onChange={(v) => update(i, { duration: v ?? null })} />
                    <Select size="small" value={l.duration_unit} disabled={readOnly} style={{ width: 86 }}
                      onChange={(v) => update(i, { duration_unit: v })}
                      options={(['days', 'weeks', 'months'] as const).map((u) => ({ value: u, label: t(`consult.units.${u}`) }))} />
                  </Space.Compact>
                </div>
                <div className="rx-field">
                  <Tooltip title={t('rx.quantityHelp')}><span>{t('rx.quantity')}</span></Tooltip>
                  <Input size="small" value={l.quantity} maxLength={40} disabled={readOnly} style={{ width: 104 }}
                    placeholder={t('rx.quantityPlaceholder')} onChange={(e) => update(i, { quantity: e.target.value })} />
                </div>
                <div className="rx-field rx-field-grow">
                  <span>{t('rx.instructionsLabel')}</span>
                  <Input size="small" placeholder={t('rx.instructions')} value={l.instructions} maxLength={300} disabled={readOnly}
                    onChange={(e) => update(i, { instructions: e.target.value })} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="section-title">{t('rx.notes')}</div>
      <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} value={rx.notes} disabled={readOnly} maxLength={1000}
        placeholder={t('rx.notesPlaceholder')} onChange={(e) => onChange({ notes: e.target.value })} />

      {saveOpen && (
        <SaveTemplateModal items={items} notes={rx.notes} diagnoses={diagnoses}
          onClose={(saved) => { setSaveOpen(false); if (saved) loadTemplates(); }} />
      )}
    </>
  );
}

function SaveTemplateModal({ items, notes, diagnoses, onClose }: {
  items: RxLine[]; notes: string; diagnoses: Diagnosis[]; onClose: (saved: boolean) => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const firstDx = diagnoses[0];
  const dxValues = useMasters('diagnosis');

  useEffect(() => {
    const match = dxValues.find((d) => d.code === firstDx?.master);
    form.setFieldsValue({ name: firstDx ? `${firstDx.label}` : '', diagnosis: match?.id });
  }, [dxValues, firstDx, form]);

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await api.post('/prescription-templates/', {
        name: values.name, diagnosis: values.diagnosis ?? null, notes,
        items: items.map(({ id: _id, medicine_flags: _f, ...rest }) => rest),
      });
      message.success(t('rx.templateSaved'));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open width={480} title={t('rx.saveTemplate')} onCancel={() => onClose(false)} onOk={save}
      okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}>
      <div className="form-help">{t('rx.saveTemplateHelp', { n: items.length })}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="name" label={t('rx.templateName')} rules={[{ required: true, message: t('common.required') }]}>
          <Input maxLength={150} />
        </Form.Item>
        <Form.Item name="diagnosis" label={t('rx.templateDiagnosis')} extra={t('rx.templateDiagnosisHelp')}>
          <MasterSelect category="diagnosis" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

/** The patient's last prescription (from an earlier check-up): continue all or some of its medicines. */
function LastPrescription({ patientId, visitId, current, onContinue }: {
  patientId: string;
  visitId?: string;
  current: RxLine[];
  onContinue: (lines: RxLine[]) => void;
}) {
  const { t } = useTranslation();
  const [last, setLast] = useState<Prescription | null>(null);
  const [open, setOpen] = useState(true);
  useEffect(() => {
    api.get<Page<Prescription>>('/prescriptions/', { params: { patient: patientId, page_size: 5 } })
      .then(({ data }) => setLast(data.results.find((p) => p.visit !== visitId && p.items.length > 0) ?? null))
      .catch(() => setLast(null));
  }, [patientId, visitId]);
  if (!last) return null;
  const already = new Set(current.map((l) => l.medicine ?? l.medicine_name));
  const left = last.items.filter((l) => !already.has(l.medicine ?? l.medicine_name));
  const summary = (l: RxLine) => [
    l.dose ? `${l.dose} ${l.dose_unit}`.trim() : '', l.frequency,
    l.duration ? `${l.duration} ${t(`consult.units.${l.duration_unit}`)}` : '',
  ].filter(Boolean).join(' · ');
  return (
    <div className="last-rx">
      <div className="last-rx-head">
        <button type="button" className="link-button" onClick={() => setOpen(!open)}>
          <b>{t('rx.lastPrescription')}</b> <span className="cell-sub">
            {dayjs(last.visit_date).format('DD-MM-YYYY')} · {last.doctor_name}{last.medicine_days ? ` · ${t('rx.daysShort', { n: last.medicine_days })}` : ''}
          </span>
        </button>
        {left.length > 0 && (
          <Button size="small" type="primary" ghost onClick={() => onContinue(left)}>{t('rx.continueAll', { count: left.length })}</Button>
        )}
      </div>
      {open && (
        <div className="last-rx-lines">
          {last.items.map((l) => {
            const added = already.has(l.medicine ?? l.medicine_name);
            return (
              <div className="last-rx-line" key={l.id}>
                <span><b>{l.medicine_name}</b> <span className="cell-sub">{summary(l)}</span></span>
                {added ? <Tag className="tag-tight" color="green">{t('rx.alreadyAdded')}</Tag>
                  : <Button size="small" onClick={() => onContinue([l])}>{t('rx.continueOne')}</Button>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
