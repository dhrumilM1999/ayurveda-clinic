import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// Choose a patient photo: from a file, or take one with the computer's camera.
import { CameraOutlined, DeleteOutlined, UploadOutlined } from '@ant-design/icons';
import { Avatar, Button, Modal, Space } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
export function PhotoPicker({ value, onChange, existingUrl }) {
    const { t } = useTranslation();
    const fileInput = useRef(null);
    const video = useRef(null);
    const [preview, setPreview] = useState(null);
    const [cameraOpen, setCameraOpen] = useState(false);
    const [cameraError, setCameraError] = useState(null);
    const stream = useRef(null);
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
        }
        catch {
            setCameraError(t('patients.cameraError'));
        }
    };
    const capture = () => {
        const el = video.current;
        if (!el)
            return;
        const side = Math.min(el.videoWidth, el.videoHeight);
        const canvas = document.createElement('canvas');
        canvas.width = 480;
        canvas.height = 480;
        canvas.getContext('2d').drawImage(el, (el.videoWidth - side) / 2, (el.videoHeight - side) / 2, side, side, 0, 0, 480, 480);
        canvas.toBlob((blob) => blob && onChange(blob), 'image/jpeg', 0.9);
        stopCamera();
        setCameraOpen(false);
    };
    const shown = preview ?? existingUrl ?? undefined;
    return (_jsxs("div", { style: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }, children: [_jsx(Avatar, { size: 112, src: shown, shape: "square", style: { borderRadius: 18, background: '#ece6d8', color: '#8a8270' }, children: t('patients.photo') }), _jsxs(Space, { size: 4, children: [_jsx(Button, { size: "small", icon: _jsx(UploadOutlined, {}), onClick: () => fileInput.current?.click(), children: t('patients.choosePhoto') }), _jsx(Button, { size: "small", icon: _jsx(CameraOutlined, {}), onClick: openCamera, children: t('patients.takePhoto') }), value && _jsx(Button, { size: "small", type: "text", danger: true, icon: _jsx(DeleteOutlined, {}), onClick: () => onChange(null), "aria-label": t('common.remove') })] }), _jsx("input", { ref: fileInput, type: "file", accept: "image/jpeg,image/png,image/webp", style: { display: 'none' }, onChange: (e) => {
                    const file = e.target.files?.[0];
                    if (file)
                        onChange(file);
                    e.target.value = '';
                } }), _jsx(Modal, { open: cameraOpen, title: t('patients.takePhoto'), onCancel: () => {
                    stopCamera();
                    setCameraOpen(false);
                }, onOk: capture, okText: t('patients.capture'), cancelText: t('common.cancel'), okButtonProps: { disabled: !!cameraError }, destroyOnClose: true, children: cameraError ? (_jsx("p", { children: cameraError })) : (_jsx("video", { ref: video, playsInline: true, muted: true, style: { width: '100%', borderRadius: 12, background: '#000' } })) })] }));
}
