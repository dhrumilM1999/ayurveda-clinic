// The clinic logo (Settings -> Clinic): printed on prescriptions, certificates, reports and bills.
// PNG or JPG, up to 2 MB. Tip: a logo on a white or transparent background, wider than tall, prints best.
import { DeleteOutlined, UploadOutlined } from '@ant-design/icons';
import { App, Button, Space, Upload } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';

export function LogoUpload({ hasLogo, disabled }: { hasLogo: boolean; disabled?: boolean }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [has, setHas] = useState(hasLogo);
  const [url, setUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Show the saved logo (loaded with the login token, so it is not public)
  const loadPreview = useCallback(async () => {
    try {
      const { data } = await api.get('/organization/logo/', { responseType: 'blob' });
      setUrl((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(data); });
    } catch {
      setUrl(null);
    }
  }, []);
  useEffect(() => { setHas(hasLogo); if (hasLogo) loadPreview(); }, [hasLogo, loadPreview]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);

  const upload = async (file: File) => {
    setBusy(true);
    try {
      const body = new FormData();
      body.append('file', file);
      await api.post('/organization/logo/', body);
      setHas(true);
      await loadPreview();
      message.success(t('settings.logoSaved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await api.delete('/organization/logo/');
      setHas(false);
      setUrl(null);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Space size={12} wrap align="center">
      {has && url
        ? <img src={url} alt={t('settings.logo')} className="logo-preview" />
        : <span className="cell-sub">{t('settings.noLogo')}</span>}
      {!disabled && (
        <>
          <Upload accept="image/png,image/jpeg" showUploadList={false} beforeUpload={(file) => { upload(file); return false; }}>
            <Button size="small" icon={<UploadOutlined />} loading={busy}>{has ? t('settings.logoChange') : t('settings.logoUpload')}</Button>
          </Upload>
          {has && <Button size="small" type="text" danger icon={<DeleteOutlined />} disabled={busy} onClick={remove}>{t('common.remove')}</Button>}
        </>
      )}
    </Space>
  );
}
