// Pharmacy reports (Additional settings -> "Pharmacy reports"): what to buy, daily report, top selling, slow
// medicines, margin and GST of pharmacy bills. One screen shows every report from the same table shape.
// SAFE TO EDIT: the words (src/i18n/*.json, "pharmacyReports"). The numbers come from backend/apps/pharmacy/reports.py.
import { DatePicker, Empty, Segmented, Table } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import { money } from '../medicines/shared';
import { qty } from './common';

type Column = { key: string; label: string; kind: 'text' | 'money' | 'number' };
type ReportInfo = { code: string; title: string; dates: boolean; money: boolean };
type ReportData = { columns: Column[]; rows: Record<string, string | number>[]; totals: Record<string, string | number> | null };

export function ReportsTab() {
  const { t } = useTranslation();
  const [list, setList] = useState<ReportInfo[]>([]);
  const [code, setCode] = useState('reorder');
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs().startOf('month'), dayjs()]);
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const info = list.find((r) => r.code === code);

  useEffect(() => { api.get<ReportInfo[]>('/pharmacy-reports/').then(({ data: d }) => setList(d)).catch(() => setList([])); }, []);
  useEffect(() => {
    if (!list.some((r) => r.code === code)) return;
    setLoading(true);
    api.get<ReportData>(`/pharmacy-reports/${code}/`, {
      params: { date_from: range[0].format('YYYY-MM-DD'), date_to: range[1].format('YYYY-MM-DD') },
    }).then(({ data: d }) => setData(d)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [code, range, list]);

  const cell = (c: Column, v: string | number | undefined) => {
    if (v === undefined || v === null || v === '') return '';
    return c.kind === 'money' ? <span className="num">{money(v)}</span> : c.kind === 'number' ? <span className="num">{qty(v)}</span> : v;
  };
  const noteKey: Record<string, string> = { reorder: 'reorderNote', margin: 'marginNote', gst: 'gstNote', non_moving: 'offNote' };

  return (
    <>
      <div className="filter-bar">
        <Segmented value={code} onChange={(v) => setCode(String(v))}
          options={list.map((r) => ({ value: r.code, label: t(`pharmacyReports.titles.${r.code}`, { defaultValue: r.title }) }))} />
        {info?.dates && (
          <DatePicker.RangePicker value={range} allowClear={false} format="DD-MM-YYYY"
            onChange={(v) => v?.[0] && v[1] && setRange([v[0], v[1]])} />
        )}
      </div>
      {noteKey[code] && <div className="cell-sub" style={{ margin: '4px 0 12px' }}>{t(`pharmacyReports.${noteKey[code]}`)}</div>}
      <Table
        rowKey={(_, i) => String(i)}
        size="small"
        loading={loading}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        scroll={{ x: 800 }}
        dataSource={data?.rows ?? []}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('pharmacyReports.empty')} /> }}
        columns={(data?.columns ?? []).map((c) => ({
          title: t(`pharmacyReports.cols.${c.key}`, { defaultValue: c.label }), key: c.key, dataIndex: c.key,
          align: c.kind === 'text' ? undefined : ('right' as const),
          render: (v: string | number) => cell(c, v),
        }))}
        summary={() => (data?.totals ? (
          <Table.Summary.Row>
            {data.columns.map((c, i) => (
              <Table.Summary.Cell key={c.key} index={i} align={c.kind === 'text' ? undefined : 'right'}>
                <b>{i === 0 ? t('pharmacy.total') : cell(c, data.totals?.[c.key])}</b>
              </Table.Summary.Cell>
            ))}
          </Table.Summary.Row>
        ) : null)}
      />
    </>
  );
}
