// SAFE TO EDIT: the items in the left menu.
// - labelKey: the screen text key in src/i18n/*.json (under "menu")
// - permission: the menu item only shows if the user has this permission in the current branch
// - path: must match a route in src/App.tsx
// - feature: the item hides when that module is switched off for the branch (Settings)
// - multiBranchOnly: the item shows only when "Use more than one branch" is on (Settings)
import {
  AppstoreAddOutlined, ApartmentOutlined, DollarOutlined, WalletOutlined, AuditOutlined, ExperimentOutlined, ShopOutlined, FormOutlined, MedicineBoxOutlined, CalendarOutlined, DashboardOutlined, HomeOutlined,
  IdcardOutlined, OrderedListOutlined, SafetyCertificateOutlined, ScheduleOutlined, SettingOutlined, TeamOutlined,
} from '@ant-design/icons';
import type { ReactNode } from 'react';

export interface MenuItemConfig {
  key: string;
  path: string;
  labelKey: string;
  icon: ReactNode;
  permission?: string;
  feature?: string;
  multiBranchOnly?: boolean;
}

export const menuItems: MenuItemConfig[] = [
  { key: 'dashboard', path: '/', labelKey: 'menu.dashboard', icon: <DashboardOutlined />, permission: 'dashboard.view' },
  { key: 'patients', path: '/patients', labelKey: 'menu.patients', icon: <IdcardOutlined />, permission: 'patients.view' },
  { key: 'appointments', path: '/appointments', labelKey: 'menu.appointments', icon: <ScheduleOutlined />, permission: 'appointments.view', feature: 'appointments' },
  { key: 'consult', path: '/consult', labelKey: 'menu.consult', icon: <MedicineBoxOutlined />, permission: 'emr.view' },
  { key: 'medicines', path: '/medicines', labelKey: 'menu.medicines', icon: <ExperimentOutlined />, permission: 'medicines.view' },
  { key: 'billing', path: '/billing', labelKey: 'menu.billing', icon: <WalletOutlined />, permission: 'billing.view' },
  { key: 'pharmacy', path: '/pharmacy', labelKey: 'menu.pharmacy', icon: <ShopOutlined />, permission: 'pharmacy.view', feature: 'pharmacy' },
  { key: 'queue', path: '/queue', labelKey: 'menu.queue', icon: <OrderedListOutlined />, permission: 'appointments.view', feature: 'appointments' },
  { key: 'branches', path: '/branches', labelKey: 'menu.branches', icon: <ApartmentOutlined />, permission: 'branches.view', multiBranchOnly: true },
  { key: 'rooms', path: '/rooms', labelKey: 'menu.rooms', icon: <HomeOutlined />, permission: 'rooms.view' },
  { key: 'staff', path: '/staff', labelKey: 'menu.staff', icon: <TeamOutlined />, permission: 'staff.view' },
  { key: 'roles', path: '/roles', labelKey: 'menu.roles', icon: <SafetyCertificateOutlined />, permission: 'roles.view' },
  { key: 'schedules', path: '/schedules', labelKey: 'menu.schedules', icon: <CalendarOutlined />, permission: 'schedules.view' },
  { key: 'templates', path: '/templates', labelKey: 'menu.templates', icon: <FormOutlined />, permission: 'settings.manage' },
  { key: 'fees', path: '/fees-services', labelKey: 'menu.fees', icon: <DollarOutlined />, permission: 'billing.manage' },
  { key: 'settings', path: '/settings', labelKey: 'menu.settings', icon: <SettingOutlined />, permission: 'settings.manage' },
  { key: 'additional', path: '/additional-settings', labelKey: 'menu.additional', icon: <AppstoreAddOutlined />, permission: 'settings.manage' },
  { key: 'audit', path: '/audit-log', labelKey: 'menu.audit', icon: <AuditOutlined />, permission: 'audit.view' },
];
