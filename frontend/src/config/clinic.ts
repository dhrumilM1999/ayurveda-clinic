// SAFE TO EDIT: app name, logo, colours, fonts and default language.
// Save the file and the browser updates by itself (wait a few seconds).
// Colours are written like '#1f5c45' (pick any colour at https://htmlcolorcodes.com).

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

  colors: {
    // Main colour: buttons, links, selected items
    primary: '#2563eb',
    // Left menu and login panel (a darker shade of the main colour looks best)
    sidebar: '#10284a',
    // Highlight colour: selected menu item, small accents (light blue)
    accent: '#5b9bff',
    // Page background behind the white cards
    background: '#f2f5fb',
    // Main text colour
    text: '#1b2a41',
    // Lines and borders
    border: '#dbe3f0',
    // Status colours
    success: '#2f8a57',
    warning: '#d48a0c',
    error: '#c2412d',
  },

  fonts: {
    // Body text. Gujarati uses "Hind Vadodara", Hindi uses "Hind" automatically.
    body: "'Plus Jakarta Sans', 'Hind Vadodara', 'Hind', 'Nirmala UI', 'Segoe UI', sans-serif",
    // Clinic name and page titles
    heading: "'Fraunces Variable', 'Hind Vadodara', 'Hind', Georgia, serif",
  },

  // Corner roundness of buttons and boxes (in pixels)
  borderRadius: 10,
};
