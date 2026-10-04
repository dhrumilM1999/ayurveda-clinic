// Turns the colours and fonts from config/clinic.ts into the Ant Design theme.
// To change colours or fonts, edit config/clinic.ts, not this file.
import type { ThemeConfig } from 'antd';
import { clinicConfig } from './config/clinic';

// Fonts are stored inside the project, so they work without internet.
import '@fontsource/plus-jakarta-sans/400.css';
import '@fontsource/plus-jakarta-sans/500.css';
import '@fontsource/plus-jakarta-sans/600.css';
import '@fontsource/plus-jakarta-sans/700.css';
import '@fontsource/hind-vadodara/400.css';
import '@fontsource/hind-vadodara/500.css';
import '@fontsource/hind-vadodara/600.css';
import '@fontsource/hind/400.css';
import '@fontsource/hind/500.css';
import '@fontsource/hind/600.css';
import '@fontsource-variable/fraunces';

const c = clinicConfig.colors;

/** Same colour with transparency, e.g. alpha('#c98a2b', 0.2) */
export function alpha(hex: string, opacity: number): string {
  const n = parseInt(hex.replace('#', ''), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${opacity})`;
}

// Make the colours available to styles.css as var(--clinic-primary) etc.
export function applyCssVariables() {
  const root = document.documentElement.style;
  root.setProperty('--clinic-primary', c.primary);
  root.setProperty('--clinic-sidebar', c.sidebar);
  root.setProperty('--clinic-accent', c.accent);
  root.setProperty('--clinic-accent-soft', alpha(c.accent, 0.16));
  root.setProperty('--clinic-primary-soft', alpha(c.primary, 0.08));
  root.setProperty('--clinic-bg', c.background);
  root.setProperty('--clinic-text', c.text);
  root.setProperty('--clinic-border', c.border);
  root.setProperty('--clinic-font-body', clinicConfig.fonts.body);
  root.setProperty('--clinic-font-heading', clinicConfig.fonts.heading);
  root.setProperty('--clinic-radius', `${clinicConfig.borderRadius}px`);
}

export const antTheme: ThemeConfig = {
  token: {
    colorPrimary: c.primary,
    colorSuccess: c.success,
    colorWarning: c.warning,
    colorError: c.error,
    colorInfo: c.primary,
    colorText: c.text,
    colorBorder: c.border,
    colorBorderSecondary: alpha(c.border, 0.7),
    colorBgLayout: c.background,
    fontFamily: clinicConfig.fonts.body,
    fontSize: 14,
    borderRadius: clinicConfig.borderRadius,
    controlHeight: 38,
    boxShadowTertiary: '0 1px 2px rgba(35, 48, 42, 0.04), 0 2px 8px rgba(35, 48, 42, 0.04)',
  },
  components: {
    Layout: { siderBg: c.sidebar, headerBg: '#ffffff', bodyBg: c.background, headerHeight: 64 },
    Menu: {
      darkItemBg: c.sidebar,
      darkSubMenuItemBg: c.sidebar,
      darkItemColor: 'rgba(255, 255, 255, 0.72)',
      darkItemHoverColor: '#ffffff',
      darkItemHoverBg: 'rgba(255, 255, 255, 0.06)',
      darkItemSelectedBg: alpha(c.accent, 0.2),
      darkItemSelectedColor: '#f6dcae',
      itemHeight: 44,
      itemMarginInline: 12,
      itemBorderRadius: 10,
      iconSize: 17,
    },
    Card: { borderRadiusLG: 14, paddingLG: 22 },
    Table: {
      headerBg: '#faf8f3',
      headerColor: alpha(c.text, 0.7),
      headerSplitColor: 'transparent',
      rowHoverBg: alpha(c.primary, 0.035),
      borderColor: alpha(c.border, 0.7),
      cellPaddingBlock: 14,
    },
    Button: { fontWeight: 600, primaryShadow: `0 2px 6px ${alpha(c.primary, 0.25)}` },
    Modal: { borderRadiusLG: 16, titleFontSize: 18 },
    Tag: { borderRadiusSM: 6 },
    Input: { activeShadow: `0 0 0 3px ${alpha(c.primary, 0.12)}` },
    Select: { optionSelectedBg: alpha(c.primary, 0.08) },
  },
};
