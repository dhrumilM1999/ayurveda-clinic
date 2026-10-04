// Dashboard. For now a welcome screen; real numbers come in Step 8 (reports).
import { CalendarOutlined, TeamOutlined, UnorderedListOutlined, WalletOutlined } from '@ant-design/icons';
import { Card, Col, Row } from 'antd';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { LeafArt } from '../components/LeafArt';
import { clinicConfig } from '../config/clinic';
import { alpha } from '../theme';

const c = clinicConfig.colors;

export default function DashboardPage() {
  const { t } = useTranslation();
  const { me, branch } = useAuth();

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

      <Row gutter={[20, 20]}>
        {tiles.map((tile) => (
          <Col xs={24} sm={12} xl={6} key={tile.key}>
            <Card className="stat-card">
              <div className="stat-icon" style={{ background: alpha(tile.color, 0.12), color: tile.color }}>
                {tile.icon}
              </div>
              <div>
                <div className="stat-label">{t(`dashboard.${tile.key}`)}</div>
                <div className="stat-value">—</div>
                <div className="stat-note">{t('dashboard.comingSoon')}</div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </>
  );
}
