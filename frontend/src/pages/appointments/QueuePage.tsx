// Today's waiting queue, one card per doctor. Refreshes by itself every 15 seconds.
// "Call next" finishes the current patient and calls the next token.
import { DesktopOutlined, ReloadOutlined, SoundOutlined, UserAddOutlined } from '@ant-design/icons';
import { App, Button, Card, Col, Empty, Row, Space, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import type { QueueData, QueueGroup, QueueItem } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { BookAppointmentModal } from './BookAppointmentModal';

const REFRESH_SECONDS = 15;

/** Loads the queue now and then every few seconds. */
export function useQueue(refreshSeconds: number) {
  const [data, setData] = useState<QueueData | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    api.get<QueueData>('/appointments/queue/')
      .then(({ data: d }) => { setData(d); setError(null); })
      .catch(setError);
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, refreshSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [load, refreshSeconds]);

  return { data, error, reload: load };
}

function minutesSince(iso: string | null) {
  return iso ? Math.max(0, dayjs().diff(dayjs(iso), 'minute')) : 0;
}

export default function QueuePage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const navigate = useNavigate();
  const { data, reload } = useQueue(REFRESH_SECONDS);
  const [busy, setBusy] = useState<string | null>(null);
  const [walkIn, setWalkIn] = useState<string | null>(null);
  const manage = can('appointments.manage');

  const post = async (key: string, urls: string[]) => {
    setBusy(key);
    try {
      for (const url of urls) await api.post(url);
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(null);
    }
  };

  const callNext = (group: QueueGroup) => {
    const urls = group.now.map((n) => `/appointments/${n.id}/complete/`);
    if (group.waiting[0]) urls.push(`/appointments/${group.waiting[0].id}/start/`);
    post(group.doctor, urls);
  };

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('queue.title')}</Typography.Title>
          <div className="cell-sub">{t('queue.subtitle', { seconds: REFRESH_SECONDS })}</div>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={reload}>{t('appointments.refresh')}</Button>
          <Button icon={<DesktopOutlined />} onClick={() => navigate('/queue/display')}>{t('queue.openTv')}</Button>
        </Space>
      </div>

      {data && data.doctors.length === 0 && (
        <Card><Empty description={t('queue.empty')}><Link to="/appointments">{t('queue.goToAppointments')}</Link></Empty></Card>
      )}

      <Row gutter={[14, 14]}>
        {data?.doctors.map((group) => (
          <Col xs={24} lg={12} xxl={8} key={group.doctor}>
            <Card
              title={group.doctor_name}
              extra={<span className="cell-sub">{t('queue.counts', { booked: group.booked_count, done: group.done_count })}</span>}
              className="queue-card"
            >
              <div className="queue-now">
                <div className="queue-label">{t('queue.withDoctor')}</div>
                {group.now.length ? group.now.map((item) => (
                  <div className="queue-now-row" key={item.id}>
                    <span className="token-big">{item.token_number ?? '—'}</span>
                    <div>
                      <Link to={`/patients/${item.patient_detail.id}`}><b>{item.patient_detail.full_name}</b></Link>
                      <div className="cell-sub">{t('queue.since', { n: minutesSince(item.consultation_started_at) })}</div>
                    </div>
                  </div>
                )) : <div className="cell-sub">{t('queue.nobody')}</div>}
              </div>

              <div className="queue-label" style={{ marginTop: 12 }}>
                {t('queue.waiting', { n: group.waiting.length })}
              </div>
              {group.waiting.length ? (
                <ol className="queue-list">
                  {group.waiting.map((item: QueueItem) => (
                    <li key={item.id}>
                      <span className="token-chip">#{item.token_number}</span>
                      <Link to={`/patients/${item.patient_detail.id}`} className="queue-name">{item.patient_detail.full_name}</Link>
                      <span className="cell-sub">
                        {item.kind === 'walk_in' ? t('appointments.walkInShort') : t('queue.booked')} · {t('queue.waitingFor', { n: minutesSince(item.checked_in_at) })}
                      </span>
                    </li>
                  ))}
                </ol>
              ) : <div className="cell-sub">{t('queue.noneWaiting')}</div>}

              {manage && (
                <div className="queue-actions">
                  <Button size="small" icon={<UserAddOutlined />} onClick={() => setWalkIn(group.doctor)}>{t('appointments.walkIn')}</Button>
                  <Button
                    type="primary"
                    size="small"
                    icon={<SoundOutlined />}
                    loading={busy === group.doctor}
                    disabled={!group.waiting.length && !group.now.length}
                    onClick={() => callNext(group)}
                  >
                    {group.waiting.length ? t('queue.callNext') : t('queue.finishCurrent')}
                  </Button>
                </div>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <BookAppointmentModal
        open={walkIn !== null}
        kind="walk_in"
        defaultDoctor={walkIn ?? undefined}
        onClose={(changed) => { setWalkIn(null); if (changed) reload(); }}
      />
    </>
  );
}
