// Purchase invoices (stock in), opening stock, and returns to suppliers.
import { PlusOutlined } from '@ant-design/icons';
import { Button, Input, Segmented, Space, Table, Tag } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { PurchaseItemRecord, PurchaseRecord, PurchaseReturnRecord } from '../../api/types';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { expiryText, qty } from './common';
import { PurchaseModal } from './PurchaseModal';

export function PurchasesTab() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [view, setView] = useState<'purchases' | 'opening' | 'returns'>('purchases');
  const [open, setOpen] = useState<'purchase' | 'opening' | null>(null);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');

  return (
    <>
      <div className="filter-bar">
        <Segmented value={view} onChange={(v) => setView(v as typeof view)}
          options={[
            { value: 'purchases', label: t('pharmacy.purchaseInvoices') },
            { value: 'opening', label: t('pharmacy.openingStock') },
            { value: 'returns', label: t('pharmacy.supplierReturns') },
          ]} />
        {view !== 'returns' && (
          <Input.Search allowClear placeholder={t('pharmacy.purchaseSearch')} value={search} style={{ width: 260 }}
            onChange={(e) => { setSearch(e.target.value); if (!e.target.value) setQuery(''); }} onSearch={(v) => setQuery(v.trim())} />
        )}
        <span style={{ flex: 1 }} />
        {can('pharmacy.stock') && view !== 'returns' && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(view === 'opening' ? 'opening' : 'purchase')}>
            {view === 'opening' ? t('pharmacy.openingStock') : t('pharmacy.addPurchase')}
          </Button>
        )}
      </div>
      {view === 'returns' ? <ReturnsList /> : <PurchaseList key={`${view}-${open}`} opening={view === 'opening'} query={query} />}
      {open && <PurchaseModal opening={open === 'opening'} onClose={() => setOpen(null)} />}
    </>
  );
}

function PurchaseList({ opening, query }: { opening: boolean; query: string }) {
  const { t } = useTranslation();
  const { rows, loading, pagination } = useList<PurchaseRecord>('/purchases/', { opening: opening ? 1 : 0, q: query || undefined });
  return (
    <Table<PurchaseRecord>
      rowKey="id"
      loading={loading}
      dataSource={rows}
      pagination={pagination}
      locale={{ emptyText: t('pharmacy.noPurchases') }}
      expandable={{
        expandedRowRender: (p) => (
          <Table<PurchaseItemRecord> size="small" rowKey="id" pagination={false} dataSource={p.items} className="inner-table" scroll={{ x: 900 }}
            columns={[
              { title: t('rx.medicine'), dataIndex: 'medicine_name' },
              { title: t('pharmacy.batch'), dataIndex: 'batch_no', render: (b: string) => <span className="mono">{b}</span> },
              { title: t('pharmacy.mfg'), dataIndex: 'mfg_date', render: expiryText },
              { title: t('pharmacy.expiry'), dataIndex: 'expiry_date', render: expiryText },
              { title: t('pharmacy.qty'), key: 'q', align: 'right' as const, render: (_: unknown, i: PurchaseItemRecord) => <span className="num">{qty(i.quantity)}{Number(i.free_quantity) ? ` + ${qty(i.free_quantity)} ${t('pharmacy.freeShort')}` : ''}</span> },
              { title: t('pharmacy.rateNoGst'), dataIndex: 'purchase_rate', align: 'right' as const, render: (v: string | null) => <span className="num">{money(v)}</span> },
              { title: t('pharmacy.discount'), dataIndex: 'discount_percent', align: 'right' as const, render: (v: string) => (Number(v) ? `${qty(v)}%` : '—') },
              { title: 'GST', dataIndex: 'gst_rate', align: 'right' as const, render: (v: string) => `${qty(v)}%` },
              { title: 'MRP', dataIndex: 'mrp', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
              { title: t('pharmacy.sellingPrice'), dataIndex: 'selling_price', align: 'right' as const, render: (v: string | null) => <span className="num">{money(v)}</span> },
              { title: t('pharmacy.amount'), dataIndex: 'amount', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
            ]} />
        ),
      }}
      columns={[
        { title: t('pharmacy.invoiceDate'), dataIndex: 'invoice_date', width: 120, render: (d: string) => <b>{dayjs(d).format('DD-MM-YYYY')}</b> },
        ...(opening ? [] : [
          { title: t('pharmacy.invoiceNo'), dataIndex: 'invoice_no', render: (v: string) => v || '—' },
          { title: t('pharmacy.supplier'), dataIndex: 'supplier_name', render: (v: string) => v || '—' },
        ]),
        { title: t('pharmacy.medicines'), key: 'n', width: 110, align: 'center' as const, render: (_: unknown, p: PurchaseRecord) => p.items.length },
        ...(opening ? [] : [{ title: 'GST', dataIndex: 'gst_amount', width: 110, align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> }]),
        { title: t('pharmacy.purchaseTotal'), dataIndex: 'total_amount', width: 130, align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
        { title: t('pharmacy.enteredBy'), dataIndex: 'created_by_name', width: 160 },
      ]}
    />
  );
}

function ReturnsList() {
  const { t } = useTranslation();
  const { rows, loading, pagination } = useList<PurchaseReturnRecord>('/purchase-returns/', {});
  return (
    <>
      <div className="form-help">{t('pharmacy.supplierReturnsHelp')}</div>
      <Table<PurchaseReturnRecord>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        locale={{ emptyText: t('pharmacy.noSupplierReturns') }}
        columns={[
          { title: t('appointments.date'), dataIndex: 'return_date', width: 120, render: (d: string) => <b>{dayjs(d).format('DD-MM-YYYY')}</b> },
          { title: t('pharmacy.supplier'), dataIndex: 'supplier_name', render: (v: string) => v || '—' },
          {
            title: t('pharmacy.medicines'), key: 'items',
            render: (_: unknown, r: PurchaseReturnRecord) => (
              <Space size={4} wrap>{r.items.map((i) => <Tag key={i.id} className="tag-tight" style={{ marginInlineStart: 0 }}>{i.medicine_name} · {i.batch_no} · {qty(i.quantity)}</Tag>)}</Space>
            ),
          },
          { title: t('pharmacy.reason'), dataIndex: 'reason' },
          { title: t('pharmacy.debitNoteNo'), dataIndex: 'reference', render: (v: string) => v || '—' },
          { title: t('pharmacy.amount'), dataIndex: 'total_amount', width: 120, align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
        ]}
      />
    </>
  );
}
