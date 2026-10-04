// Check-up sections for before/after photos and symptom-score progress.
import { CameraOutlined, DeleteOutlined } from '@ant-design/icons';
import { App, Button, Empty, Image, Input, Popconfirm, Segmented, Space, Spin, Table } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Complaint, VisitListItem, VisitPhoto } from '../../api/types';

type PhotoKind = VisitPhoto['kind'];

/** Loads a private photo through the API (with login) and shows it. */
function PrivatePhoto({ visitId, photo }: { visitId: string; photo: VisitPhoto }) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    let objectUrl: string | undefined;
    api.get(`/visits/${visitId}/photos/${photo.id}/file/`, { responseType: 'blob' })
      .then(({ data }) => { objectUrl = URL.createObjectURL(data); setUrl(objectUrl); })
      .catch(() => setUrl(undefined));
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [visitId, photo.id]);
  return url ? <Image src={url} alt={photo.caption} className="visit-photo-img" /> : <div className="visit-photo-img"><Spin size="small" /></div>;
}

function PhotoCard({ photo, onDelete }: { photo: VisitPhoto; onDelete?: () => void }) {
  const { t } = useTranslation();
  return (
    <figure className="visit-photo">
      <PrivatePhoto visitId={photo.visit} photo={photo} />
      <figcaption>
        <span className={`photo-kind kind-${photo.kind}`}>{t(`consult.photoKind.${photo.kind}`)}</span>
        <span className="cell-sub">{dayjs(photo.visit_date).format('DD-MM-YYYY')}{photo.caption ? ` · ${photo.caption}` : ''}</span>
        {onDelete && (
          <Popconfirm title={t('consult.removePhoto')} okText={t('common.yes')} cancelText={t('common.no')} onConfirm={onDelete}>
            <Button size="small" type="text" danger icon={<DeleteOutlined />} aria-label={t('common.remove')} />
          </Popconfirm>
        )}
      </figcaption>
    </figure>
  );
}

export function PhotosSection({ visitId, patientId, readOnly }: { visitId: string; patientId: string; readOnly?: boolean }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [photos, setPhotos] = useState<VisitPhoto[]>([]);
  const [kind, setKind] = useState<PhotoKind>('before');
  const [caption, setCaption] = useState('');
  const [uploading, setUploading] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    api.get<VisitPhoto[]>('/visits/patient-photos/', { params: { patient: patientId } })
      .then(({ data }) => setPhotos(data)).catch(() => setPhotos([]));
  }, [patientId]);
  useEffect(() => { load(); }, [load]);

  const upload = async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    form.append('kind', kind);
    form.append('caption', caption);
    setUploading(true);
    try {
      await api.post(`/visits/${visitId}/photos/`, form);
      setCaption('');
      message.success(t('common.saved'));
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setUploading(false);
    }
  };

  const remove = async (photo: VisitPhoto) => {
    await api.delete(`/visits/${photo.visit}/photos/${photo.id}/`);
    load();
  };

  const thisVisit = photos.filter((p) => p.visit === visitId);
  const firstBefore = photos.find((p) => p.kind === 'before');
  const latestAfter = [...photos].reverse().find((p) => p.kind !== 'before' && p !== firstBefore);

  return (
    <>
      <div className="section-title">{t('consult.sections.photos')}</div>
      {!readOnly && (
        <div className="chip-picker">
          <Space wrap size={8}>
            <Segmented size="small" value={kind} onChange={(v) => setKind(v as PhotoKind)}
              options={(['before', 'progress', 'after'] as PhotoKind[]).map((k) => ({ value: k, label: t(`consult.photoKind.${k}`) }))} />
            <Input size="small" placeholder={t('consult.photoCaption')} value={caption} maxLength={200}
              onChange={(e) => setCaption(e.target.value)} style={{ width: 220 }} />
            <Button size="small" type="primary" icon={<CameraOutlined />} loading={uploading} onClick={() => input.current?.click()}>
              {t('consult.addPhoto')}
            </Button>
          </Space>
          {/* capture: on a tablet or phone this opens the camera directly */}
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" style={{ display: 'none' }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ''; }} />
          <div className="cell-sub" style={{ marginTop: 6 }}>{t('consult.photoHelp')}</div>
        </div>
      )}

      {firstBefore && latestAfter && (
        <>
          <div className="section-title">{t('consult.compare')}</div>
          <div className="photo-compare">
            <PhotoCard photo={firstBefore} />
            <PhotoCard photo={latestAfter} />
          </div>
        </>
      )}

      <div className="section-title">{t('consult.thisVisitPhotos', { n: thisVisit.length })}</div>
      {thisVisit.length ? (
        <div className="photo-grid">
          {thisVisit.map((p) => <PhotoCard key={p.id} photo={p} onDelete={readOnly ? undefined : () => remove(p)} />)}
        </div>
      ) : <div className="cell-sub">{t('consult.noPhotos')}</div>}

      {photos.length > thisVisit.length && (
        <>
          <div className="section-title">{t('consult.earlierPhotos')}</div>
          <div className="photo-grid">
            {photos.filter((p) => p.visit !== visitId).map((p) => <PhotoCard key={p.id} photo={p} />)}
          </div>
        </>
      )}
    </>
  );
}

