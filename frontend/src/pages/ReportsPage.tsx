// Reports: collection, income by doctor / branch, new vs repeat patients, missed follow-ups, GST summary.
// Pick a report, the dates and the branch; the table and the totals come from /reports/<code>/.
// "Excel" and "PDF" download the same report (every download is written to the audit log).
// Each report shows only to staff who may see its data (e.g. money reports need "See bills").
import { FileExcelOutlined, FilePdfOutlined } from '@ant-design/icons';
import { App, Button, DatePicker, Empty, Segmented, Select, Space, Statistic, Table, Typography } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';

type ReportCode = 'collection' | 'by_doctor' | 'by_branch' | 'patients' | 'follow_ups' | 'gst';
type Cell = string | number | null;
type Row = Record<string, Cell>;
interface ReportData {
  code: ReportCode;
  subtitle: string;
  branches: { id: string; name: string }[];
  columns: { key: string; type: 'text' | 'date' | 'month' | 'int' | 'money' }[];
  rows: Row[];
  totals: Row | null;
}

// The permission each report needs (as well as "See reports"), and the totals shown as big numbers on top.
const REPORTS: { code: ReportCode; needs: string; grouped?: boolean; headline: string[] }[] = [
  { code: 'collection', needs: 'billing.view', grouped: true, headline: ['cash', 'upi', 'card', 'refunds', 'net'] },
  { code: 'by_doctor', needs: 'billing.view', headline: ['billed', 'received', 'due'] },
  { code: 'by_branch', needs: 'billing.view', headline: ['billed', 'received', 'due'] },
  { code: 'patients', needs: 'appointments.view', grouped: true, headline: ['patients', 'new', 'repeat', 'repeat_percent'] },
  { code: 'follow_ups', needs: 'patients.view', headline: [] },
  { code: 'gst', needs: 'billing.view', headline: ['net_taxable', 'net_tax'] },
];

