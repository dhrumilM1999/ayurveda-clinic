// Pharmacy: dispense, stock by batch, purchases, suppliers - always.
// Extra tabs follow the switches in Additional settings: counter sale, sales & returns, bills, stock check,
// stock ledger, reports, racks.
import { Segmented, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { BillsTab } from './BillsTab';
import { CounterSaleTab } from './CounterSaleTab';
import { DispenseTab } from './DispenseTab';
import MedicinesPage from '../medicines/MedicinesPage';
import { LedgerTab } from './LedgerTab';
import { PurchasesTab } from './PurchasesTab';
import { ReportsTab } from './ReportsTab';
import { SalesTab } from './SalesTab';
import { SetupTab } from './SetupTab';
import { StockCheckTab } from './StockCheckTab';
import { StockTab } from './StockTab';
import { SupplierDuesTab } from './SupplierDuesTab';

export default function PharmacyPage() {
  const { t } = useTranslation();
  const { can, hasFeature } = useAuth();
  const [params, setParams] = useSearchParams();
  const billing = hasFeature('pharmacy_billing');

  const tabs = [
    { key: 'dispense', label: t('pharmacy.tabs.dispense'), children: <DispenseTab /> },
    ...(billing && hasFeature('pharmacy_counter_sale') && can('pharmacy.dispense')
      ? [{ key: 'counter', label: t('pharmacy.tabs.counter'), children: <CounterSaleTab /> }] : []),
    ...(billing || hasFeature('pharmacy_sales_returns') ? [{ key: 'sales', label: t('pharmacy.tabs.sales'), children: <SalesTab /> }] : []),
    ...(billing && can('billing.view') ? [{ key: 'bills', label: t('pharmacy.tabs.bills'), children: <BillsTab /> }] : []),
    { key: 'stock', label: t('pharmacy.tabs.stock'), children: <StockTab /> },
    ...(can('medicines.view') && !hasFeature('separate_medicine_menu') ? [{ key: 'medicines', label: t('pharmacy.tabs.medicines'), children: <MedicinesPage embedded /> }] : []),
    { key: 'purchases', label: t('pharmacy.tabs.purchases'), children: <PurchasesTab /> },
    ...(hasFeature('pharmacy_suppliers') && can('pharmacy.stock') ? [{ key: 'dues', label: t('pharmacy.tabs.dues'), children: <SupplierDuesTab /> }] : []),
    ...(hasFeature('pharmacy_stock_check') ? [{ key: 'check', label: t('pharmacy.tabs.check'), children: <StockCheckTab /> }] : []),
    ...(hasFeature('pharmacy_stock_ledger') ? [{ key: 'ledger', label: t('pharmacy.tabs.ledger'), children: <LedgerTab /> }] : []),
    ...(hasFeature('pharmacy_reports') ? [{ key: 'reports', label: t('pharmacy.tabs.reports'), children: <ReportsTab /> }] : []),
    // Racks & suppliers tab: whichever of the two is switched on (Additional settings)
    ...(hasFeature('pharmacy_racks') || hasFeature('pharmacy_suppliers') ? [{
      key: 'setup',
      label: !hasFeature('pharmacy_racks') ? t('pharmacy.tabs.suppliers') : !hasFeature('pharmacy_suppliers') ? t('pharmacy.racks') : t('pharmacy.tabs.setup'),
      children: <SetupTab />,
    }] : []),
  ];
  // The tabs are grouped, so the screen shows 4 clear sections and only the few tabs of the chosen section.
  // SAFE TO EDIT: move a tab key to another group here.
  const GROUPS: { key: string; tabs: string[] }[] = [
    { key: 'sell', tabs: ['dispense', 'counter', 'sales', 'bills'] },
    { key: 'stock', tabs: ['stock', 'medicines', 'check', 'ledger', 'setup'] },
    { key: 'buy', tabs: ['purchases', 'dues'] },
    { key: 'reports', tabs: ['reports'] },
  ];
  // A tab that was switched off (e.g. an old link) falls back to the first tab
  const asked = params.get('tab') ?? 'dispense';
  const tab = tabs.some((x) => x.key === asked) ? asked : 'dispense';
  const groups = GROUPS.map((g) => ({ ...g, items: tabs.filter((x) => g.tabs.includes(x.key)) })).filter((g) => g.items.length > 0);
  const group = groups.find((g) => g.tabs.includes(tab)) ?? groups[0]!;
  const current = tabs.find((x) => x.key === tab)!;

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('pharmacy.title')}</Typography.Title>
          <div className="cell-sub">{t('pharmacy.subtitle')}</div>
        </div>
      </div>
      <Segmented className="pharm-groups" size="large" value={group.key}
        onChange={(key) => setParams({ tab: groups.find((g) => g.key === key)!.items[0]!.key })}
        options={groups.map((g) => ({ value: g.key, label: t(`pharmacy.groups.${g.key}`) }))} />
      {group.items.length > 1 && (
        <div className="pharm-subtabs">
          {group.items.map((x) => (
            <button type="button" key={x.key} className={x.key === tab ? 'active' : ''} onClick={() => setParams({ tab: x.key })}>{x.label}</button>
          ))}
        </div>
      )}
      <div key={tab}>{current.children}</div>
    </>
  );
}
