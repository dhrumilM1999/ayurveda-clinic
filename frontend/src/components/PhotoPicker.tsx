// Choose a patient photo: from a file, or take one with the computer's camera.
import { CameraOutlined, DeleteOutlined, UploadOutlined } from '@ant-design/icons';
import { Avatar, Button, Modal, Space } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  value: Blob | null;
  onChange: (photo: Blob | null) => void;
  existingUrl?: string | null;
}

export function PhotoPicker({ value, onChange, existingUrl }: Props) {
  const { t } = useTranslation();
  const fileInput = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const stream = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!value) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(value);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [value]);

  const stopCamera = () => {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  };

  const openCamera = async () => {
    setCameraError(null);
    setCameraOpen(true);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 640 } });
      if (video.current) {
        video.current.srcObject = stream.current;
        await video.current.play();
      }
    } catch {
      setCameraError(t('patients.cameraError'));
    }
  };

  const capture = () => {
    const el = video.current;
    if (!el) return;
    const side = Math.min(el.videoWidth, el.videoHeight);
    const canvas = document.createElement('canvas');
    canvas.width = 480;
    canvas.height = 480;
    canvas.getContext('2d')!.drawImage(el, (el.videoWidth - side) / 2, (el.videoHeight - side) / 2, side, side, 0, 0, 480, 480);
    canvas.toBlob((blob) => blob && onChange(blob), 'image/jpeg', 0.9);
    stopCamera();
    setCameraOpen(false);
  };

  const shown = preview ?? existingUrl ?? undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
      <Avatar size={112} src={shown} shape="square" style={{ borderRadius: 18, background: '#ece6d8', color: '#8a8270' }}>
        {t('patients.photo')}
      </Avatar>
      <Space size={4}>
        <Button size="small" icon={<UploadOutlined />} onClick={() => fileInput.current?.click()}>
          {t('patients.choosePhoto')}
        </Button>
        <Button size="small" icon={<CameraOutlined />} onClick={openCamera}>
          {t('patients.takePhoto')}
        </Button>
        {value && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange(null)} aria-label={t('common.remove')} />}
      </Space>
      <input
        ref={fileInput}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onChange(file);
          e.target.value = '';
        }}
      />
      <Modal
        open={cameraOpen}
        title={t('patients.takePhoto')}
        onCancel={() => {
          stopCamera();
          setCameraOpen(false);
        }}
        onOk={capture}
        okText={t('patients.capture')}
        cancelText={t('common.cancel')}
        okButtonProps={{ disabled: !!cameraError }}
        destroyOnHidden
      >
        {cameraError ? (
          <p>{cameraError}</p>
        ) : (
          <video ref={video} playsInline muted style={{ width: '100%', borderRadius: 12, background: '#000' }} />
        )}
      </Modal>
    </div>
  );
}
