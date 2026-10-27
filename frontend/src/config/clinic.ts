// SAFE TO EDIT: app name, logo, colours, fonts and default language.
// Save the file and the browser updates by itself (wait a few seconds).
// Colours are written like '#1f5c45' (pick any colour at https://htmlcolorcodes.com).

// SAFE TO EDIT: the colours (main colour, menu, highlight, page background, text, lines)
const DEFAULT_COLORS = {
    // Main colour: buttons, links, selected items (ember orange)
    primary: '#e0560f',
    // Left menu, login panel and the greeting box (flat dark charcoal)
    sidebar: '#1f2430',
    // Small accents: the bar before section titles, the avatar
    accent: '#e0560f',
    // Page background behind the white cards
    background: '#f4f4f2',
    // Main text colour
    text: '#1c1f26',
    // Lines and borders
    border: '#dcdcd6',
    // Status colours (success is the second colour: teal)
    success: '#0f8f84',
    warning: '#d48a0c',
    error: '#c2412d',
};

// PREVIEW ONLY: open any page with ?palette=saffron | maroon | charcoal | plum to try another colour tone
// (remembered in this browser; ?palette=default goes back). The real colours are DEFAULT_COLORS below.
const PALETTES: Record<string, Partial<typeof DEFAULT_COLORS>> = {
  saffron: { primary: '#c2571a', sidebar: '#3b2314', accent: '#e8a33d', background: '#f7f1e8', text: '#2b1d12', border: '#e3d6c3' },
  maroon: { primary: '#8b2c3b', sidebar: '#3a1219', accent: '#d9a441', background: '#f8f1ee', text: '#2a1518', border: '#e6d3cd' },
  charcoal: { primary: '#374151', sidebar: '#1f2430', accent: '#c9a227', background: '#f4f4f2', text: '#1c1f26', border: '#dcdcd6' },
  klinvexa: { primary: '#2563eb', sidebar: '#0f172a', accent: '#14b8a6', background: '#f1f5f9', text: '#0f172a', border: '#e2e8f0', success: '#14b8a6' },
  ember: { primary: '#e0560f', sidebar: '#1f2430', accent: '#e0560f', background: '#f4f4f2', text: '#1c1f26', border: '#dcdcd6' },
  teal: { primary: '#0f8f84', sidebar: '#1f2430', accent: '#0f8f84', background: '#f4f4f2', text: '#1c1f26', border: '#dcdcd6' },
  crimson: { primary: '#c42a4d', sidebar: '#1f2430', accent: '#c42a4d', background: '#f4f4f2', text: '#1c1f26', border: '#dcdcd6' },
  plum: { primary: '#6d3fa0', sidebar: '#2a1745', accent: '#b18ae0', background: '#f3eff8', text: '#20152e', border: '#d9cfe8' },
};
function pickColors() {
  let name = '';
  try {
    name = new URLSearchParams(window.location.search).get('palette') ?? localStorage.getItem('palette') ?? '';
    if (new URLSearchParams(window.location.search).has('palette')) localStorage.setItem('palette', name);
  } catch { /* no storage: fine */ }
  return { ...DEFAULT_COLORS, ...(PALETTES[name] ?? {}) };
}

export const clinicConfig = {
  // Default name, used only until a clinic name is saved in Settings -> Clinic details
  // (the saved clinic name and logo are shown in the menu and on the login page).
  appName: 'Ayurveda Clinic',
  // (The small line under the name and the sentence on the login page are screen text:
  //  change them in src/i18n/*.json -> "layout.tagline" and "login.quote".)
  // Default logo (inside frontend/public/), used only until the clinic uploads its own logo in Settings
  logoPath: '/logo.svg',
  // Language when someone opens the app for the first time: 'en', 'gu' or 'hi'
  defaultLanguage: 'en' as 'en' | 'gu' | 'hi',

  colors: pickColors(),


  fonts: {
    // Satoshi (files in public/fonts). Body text. Gujarati uses "Hind Vadodara", Hindi uses "Hind" automatically.
    body: "'Satoshi', 'Plus Jakarta Sans', 'Hind Vadodara', 'Hind', 'Nirmala UI', 'Segoe UI', sans-serif",
    // Clinic name and page titles
    heading: "'Satoshi', 'Hind Vadodara', 'Hind', 'Segoe UI', sans-serif",
  },

  // Corner roundness of buttons and boxes (in pixels)
  borderRadius: 10,
};

// The software's own brand (not the clinic's): shown in the app only - menu, login screen and browser tab.
// It is never printed on prescriptions, bills or other print-outs. Files: frontend/public/brand/.
export const softwareConfig = {
  name: 'Klinvexa',
  nameParts: ['Klin', 'vexa'] as [string, string],
  markPath: '/brand/klinvexa-mark.svg',
  // the full logo (wordmark): one for light screens, one for dark screens (menu, login panel)
  logoPath: '/brand/klinvexa-logo.svg',
  logoWhitePath: '/brand/klinvexa-logo-white.svg',
};
