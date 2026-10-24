// Check-up section for lab tests and scans: the doctor advises tests, and later attaches the report.
// SAFE TO EDIT: the words are in src/i18n/*.json under "investigations".
import { DeleteOutlined, EyeOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';
import { App, Button, Empty, Popconfirm, Select, Space, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Investigation, LabTest } from '../../api/types';

export function InvestigationsSection({ visitId, patientId, readOnly }: { visitId: string; patientId: string; readOnly?: boolean }) {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const [tests, setTests] = useState<LabTest[]>([]);
  const [rows, setRows] = useState<Investigation[]>([]);
  const [earlier, setEarlier] = useState<Investigation[]>([]);
  const [pick, setPick] = useState<string | undefined>();
  const [typed, setTyped] = useState('');
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const uploadFor = useRef<Investigation | null>(null);

  const lang = i18n.language.slice(0, 2);
  const nameOf = (r: { test_name: string; test_name_gu?: string; test_name_hi?: string }) =>
    (lang === 'gu' && r.test_name_gu) || (lang === 'hi' && r.test_name_hi) || r.test_name;
  const labelOf = (x: LabTest) => (lang === 'gu' && x.name_gu) || (lang === 'hi' && x.name_hi) || x.name;

  const load = useCallback(() => {
    api.get<LabTest[]>('/lab-tests/').then(({ data }) => setTests(data)).catch(() => setTests([]));
    api.get<Investigation[]>('/investigations/', { params: { visit: visitId } }).then(({ data }) => setRows(data)).catch(() => setRows([]));
    api.get<Investigation[]>('/investigations/', { params: { patient: patientId, status: 'advised' } })
      .then(({ data }) => setEarlier(data.filter((r) => r.visit !== visitId))).catch(() => setEarlier([]));
  }, [visitId, patientId]);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    const name = typed.trim();
    if (!pick && !name) return;
    setBusy(true);
    try {
      await api.post('/investigations/', pick ? { visit: visitId, test: pick } : { visit: visitId, test_name: name });
      setPick(undefined);
      setTyped('');
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  const attach = async (file: File) => {
    const inv = uploadFor.current;
    if (!inv) return;
    const form = new FormData();
    form.append('patient', patientId);
    form.append('title', inv.test_name);
    form.append('document_date', dayjs().format('YYYY-MM-DD'));
    form.append('file', file);
    setBusy(true);
    try {
      const { data } = await api.post<{ id: string }>('/patient-documents/', form);
      await api.patch(`/investigations/${inv.id}/`, { document: data.id });
      message.success(t('common.saved'));
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (r: Investigation, status: Investigation['status']) => {
    try {
      await api.patch(`/investigations/${r.id}/`, { status });
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const remove = async (r: Investigation) => {
    try {
      await api.delete(`/investigations/${r.id}/`);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const view = async (r: Investigation) => {
    if (!r.document) return;
    try {
      const { data } = await api.get(`/patient-documents/${r.document}/file/`, { params: { download: 0 }, responseType: 'blob' });
      const url = URL.createObjectURL(data);
      window.open(url, '_blank', 'noopener');
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  const statusTag = (s: Investigation['status']) => (
    <Tag bordered={false} color={s === 'done' ? 'green' : s === 'advised' ? 'gold' : 'default'}>{t(`investigations.status.${s}`)}</Tag>
  );

  const line = (r: Investigation) => (
    <div key={r.id} className="inv-row">
      <div className="inv-main">
        <b>{nameOf(r)}</b> {statusTag(r.status)}
        <div className="cell-sub">
          {t('investigations.advisedOn', { date: dayjs(r.advised_on).format('DD-MM-YYYY') })}
          {r.reported_on ? ` · ${t('investigations.reportedOn', { date: dayjs(r.reported_on).format('DD-MM-YYYY') })}` : ''}
          {r.note ? ` · ${r.note}` : ''}
        </div>
      </div>
      <Space size={4} wrap>
        {r.document && <Button size="small" icon={<EyeOutlined />} onClick={() => view(r)}>{t('investigations.viewReport')}</Button>}
        {!readOnly && (
          <>
            <Button size="small" icon={<UploadOutlined />} loading={busy} onClick={() => { uploadFor.current = r; input.current?.click(); }}>
              {r.document ? t('investigations.replaceReport') : t('investigations.addReport')}
            </Button>
            {r.status === 'advised' && <Button size="small" onClick={() => setStatus(r, 'done')}>{t('investigations.markDone')}</Button>}
            <Popconfirm title={t('investigations.removeAsk')} okText={t('common.yes')} cancelText={t('common.no')} onConfirm={() => remove(r)}>
              <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.remove')} />
            </Popconfirm>
          </>
        )}
      </Space>
    </div>
  );

  return (
    <>
      <div className="section-title">{t('consult.sections.investigations')}</div>
      {!readOnly && (
        <div className="chip-picker">
          <Space wrap size={8}>
            <Select
              showSearch allowClear value={pick} onChange={setPick} placeholder={t('investigations.pick')} style={{ width: 300 }}
              optionFilterProp="label" onSearch={setTyped}
              options={tests.map((x) => ({ value: x.id, label: `${labelOf(x)}${lang !== 'en' ? ` · ${x.name}` : ''}` }))}
              notFoundContent={typed ? t('investigations.notInList', { name: typed }) : undefined}
            />
            <Button type="primary" icon={<PlusOutlined />} loading={busy} onClick={add} disabled={!pick && !typed.trim()}>
              {pick || !typed.trim() ? t('investigations.advise') : t('investigations.adviseTyped')}
            </Button>
          </Space>
          <div className="cell-sub" style={{ marginTop: 6 }}>{t('investigations.help')}</div>
          <input
            ref={input} type="file" accept="application/pdf,image/jpeg,image/png,image/webp" style={{ display: 'none' }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) attach(f); e.target.value = ''; }}
          />
        </div>
      )}
      {rows.length ? rows.map(line) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('investigations.none')} />}
      {earlier.length > 0 && (
        <>
          <div className="section-title">{t('investigations.earlier', { n: earlier.length })}</div>
          {earlier.map(line)}
        </>
      )}
    </>
  );
}
