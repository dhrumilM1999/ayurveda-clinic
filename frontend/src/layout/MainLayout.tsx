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
  const { me, branch, features, can, switchBranch, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const onIdle = useCallback(() => logout('idle'), [logout]);
  useIdleLogout(me?.idle_timeout_minutes, onIdle);

  const multiBranch = !!me?.organization?.multi_branch;
  const visibleItems = menuItems.filter(
    (item) => (!item.permission || can(item.permission)) && (!item.feature || features[item.feature] !== false)
      && (!item.multiBranchOnly || multiBranch),
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
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        className="app-sider"
        collapsible
        collapsed={collapsed}
        trigger={null}
        breakpoint="lg"
        onBreakpoint={(broken) => setCollapsed(broken)}
        width={224}
        collapsedWidth={76}
      >
        <div className="app-brand">
          <img src={clinicConfig.logoPath} alt="" />
          {!collapsed && (
            <div>
              <div className="app-brand-name">{clinicConfig.appName}</div>
              <div className="app-brand-sub">{t('layout.tagline')}</div>
            </div>
          )}
        </div>
        <div className="app-sider-divider" />
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selected ? [selected.key] : []}
          items={visibleItems.map((item) => ({ key: item.key, icon: item.icon, label: t(item.labelKey) }))}
          onClick={({ key }) => {
            const item = menuItems.find((m) => m.key === key);
            if (item) navigate(item.path);
          }}
        />
        {!collapsed && me?.organization && <div className="app-sider-footer">{me.organization.name}</div>}
      </Sider>

      <Layout>
        <Header className="app-header">
          <div className="app-header-left">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
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
            /> : (
              // Single-branch mode: just show the clinic / branch name
              <span className="branch-name"><EnvironmentOutlined /> {branch?.name}</span>
            )}
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
            <Outlet key={branch.id} />
          )}
        </Content>
      </Layout>
    </Layout>
  );
}
