import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
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
        { key: 'todayPatients', icon: _jsx(TeamOutlined, {}), color: c.primary },
        { key: 'appointments', icon: _jsx(CalendarOutlined, {}), color: '#3d6fb6' },
        { key: 'queue', icon: _jsx(UnorderedListOutlined, {}), color: c.accent },
        { key: 'collection', icon: _jsx(WalletOutlined, {}), color: '#8a4fa8' },
    ];
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "hero", children: [_jsxs("div", { className: "hero-date", children: [weekday, " \u00B7 ", dayjs().format('DD-MM-YYYY')] }), _jsx("div", { className: "hero-title", children: t(greetingKey, { name: me?.user.full_name }) }), _jsx("div", { className: "hero-sub", children: t('dashboard.workingIn', { branch: branch?.name, role: branch?.role?.name ?? t('layout.orgAdmin') }) }), _jsx(LeafArt, { className: "hero-leaf" })] }), _jsx(Row, { gutter: [20, 20], children: tiles.map((tile) => (_jsx(Col, { xs: 24, sm: 12, xl: 6, children: _jsxs(Card, { className: "stat-card", children: [_jsx("div", { className: "stat-icon", style: { background: alpha(tile.color, 0.12), color: tile.color }, children: tile.icon }), _jsxs("div", { children: [_jsx("div", { className: "stat-label", children: t(`dashboard.${tile.key}`) }), _jsx("div", { className: "stat-value", children: "\u2014" }), _jsx("div", { className: "stat-note", children: t('dashboard.comingSoon') })] })] }) }, tile.key))) })] }));
}
