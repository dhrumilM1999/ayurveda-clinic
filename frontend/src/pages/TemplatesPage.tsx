// Check-up templates (Ashtavidha, Prakriti...): admins add and edit questions and answers here.
// Changing the questions makes a new version; old check-ups keep the questions they were filled with.
import { ArrowDownOutlined, ArrowUpOutlined, DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Col, Input, InputNumber, Modal, Row, Segmented, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { ExamField, ExamTemplate, Lang3 } from '../api/types';
import { clearTemplatesCache } from './consult/VisitWorkspace';
import { useLang3, useTemplateName } from './consult/shared';

type Kind = ExamTemplate['kind'];
const DOSHAS = ['vata', 'pitta', 'kapha'] as const;

function slug(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').replace(/^(\d)/, 'q$1').slice(0, 40) || 'q';
}
function uniqueKey(base: string, taken: string[]) {
  let key = base;
  let n = 2;
  while (taken.includes(key)) key = `${base}_${n++}`.slice(0, 40);
  return key;
}
const emptyLabel = (): Lang3 => ({ en: '', gu: '', hi: '' });

export default function TemplatesPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const name = useTemplateName();
  const [rows, setRows] = useState<ExamTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<ExamTemplate | 'new-form' | 'new-questionnaire' | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<ExamTemplate[]>('/exam-templates/', { params: { all: 1 } });
      setRows(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [message, t]);
  useEffect(() => { load(); }, [load]);

  const toggle = async (tpl: ExamTemplate, on: boolean) => {
    try {
      await api.patch(`/exam-templates/${tpl.id}/`, { is_active: on });
      clearTemplatesCache();
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('templatesAdmin.title')}</Typography.Title>
          <div className="cell-sub">{t('templatesAdmin.subtitle')}</div>
        </div>
        <Space wrap>
          <Button icon={<PlusOutlined />} onClick={() => setEditing('new-questionnaire')}>{t('templatesAdmin.addQuestionnaire')}</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new-form')}>{t('templatesAdmin.addForm')}</Button>
        </Space>
      </div>
      <Table<ExamTemplate>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={false}
        columns={[
          { title: t('templatesAdmin.name'), key: 'name', render: (_: unknown, tpl: ExamTemplate) => <b>{name(tpl)}</b> },
          {
            title: t('templatesAdmin.kind'), dataIndex: 'kind',
            render: (k: Kind) => <Tag color={k === 'questionnaire' ? 'purple' : 'blue'}>{t(`templatesAdmin.kinds.${k}`)}</Tag>,
          },
          { title: t('templatesAdmin.questions'), key: 'n', render: (_: unknown, tpl: ExamTemplate) => tpl.fields.length },
          { title: t('templatesAdmin.version'), dataIndex: 'version', render: (v: number) => `v${v}` },
          {
            title: t('common.active'), dataIndex: 'is_active',
            render: (on: boolean, tpl: ExamTemplate) => <Switch size="small" checked={on} onChange={(v) => toggle(tpl, v)} />,
          },
          {
            title: '', key: 'edit', align: 'right' as const,
            render: (_: unknown, tpl: ExamTemplate) => (
              <Button size="small" icon={<EditOutlined />} onClick={() => setEditing(tpl)}>{t('common.edit')}</Button>
            ),
          },
        ]}
      />
      {editing && (
        <TemplateEditor
          template={typeof editing === 'string' ? null : editing}
          kind={typeof editing === 'string' ? (editing === 'new-form' ? 'form' : 'questionnaire') : editing.kind}
          onClose={(saved) => { setEditing(null); if (saved) { clearTemplatesCache(); load(); } }}
        />
      )}
    </>
  );
}

