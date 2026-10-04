// List of stock received (purchases) in this branch.
import { PlusOutlined } from '@ant-design/icons';
import { Button, Table } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { PurchaseRecord } from '../../api/types';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { money } from '../medicines/shared';
import { expiryText } from './DispenseTab';
import { PurchaseModal } from './PurchaseModal';

export function PurchasesTab() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [open, setOpen] = useState(false);
  const { rows, loading, reload, pagination } = useList<PurchaseRecord>('/purchases/', {});

  return (
    <>
      <div className="section-toolbar">
        <span className="cell-sub">{t('pharmacy.purchasesHelp')}</span>
        {can('pharmacy.stock') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>{t('pharmacy.addPurchase')}</Button>}
      </div>
      <Table<PurchaseRecord>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        locale={{ emptyText: t('pharmacy.noPurchases') }}
        expandable={{
          expandedRowRender: (p) => (
            <Table size="small" rowKey="id" pagination={false} dataSource={p.items} className="inner-table"
              columns={[
                { title: t('rx.medicine'), dataIndex: 'medicine_name' },
                { title: t('pharmacy.batch'), dataIndex: 'batch_no', render: (b: string) => <span className="mono">{b}</span> },
                { title: t('pharmacy.expiry'), dataIndex: 'expiry_date', render: expiryText },
                { title: t('pharmacy.qty'), dataIndex: 'quantity', align: 'right' as const, render: (v: string) => <span className="num">{Number(v)}</span> },
                { title: t('pharmacy.purchaseRate'), dataIndex: 'purchase_rate', align: 'right' as const, render: (v: string | null) => <span className="num">{money(v)}</span> },
                { title: 'MRP', dataIndex: 'mrp', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
                { title: t('pharmacy.amount'), dataIndex: 'amount', align: 'right' as const, render: (v: string) => <span className="num">{money(v)}</span> },
              ]} />
          ),
        }}
        columns={[
          { title: t('pharmacy.invoiceDate'), dataIndex: 'invoice_date', width: 130, render: (d: string) => <b>{dayjs(d).format('DD-MM-YYYY')}</b> },
          { title: t('pharmacy.invoiceNo'), dataIndex: 'invoice_no', render: (v: string) => v || '—' },
          { title: t('pharmacy.supplier'), dataIndex: 'supplier_name', render: (v: string) => v || '—' },
          { title: t('pharmacy.medicines'), key: 'n', width: 110, align: 'center' as const, render: (_: unknown, p: PurchaseRecord) => p.items.length },
          { title: t('pharmacy.purchaseTotal'), dataIndex: 'total_amount', width: 140, align: 'right' as const, render: (v: string) => <b className="num">{money(v)}</b> },
          { title: t('pharmacy.enteredBy'), dataIndex: 'created_by_name', width: 160 },
        ]}
      />
      {open && <PurchaseModal onClose={(saved) => { setOpen(false); if (saved) reload(); }} />}
    </>
  );
}
