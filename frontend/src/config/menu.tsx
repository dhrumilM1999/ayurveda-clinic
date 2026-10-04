// SAFE TO EDIT: the items in the left menu.
// - labelKey: the screen text key in src/i18n/*.json (under "menu")
// - permission: the menu item only shows if the user has this permission in the current branch
// - path: must match a route in src/App.tsx
import {
  ApartmentOutlined, AuditOutlined, CalendarOutlined, DashboardOutlined, HomeOutlined,
  IdcardOutlined, SafetyCertificateOutlined, SettingOutlined, TeamOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';

export interface MenuItemConfig {
  key: string;
  path: string;
  labelKey: string;
  icon: ReactNode;
  permission?: string;
}

export const menuItems: MenuItemConfig[] = [
  { key: 'dashboard', path: '/', labelKey: 'menu.dashboard', icon: <DashboardOutlined />, permission: 'dashboard.view' },
  { key: 'patients', path: '/patients', labelKey: 'menu.patients', icon: <IdcardOutlined />, permission: 'patients.view' },
  { key: 'branches', path: '/branches', labelKey: 'menu.branches', icon: <ApartmentOutlined />, permission: 'branches.view' },
  { key: 'rooms', path: '/rooms', labelKey: 'menu.rooms', icon: <HomeOutlined />, permission: 'rooms.view' },
  { key: 'staff', path: '/staff', labelKey: 'menu.staff', icon: <TeamOutlined />, permission: 'staff.view' },
  { key: 'roles', path: '/roles', labelKey: 'menu.roles', icon: <SafetyCertificateOutlined />, permission: 'roles.view' },
  { key: 'schedules', path: '/schedules', labelKey: 'menu.schedules', icon: <CalendarOutlined />, permission: 'schedules.view' },
  { key: 'settings', path: '/settings', labelKey: 'menu.settings', icon: <SettingOutlined />, permission: 'settings.manage' },
  { key: 'audit', path: '/audit-log', labelKey: 'menu.audit', icon: <AuditOutlined />, permission: 'audit.view' },
];