function TemplateEditor({ template, kind, onClose }: { template: ExamTemplate | null; kind: Kind; onClose: (saved: boolean) => void }) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const lang = useLang3();
  const questionnaire = kind === 'questionnaire';
  const [names, setNames] = useState({ name: template?.name ?? '', name_gu: template?.name_gu ?? '', name_hi: template?.name_hi ?? '' });
  const [description, setDescription] = useState<Lang3>({ ...emptyLabel(), ...(template?.description ?? {}) });
  const [fields, setFields] = useState<ExamField[]>(template ? structuredClone(template.fields) : []);
  const [saving, setSaving] = useState(false);
  // Short names already saved must not change (old check-ups use them)
  const savedKeys = new Set(template?.fields.map((f) => f.key) ?? []);

  const setField = (i: number, patch: Partial<ExamField>) => setFields((list) => list.map((f, j) => (j === i ? { ...f, ...patch } : f)));
  const move = (i: number, by: number) => setFields((list) => {
    const copy = [...list];
    const [item] = copy.splice(i, 1);
    copy.splice(i + by, 0, item!);
    return copy;
  });
  const addField = () => setFields((list) => [...list, {
    key: uniqueKey(`q${list.length + 1}`, list.map((f) => f.key)),
    type: 'choice',
    label: emptyLabel(),
    options: questionnaire
      ? DOSHAS.map((d) => ({ value: d, label: emptyLabel() }))
      : [{ value: 'a1', label: emptyLabel() }, { value: 'a2', label: emptyLabel() }],
  }]);

  const save = async () => {
    // Fill automatic short names from the English text for new questions / answers
    const ready = fields.map((f) => {
      const key = savedKeys.has(f.key) ? f.key : uniqueKey(slug(f.label.en || f.key), fields.filter((o) => o !== f).map((o) => o.key));
      const options = f.options?.map((o, idx, all) => {
        if (questionnaire) return o;
        const usedBefore = template?.fields.find((x) => x.key === f.key)?.options?.some((x) => x.value === o.value);
        return usedBefore ? o : { ...o, value: uniqueKey(slug(o.label.en || `a${idx + 1}`), all.filter((x) => x !== o).map((x) => x.value)) };
      });
      return { ...f, key, ...(f.type === 'choice' || f.type === 'multi' ? { options } : { options: undefined }) };
    });
    setSaving(true);
    try {
      const payload = { ...names, kind, description, fields: ready };
      const { data } = template
        ? await api.patch<ExamTemplate>(`/exam-templates/${template.id}/`, payload)
        : await api.post<ExamTemplate>('/exam-templates/', payload);
      message.success(t('templatesAdmin.savedVersion', { v: data.version }));
      onClose(true);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const LabelInputs = ({ value, onChange, placeholder }: { value: Lang3; onChange: (v: Lang3) => void; placeholder: string }) => (
    <Row gutter={6}>
      {(['en', 'gu', 'hi'] as const).map((l) => (
        <Col span={8} key={l}>
          <Input size="small" addonBefore={l.toUpperCase()} value={value[l]} placeholder={l === 'en' ? placeholder : undefined}
            onChange={(e) => onChange({ ...value, [l]: e.target.value })} />
        </Col>
      ))}
    </Row>
  );

  return (
    <Modal open width={980} title={template ? t('templatesAdmin.editTitle', { name: lang({ en: template.name, gu: template.name_gu, hi: template.name_hi }) }) : t(questionnaire ? 'templatesAdmin.addQuestionnaire' : 'templatesAdmin.addForm')}
      onCancel={() => modal.confirm({ title: t('templatesAdmin.closeConfirm'), okText: t('common.yes'), cancelText: t('common.no'), onOk: () => onClose(false) })}
      onOk={save} okText={t('common.save')} cancelText={t('common.cancel')} confirmLoading={saving}
      keyboard={false} maskClosable={false} destroyOnHidden>
      {template && <div className="cell-sub" style={{ marginBottom: 8 }}>{t('templatesAdmin.versionHelp', { v: template.version })}</div>}
      <div className="section-title" style={{ marginTop: 0 }}>{t('templatesAdmin.name')}</div>
      <Row gutter={6}>
        <Col span={8}><Input size="small" addonBefore="EN" value={names.name} onChange={(e) => setNames({ ...names, name: e.target.value })} /></Col>
        <Col span={8}><Input size="small" addonBefore="GU" value={names.name_gu} onChange={(e) => setNames({ ...names, name_gu: e.target.value })} /></Col>
        <Col span={8}><Input size="small" addonBefore="HI" value={names.name_hi} onChange={(e) => setNames({ ...names, name_hi: e.target.value })} /></Col>
      </Row>
      <div className="section-title">{t('templatesAdmin.description')}</div>
      {LabelInputs({ value: description, onChange: setDescription, placeholder: t('templatesAdmin.descriptionPlaceholder') })}
      {questionnaire && <div className="cell-sub" style={{ marginTop: 6 }}>{t('templatesAdmin.questionnaireHelp')}</div>}

      <div className="section-title">{t('templatesAdmin.questionsTitle', { n: fields.length })}</div>
      <div className="tpl-editor">
        {fields.map((f, i) => (
          <Card size="small" key={i} className="tpl-question">
            <div className="tpl-question-head">
              <b>{i + 1}.</b>
              {!questionnaire && (
                <Segmented size="small" value={f.type}
                  onChange={(v) => setField(i, {
                    type: v as ExamField['type'],
                    options: v === 'choice' || v === 'multi' ? (f.options?.length ? f.options : [{ value: 'a1', label: emptyLabel() }]) : undefined,
                  })}
                  options={(['choice', 'multi', 'number', 'text'] as const).map((k) => ({ value: k, label: t(`templatesAdmin.types.${k}`) }))} />
              )}
              <span style={{ flex: 1 }} />
              <Button size="small" type="text" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => move(i, -1)} aria-label={t('templatesAdmin.moveUp')} />
              <Button size="small" type="text" icon={<ArrowDownOutlined />} disabled={i === fields.length - 1} onClick={() => move(i, 1)} aria-label={t('templatesAdmin.moveDown')} />
              <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.remove')}
                onClick={() => setFields((list) => list.filter((_, j) => j !== i))} />
            </div>
            {LabelInputs({ value: f.label, onChange: (label) => setField(i, { label }), placeholder: t('templatesAdmin.questionPlaceholder') })}
            {f.type === 'number' && (
              <Space size={6} style={{ marginTop: 6 }}>
                <Input size="small" addonBefore={t('templatesAdmin.unit')} value={f.unit} style={{ width: 160 }} onChange={(e) => setField(i, { unit: e.target.value })} />
                <InputNumber size="small" addonBefore="min" value={f.min} onChange={(v) => setField(i, { min: v ?? undefined })} />
                <InputNumber size="small" addonBefore="max" value={f.max} onChange={(v) => setField(i, { max: v ?? undefined })} />
              </Space>
            )}
            {(f.type === 'choice' || f.type === 'multi') && (
              <div className="tpl-options">
                {(f.options ?? []).map((o, k) => (
                  <div className="tpl-option" key={k}>
                    {questionnaire ? (
                      <Select size="small" value={o.value} style={{ width: 96 }}
                        onChange={(v) => setField(i, { options: f.options!.map((x, m) => (m === k ? { ...x, value: v } : x)) })}
                        options={DOSHAS.map((d) => ({ value: d, label: t(`consult.dosha.${d}`) }))} />
                    ) : <span className="cell-sub">{t('templatesAdmin.answer')} {k + 1}</span>}
                    <div style={{ flex: 1 }}>
                      {LabelInputs({
                        value: o.label, placeholder: t('templatesAdmin.answerPlaceholder'),
                        onChange: (label) => setField(i, { options: f.options!.map((x, m) => (m === k ? { ...x, label } : x)) }),
                      })}
                    </div>
                    <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.remove')}
                      disabled={(f.options?.length ?? 0) <= 1}
                      onClick={() => setField(i, { options: f.options!.filter((_, m) => m !== k) })} />
                  </div>
                ))}
                {!questionnaire && (
                  <Button size="small" type="dashed" icon={<PlusOutlined />}
                    onClick={() => setField(i, { options: [...(f.options ?? []), { value: `a${(f.options?.length ?? 0) + 1}`, label: emptyLabel() }] })}>
                    {t('templatesAdmin.addAnswer')}
                  </Button>
                )}
              </div>
            )}
          </Card>
        ))}
        <Button type="dashed" block icon={<PlusOutlined />} onClick={addField}>{t('templatesAdmin.addQuestion')}</Button>
      </div>
    </Modal>
  );
}
