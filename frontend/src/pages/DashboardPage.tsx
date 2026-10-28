// Dashboard in simple OPD words.
// - Doctor: "My OPD today" (waiting, with me, seen, booked; new cases vs follow-ups) and the next patients.
// - Front desk / admin: the whole clinic's OPD today, and today's money (OPD and pharmacy) for staff who see bills.
// - Pharmacy stock alerts when that extra is switched on.
// The numbers come from /dashboard/today/ and refresh every minute.
import {
  BarChartOutlined, FileTextOutlined, GiftOutlined, HeartOutlined, OrderedListOutlined, ScheduleOutlined,
  CheckCircleOutlined, ClockCircleOutlined, MedicineBoxOutlined, ShopOutlined, TeamOutlined, UserAddOutlined,
  WalletOutlined, WarningOutlined,
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
import { useBranding } from '../branding/BrandingContext';
import { clinicConfig } from '../config/clinic';
import { alpha } from '../theme';
import { money } from './medicines/shared';
import { AlertTiles } from './pharmacy/StockTab';

const c = clinicConfig.colors;
const REFRESH_SECONDS = 60;

// Big shortcut buttons at the top. SAFE TO EDIT: add, remove or re-order a line (permission = who sees it,
// feature = the extra that must be on). Texts are in the i18n files under dashboard.shortcuts.
type Shortcut = { key: string; path: string; icon: ReactNode; color: string; permission: string; feature?: string };
const SHORTCUTS: Shortcut[] = [
  { key: 'newPatient', path: '/patients/new', icon: <UserAddOutlined />, color: c.primary, permission: 'patients.create' },
  { key: 'appointments', path: '/appointments', icon: <ScheduleOutlined />, color: c.accent, permission: 'appointments.view', feature: 'appointments' },
  { key: 'queue', path: '/queue', icon: <OrderedListOutlined />, color: '#d4851c', permission: 'appointments.view', feature: 'appointments' },
  { key: 'checkup', path: '/consult', icon: <MedicineBoxOutlined />, color: '#1f8a70', permission: 'emr.view' },
  { key: 'billing', path: '/billing', icon: <FileTextOutlined />, color: c.primary, permission: 'billing.view' },
  { key: 'pharmacy', path: '/pharmacy', icon: <ShopOutlined />, color: '#b5497a', permission: 'pharmacy.view', feature: 'pharmacy' },
  { key: 'products', path: '/products', icon: <GiftOutlined />, color: '#c2412d', permission: 'products.view', feature: 'pharmacy' },
  { key: 'availability', path: '/schedules', icon: <ClockCircleOutlined />, color: c.accent, permission: 'schedules.view' },
  { key: 'therapy', path: '/therapy', icon: <HeartOutlined />, color: '#1f8a70', permission: 'therapy.view', feature: 'panchakarma' },
  { key: 'reports', path: '/reports', icon: <BarChartOutlined />, color: '#d4851c', permission: 'reports.view' },
];

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

function opdTiles(t: (k: string, o?: Record<string, unknown>) => string, o: OpdCounts): Tile[] {
  return [
    { key: 'waiting', icon: <ClockCircleOutlined />, color: c.accent, value: o.waiting, note: t('dashboard.waitingNote'), link: '/queue' },
    { key: 'seen', icon: <CheckCircleOutlined />, color: c.success, value: o.seen, note: t('dashboard.seenNote') },
    { key: 'booked', icon: <TeamOutlined />, color: '#8a4fa8', value: o.booked, note: t('dashboard.bookedNote', { n: o.not_arrived }), link: '/appointments' },
  ];
}

/** What needs a decision now: the next appointments, late patients, patients seen but not billed, late therapy. */
function AttentionPanel({ a, canBill, canTherapy }: { a: NonNullable<DashboardToday['attention']>; canBill: boolean; canTherapy: boolean }) {
  const { t } = useTranslation();
  const hhmm = (x: string) => dayjs(`2000-01-01 ${x}`).format('h:mm A');
  const rows = (list: typeof a.upcoming) => list.map((r) => (
    <div key={r.appointment} className="dash-next-row">
      <span className="token-chip">{hhmm(r.time)}</span>
      <div style={{ minWidth: 0 }}>
        <b>{r.patient}</b> <span className="cell-sub mono">{r.uhid}</span>
        <div className="cell-sub">{[r.doctor, r.reason].filter(Boolean).join(' · ')}</div>
      </div>
    </div>
  ));
  const flags = [
    ...(a.to_bill ? [{ key: 'toBill', n: a.to_bill, to: '/appointments', color: '#c0392b' }] : []),
    ...(a.therapy_overdue && canTherapy ? [{ key: 'therapyLate', n: a.therapy_overdue, to: '/therapy', color: '#d4730c' }] : []),
  ];
  return (
    <>
      <div className="section-title">{t('dashboard.attention.title')}</div>
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={12}>
          <Card size="small" title={t('dashboard.attention.upcoming')} className="dash-next"
            extra={<Link to="/appointments">{t('dashboard.attention.all')}</Link>}>
            {a.upcoming.length ? rows(a.upcoming) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('dashboard.attention.noUpcoming')} />}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" className="dash-next"
            title={<>{t('dashboard.attention.timePassed')} {a.time_passed > 0 && <Tag color="orange" className="tag-tight">{a.time_passed}</Tag>}</>}
            extra={a.time_passed > 0 ? <Link to="/appointments">{t('dashboard.attention.decide')}</Link> : null}>
            {a.time_passed ? rows(a.time_passed_list) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('dashboard.attention.noneLate')} />}
          </Card>
        </Col>
      </Row>
      {flags.length > 0 && (canBill || canTherapy) && (
        <div className="dash-cases" style={{ marginTop: 12 }}>
          {flags.map((f) => (
            <Link key={f.key} to={f.to}><Tag color={f.color === '#c0392b' ? 'red' : 'orange'}>{t(`dashboard.attention.${f.key}`, { count: f.n })}</Tag></Link>
          ))}
        </div>
      )}
    </>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const { me, branch, can, features, hasFeature } = useAuth();
  const navigate = useNavigate();
  const { logoUrl } = useBranding();
  // A positive thought: a new one each day; the button shows the next one
  const quotes = t('dashboard.quotes', { returnObjects: true }) as unknown as string[];
  const [quoteNo, setQuoteNo] = useState(0);
  const quote = Array.isArray(quotes) && quotes.length ? quotes[(dayjs().diff(dayjs().startOf('year'), 'day') + quoteNo) % quotes.length] : '';
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
      <Tag color="cyan">{t('dashboard.followUps', { count: o.follow_ups })}</Tag>
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
        {(mine ?? clinic) && (
          <div className="hero-pills">
            <span><b>{(mine ?? clinic)!.booked}</b> {t('dashboard.pillAppointments')}</span>
            <span><b>{(mine ?? clinic)!.waiting}</b> {t('dashboard.pillWaiting')}</span>
          </div>
        )}
        {quote && (
          <button type="button" className="hero-quote" title={t('dashboard.nextQuote')} onClick={() => setQuoteNo((n) => n + 1)}>
            “{quote}”
          </button>
        )}
        {logoUrl ? <div className="hero-logo"><img src={logoUrl} alt={clinicConfig.appName} /></div> : <LeafArt className="hero-leaf" />}
      </div>

      <div className="section-title">{t('dashboard.quickActions')}</div>
      <div className="shortcut-grid">
        {SHORTCUTS.filter((x) => can(x.permission) && (!x.feature || features[x.feature] !== false) && (x.key !== 'availability' || me?.user.is_doctor)).map((x) => (
          <Link key={x.key} to={x.path} className="shortcut" style={{ ['--sc' as string]: x.color }}>
            <span className="shortcut-icon">{x.icon}</span>
            <span className="shortcut-label">{t(`dashboard.shortcuts.${x.key}`)}</span>
            <span className="shortcut-desc">{t(`dashboard.shortcutsHelp.${x.key}`)}</span>
          </Link>
        ))}
      </div>

      {data?.attention && <AttentionPanel a={data.attention} canBill={can('billing.view')} canTherapy={can('therapy.view')} />}

      {mine && (
        <>
          <div className="section-toolbar">
            <div className="section-title" style={{ margin: 0 }}>{t('dashboard.myOpd')}</div>
            {caseLine(mine)}
          </div>
          <Row gutter={[12, 12]}>
            <Col xs={24} xl={16}><Tiles tiles={opdTiles(t, mine)} xl={12} /></Col>
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
                    <Tag color="gold" className="tag-tight">{t('dashboard.waitingShort')}</Tag>
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
          <Tiles tiles={opdTiles(t, clinic)} />
        </>
      )}

      {m && (
        <>
          <div className="section-title" style={{ marginTop: 16 }}>{t('dashboard.moneyToday')}</div>
          <Tiles tiles={[
            ...(hasFeature('opd_billing')
              ? [{ key: 'opdCollection', icon: <WalletOutlined />, color: c.primary, value: money(m.opd), note: t(hasFeature('combined_opd_bill') ? 'dashboard.opdCollectionNoteCombined' : 'dashboard.opdCollectionNote'), link: '/billing' }] : []),
            ...(features.pharmacy !== false && hasFeature('pharmacy_billing')
              ? [{ key: 'pharmacyCollection', icon: <ShopOutlined />, color: '#8a4fa8', value: money(m.pharmacy), note: t('dashboard.pharmacyCollectionNote'), link: '/billing' }] : []),
            { key: 'totalCollection', icon: <WalletOutlined />, color: c.primary, value: money(m.total), note: t('dashboard.totalCollectionNote') },
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
