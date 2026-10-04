// Dashboard. Appointment numbers are live; the other numbers come in later steps (reports).
import { CalendarOutlined, TeamOutlined, UnorderedListOutlined, WalletOutlined } from '@ant-design/icons';
import { Card, Col, Row } from 'antd';
import { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { QueueData } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { LeafArt } from '../components/LeafArt';
import { clinicConfig } from '../config/clinic';
import { alpha } from '../theme';

const c = clinicConfig.colors;

export default function DashboardPage() {
  const { t } = useTranslation();
  const { me, branch, can, features } = useAuth();
  const [queue, setQueue] = useState<QueueData | null>(null);
  const showAppointments = can('appointments.view') && features.appointments !== false;

  useEffect(() => {
    if (!showAppointments) return;
    api.get<QueueData>('/appointments/queue/').then(({ data }) => setQueue(data)).catch(() => setQueue(null));
  }, [showAppointments]);

  // Today's numbers from the queue: total appointments (not cancelled) and patients waiting
  const totals = queue?.doctors.reduce(
    (sum, g) => ({
      appointments: sum.appointments + g.booked_count + g.done_count + g.waiting.length + g.now.length,
      waiting: sum.waiting + g.waiting.length,
    }),
    { appointments: 0, waiting: 0 },
  );
  const live: Record<string, { value: number; link: string; note: string } | undefined> = totals ? {
    appointments: { value: totals.appointments, link: '/appointments', note: t('dashboard.today') },
    queue: { value: totals.waiting, link: '/queue', note: t('dashboard.waitingNow') },
  } : {};

  const hour = new Date().getHours();
  const greetingKey = hour < 12 ? 'dashboard.goodMorning' : hour < 17 ? 'dashboard.goodAfternoon' : 'dashboard.goodEvening';
  const weekday = t(`weekdays.${(dayjs().day() + 6) % 7}`);

  const tiles = [
    { key: 'todayPatients', icon: <TeamOutlined />, color: c.primary },
    { key: 'appointments', icon: <CalendarOutlined />, color: '#3d6fb6' },
    { key: 'queue', icon: <UnorderedListOutlined />, color: c.accent },
    { key: 'collection', icon: <WalletOutlined />, color: '#8a4fa8' },
  ];

  return (
    <>
      <div className="hero">
        <div className="hero-date">{weekday} · {dayjs().format('DD-MM-YYYY')}</div>
        <div className="hero-title">{t(greetingKey, { name: me?.user.full_name })}</div>
        <div className="hero-sub">
          {t('dashboard.workingIn', { branch: branch?.name, role: branch?.role?.name ?? t('layout.orgAdmin') })}
        </div>
        <LeafArt className="hero-leaf" />
      </div>

      <Row gutter={[12, 12]}>
        {tiles.map((tile) => (
          <Col xs={24} sm={12} xl={6} key={tile.key}>
            <Card className="stat-card" hoverable={!!live[tile.key]}>
              <div className="stat-icon" style={{ background: alpha(tile.color, 0.12), color: tile.color }}>
                {tile.icon}
              </div>
              <div>
                <div className="stat-label">
                  {live[tile.key] ? <Link to={live[tile.key]!.link} style={{ color: 'inherit' }}>{t(`dashboard.${tile.key}`)}</Link> : t(`dashboard.${tile.key}`)}
                </div>
                <div className="stat-value">{live[tile.key]?.value ?? '—'}</div>
                <div className="stat-note">{live[tile.key]?.note ?? t('dashboard.comingSoon')}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </>
  );
}
