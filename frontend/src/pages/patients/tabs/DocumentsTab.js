import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Uploaded reports and files. Files are private: opened through the API (written to the audit log).
import { DeleteOutlined, DownloadOutlined, EyeOutlined, FilePdfOutlined, FileImageOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, App, Button, DatePicker, Form, Input, Modal, Popconfirm, Space, Table, Typography, Upload } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import { useMasterLabel } from '../../../api/masters';
import { useAuth } from '../../../auth/AuthContext';
import { MasterSelect } from '../../../components/MasterSelect';
function size(bytes) {
    return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`;
}
export function DocumentsTab({ patientId }) {
    const { t } = useTranslation();
    const { message } = App.useApp();
    const { can } = useAuth();
    const label = useMasterLabel();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(false);
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [files, setFiles] = useState([]);
    const [form] = Form.useForm();
    const canView = can('emr.view');
    const canUpload = can('patients.edit') || can('patients.create') || can('emr.edit');
    const load = useCallback(async () => {
        if (!canView)
            return;
        setLoading(true);
        try {
            const { data } = await api.get('/patient-documents/', { params: { patient: patientId } });
            setRows(data);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
        finally {
            setLoading(false);
        }
    }, [patientId, canView, message, t]);
    useEffect(() => {
        load();
    }, [load]);
    const openFile = async (doc, download) => {
        try {
            const { data } = await api.get(`/patient-documents/${doc.id}/file/`, {
                params: { download: download ? 1 : 0 }, responseType: 'blob',
            });
            const url = URL.createObjectURL(data);
            if (download) {
                const link = document.createElement('a');
                link.href = url;
                link.download = doc.original_name;
                link.click();
            }
            else {
                window.open(url, '_blank', 'noopener');
            }
            window.setTimeout(() => URL.revokeObjectURL(url), 60000);
        }
        catch (err) {
            message.error(errorMessage(err, t('common.loadFailed')));
        }
    };
    const save = async () => {
        const values = await form.validateFields();
        const file = files[0]?.originFileObj;
        if (!file) {
            message.warning(t('documents.chooseFile'));
            return;
        }
        const body = new FormData();
        body.append('patient', patientId);
        body.append('title', values.title);
        body.append('file', file);
        if (values.document_type)
            body.append('document_type', values.document_type);
        if (values.document_date)
            body.append('document_date', values.document_date.format('YYYY-MM-DD'));
        if (values.notes)
            body.append('notes', values.notes);
        setSaving(true);
        try {
            await api.post('/patient-documents/', body);
            message.success(t('documents.uploaded'));
            setOpen(false);
            load();
        }
        catch (err) {
            message.error(errorMessage(err, t('common.saveFailed')));
        }
        finally {
            setSaving(false);
        }
    };
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", style: { marginBottom: 12 }, children: [_jsx(Typography.Text, { type: "secondary", children: t('documents.help') }), canUpload && (_jsx(Button, { type: "primary", icon: _jsx(UploadOutlined, {}), onClick: () => { form.resetFields(); setFiles([]); setOpen(true); }, children: t('documents.upload') }))] }), !canView ? (_jsx(Alert, { type: "info", showIcon: true, message: t('documents.cannotView') })) : (_jsx(Table, { rowKey: "id", size: "small", loading: loading, dataSource: rows, pagination: false, scroll: { x: true }, columns: [
                    {
                        title: t('documents.title'), dataIndex: 'title',
                        render: (title, d) => (_jsxs(Space, { children: [d.content_type === 'application/pdf' ? _jsx(FilePdfOutlined, { style: { color: '#c2412d' } }) : _jsx(FileImageOutlined, { style: { color: '#3d6fb6' } }), _jsxs("div", { children: [_jsx("div", { style: { fontWeight: 600 }, children: title }), _jsxs(Typography.Text, { type: "secondary", style: { fontSize: 12 }, children: [d.original_name, " \u00B7 ", size(d.size_bytes)] })] })] })),
                    },
                    { title: t('documents.type'), dataIndex: 'document_type', render: (v) => label(v) || '—' },
                    { title: t('documents.date'), dataIndex: 'document_date', render: (v) => (v ? dayjs(v).format('DD-MM-YYYY') : '—') },
                    {
                        title: t('documents.uploadedBy'), key: 'by',
                        render: (_, d) => `${d.uploaded_by_name} · ${dayjs(d.created_at).format('DD-MM-YYYY')}`,
                    },
                    {
                        title: '', key: 'actions', width: 140,
                        render: (_, d) => (_jsxs(Space, { size: 4, children: [_jsx(Button, { size: "small", icon: _jsx(EyeOutlined, {}), onClick: () => openFile(d, false), children: t('common.view') }), _jsx(Button, { size: "small", icon: _jsx(DownloadOutlined, {}), onClick: () => openFile(d, true), "aria-label": t('documents.download') }), can('emr.edit') && (_jsx(Popconfirm, { title: t('documents.confirmRemove'), okText: t('common.yes'), cancelText: t('common.no'), onConfirm: () => api.delete(`/patient-documents/${d.id}/`).then(load), children: _jsx(Button, { size: "small", type: "text", danger: true, icon: _jsx(DeleteOutlined, {}), "aria-label": t('common.remove') }) }))] })),
                    },
                ] })), _jsx(Modal, { open: open, title: t('documents.upload'), onCancel: () => setOpen(false), onOk: save, confirmLoading: saving, okText: t('documents.upload'), cancelText: t('common.cancel'), destroyOnClose: true, children: _jsxs(Form, { form: form, layout: "vertical", children: [_jsxs(Upload.Dragger, { fileList: files, beforeUpload: () => false, maxCount: 1, accept: ".pdf,.jpg,.jpeg,.png,.webp", onChange: ({ fileList }) => {
                                setFiles(fileList);
                                const name = fileList[0]?.name;
                                if (name && !form.getFieldValue('title'))
                                    form.setFieldValue('title', name.replace(/\.[^.]+$/, ''));
                            }, style: { marginBottom: 16 }, children: [_jsx("p", { className: "ant-upload-drag-icon", children: _jsx(UploadOutlined, {}) }), _jsx("p", { children: t('documents.dropHere') }), _jsx("p", { className: "ant-upload-hint", children: t('documents.allowed') })] }), _jsx(Form.Item, { name: "title", label: t('documents.title'), rules: [{ required: true, message: t('common.required') }], children: _jsx(Input, {}) }), _jsx(Form.Item, { name: "document_type", label: t('documents.type'), children: _jsx(MasterSelect, { category: "document_type" }) }), _jsx(Form.Item, { name: "document_date", label: t('documents.date'), children: _jsx(DatePicker, { format: "DD-MM-YYYY", style: { width: '100%' } }) }), _jsx(Form.Item, { name: "notes", label: t('rooms.notes'), children: _jsx(Input, {}) })] }) })] }));
}
