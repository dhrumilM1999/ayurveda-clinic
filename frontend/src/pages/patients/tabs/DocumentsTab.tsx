// Uploaded reports and files. Files are private: opened through the API (written to the audit log).
import { DeleteOutlined, DownloadOutlined, EyeOutlined, FilePdfOutlined, FileImageOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, App, Button, DatePicker, Form, Input, Modal, Popconfirm, Space, Table, Typography, Upload } from 'antd';
import type { UploadFile } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import { useMasterLabel } from '../../../api/masters';
import type { MasterRef, PatientDocument } from '../../../api/types';
import { useAuth } from '../../../auth/AuthContext';
import { MasterSelect } from '../../../components/MasterSelect';

function size(bytes: number) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`;
}

export function DocumentsTab({ patientId }: { patientId: string }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const label = useMasterLabel();
  const [rows, setRows] = useState<PatientDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [form] = Form.useForm();
  const canView = can('emr.view');
  const canUpload = can('patients.edit') || can('patients.create') || can('emr.edit');

  const load = useCallback(async () => {
    if (!canView) return;
    setLoading(true);
    try {
      const { data } = await api.get<PatientDocument[]>('/patient-documents/', { params: { patient: patientId } });
      setRows(data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [patientId, canView, message, t]);

  useEffect(() => {
    load();
  }, [load]);

  const openFile = async (doc: PatientDocument, download: boolean) => {
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
      } else {
        window.open(url, '_blank', 'noopener');
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
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
    if (values.document_type) body.append('document_type', values.document_type);
    if (values.document_date) body.append('document_date', values.document_date.format('YYYY-MM-DD'));
    if (values.notes) body.append('notes', values.notes);
    setSaving(true);
    try {
      await api.post('/patient-documents/', body);
      message.success(t('documents.uploaded'));
      setOpen(false);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="page-toolbar" style={{ marginBottom: 12 }}>
        <Typography.Text type="secondary">{t('documents.help')}</Typography.Text>
        {canUpload && (
          <Button type="primary" icon={<UploadOutlined />} onClick={() => { form.resetFields(); setFiles([]); setOpen(true); }}>
            {t('documents.upload')}
          </Button>
        )}
      </div>

      {!canView ? (
        <Alert type="info" showIcon message={t('documents.cannotView')} />
      ) : (
        <Table<PatientDocument>
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={rows}
          pagination={false}
          scroll={{ x: true }}
          columns={[
            {
              title: t('documents.title'), dataIndex: 'title',
              render: (title: string, d: PatientDocument) => (
                <Space>
                  {d.content_type === 'application/pdf' ? <FilePdfOutlined style={{ color: '#c2412d' }} /> : <FileImageOutlined style={{ color: '#3d6fb6' }} />}
                  <div>
                    <div style={{ fontWeight: 600 }}>{title}</div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{d.original_name} · {size(d.size_bytes)}</Typography.Text>
                  </div>
                </Space>
              ),
            },
            { title: t('documents.type'), dataIndex: 'document_type', render: (v: MasterRef | null) => label(v) || '—' },
            { title: t('documents.date'), dataIndex: 'document_date', render: (v: string | null) => (v ? dayjs(v).format('DD-MM-YYYY') : '—') },
            {
              title: t('documents.uploadedBy'), key: 'by',
              render: (_: unknown, d: PatientDocument) => `${d.uploaded_by_name} · ${dayjs(d.created_at).format('DD-MM-YYYY')}`,
            },
            {
              title: '', key: 'actions', width: 140,
              render: (_: unknown, d: PatientDocument) => (
                <Space size={4}>
                  <Button size="small" icon={<EyeOutlined />} onClick={() => openFile(d, false)}>{t('common.view')}</Button>
                  <Button size="small" icon={<DownloadOutlined />} onClick={() => openFile(d, true)} aria-label={t('documents.download')} />
                  {can('emr.edit') && (
                    <Popconfirm title={t('documents.confirmRemove')} okText={t('common.yes')} cancelText={t('common.no')}
                      onConfirm={() => api.delete(`/patient-documents/${d.id}/`).then(load)}>
                      <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.remove')} />
                    </Popconfirm>
                  )}
                </Space>
              ),
            },
          ]}
        />
      )}

      <Modal open={open} title={t('documents.upload')} onCancel={() => setOpen(false)} onOk={save} confirmLoading={saving}
        okText={t('documents.upload')} cancelText={t('common.cancel')} destroyOnClose>
        <Form form={form} layout="vertical">
          <Upload.Dragger
            fileList={files}
            beforeUpload={() => false}
            maxCount={1}
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            onChange={({ fileList }) => {
              setFiles(fileList);
              const name = fileList[0]?.name;
              if (name && !form.getFieldValue('title')) form.setFieldValue('title', name.replace(/\.[^.]+$/, ''));
            }}
            style={{ marginBottom: 16 }}
          >
            <p className="ant-upload-drag-icon"><UploadOutlined /></p>
            <p>{t('documents.dropHere')}</p>
            <p className="ant-upload-hint">{t('documents.allowed')}</p>
          </Upload.Dragger>
          <Form.Item name="title" label={t('documents.title')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
          <Form.Item name="document_type" label={t('documents.type')}><MasterSelect category="document_type" /></Form.Item>
          <Form.Item name="document_date" label={t('documents.date')}><DatePicker format="DD-MM-YYYY" style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="notes" label={t('rooms.notes')}><Input /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
