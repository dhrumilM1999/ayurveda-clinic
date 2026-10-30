// The frame around every screen: left menu, top bar with branch and language switchers.
import { DownOutlined, EnvironmentOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';
import { Alert, Avatar, Badge, Button, Dropdown, Grid, Layout, Menu, Segmented, Select } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { useIdleLogout } from '../auth/useIdleLogout';
import { SoftwareBrand } from '../components/SoftwareBrand';
import { clinicConfig } from '../config/clinic';
import { menuItems } from '../config/menu';
import { ErrorBoundary } from '../errorLog/ErrorBoundary';
import { addStep } from '../errorLog/tracker';
import { LANGUAGES, setLanguage } from '../i18n';

const { Header, Sider, Content } = Layout;
const { useBreakpoint } = Grid;

// Left menu: a thin strip of icons; it opens to full width while the mouse is over it, and stays open (pushing the page)
// after the toggle button is pressed. SAFE TO EDIT: the two widths (pixels) and the pinned choice key.
const MENU_WIDE = 224;
const MENU_THIN = 72;
const PINNED_KEY = 'menu-pinned';

function loadPinned(): boolean {
  try { return localStorage.getItem(PINNED_KEY) === '1'; } catch { return false; }
}

const SHORT_LANGUAGE: Record<string, string> = { en: 'EN', gu: 'ગુ', hi: 'हि' };

function initials(name: string) {
  return name
    .replace(/^(dr|mr|mrs|ms)\.?\s+/i, '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join('');
}

export default function MainLayout() {
  const { t, i18n } = useTranslation();
  const { me, branch, features, hasFeature, can, switchBranch, logout } = useAuth();
  const [pinned, setPinned] = useState(loadPinned); // opened with the toggle button
  const [hover, setHover] = useState(false); // the mouse is over the thin strip
  const leaveTimer = useRef<number>();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();
  // On a phone the menu is hidden until the menu button is pressed (it floats over the page, and closes after a choice)
  const isPhone = screens.sm === false;
  // On a phone only the toggle button opens the menu. On a computer the mouse also opens it while it is over the strip.
  const collapsed = isPhone ? !pinned : !(pinned || hover);
  useEffect(() => { try { localStorage.setItem(PINNED_KEY, pinned ? '1' : '0'); } catch { /* not remembered */ } }, [pinned]);
  const hoverIn = () => { window.clearTimeout(leaveTimer.current); if (!isPhone) setHover(true); };
  const hoverOut = () => { window.clearTimeout(leaveTimer.current); leaveTimer.current = window.setTimeout(() => setHover(false), 150); };
  useEffect(() => { addStep('page', location.pathname); }, [location.pathname]);

  const onIdle = useCallback(() => logout('idle'), [logout]);
  useIdleLogout(me?.idle_timeout_minutes, onIdle);

  const multiBranch = !!me?.organization?.multi_branch;
  // Number of new online enquiries (badge on the menu item)
  const [newEnquiries, setNewEnquiries] = useState(0);
  const showEnquiries = can('enquiries.view') && hasFeature('online_enquiry');
  useEffect(() => {
    if (!showEnquiries) return undefined;
    const load = () => api.get<{ new: number }>('/enquiries/summary/').then(({ data }) => setNewEnquiries(data.new)).catch(() => undefined);
    load();
    const timer = window.setInterval(load, 60000);
    return () => window.clearInterval(timer);
  }, [showEnquiries]);
  const visibleItems = menuItems.filter(
    (item) => (!item.permission || can(item.permission)) && (!item.feature || features[item.feature] !== false)
      && (!item.anyFeature || item.anyFeature.some((code) => hasFeature(code)))
      && (!item.multiBranchOnly || multiBranch)
      // The medicine list is a tab inside Pharmacy, unless "Medicines as its own menu" is on (Additional settings)
      // or the person cannot open Pharmacy
      && !(item.key === 'medicines' && features.pharmacy !== false && can('pharmacy.view') && !hasFeature('separate_medicine_menu')),
  );
  const selected = visibleItems.find((item) =>
    item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path),
  );

  const changeLanguage = (code: string) => {
    setLanguage(code);
    api.patch('/auth/me/', { preferred_language: code }).catch(() => undefined);
  };

  const roleLabel = me?.user.is_org_admin ? t('layout.orgAdmin') : branch?.role?.name ?? '';

  return (
    <Layout hasSider style={{ minHeight: '100vh' }}>
      {/* The slot keeps the page from moving: the menu opens OVER the page while hovered */}
      <div className="app-sider-slot" style={{ width: isPhone ? 0 : pinned ? MENU_WIDE : MENU_THIN }}
        onMouseEnter={hoverIn} onMouseLeave={hoverOut}>
      <Sider
        className={`app-sider${hover && !pinned && !isPhone ? ' app-sider-hover' : ''}`}
        collapsible
        collapsed={collapsed}
        trigger={null}
        width={MENU_WIDE}
        collapsedWidth={isPhone ? 0 : MENU_THIN}
      >
        <SoftwareBrand variant={collapsed ? 'mark' : 'sider'} />
        <div className="app-sider-divider" />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selected ? [selected.key] : []}
          items={visibleItems.map((item) => ({ key: item.key, icon: item.icon, label: item.key === 'enquiries' && newEnquiries > 0
            ? <span>{t(item.labelKey)} <Badge count={newEnquiries} size="small" /></span> : t(item.labelKey) }))}
          onClick={({ key }) => {
            const item = menuItems.find((m) => m.key === key);
            if (item) navigate(item.path);
            if (isPhone) setPinned(false);
          }}
        />
        {!collapsed && me?.organization && <div className="app-sider-footer">{me.organization.name}</div>}
      </Sider>
      </div>

      <Layout>
        <Header className="app-header">
          <div className="app-header-left">
            <Button
              type="text"
              icon={pinned ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
              onClick={() => { setPinned(!pinned); setHover(false); }}
              aria-label={t('layout.toggleMenu')}
            />
            {multiBranch ? <Select
              className="branch-picker"
              style={{ minWidth: 240, maxWidth: 340 }}
              value={branch?.id}
              onChange={switchBranch}
              suffixIcon={<DownOutlined />}
              prefix={<EnvironmentOutlined style={{ color: clinicConfig.colors.primary }} />}
              options={me?.branches.map((b) => ({ value: b.id, label: b.name }))}
              placeholder={t('layout.chooseBranch')}
              aria-label={t('layout.branch')}
            /> : null /* one clinic: nothing to choose, so no branch name here */}
          </div>
          <div className="app-header-right">
            <Segmented
              value={i18n.language}
              onChange={(value) => changeLanguage(String(value))}
              options={LANGUAGES.map((l) => ({ value: l.code, label: SHORT_LANGUAGE[l.code], title: l.label }))}
              aria-label={t('layout.language')}
            />
            <Dropdown
              trigger={['click']}
              menu={{
                items: [{ key: 'logout', icon: <LogoutOutlined />, label: t('layout.logout'), danger: true }],
                onClick: () => logout(),
              }}
            >
              <div className="user-chip" role="button" tabIndex={0}>
                <Avatar style={{ background: clinicConfig.colors.accent, fontWeight: 600 }}>
                  {initials(me?.user.full_name ?? '?')}
                </Avatar>
                <div className="user-chip-text">
                  <div className="user-chip-name">{me?.user.full_name}</div>
                  <div className="user-chip-role">{roleLabel}</div>
                </div>
                <DownOutlined style={{ fontSize: 10, opacity: 0.5 }} />
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content className="app-content">
          {!branch ? (
            <Alert type="warning" showIcon message={t('layout.noBranch')} />
          ) : (
            // key={branch.id}: reload the screen when the branch changes
            <ErrorBoundary resetKey={location.pathname}><Outlet key={branch.id} /></ErrorBoundary>
          )}
        </Content>
      </Layout>
    </Layout>
  );
}
