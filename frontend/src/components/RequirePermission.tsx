// Shows the screen only if the user has the permission in the current branch.
import { Result } from 'antd';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';

export function RequirePermission({ code, children }: { code: string; children: ReactNode }) {
  const { can } = useAuth();
  const { t } = useTranslation();
  if (!can(code)) {
    return <Result status="403" title={t('common.noAccessTitle')} subTitle={t('common.noAccessText')} />;
  }
  return <>{children}</>;
}
