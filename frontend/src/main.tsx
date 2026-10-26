import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './i18n';
import './styles.css';
import './premium.css';
import App from './App';
import { AuthProvider } from './auth/AuthContext';
import { BrandingProvider } from './branding/BrandingContext';
import { installGlobalHandlers } from './errorLog/tracker';

installGlobalHandlers();

// ?design=premium shows the premium look (preview); ?design=standard goes back. The choice is remembered in this browser.
try {
  const asked = new URLSearchParams(window.location.search).get('design');
  if (asked === 'premium' || asked === 'standard') localStorage.setItem('design', asked);
  document.documentElement.dataset.design = localStorage.getItem('design') === 'premium' ? 'premium' : 'standard';
} catch { /* browser storage is off: the standard look */ }

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <BrandingProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrandingProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
