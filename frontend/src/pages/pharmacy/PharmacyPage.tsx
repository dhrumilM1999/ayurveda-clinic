// Pharmacy: dispense and bill, sales and returns, bills and daily closing, stock with racks and alerts,
// purchases / opening stock / supplier returns, physical stock check, stock ledger, set-up (racks, suppliers).
import { Tabs, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { BillsTab } from './BillsTab';
import { DispenseTab } from './DispenseTab';
import { LedgerTab } from './LedgerTab';
import { PurchasesTab } from './PurchasesTab';
import { SalesTab } from './SalesTab';
import { SetupTab } from './SetupTab';
import { StockCheckTab } from './StockCheckTab';
import { StockTab } from './StockTab';

export default function PharmacyPage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') ?? 'dispense';

  const tabs = [
    { key: 'dispense', label: t('pharmacy.tabs.dispense'), children: <DispenseTab /> },
    { key: 'sales', label: t('pharmacy.tabs.sales'), children: <SalesTab /> },
    ...(can('billing.view') ? [{ key: 'bills', label: t('pharmacy.tabs.bills'), children: <BillsTab /> }] : []),
    { key: 'stock', label: t('pharmacy.tabs.stock'), children: <StockTab /> },
    { key: 'purchases', label: t('pharmacy.tabs.purchases'), children: <PurchasesTab /> },
    { key: 'check', label: t('pharmacy.tabs.check'), children: <StockCheckTab /> },
    { key: 'ledger', label: t('pharmacy.tabs.ledger'), children: <LedgerTab /> },
    { key: 'setup', label: t('pharmacy.tabs.setup'), children: <SetupTab /> },
  ];

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