/**
 * Symptom scores (0-10) per complaint over the visits: shows if the patient is getting better.
 * The current visit uses the scores being typed now.
 */
export function ProgressSection({ patientId, visitId, visitDate, complaints }: {
  patientId: string;
  visitId: string;
  visitDate: string;
  complaints: Complaint[];
}) {
  const { t } = useTranslation();
  const [visits, setVisits] = useState<VisitListItem[] | null>(null);

  useEffect(() => {
    api.get<{ results: VisitListItem[] }>('/visits/', { params: { patient: patientId, page_size: 50 } })
      .then(({ data }) => setVisits(data.results)).catch(() => setVisits([]));
  }, [patientId]);

  if (!visits) return <Spin />;

  const current: Record<string, number> = Object.fromEntries(
    complaints.filter((c) => c.score !== null && c.score !== undefined).map((c) => [c.label, c.score as number]),
  );
  // Oldest first, last 8 visits; the current visit uses live scores
  const columns = [...visits].reverse()
    .map((v) => ({ id: v.id, date: v.visit_date, scores: v.id === visitId ? current : v.scores }))
    .filter((v) => v.id === visitId || Object.keys(v.scores).length > 0)
    .slice(-8);
  if (!columns.some((c) => c.id === visitId)) columns.push({ id: visitId, date: visitDate, scores: current });
  const labels = [...new Set(columns.flatMap((c) => Object.keys(c.scores)))];

  if (!labels.length) {
    return (
      <>
        <div className="section-title">{t('consult.sections.progress')}</div>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('consult.progressEmpty')} />
      </>
    );
  }

  const trend = (label: string) => {
    const values = columns.map((c) => c.scores[label]).filter((v): v is number => v !== undefined);
    if (values.length < 2) return null;
    const change = values[values.length - 1]! - values[0]!;
    if (change < 0) return <span className="trend trend-better">▼ {t('consult.better', { n: -change })}</span>;
    if (change > 0) return <span className="trend trend-worse">▲ {t('consult.worse', { n: change })}</span>;
    return <span className="trend">= {t('consult.same')}</span>;
  };

  return (
    <>
      <div className="section-title">{t('consult.sections.progress')}</div>
      <div className="cell-sub" style={{ marginBottom: 8 }}>{t('consult.progressHelp')}</div>
      <Table
        size="small"
        rowKey="label"
        pagination={false}
        scroll={{ x: true }}
        dataSource={labels.map((label) => ({ label }))}
        columns={[
          { title: t('consult.sections.complaints'), dataIndex: 'label', fixed: 'left' as const, render: (l: string) => <b>{l}</b> },
          ...columns.map((c) => ({
            title: c.id === visitId ? t('consult.today') : dayjs(c.date).format('DD-MM-YY'),
            key: c.id,
            align: 'center' as const,
            render: (_: unknown, row: { label: string }) => {
              const v = c.scores[row.label];
              return v === undefined ? <span className="cell-sub">—</span> : <span className={`score-cell score-${Math.min(3, Math.ceil(v / 3.4))}`}>{v}</span>;
            },
          })),
          { title: t('consult.trend'), key: 'trend', render: (_: unknown, row: { label: string }) => trend(row.label) },
        ]}
      />
    </>
  );
}
