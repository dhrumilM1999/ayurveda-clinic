import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// The frame around every screen: left menu, top bar with branch and language switchers.
import { DownOutlined, EnvironmentOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { Alert, Avatar, Button, Dropdown, Layout, Menu, Segmented, Select } from 'antd';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { useIdleLogout } from '../auth/useIdleLogout';
import { clinicConfig } from '../config/clinic';
import { menuItems } from '../config/menu';
import { LANGUAGES, setLanguage } from '../i18n';
const { Header, Sider, Content } = Layout;
const SHORT_LANGUAGE = { en: 'EN', gu: 'ગુ', hi: 'हि' };
function initials(name) {
    return name
        .replace(/^(dr|mr|mrs|ms)\.?\s+/i, '')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0].toUpperCase())
        .join('');
}
export default function MainLayout() {
    const { t, i18n } = useTranslation();
    const { me, branch, can, switchBranch, logout } = useAuth();
    const [collapsed, setCollapsed] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const onIdle = useCallback(() => logout('idle'), [logout]);
    useIdleLogout(me?.idle_timeout_minutes, onIdle);
    const visibleItems = menuItems.filter((item) => !item.permission || can(item.permission));
    const selected = visibleItems.find((item) => item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path));
    const changeLanguage = (code) => {
        setLanguage(code);
        api.patch('/auth/me/', { preferred_language: code }).catch(() => undefined);
    };
    const roleLabel = me?.user.is_org_admin ? t('layout.orgAdmin') : branch?.role?.name ?? '';
    return (_jsxs(Layout, { style: { minHeight: '100vh' }, children: [_jsxs(Sider, { className: "app-sider", collapsible: true, collapsed: collapsed, trigger: null, breakpoint: "lg", onBreakpoint: (broken) => setCollapsed(broken), width: 248, collapsedWidth: 76, children: [_jsxs("div", { className: "app-brand", children: [_jsx("img", { src: clinicConfig.logoPath, alt: "" }), !collapsed && (_jsxs("div", { children: [_jsx("div", { className: "app-brand-name", children: clinicConfig.appName }), _jsx("div", { className: "app-brand-sub", children: t('layout.tagline') })] }))] }), _jsx("div", { className: "app-sider-divider" }), _jsx(Menu, { theme: "dark", mode: "inline", selectedKeys: selected ? [selected.key] : [], items: visibleItems.map((item) => ({ key: item.key, icon: item.icon, label: t(item.labelKey) })), onClick: ({ key }) => {
                            const item = menuItems.find((m) => m.key === key);
                            if (item)
                                navigate(item.path);
                        } }), !collapsed && me?.organization && _jsx("div", { className: "app-sider-footer", children: me.organization.name })] }), _jsxs(Layout, { children: [_jsxs(Header, { className: "app-header", children: [_jsxs("div", { className: "app-header-left", children: [_jsx(Button, { type: "text", icon: collapsed ? _jsx(MenuUnfoldOutlined, {}) : _jsx(MenuFoldOutlined, {}), onClick: () => setCollapsed(!collapsed), "aria-label": t('layout.toggleMenu') }), _jsx(Select, { className: "branch-picker", style: { minWidth: 240, maxWidth: 340 }, value: branch?.id, onChange: switchBranch, suffixIcon: _jsx(DownOutlined, {}), prefix: _jsx(EnvironmentOutlined, { style: { color: clinicConfig.colors.primary } }), options: me?.branches.map((b) => ({ value: b.id, label: b.name })), placeholder: t('layout.chooseBranch'), "aria-label": t('layout.branch') })] }), _jsxs("div", { className: "app-header-right", children: [_jsx(Segmented, { value: i18n.language, onChange: (value) => changeLanguage(String(value)), options: LANGUAGES.map((l) => ({ value: l.code, label: SHORT_LANGUAGE[l.code], title: l.label })), "aria-label": t('layout.language') }), _jsx(Dropdown, { trigger: ['click'], menu: {
                                            items: [{ key: 'logout', icon: _jsx(LogoutOutlined, {}), label: t('layout.logout'), danger: true }],
                                            onClick: () => logout(),
                                        }, children: _jsxs("div", { className: "user-chip", role: "button", tabIndex: 0, children: [_jsx(Avatar, { style: { background: clinicConfig.colors.accent, fontWeight: 600 }, children: initials(me?.user.full_name ?? '?') }), _jsxs("div", { className: "user-chip-text", children: [_jsx("div", { className: "user-chip-name", children: me?.user.full_name }), _jsx("div", { className: "user-chip-role", children: roleLabel })] }), _jsx(DownOutlined, { style: { fontSize: 10, opacity: 0.5 } })] }) })] })] }), _jsx(Content, { className: "app-content", children: !branch ? (_jsx(Alert, { type: "warning", showIcon: true, message: t('layout.noBranch') })) : (
                        // key={branch.id}: reload the screen when the branch changes
                        _jsx(Outlet, {}, branch.id)) })] })] }));
}
