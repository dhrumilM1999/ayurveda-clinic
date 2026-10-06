// Pharmacy: dispense, stock by batch, purchases, suppliers - always.
// Extra tabs follow the switches in Additional settings: counter sale, sales & returns, bills, stock check,
// stock ledger, racks.
import { Tabs, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { BillsTab } from './BillsTab';
import { CounterSaleTab } from './CounterSaleTab';
import { DispenseTab } from './DispenseTab';
import { LedgerTab } from './LedgerTab';
import { PurchasesTab } from './PurchasesTab';
import { SalesTab } from './SalesTab';
import { SetupTab } from './SetupTab';
import { StockCheckTab } from './StockCheckTab';
import { StockTab } from './StockTab';

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
    { key: 'purchases', label: t('pharmacy.tabs.purchases'), children: <PurchasesTab /> },
    ...(hasFeature('pharmacy_stock_check') ? [{ key: 'check', label: t('pharmacy.tabs.check'), children: <StockCheckTab /> }] : []),
    ...(hasFeature('pharmacy_stock_ledger') ? [{ key: 'ledger', label: t('pharmacy.tabs.ledger'), children: <LedgerTab /> }] : []),
    // Racks & suppliers tab: whichever of the two is switched on (Additional settings)
    ...(hasFeature('pharmacy_racks') || hasFeature('pharmacy_suppliers') ? [{
      key: 'setup',
      label: !hasFeature('pharmacy_racks') ? t('pharmacy.tabs.suppliers') : !hasFeature('pharmacy_suppliers') ? t('pharmacy.racks') : t('pharmacy.tabs.setup'),
      children: <SetupTab />,
    }] : []),
  ];
  // A tab that was switched off (e.g. an old link) falls back to the first tab
  const asked = params.get('tab') ?? 'dispense';
  const tab = tabs.some((x) => x.key === asked) ? asked : 'dispense';

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('pharmacy.title')}</Typography.Title>
          <div className="cell-sub">{t('pharmacy.subtitle')}</div>
        </div>
      </div>
      <Tabs className="page-tabs" activeKey={tab} onChange={(key) => setParams({ tab: key })} destroyInactiveTabPane items={tabs} />
    </>
  );
}
