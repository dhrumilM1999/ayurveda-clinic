// Stock ledger: every stock movement (opening, purchase, free, sale, returns, damaged, expired, corrections,
// physical count) with opening and closing balance for the chosen period.
import { Button, DatePicker, Drawer, Select, Spin, Table, Tag } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { Ledger, MovementKind, StockMovement } from '../../api/types';
import { MedicinePicker, qty } from './common';

export const KINDS: MovementKind[] = ['opening', 'purchase', 'free', 'dispense', 'sale_return', 'purchase_return', 'damaged', 'expired', 'adjust', 'verification'];
const KIND_COLORS: Record<MovementKind, string> = {
  opening: 'default', purchase: 'green', free: 'cyan', dispense: 'blue', sale_return: 'geekblue', purchase_return: 'orange',
  damaged: 'red', expired: 'magenta', adjust: 'gold', verification: 'purple',
};

function LedgerView({ medicine, initialRange }: { medicine?: string; initialRange?: [Dayjs, Dayjs] }) {
  const { t } = useTranslation();
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(initialRange ?? null);
  const [kind, setKind] = useState<MovementKind>();
  const [data, setData] = useState<Ledger | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: d } = await api.get<Ledger>('/stock/movements/', {
        params: {
          medicine, kind,
          date_from: range?.[0].format('YYYY-MM-DD'), date_to: range?.[1].format('YYYY-MM-DD'),
        },
      });
      setData(d);
    } finally {
      setLoading(false);
    }
  }, [medicine, kind, range]);
  useEffect(() => { load(); }, [load]);

  return (
    <>
      <div className="filter-bar">
        <DatePicker.RangePicker value={range} onChange={(v) => setRange(v as [Dayjs, Dayjs] | null)} format="DD-MM-YYYY" />
        <Select allowClear placeholder={t('pharmacy.allMovements')} value={kind} onChange={setKind} style={{ width: 200 }}
          options={KINDS.map((k) => ({ value: k, label: t(`pharmacy.kinds.${k}`) }))} />
      </div>
      {!data ? <Spin /> : (
        <>
          {medicine && (
            <div className="ledger-statement">
              <div><span className="cell-sub">{t('pharmacy.openingBalance')}</span><b className="num">{qty(data.opening)}</b></div>
              {KINDS.filter((k) => data.by_kind[k]).map((k) => (
                <div key={k}><span className="cell-sub">{t(`pharmacy.kinds.${k}`)}</span>
                  <b className={`num ${Number(data.by_kind[k]) < 0 ? 'text-out' : 'text-in'}`}>{Number(data.by_kind[k]) > 0 ? '+' : ''}{qty(data.by_kind[k])}</b></div>
              ))}
              <div className="strong"><span className="cell-sub">{t('pharmacy.closingBalance')}</span><b className="num">{qty(data.closing)}</b></div>
            </div>
          )}
          <Table<StockMovement>
            rowKey="id"
            size="small"
            loading={loading}
            pagination={{ pageSize: 50, hideOnSinglePage: true }}
            dataSource={data.lines}
            scroll={{ x: 800 }}
            locale={{ emptyText: t('pharmacy.noMovements') }}
            columns={[
              { title: t('pharmacy.when'), dataIndex: 'created_at', width: 130, render: (d: string) => dayjs(d).format('DD-MM-YY HH:mm') },
              ...(medicine ? [] : [{ title: t('rx.medicine'), dataIndex: 'medicine_name' }]),
              { title: t('pharmacy.batch'), dataIndex: 'batch_no', render: (b: string) => <span className="mono">{b}</span> },
              { title: t('pharmacy.type'), dataIndex: 'kind', render: (k: MovementKind) => <Tag color={KIND_COLORS[k]} className="tag-tight" style={{ marginInlineStart: 0 }}>{t(`pharmacy.kinds.${k}`)}</Tag> },
              {
                title: t('pharmacy.change'), key: 'q', align: 'right' as const,
                render: (_: unknown, m: StockMovement) => (
                  <b className={`num ${Number(m.quantity) < 0 ? 'text-out' : 'text-in'}`}>{Number(m.quantity) > 0 ? '+' : ''}{qty(m.quantity)}</b>
                ),
              },
              { title: t('pharmacy.balance'), dataIndex: 'balance_after', align: 'right' as const, render: (v: string) => <span className="num">{qty(v)}</span> },
              {
                title: t('pharmacy.reference'), key: 'r',
                render: (_: unknown, m: StockMovement) => (
                  <div style={{ lineHeight: 1.35 }}>
                    {m.reference_label || m.reason || '—'}
                    <div className="cell-sub">{[m.reference_label ? m.reason : '', m.by].filter(Boolean).join(' · ')}</div>
                  </div>
                ),
              },
            ]}
          />
        </>
      )}
    </>
  );
}

export function LedgerTab() {
  const { t } = useTranslation();
  const [medicine, setMedicine] = useState<{ id: string; name: string } | null>(null);
  return (
    <>
      <div className="filter-bar">
        <div style={{ width: 340 }}>
          <MedicinePicker size="middle" value={medicine?.id} label={medicine?.name} placeholder={t('pharmacy.ledgerPick')}
            onPick={(m) => setMedicine({ id: m.id, name: m.name })} />
        </div>
        {medicine && <Button onClick={() => setMedicine(null)}>{t('pharmacy.allMedicines')}</Button>}
        <span className="cell-sub">{t('pharmacy.ledgerHelp')}</span>
      </div>
      <LedgerView key={medicine?.id ?? 'all'} medicine={medicine?.id} initialRange={[dayjs().startOf('month'), dayjs()]} />
    </>
  );
}

export function LedgerDrawer({ medicine, name, onClose }: { medicine: string; name: string; onClose: () => void }) {
  const { t } = useTranslation();
  return (
    <Drawer open width={860} title={t('pharmacy.historyTitle', { name })} onClose={onClose}>
      <LedgerView medicine={medicine} />
    </Drawer>
  );
}
