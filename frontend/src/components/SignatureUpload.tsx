// A doctor's signature image (printed on prescriptions and certificates). PNG or JPG, up to 1 MB.
// Tip: sign on white paper, take a photo, crop it close to the signature.
import { CheckCircleFilled, DeleteOutlined, UploadOutlined } from '@ant-design/icons';
import { App, Button, Space, Upload } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';

export function SignatureUpload({ staffId, hasSignature }: { staffId: string; hasSignature: boolean }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [has, setHas] = useState(hasSignature);
  const [busy, setBusy] = useState(false);

  const upload = async (file: File) => {
    setBusy(true);
    try {
      const body = new FormData();
      body.append('file', file);
      await api.post(`/staff/${staffId}/signature/`, body);
      setHas(true);
      message.success(t('staff.signatureSaved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await api.delete(`/staff/${staffId}/signature/`);
      setHas(false);
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Space size={8} wrap>
      {has && <span><CheckCircleFilled style={{ color: 'var(--clinic-primary)' }} /> {t('staff.signatureOn')}</span>}
      <Upload accept="image/png,image/jpeg" showUploadList={false} beforeUpload={(file) => { upload(file); return false; }}>
        <Button size="small" icon={<UploadOutlined />} loading={busy}>{has ? t('staff.signatureChange') : t('staff.signatureUpload')}</Button>
      </Upload>
      {has && <Button size="small" type="text" danger icon={<DeleteOutlined />} disabled={busy} onClick={remove}>{t('common.remove')}</Button>}
    </Space>
  );
}
