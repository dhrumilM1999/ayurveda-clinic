// Error log: everything that went wrong for anyone, from login onwards. For the owner.
// SAFE TO EDIT: the words are in src/i18n/*.json under "errorLog".
import { CopyOutlined } from '@ant-design/icons';
import { App, Button, Card, Input, Segmented, Select, Space, Statistic, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { ErrorLogEntry } from '../api/types';
import { useList } from '../api/useList';
import { ListEmpty } from '../components/ListEmpty';
import { LiveSearch } from '../components/LiveSearch';

const LEVEL_COLOR: Record<string, string> = { error: 'red', warning: 'orange', notice: 'default' };
interface Summary { open_errors: number; open_warnings: number; open_notices: number; last_24h: number }

/** A plain-text description of one problem, to paste to Claude in the chat. */
function describe(e: ErrorLogEntry): string {
  const lines = [
    `Error ${e.request_code} (${e.level}, ${e.source}${e.status_code ? `, HTTP ${e.status_code}` : ''}) - seen ${e.count} time(s), last ${dayjs(e.last_seen).format('DD-MM-YYYY HH:mm')}`,
    `User: ${e.username || '-'}  Page: ${e.screen || '-'}  Request: ${[e.method, e.path].filter(Boolean).join(' ') || '-'}`,
    `Message: ${e.message}`,
  ];
  if (e.details) lines.push('', 'Technical detail:', e.details.slice(0, 3000));
  if (e.trail?.length) lines.push('', 'Steps before it:', ...e.trail.map((s) => `${s.t} ${s.type}: ${s.text}`));
  return lines.join('\n');
}

function Detail({ id, onChanged }: { id: string; onChanged: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [row, setRow] = useState<ErrorLogEntry | null>(null);
  const [note, setNote] = useState('');

  useEffect(() => {
    api.get<ErrorLogEntry>(`/error-logs/${id}/`).then(({ data }) => { setRow(data); setNote(data.note); }).catch(() => setRow(null));
  }, [id]);

  const patch = async (body: Partial<ErrorLogEntry>) => {
    try {
      const { data } = await api.patch<ErrorLogEntry>(`/error-logs/${id}/`, body);
      setRow(data);
      onChanged();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const copy = async () => {
    if (!row) return;
    try {
      await navigator.clipboard.writeText(describe(row));
      message.success(t('errorLog.copied'));
    } catch {
      message.error(t('common.saveFailed'));
    }
  };

  if (!row) return null;
  return (
    <div className="errlog-detail">
      <Space wrap style={{ marginBottom: 8 }}>
        <Button size="small" icon={<CopyOutlined />} onClick={copy}>{t('errorLog.copy')}</Button>
        <Button size="small" type={row.is_resolved ? 'default' : 'primary'} onClick={() => patch({ is_resolved: !row.is_resolved })}>
          {row.is_resolved ? t('errorLog.reopen') : t('errorLog.resolve')}
        </Button>
        {row.is_resolved && row.resolved_by_name && <span className="cell-sub">{t('errorLog.resolvedBy', { name: row.resolved_by_name })}</span>}
        <Input size="small" style={{ width: 280 }} maxLength={500} placeholder={t('errorLog.note')} value={note}
          onChange={(e) => setNote(e.target.value)} onBlur={() => note !== row.note && patch({ note })} />
      </Space>
      <div className="cell-sub">
        {t('errorLog.first')}: {dayjs(row.created_at).format('DD-MM-YYYY HH:mm')}
        {row.ip_address ? ` · ${row.ip_address}` : ''}{row.user_agent ? ` · ${row.user_agent}` : ''}
      </div>
      {row.details && (
        <>
          <div className="section-title">{t('errorLog.details')}</div>
          <pre className="errlog-pre">{row.details}</pre>
        </>
      )}
      <div className="section-title">{t('errorLog.trail')}</div>
      {row.trail?.length ? (
        <ol className="errlog-trail">
          {row.trail.map((s, i) => <li key={i}><span className="cell-sub">{s.t}</span> <Tag bordered={false}>{s.type}</Tag> {s.text}</li>)}
        </ol>
      ) : <div className="cell-sub">{t('errorLog.noTrail')}</div>}
    </div>
  );
}

export default function ErrorLogPage() {
  const { t } = useTranslation();
  const [level, setLevel] = useState<string | undefined>();
  const [source, setSource] = useState<string | undefined>();
  const [state, setState] = useState<'open' | 'done' | 'all'>('open');
  const [search, setSearch] = useState('');
  const [session, setSession] = useState<string | undefined>();
  const [summary, setSummary] = useState<Summary | null>(null);

  const { rows, loading, pagination, failed, reload } = useList<ErrorLogEntry>('/error-logs/', {
    level, source, search, session_id: session, ordering: '-last_seen',
    is_resolved: state === 'all' ? undefined : state === 'done',
  });

  const loadSummary = useCallback(() => {
    api.get<Summary>('/error-logs/summary/').then(({ data }) => setSummary(data)).catch(() => setSummary(null));
  }, []);
  useEffect(() => { loadSummary(); }, [loadSummary]);
  const changed = () => { reload(); loadSummary(); };

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('errorLog.title')}</Typography.Title>
        <Space wrap>
          <Segmented value={state} onChange={(v) => setState(v as typeof state)}
            options={[{ value: 'open', label: t('errorLog.stateOpen') }, { value: 'done', label: t('errorLog.stateDone') }, { value: 'all', label: t('errorLog.stateAll') }]} />
          <Select allowClear placeholder={t('errorLog.levelFilter')} style={{ width: 150 }} value={level} onChange={setLevel}
            options={['error', 'warning', 'notice'].map((l) => ({ value: l, label: t(`errorLog.level.${l}`) }))} />
          <Select allowClear placeholder={t('errorLog.sourceFilter')} style={{ width: 130 }} value={source} onChange={setSource}
            options={['backend', 'frontend'].map((s) => ({ value: s, label: t(`errorLog.source.${s}`) }))} />
          <LiveSearch placeholder={t('errorLog.searchHelp')} onSearch={setSearch} loading={loading} width={240} />
        </Space>
      </div>
      <Typography.Paragraph type="secondary">{t('errorLog.help')}</Typography.Paragraph>

      {summary && (
        <Space size={12} wrap style={{ marginBottom: 12 }}>
          <Card size="small"><Statistic title={t('errorLog.open')} value={summary.open_errors} valueStyle={{ color: summary.open_errors ? '#c2412d' : undefined }} /></Card>
          <Card size="small"><Statistic title={t('errorLog.warnings')} value={summary.open_warnings} /></Card>
          <Card size="small"><Statistic title={t('errorLog.notices')} value={summary.open_notices} /></Card>
          <Card size="small"><Statistic title={t('errorLog.last24')} value={summary.last_24h} /></Card>
        </Space>
      )}
      {session && (
        <div style={{ marginBottom: 8 }}>
          <Tag closable onClose={() => setSession(undefined)} color="blue">{t('errorLog.session')}: {session.slice(0, 8)}</Tag>
          <Button size="small" type="link" onClick={() => setSession(undefined)}>{t('errorLog.clearSession')}</Button>
        </div>
      )}

      <Table<ErrorLogEntry>
        rowKey="id" size="small" loading={loading} dataSource={rows} pagination={pagination} scroll={{ x: true }}
        locale={{ emptyText: <ListEmpty failed={failed} onRetry={reload} text={t('errorLog.none')} /> }}
        expandable={{ expandedRowRender: (r) => <Detail id={r.id} onChanged={changed} />, rowExpandable: () => true }}
        columns={[
          { title: t('errorLog.when'), dataIndex: 'last_seen', width: 150, render: (v: string) => dayjs(v).format('DD-MM-YYYY HH:mm') },
          { title: t('errorLog.levelFilter'), dataIndex: 'level', width: 100, render: (l: string, r) => (
            <Space size={4} direction="vertical">
              <Tag color={LEVEL_COLOR[l]} bordered={false}>{t(`errorLog.level.${l}`)}</Tag>
              {r.is_resolved && <Tag color="green" bordered={false}>{t('errorLog.stateDone')}</Tag>}
            </Space>
          ) },
          { title: t('errorLog.who'), dataIndex: 'username', render: (u: string, r) => (
            <div>
              <b>{u || '-'}</b>
              <div className="cell-sub">{r.branch_name}</div>
              {r.session_id && <a onClick={() => setSession(r.session_id)} title={t('errorLog.sessionHelp')}>{t('errorLog.session')}</a>}
            </div>
          ) },
          { title: t('errorLog.what'), dataIndex: 'message', render: (m: string, r) => (
            <div style={{ maxWidth: 520 }}>
              <div style={{ wordBreak: 'break-word' }}>{m.length > 220 ? `${m.slice(0, 220)}…` : m}</div>
              <div className="cell-sub">
                {r.status_code ? `HTTP ${r.status_code} · ` : ''}{[r.method, r.path].filter(Boolean).join(' ')}
              </div>
            </div>
          ) },
          { title: t('errorLog.where'), dataIndex: 'screen', render: (v: string, r) => <div><div>{v || '-'}</div><div className="cell-sub">{t(`errorLog.source.${r.source}`)}</div></div> },
          { title: t('errorLog.times'), dataIndex: 'count', width: 70, align: 'right' as const },
          { title: t('errorLog.code'), dataIndex: 'request_code', width: 100, render: (c: string) => <code>{c}</code> },
        ]}
      />
    </>
  );
}
