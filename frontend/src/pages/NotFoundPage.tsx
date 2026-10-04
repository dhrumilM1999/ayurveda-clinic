import { Button, Result } from 'antd';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

export default function NotFoundPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <Result
      status="404"
      title={t('common.notFound')}
      extra={<Button onClick={() => navigate('/')}>{t('menu.dashboard')}</Button>}
    />
  );
}
