// Today's waiting queue, one card per doctor. Refreshes by itself every few seconds.
// "Call next" finishes the current patient and calls the next token.
import { DesktopOutlined, ReloadOutlined, UserAddOutlined } from '@ant-design/icons';
import { Button, Card, Col, Empty, Row, Space, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import type { QueueData, QueueItem } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { useLiveRefresh } from '../../api/useLiveRefresh';
import { BookAppointmentModal } from './BookAppointmentModal';
import { OpdBillButton } from '../billing/OpdBillModal';

const REFRESH_SECONDS = 6;

/** Loads the queue now and then every few seconds. */
export function useQueue(refreshSeconds: number) {
  const [data, setData] = useState<QueueData | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    api.get<QueueData>('/appointments/queue/')
      .then(({ data: d }) => { setData(d); setError(null); })
      .catch(setError);
  }, []);

  useEffect(() => { load(); }, [load]);
  useLiveRefresh(load, refreshSeconds);

  return { data, error, reload: load };
}

function minutesSince(iso: string | null) {
  return iso ? Math.max(0, dayjs().diff(dayjs(iso), 'minute')) : 0;
}

export default function QueuePage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const navigate = useNavigate();
  const { data, reload } = useQueue(REFRESH_SECONDS);
  const [walkIn, setWalkIn] = useState<string | null>(null);
  const manage = can('appointments.manage');

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

      <Row gutter={[12, 12]}>
        {data?.doctors.map((group) => (
          <Col xs={24} lg={12} xxl={8} key={group.doctor}>
            <Card
              title={group.doctor_name}
              extra={<span className="cell-sub">{t('queue.counts', { booked: group.booked_count, done: group.done_count })}</span>}
              className="queue-card"
            >
              <div className="queue-label">
                {t('queue.waiting', { n: group.waiting.length })}
              </div>
              {group.waiting.length ? (
                <ol className="queue-list">
                  {group.waiting.map((item: QueueItem, index: number) => (
                    <li key={item.id}>
                      <span className="token-chip">#{item.token_number}</span>
                      {index === 0 && <Tag color="orange" className="tag-tight">{t('queue.next')}</Tag>}
                      <Link to={`/patients/${item.patient_detail.id}`} className="queue-name">{item.patient_detail.full_name}</Link>
                      <span className="cell-sub">
                        {item.kind === 'walk_in' ? t('appointments.walkInShort') : t('queue.booked')} · {t('queue.waitingFor', { n: minutesSince(item.checked_in_at) })}
                      </span>
                      <span className="queue-bill"><OpdBillButton appointmentId={item.id} bill={item.opd_bill} onChanged={reload} /></span>
                    </li>
                  ))}
                </ol>
              ) : <div className="cell-sub">{t('queue.noneWaiting')}</div>}

              {manage && (
                <div className="queue-actions">
                  <Button size="small" icon={<UserAddOutlined />} onClick={() => setWalkIn(group.doctor)}>{t('appointments.walkIn')}</Button>
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