/** 1,23,456.50 (Indian grouping) */
const rupees = (v: Cell) => `₹ ${Number(v ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function ReportsPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { me, branch } = useAuth();

  // Branches where the user may see a report (by its permission)
  const branchesFor = (needs: string) =>
    (me?.branches ?? []).filter((b) => b.permissions.includes('reports.view') && b.permissions.includes(needs));
  const available = REPORTS.filter((r) => branchesFor(r.needs).some((b) => b.id === branch?.id)
    && (r.code !== 'by_branch' || branchesFor(r.needs).length > 1));

  const [code, setCode] = useState<ReportCode>(available[0]?.code ?? 'collection');
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs().startOf('month'), dayjs()]);
  const [group, setGroup] = useState<'day' | 'month'>('day');
  const [branchChoice, setBranchChoice] = useState<string>('current');
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<'xlsx' | 'pdf' | null>(null);

  const info = REPORTS.find((r) => r.code === code) ?? REPORTS[0];
  const choosable = branchesFor(info.needs);
  const params = useMemo(() => ({
    date_from: range[0].format('YYYY-MM-DD'),
    date_to: range[1].format('YYYY-MM-DD'),
    branch: branchChoice === 'current' ? branch?.id : branchChoice,
    group,
  }), [range, branchChoice, branch?.id, group]);

  useEffect(() => { setBranchChoice(code === 'by_branch' ? 'all' : 'current'); }, [code, branch?.id]);
  // After switching branch, a report may no longer be allowed: show the first one that is
  const allowedHere = available.some((r) => r.code === code);
  useEffect(() => { if (!allowedHere && available[0]) setCode(available[0].code); }, [allowedHere, available]);

  useEffect(() => {
    if (!allowedHere) return;
    let alive = true;
    setLoading(true);
    api.get<ReportData>(`/reports/${code}/`, { params })
      .then(({ data: d }) => alive && setData(d))
      .catch((err) => { if (alive) { setData(null); message.error(errorMessage(err, t('common.loadFailed'))); } })
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [code, allowedHere, params, message, t]);

  const download = async (kind: 'xlsx' | 'pdf') => {
    setBusy(kind);
    try {
      const { data: blob } = await api.get(`/reports/${code}/`, { params: { ...params, export: kind }, responseType: 'blob' });
      const file = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = file;
      a.download = `${code}-${params.date_from}-to-${params.date_to}.${kind}`;
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(file), 10_000);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setBusy(null);
    }
  };

  if (!available.length) {
    return <Empty description={t('reports.nothingAllowed')} />;
  }

  const label = (key: string) => {
    if (key === 'period') return t(group === 'month' ? 'reports.cols.month' : 'reports.cols.date');
    if (key === 'name') return t(code === 'by_branch' ? 'reports.cols.branch' : 'reports.cols.doctor');
    return t(`reports.cols.${key}`);
  };
  const show = (value: Cell, type: string, key?: string) => {
    if (value === null || value === '') return '—';
    if (value === 'Total') return t('reports.total');
    if (type === 'money') return rupees(value);
    if (type === 'date') return dayjs(String(value)).format('DD-MM-YYYY');
    if (type === 'month') return dayjs(String(value)).format('MMM YYYY');
    if (key === 'repeat_percent') return `${value}%`;
    return value;
  };

  const columns = (data?.code === code ? data.columns : []).map((c) => ({
    title: label(c.key),
    dataIndex: c.key,
    align: (c.type === 'money' || c.type === 'int' ? 'right' : 'left') as 'right' | 'left',
    render: (v: Cell, row: Row) => (c.key === 'patient' && row.patient_id
      ? <Link to={`/patients/${row.patient_id}`}>{String(v)}</Link>
      : show(v, c.type, c.key)),
  }));
  const typeOf = (key: string) => data?.columns.find((c) => c.key === key)?.type ?? 'int';

  const presets: { label: string; value: [Dayjs, Dayjs] }[] = [
    { label: t('reports.range.today'), value: [dayjs(), dayjs()] },
    { label: t('reports.range.yesterday'), value: [dayjs().subtract(1, 'day'), dayjs().subtract(1, 'day')] },
    { label: t('reports.range.thisMonth'), value: [dayjs().startOf('month'), dayjs()] },
    { label: t('reports.range.lastMonth'), value: [dayjs().subtract(1, 'month').startOf('month'), dayjs().subtract(1, 'month').endOf('month')] },
    {
      label: t('reports.range.thisYear'), // financial year: 1 April - 31 March
      value: [dayjs().month() >= 3 ? dayjs().month(3).startOf('month') : dayjs().subtract(1, 'year').month(3).startOf('month'), dayjs()],
    },
  ];

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('reports.title')}</Typography.Title>
          <div className="cell-sub">{t('reports.subtitle')}</div>
        </div>
        <Space wrap>
          <Button icon={<FileExcelOutlined />} loading={busy === 'xlsx'} disabled={!data || loading} onClick={() => download('xlsx')}>
            {t('reports.excel')}
          </Button>
          <Button icon={<FilePdfOutlined />} loading={busy === 'pdf'} disabled={!data || loading} onClick={() => download('pdf')}>
            {t('reports.pdf')}
          </Button>
        </Space>
      </div>

      <div className="report-kinds">
        <Segmented value={code} onChange={(v) => setCode(v as ReportCode)}
          options={available.map((r) => ({ value: r.code, label: t(`reports.kinds.${r.code}`) }))} />
      </div>

      <Space wrap style={{ marginBottom: 8 }}>
        <DatePicker.RangePicker value={range} format="DD-MM-YYYY" allowClear={false} presets={presets}
          onChange={(v) => v?.[0] && v[1] && setRange([v[0], v[1]])} />
        {info.grouped && (
          <Segmented value={group} onChange={(v) => setGroup(v as 'day' | 'month')}
            options={[{ value: 'day', label: t('reports.group.day') }, { value: 'month', label: t('reports.group.month') }]} />
        )}
        {choosable.length > 1 && (
          <Select value={branchChoice} onChange={setBranchChoice} style={{ minWidth: 200 }}
            options={[
              { value: 'current', label: t('reports.currentBranch', { name: branch?.name }) },
              { value: 'all', label: t('reports.allBranches') },
              ...choosable.filter((b) => b.id !== branch?.id).map((b) => ({ value: b.id, label: b.name })),
            ]} />
        )}
      </Space>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>{t(`reports.help.${code}`)}</Typography.Paragraph>

      {data?.code === code && data.totals && info.headline.length > 0 && (
        <div className="stat-row report-headline">
          {info.headline.map((key) => (
            <Statistic key={key} title={label(key)}
              value={String(show(data.totals?.[key] ?? 0, typeOf(key), key))} />
          ))}
        </div>
      )}
      {data?.code === 'follow_ups' && code === 'follow_ups' && (
        <div className="stat-row report-headline">
          <Statistic title={t('reports.missedCount')} value={data.rows.length} />
        </div>
      )}

      <Table<Row>
        className="report-table"
        size="small"
        rowKey={(_, i) => String(i)}
        loading={loading}
        dataSource={data?.code === code ? data.rows : []}
        columns={columns}
        scroll={{ x: true }}
        pagination={{ pageSize: 50, hideOnSinglePage: true, showSizeChanger: false }}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('reports.empty')} /> }}
        summary={() => (data?.code === code && data.totals ? (
          <Table.Summary.Row className="report-total">
            {data.columns.map((c, i) => (
              <Table.Summary.Cell key={c.key} index={i} align={c.type === 'money' || c.type === 'int' ? 'right' : 'left'}>
                <b>{show(data.totals?.[c.key] ?? '', c.type, c.key)}</b>
              </Table.Summary.Cell>
            ))}
          </Table.Summary.Row>
        ) : null)}
      />
    </>
  );
}
