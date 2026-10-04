// Pharmacy: dispense prescriptions, stock by batch, purchases (stock in) and suppliers.
import { Tabs, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { DispenseTab } from './DispenseTab';
import { PurchasesTab } from './PurchasesTab';
import { StockTab } from './StockTab';
import { SuppliersTab } from './SuppliersTab';

export default function PharmacyPage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') ?? 'dispense';

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('pharmacy.title')}</Typography.Title>
          <div className="cell-sub">{t('pharmacy.subtitle')}</div>
        </div>
      </div>
      <Tabs
        className="page-tabs"
        activeKey={tab}
        onChange={(key) => setParams({ tab: key })}
        destroyInactiveTabPane
        items={[
          { key: 'dispense', label: t('pharmacy.tabs.dispense'), children: <DispenseTab /> },
          { key: 'stock', label: t('pharmacy.tabs.stock'), children: <StockTab /> },
          { key: 'purchases', label: t('pharmacy.tabs.purchases'), children: <PurchasesTab /> },
          ...(can('pharmacy.stock') ? [{ key: 'suppliers', label: t('pharmacy.tabs.suppliers'), children: <SuppliersTab /> }] : []),
        ]}
      />
    </>
  );
}
