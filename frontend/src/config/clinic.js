// SAFE TO EDIT: app name, logo, colours, fonts and default language.
// Save the file and the browser updates by itself (wait a few seconds).
// Colours are written like '#1f5c45' (pick any colour at https://htmlcolorcodes.com).
export const clinicConfig = {
    // Name shown in the menu and on the login page
    appName: 'Ayurveda Clinic',
    // (The small line under the name and the sentence on the login page are screen text:
    //  change them in src/i18n/*.json -> "layout.tagline" and "login.quote".)
    // Logo file inside frontend/public/
    logoPath: '/logo.svg',
    // Language when someone opens the app for the first time: 'en', 'gu' or 'hi'
    defaultLanguage: 'en',
    colors: {
        // Main colour: buttons, links, selected items
        primary: '#1f5c45',
        // Left menu and login panel (a darker shade of the main colour looks best)
        sidebar: '#12382a',
        // Highlight colour: selected menu item, small accents (turmeric gold)
        accent: '#c98a2b',
        // Page background behind the white cards
        background: '#f6f3ec',
        // Main text colour
        text: '#23302a',
        // Lines and borders
        border: '#e6e0d2',
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
