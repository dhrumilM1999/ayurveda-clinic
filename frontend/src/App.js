import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The list of screens (routes). To add a screen: add a <Route> here and an item in config/menu.tsx.
import { App as AntApp, ConfigProvider, Spin } from 'antd';
import enUS from 'antd/locale/en_US';
import hiIN from 'antd/locale/hi_IN';
import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { RequirePermission } from './components/RequirePermission';
import MainLayout from './layout/MainLayout';
import AuditLogPage from './pages/AuditLogPage';
import BranchesPage from './pages/BranchesPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import PatientDetailPage from './pages/patients/PatientDetailPage';
import PatientFormPage from './pages/patients/PatientFormPage';
import PatientsPage from './pages/patients/PatientsPage';
import RolesPage from './pages/RolesPage';
import RoomsPage from './pages/RoomsPage';
import SchedulesPage from './pages/SchedulesPage';
import SettingsPage from './pages/SettingsPage';
import StaffPage from './pages/StaffPage';
import { antTheme, applyCssVariables } from './theme';
applyCssVariables();
export default function App() {
    const { me, loading } = useAuth();
    const { i18n } = useTranslation();
    return (_jsx(ConfigProvider, { theme: antTheme, locale: i18n.language === 'hi' ? hiIN : enUS, children: _jsx(AntApp, { children: loading ? (_jsx("div", { style: { display: 'flex', justifyContent: 'center', marginTop: '30vh' }, children: _jsx(Spin, { size: "large" }) })) : !me ? (_jsx(Routes, { children: _jsx(Route, { path: "*", element: _jsx(LoginPage, {}) }) })) : (_jsx(Routes, { children: _jsxs(Route, { element: _jsx(MainLayout, {}), children: [_jsx(Route, { index: true, element: _jsx(DashboardPage, {}) }), _jsx(Route, { path: "patients", element: _jsx(RequirePermission, { code: "patients.view", children: _jsx(PatientsPage, {}) }) }), _jsx(Route, { path: "patients/new", element: _jsx(RequirePermission, { code: "patients.create", children: _jsx(PatientFormPage, {}) }) }), _jsx(Route, { path: "patients/:id", element: _jsx(RequirePermission, { code: "patients.view", children: _jsx(PatientDetailPage, {}) }) }), _jsx(Route, { path: "patients/:id/edit", element: _jsx(RequirePermission, { code: "patients.edit", children: _jsx(PatientFormPage, {}, "edit") }) }), _jsx(Route, { path: "branches", element: _jsx(RequirePermission, { code: "branches.view", children: _jsx(BranchesPage, {}) }) }), _jsx(Route, { path: "rooms", element: _jsx(RequirePermission, { code: "rooms.view", children: _jsx(RoomsPage, {}) }) }), _jsx(Route, { path: "staff", element: _jsx(RequirePermission, { code: "staff.view", children: _jsx(StaffPage, {}) }) }), _jsx(Route, { path: "roles", element: _jsx(RequirePermission, { code: "roles.view", children: _jsx(RolesPage, {}) }) }), _jsx(Route, { path: "schedules", element: _jsx(RequirePermission, { code: "schedules.view", children: _jsx(SchedulesPage, {}) }) }), _jsx(Route, { path: "settings", element: _jsx(RequirePermission, { code: "settings.manage", children: _jsx(SettingsPage, {}) }) }), _jsx(Route, { path: "audit-log", element: _jsx(RequirePermission, { code: "audit.view", children: _jsx(AuditLogPage, {}) }) }), _jsx(Route, { path: "login", element: _jsx(Navigate, { to: "/", replace: true }) }), _jsx(Route, { path: "*", element: _jsx(NotFoundPage, {}) })] }) })) }) }));
}
