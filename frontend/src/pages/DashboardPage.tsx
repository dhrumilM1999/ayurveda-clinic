// Dashboard in simple OPD words.
// - Doctor: "My OPD today" (waiting, with me, seen, booked; new cases vs follow-ups) and the next patients.
// - Front desk / admin: the whole clinic's OPD today, and today's money (OPD and pharmacy) for staff who see bills.
// - Pharmacy stock alerts when that extra is switched on.
// The numbers come from /dashboard/today/ and refresh every minute.
import {
  CheckCircleOutlined, ClockCircleOutlined, MedicineBoxOutlined, ShopOutlined, TeamOutlined, UserAddOutlined,
  UserOutlined, WalletOutlined, WarningOutlined,
} from '@ant-design/icons';
import { Button, Card, Col, Empty, Row, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { DashboardToday, OpdCounts } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { LeafArt } from '../components/LeafArt';
import { clinicConfig } from '../config/clinic';
import { alpha } from '../theme';
import { money } from './medicines/shared';
import { AlertTiles } from './pharmacy/StockTab';

const c = clinicConfig.colors;
const REFRESH_SECONDS = 60;

type Tile = { key: string; icon: ReactNode; color: string; value: ReactNode; note: string; link?: string };

function Tiles({ tiles, xl }: { tiles: Tile[]; xl?: number }) {
  const { t } = useTranslation();
  return (
    <Row gutter={[12, 12]}>
      {tiles.map((tile) => (
        <Col xs={12} md={xl ? 12 : 8} xl={xl ?? 24 / Math.min(tiles.length, 6)} key={tile.key}>
          <Card className="stat-card" hoverable={!!tile.link}>
            <div className="stat-icon" style={{ background: alpha(tile.color, 0.12), color: tile.color }}>{tile.icon}</div>
            <div>
              <div className="stat-label">
                {tile.link ? <Link to={tile.link} style={{ color: 'inherit' }}>{t(`dashboard.${tile.key}`)}</Link> : t(`dashboard.${tile.key}`)}
              </div>
              <div className="stat-value">{tile.value}</div>
              <div className="stat-note">{tile.note}</div>
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
}

function opdTiles(t: (k: string, o?: Record<string, unknown>) => string, o: OpdCounts, mine: boolean): Tile[] {
  return [
    { key: 'waiting', icon: <ClockCircleOutlined />, color: c.accent, value: o.waiting, note: t('dashboard.waitingNote'), link: '/queue' },
    { key: mine ? 'withMe' : 'withDoctor', icon: <UserOutlined />, color: '#3d6fb6', value: o.with_doctor, note: t('dashboard.withDoctorNote'), link: '/consult' },
    { key: 'seen', icon: <CheckCircleOutlined />, color: c.primary, value: o.seen, note: t('dashboard.seenNote') },
    { key: 'booked', icon: <TeamOutlined />, color: '#8a4fa8', value: o.booked, note: t('dashboard.bookedNote', { n: o.not_arrived }), link: '/appointments' },
  ];
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const { me, branch, can, features, hasFeature } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardToday | null>(null);
  const showStockAlerts = can('pharmacy.view') && features.pharmacy !== false && hasFeature('pharmacy_stock_alerts');

  const load = useCallback(() => {
    api.get<DashboardToday>('/dashboard/today/').then(({ data: d }) => setData(d)).catch(() => setData(null));
  }, []);
  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_SECONDS * 1000);
    return () => window.clearInterval(timer);
  }, [load, branch?.id]);

  const hour = new Date().getHours();
  const greetingKey = hour < 12 ? 'dashboard.goodMorning' : hour < 17 ? 'dashboard.goodAfternoon' : 'dashboard.goodEvening';
  const weekday = t(`weekdays.${(dayjs().day() + 6) % 7}`);
  const mine = data?.my_opd;
  const clinic = data?.opd;
  const m = data?.money;

  // New case / follow-up line, e.g. "3 new cases · 5 follow-ups · 2 follow-ups due today"
  const caseLine = (o: OpdCounts) => (
    <div className="dash-cases">
      <Tag color="blue" icon={<UserAddOutlined />}>{t('dashboard.newCases', { count: o.new_cases })}</Tag>
      <Tag color="green">{t('dashboard.followUps', { count: o.follow_ups })}</Tag>
      {o.walk_ins > 0 && <Tag>{t('dashboard.walkIns', { count: o.walk_ins })}</Tag>}
      {o.follow_ups_due > 0 && <Tag color="orange">{t('dashboard.followUpsDue', { count: o.follow_ups_due })}</Tag>}
      {o.no_show > 0 && <Tag color="red">{t('dashboard.noShow', { count: o.no_show })}</Tag>}
    </div>
  );

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

      {mine && (
        <>
          <div className="section-toolbar">
            <div className="section-title" style={{ margin: 0 }}>{t('dashboard.myOpd')}</div>
            {caseLine(mine)}
          </div>
          <Row gutter={[12, 12]}>
            <Col xs={24} xl={16}><Tiles tiles={opdTiles(t, mine, true)} xl={12} /></Col>
            <Col xs={24} xl={8}>
              <Card size="small" title={t('dashboard.nextPatients')} className="dash-next"
                extra={<Button size="small" type="primary" icon={<MedicineBoxOutlined />} onClick={() => navigate('/consult')}>{t('dashboard.openCheckup')}</Button>}>
                {data?.next_patients?.length ? data.next_patients.map((p) => (
                  <div key={p.appointment} className="dash-next-row">
                    <span className="token-chip">#{p.token_number ?? '—'}</span>
                    <div style={{ minWidth: 0 }}>
                      <b>{p.patient}</b> <span className="cell-sub mono">{p.uhid}</span>
                      {p.reason && <div className="cell-sub">{p.reason}</div>}
                    </div>
                    <Tag color={p.status === 'in_consultation' ? 'blue' : 'gold'} className="tag-tight">
                      {p.status === 'in_consultation' ? t('dashboard.withMeShort') : t('dashboard.waitingShort')}
                    </Tag>
                  </div>
                )) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('dashboard.nobodyWaiting')} />}
              </Card>
            </Col>
          </Row>
        </>
      )}

      {clinic && (!mine || can('appointments.manage')) && (
        <>
          <div className="section-toolbar" style={{ marginTop: mine ? 16 : 0 }}>
            <div className="section-title" style={{ margin: 0 }}>{t('dashboard.clinicOpd')}</div>
            {caseLine(clinic)}
          </div>
          <Tiles tiles={opdTiles(t, clinic, false)} />
        </>
      )}

      {m && (
        <>
          <div className="section-title" style={{ marginTop: 16 }}>{t('dashboard.moneyToday')}</div>
          <Tiles tiles={[
            { key: 'opdCollection', icon: <WalletOutlined />, color: c.primary, value: money(m.opd), note: t('dashboard.opdCollectionNote'), link: '/billing' },
            ...(features.pharmacy !== false && hasFeature('pharmacy_billing')
              ? [{ key: 'pharmacyCollection', icon: <ShopOutlined />, color: '#8a4fa8', value: money(m.pharmacy), note: t('dashboard.pharmacyCollectionNote'), link: '/billing' }] : []),
            { key: 'totalCollection', icon: <WalletOutlined />, color: '#3d6fb6', value: money(m.total), note: t('dashboard.totalCollectionNote') },
            {
              key: 'stillDue', icon: <WarningOutlined />, color: Number(m.due_today) > 0 ? '#c0392b' : c.accent,
              value: money(m.due_today), note: t('dashboard.stillDueNote', { count: m.unpaid_bills }), link: '/billing',
            },
          ]} />
        </>
      )}

      {showStockAlerts && (
        <>
          <div className="section-title" style={{ marginTop: 16 }}>{t('dashboard.stockAlerts')}</div>
          <AlertTiles onPick={(show) => navigate(`/pharmacy?tab=stock&show=${show}`)} />
        </>
      )}
    </>
  );
}
