// Import a medicine list from Excel (.xlsx) or CSV. First a preview (nothing saved), then "Import".
import { DownloadOutlined, InboxOutlined } from '@ant-design/icons';
import { Alert, App, Button, Modal, Space, Statistic, Table, Tag, Upload } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { ImportResult } from '../../api/types';

export function ImportModal({ onClose }: { onClose: (done: boolean) => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportResult | null>(null);
  const [done, setDone] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async (dryRun: boolean, chosen = file) => {
    if (!chosen) return;
    const body = new FormData();
    body.append('file', chosen);
    body.append('dry_run', dryRun ? '1' : '0');
    setBusy(true);
    try {
      const { data } = await api.post<ImportResult>('/medicines/import/', body);
      if (dryRun) setPreview(data);
      else { setDone(data); message.success(t('medicines.importDone', { n: data.created + data.updated })); }
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(false);
    }
  };

  const downloadTemplate = async () => {
    const { data } = await api.get('/medicines/import-template/', { responseType: 'blob' });
    const url = URL.createObjectURL(data);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'medicine-list-template.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const result = done ?? preview;
  const changes = (preview?.created ?? 0) + (preview?.updated ?? 0);

  return (
    <Modal open width={720} title={t('medicines.importTitle')} onCancel={() => onClose(!!done)} keyboard={false} maskClosable={false}
      footer={done ? <Button type="primary" onClick={() => onClose(true)}>{t('common.close')}</Button> : (
        <Space>
          <Button onClick={() => onClose(false)}>{t('common.cancel')}</Button>
          <Button type="primary" disabled={!preview || changes === 0} loading={busy} onClick={() => send(false)}>
            {t('medicines.importButton', { n: changes })}
          </Button>
        </Space>
      )}>
      {!done && (
        <>
          <div className="section-toolbar">
            <span className="cell-sub">{t('medicines.importHelp')}</span>
            <Button size="small" icon={<DownloadOutlined />} onClick={downloadTemplate}>{t('medicines.downloadTemplate')}</Button>
          </div>
          <Upload.Dragger accept=".xlsx,.csv" maxCount={1} showUploadList={false}
            beforeUpload={(f) => { setFile(f); setPreview(null); send(true, f); return false; }}>
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p className="ant-upload-text">{file ? file.name : t('medicines.dropFile')}</p>
            <p className="ant-upload-hint">{t('medicines.dropHint')}</p>
          </Upload.Dragger>
        </>
      )}

      {result && (
        <div style={{ marginTop: 12 }}>
          {!done && <Alert type="info" showIcon message={t('medicines.previewNote')} style={{ marginBottom: 12 }} />}
          <div className="stat-row">
            <Statistic title={t('medicines.importStatus.created')} value={result.created} />
            <Statistic title={t('medicines.importStatus.updated')} value={result.updated} />
            <Statistic title={t('medicines.importStatus.unchanged')} value={result.unchanged} />
            <Statistic title={t('medicines.importErrors')} value={result.errors.length}
              valueStyle={result.errors.length ? { color: '#c2412d' } : undefined} />
          </div>
          {result.errors.length > 0 && (
            <Table size="small" rowKey={(e) => `${e.row}-${e.message}`} pagination={false} style={{ marginTop: 12 }}
              dataSource={result.errors} scroll={{ y: 180 }}
              columns={[
                { title: t('medicines.row'), dataIndex: 'row', width: 70 },
                { title: t('medicines.problem'), dataIndex: 'message' },
              ]} />
          )}
          {!done && result.rows.length > 0 && (
            <Table size="small" rowKey="row" pagination={false} style={{ marginTop: 12 }} dataSource={result.rows} scroll={{ y: 220 }}
              columns={[
                { title: t('medicines.row'), dataIndex: 'row', width: 70 },
                { title: t('medicines.name'), dataIndex: 'name' },
                {
                  title: '', dataIndex: 'status', width: 120,
                  render: (s: string) => <Tag className="tag-tight" color={s === 'created' ? 'green' : s === 'updated' ? 'blue' : 'default'}>{t(`medicines.importStatus.${s}`)}</Tag>,
                },
              ]} />
          )}
        </div>
      )}
    </Modal>
  );
}
