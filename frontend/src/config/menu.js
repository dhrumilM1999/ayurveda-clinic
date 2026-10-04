import { jsx as _jsx } from "react/jsx-runtime";
// SAFE TO EDIT: the items in the left menu.
// - labelKey: the screen text key in src/i18n/*.json (under "menu")
// - permission: the menu item only shows if the user has this permission in the current branch
// - path: must match a route in src/App.tsx
import { ApartmentOutlined, AuditOutlined, CalendarOutlined, DashboardOutlined, HomeOutlined, IdcardOutlined, SafetyCertificateOutlined, SettingOutlined, TeamOutlined, } from '@ant-design/icons';
export const menuItems = [
    { key: 'dashboard', path: '/', labelKey: 'menu.dashboard', icon: _jsx(DashboardOutlined, {}), permission: 'dashboard.view' },
    { key: 'patients', path: '/patients', labelKey: 'menu.patients', icon: _jsx(IdcardOutlined, {}), permission: 'patients.view' },
    { key: 'branches', path: '/branches', labelKey: 'menu.branches', icon: _jsx(ApartmentOutlined, {}), permission: 'branches.view' },
    { key: 'rooms', path: '/rooms', labelKey: 'menu.rooms', icon: _jsx(HomeOutlined, {}), permission: 'rooms.view' },
    { key: 'staff', path: '/staff', labelKey: 'menu.staff', icon: _jsx(TeamOutlined, {}), permission: 'staff.view' },
    { key: 'roles', path: '/roles', labelKey: 'menu.roles', icon: _jsx(SafetyCertificateOutlined, {}), permission: 'roles.view' },
    { key: 'schedules', path: '/schedules', labelKey: 'menu.schedules', icon: _jsx(CalendarOutlined, {}), permission: 'schedules.view' },
    { key: 'settings', path: '/settings', labelKey: 'menu.settings', icon: _jsx(SettingOutlined, {}), permission: 'settings.manage' },
    { key: 'audit', path: '/audit-log', labelKey: 'menu.audit', icon: _jsx(AuditOutlined, {}), permission: 'audit.view' },
];
