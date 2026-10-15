// PDF settings: how ALL print-outs look (prescription, bills, certificates, labels, reports ...) with a live preview.
// SAFE TO EDIT: the order of the groups (GROUPS below). The list of documents and options comes from the server
// (backend/apps/documents/print_settings.py); the words are in src/i18n/*.json under "pdfSettings".
import { InfoCircleOutlined, ReloadOutlined, UndoOutlined } from '@ant-design/icons';
import { Alert, App, Button, Checkbox, ColorPicker, Input, InputNumber, Popconfirm, Segmented, Select, Slider, Space, Spin, Switch, Tabs, Tag, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import { resetPaperDefaults } from '../utils/paperDefaults';

type Values = Record<string, unknown>;
type Scope = 'org' | 'branch';
interface DocType { code: string; label: string; paper: string; papers: string[]; keys: string[] }
interface Meta {
  defaults: Values;
  doc_types: DocType[];
  saved: Record<Scope, Record<string, Values>>;
  branch: { id: string; name: string };
  multi_branch: boolean;
}

// The options, in groups. An option shows only on the documents that have it.
const GROUPS: { id: string; keys: string[] }[] = [
  { id: 'look', keys: ['paper', 'font_scale', 'accent_color', 'margin_mm'] },
  { id: 'letterhead', keys: ['show_letterhead', 'show_logo', 'header_text', 'footer_text'] },
  { id: 'sign', keys: ['show_signature', 'show_qr', 'show_doctor_reg', 'show_duplicate_watermark'] },
  { id: 'language', keys: ['language'] },
  { id: 'bills', keys: ['show_gst_columns', 'thank_you_text', 'terms_text'] },
];
const COLOR_PRESETS = ['#1f5c46', '#1e7a3c', '#0b5394', '#6a1b9a', '#8a1c1c', '#b45f06', '#333333'];

export default function PdfSettingsPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [scope, setScope] = useState<Scope>('org');
  const [drafts, setDrafts] = useState<Record<string, Values>>({});
  const [tab, setTab] = useState('all');
  const [saving, setSaving] = useState(false);
  // preview
  const [previewDoc, setPreviewDoc] = useState('prescription');
  const [paper, setPaper] = useState('');
  const [lang, setLang] = useState('');
  const [duplicate, setDuplicate] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [refreshTick, setRefreshTick] = useState(0);
  const urlRef = useRef<string | null>(null);

  const load = useCallback(async (nextScope?: Scope) => {
    try {
      const { data } = await api.get<Meta>('/print-settings/');
      setMeta(data);
      const use = nextScope ?? (data.multi_branch ? scope : 'org');
      setScope(use);
      setDrafts(JSON.parse(JSON.stringify(data.saved[use])));
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  }, [message, t, scope]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const docs = meta?.doc_types ?? [];
  const doc = docs.find((d) => d.code === tab);
  const mine = drafts[tab] ?? {};

  // What this document uses when the owner has not changed an option here (shown grey in the controls)
  const inherited = (key: string): unknown => {
    if (!meta) return undefined;
    const saved = (s: Scope, kind: string) => meta.saved[s]?.[kind]?.[key];
    // closest first: the group's value for this document, the "all documents" draft, the group's "all documents"
    const chain = [
      ...(tab !== 'all' && scope === 'branch' ? [saved('org', tab)] : []),
      ...(tab !== 'all' ? [drafts.all?.[key]] : []),
      ...(scope === 'branch' ? [saved('org', 'all')] : []),
    ];
    return chain.find((v) => v !== undefined && v !== null) ?? meta.defaults[key];
  };
  const own = (key: string) => key in mine;
  const valueOf = (key: string) => (own(key) ? mine[key] : inherited(key));
  const setValue = (key: string, value: unknown) => setDrafts((d) => ({ ...d, [tab]: { ...(d[tab] ?? {}), [key]: value } }));
  const clearValue = (key: string) => setDrafts((d) => {
    const next = { ...(d[tab] ?? {}) };
    delete next[key];
    return { ...d, [tab]: next };
  });

  // ---- live preview (a moment after the last change) ----
  useEffect(() => {
    if (!meta) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setPreviewError('');
      try {
        const res = await api.post('/print-settings/preview/', {
          doc_type: previewDoc, scope, paper, lang, duplicate, drafts,
        }, { responseType: 'blob', signal: controller.signal });
        const next = URL.createObjectURL(res.data as Blob);
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = next;
        setPdfUrl(next);
        setSource(String(res.headers['x-preview-source'] ?? ''));
      } catch (err) {
        if (!controller.signal.aborted) setPreviewError(errorMessage(err, t('pdfSettings.previewFailed')));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 700);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [meta, previewDoc, scope, paper, lang, duplicate, drafts, refreshTick, t]);

  useEffect(() => () => { if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  const changeTab = (next: string) => {
    setTab(next);
    if (next !== 'all') {
      setPreviewDoc(next);
      setPaper('');
    }
  };

  const changeScope = (next: Scope) => {
    if (JSON.stringify(drafts) !== JSON.stringify(meta?.saved[scope] ?? {}) && !window.confirm(t('pdfSettings.discardAsk'))) return;
    setScope(next);
    if (meta) setDrafts(JSON.parse(JSON.stringify(meta.saved[next])));
  };

  const dirty = !!meta && JSON.stringify(drafts) !== JSON.stringify(meta.saved[scope]);

  const saveAll = async (only?: string) => {
    if (!meta) return;
    setSaving(true);
    try {
      const kinds = new Set([...Object.keys(drafts), ...Object.keys(meta.saved[scope])]);
      for (const kind of kinds) {
        if (only && kind !== only) continue;
        const now = drafts[kind] ?? {};
        if (JSON.stringify(now) === JSON.stringify(meta.saved[scope][kind] ?? {})) continue;
        await api.put('/print-settings/', { scope, doc_type: kind, values: now });
      }
      resetPaperDefaults();
      await load(scope);
      message.success(t('common.saved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const resetTab = async () => {
    setDrafts((d) => ({ ...d, [tab]: {} }));
    // saved straight away: "back to default" for this tab
    if (!meta) return;
    setSaving(true);
    try {
      if (Object.keys(meta.saved[scope][tab] ?? {}).length) await api.put('/print-settings/', { scope, doc_type: tab, values: {} });
      resetPaperDefaults();
      await load(scope);
      message.success(t('common.saved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  // ---- one option ----
  const control = (key: string) => {
    const value = valueOf(key);
    switch (key) {
      case 'paper':
        return (
          <Segmented value={String(value || doc?.paper || '')} options={(doc?.papers ?? []).map((p) => ({ value: p, label: t(`pdfSettings.papers.${p}`) }))}
            onChange={(v) => setValue(key, String(v))} />
        );
      case 'font_scale':
        return (
          <Space style={{ width: '100%' }}>
            <Slider min={70} max={150} step={5} style={{ width: 200 }} value={Number(value)} onChange={(v) => setValue(key, v)} />
            <InputNumber min={70} max={150} suffix="%" style={{ width: 100 }} value={Number(value)} onChange={(v) => v && setValue(key, Math.round(v))} />
          </Space>
        );
      case 'accent_color':
        return (
          <ColorPicker value={String(value)} showText disabledAlpha placement="bottomLeft" presets={[{ label: t('pdfSettings.presets'), colors: COLOR_PRESETS }]}
            onChange={(c) => setValue(key, c.toHexString().toLowerCase())} />
        );
      case 'margin_mm':
        return (
          <InputNumber min={0} max={30} suffix="mm" style={{ width: 130 }} placeholder={t('pdfSettings.usualMargin')} value={value as number | null}
            onChange={(v) => (v === null ? clearValue(key) : setValue(key, Math.round(v)))} />
        );
      case 'language':
        return (
          <Select style={{ width: 240 }} value={String(value)} onChange={(v) => setValue(key, v)}
            options={['patient', 'en', 'gu', 'hi'].map((v) => ({ value: v, label: t(`pdfSettings.languages.${v}`) }))} />
        );
      case 'header_text':
      case 'footer_text':
      case 'thank_you_text':
        return <Input maxLength={key === 'footer_text' ? 300 : 200} value={String(value ?? '')} onChange={(e) => setValue(key, e.target.value)} />;
      case 'terms_text':
        return <Input.TextArea rows={3} maxLength={600} showCount value={String(value ?? '')} onChange={(e) => setValue(key, e.target.value)} />;
      default:
        return <Switch checked={value === true} onChange={(v) => setValue(key, v)} />;
    }
  };

  const keysHere = tab === 'all' ? (meta ? Object.keys(meta.defaults).filter((k) => k !== 'paper') : []) : (doc?.keys ?? []);

  const options = (
    <div>
      {GROUPS.map((group) => {
        const keys = group.keys.filter((k) => keysHere.includes(k));
        if (!keys.length) return null;
        return (
          <div key={group.id} className="pdfset-group">
            <Typography.Text strong>{t(`pdfSettings.groups.${group.id}`)}</Typography.Text>
            {keys.map((key) => (
              <div key={key} className="pdfset-row">
                <div className="pdfset-label">
                  {t(`pdfSettings.keys.${key}.label`)}
                  <div className="cell-sub">{t(`pdfSettings.keys.${key}.help`)}</div>
                </div>
                <div className="pdfset-control">
                  {control(key)}
                  {tab !== 'all' && !own(key) && <Tag style={{ marginLeft: 8 }}>{t('pdfSettings.sameAsGeneral')}</Tag>}
                  {own(key) && (key !== 'paper' || tab !== 'all') && (
                    <Button type="link" size="small" onClick={() => clearValue(key)}>
                      {tab === 'all' ? t('pdfSettings.backToDefault') : t('pdfSettings.useGeneral')}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        );
      })}
      {tab !== 'all' && doc && doc.keys.length === 1 && <Alert type="info" showIcon message={t('pdfSettings.fewOptions')} />}
      {tab === 'prescription' && <Alert type="info" showIcon style={{ marginTop: 8 }} message={t('pdfSettings.caseSheetNote')} />}
    </div>
  );

  if (!meta) return <Spin />;
  const previewDocType = docs.find((d) => d.code === previewDoc);

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('pdfSettings.title')}</Typography.Title>
          <div className="cell-sub">{t('pdfSettings.subtitle')}</div>
        </div>
        <Space wrap>
          {meta.multi_branch && (
            <Segmented value={scope} onChange={(v) => changeScope(v as Scope)}
              options={[{ value: 'org', label: t('pdfSettings.scopeOrg') }, { value: 'branch', label: t('pdfSettings.scopeBranch', { branch: meta.branch.name }) }]} />
          )}
          <Popconfirm title={t('pdfSettings.resetAsk')} okText={t('common.yes')} cancelText={t('common.no')} onConfirm={resetTab}>
            <Button icon={<UndoOutlined />} disabled={saving}>{t('pdfSettings.reset')}</Button>
          </Popconfirm>
          <Button type="primary" loading={saving} disabled={!dirty} onClick={() => saveAll()}>{t('common.save')}</Button>
        </Space>
      </div>
      {dirty && <Alert type="warning" showIcon style={{ marginBottom: 12 }} message={t('pdfSettings.unsaved')} />}
      <div className="pdfset-layout">
        <div className="pdfset-form">
          <Tabs activeKey={tab} onChange={changeTab} size="small" items={[
            { key: 'all', label: t('pdfSettings.general') },
            ...docs.map((d) => ({ key: d.code, label: t(`pdfSettings.docs.${d.code}`) })),
          ]} />
          {tab === 'all'
            ? <Alert type="info" showIcon icon={<InfoCircleOutlined />} style={{ marginBottom: 8 }} message={t('pdfSettings.generalNote')} />
            : <Alert type="info" showIcon icon={<InfoCircleOutlined />} style={{ marginBottom: 8 }} message={t('pdfSettings.docNote', { doc: t(`pdfSettings.docs.${tab}`) })} />}
          {options}
        </div>
        <div className="pdfset-preview">
          <div className="pdfset-preview-bar">
            <Space wrap size={8}>
              {tab === 'all' && (
                <Select size="small" style={{ width: 200 }} value={previewDoc} onChange={(v) => { setPreviewDoc(v); setPaper(''); }}
                  options={docs.map((d) => ({ value: d.code, label: t(`pdfSettings.docs.${d.code}`) }))} />
              )}
              {!!previewDocType?.papers.length && (
                <Segmented size="small" value={paper} onChange={(v) => setPaper(String(v))}
                  options={[{ value: '', label: t('pdfSettings.paperSaved') }, ...previewDocType.papers.map((p) => ({ value: p, label: t(`pdfSettings.papers.${p}`) }))]} />
              )}
              <Segmented size="small" value={lang} onChange={(v) => setLang(String(v))}
                options={[{ value: '', label: t('pdfSettings.langAuto') }, { value: 'en', label: 'EN' }, { value: 'gu', label: 'ગુ' }, { value: 'hi', label: 'हि' }]} />
              <Checkbox checked={duplicate} onChange={(e) => setDuplicate(e.target.checked)}>{t('pdfSettings.asReprint')}</Checkbox>
              <Button size="small" icon={<ReloadOutlined />} onClick={() => setRefreshTick((n) => n + 1)} />
            </Space>
            <div className="cell-sub">
              {source === 'real' ? t('pdfSettings.sourceReal') : source === 'sample' ? t('pdfSettings.sourceSample') : ''}
              {tab === 'all' && !!previewDocType && ` · ${t('pdfSettings.previewOf', { doc: t(`pdfSettings.docs.${previewDoc}`) })}`}
            </div>
          </div>
          <div className="pdfset-frame">
            {loading && <Spin className="pdfset-spin" />}
            {previewError && <Alert type="error" showIcon message={previewError} />}
            {pdfUrl && <iframe title={t('pdfSettings.title')} src={`${pdfUrl}#toolbar=0&navpanes=0&view=FitH`} />}
          </div>
        </div>
      </div>
    </>
  );
}
