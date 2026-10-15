// What a table shows when it has no rows: the normal "nothing here yet" text, or, when loading FAILED (server
// off, bad connection), a clear message with a Retry button. Without this a failed load looked like "no patients"
// and people registered the same patient again. Used by every list that loads with useList.
import { Button, Space } from 'antd';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

export function ListEmpty({ failed, onRetry, text }: { failed: boolean; onRetry: () => void; text: ReactNode }) {
  const { t } = useTranslation();
  if (!failed) return <>{text}</>;
  return (
    <Space direction="vertical" size={8}>
      <span>{t('common.loadFailedTable')}</span>
      <Button size="small" type="primary" onClick={onRetry}>{t('common.retry')}</Button>
    </Space>
  );
}
