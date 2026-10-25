// The clinic's own name and logo, shown in the menu, on the login screen, the TV screen and the browser tab.
// They come from Settings -> Clinic (name and logo), so every clinic gets its own look without code changes.
// ASK FIRST before editing. To change the default (when a clinic has not set a logo yet), edit config/clinic.ts.
import axios from 'axios';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { clinicConfig, softwareConfig } from '../config/clinic';

type BrandInfo = { name: string; short_name: string; has_logo: boolean; version: number };
type Branding = {
  appName: string;
  /** Address of the clinic logo picture, or null when the clinic has not uploaded one */
  logoUrl: string | null;
  /** Call after the clinic name or logo is changed, so every screen updates at once */
  refresh: () => Promise<void>;
};

const CACHE_KEY = 'clinic_branding';
const BrandingContext = createContext<Branding | null>(null);

function readCache(): BrandInfo | null {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) || 'null');
  } catch {
    return null;
  }
}

// The browser tab icon: the clinic logo on a white square
function setFavicon(url: string | null) {
  const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (!link) return;
  if (!url) {
    link.type = 'image/svg+xml';
    link.href = softwareConfig.markPath;
    return;
  }
  const img = new Image();
  img.onload = () => {
    try {
      const size = 64;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, size, size);
      const scale = Math.min((size - 6) / img.width, (size - 6) / img.height);
      const w = img.width * scale;
      const h = img.height * scale;
      ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
      link.type = 'image/png';
      link.href = canvas.toDataURL('image/png');
    } catch {
      /* keep the old icon */
    }
  };
  img.src = url;
}

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [info, setInfo] = useState<BrandInfo | null>(readCache);

  const refresh = useCallback(async () => {
    try {
      // Plain request: this works before anyone is logged in
      const { data } = await axios.get<BrandInfo>('/api/v1/branding/');
      setInfo(data);
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));
    } catch {
      /* offline or server starting: keep what we have */
    }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  const appName = info?.name || clinicConfig.appName;
  const logoUrl = info?.has_logo ? `/api/v1/branding/logo/?v=${info.version}` : null;

  // Browser tab: the software's name and mark (the clinic's own name and logo are inside the app)
  useEffect(() => { document.title = `${appName} · ${softwareConfig.name}`; }, [appName]);
  useEffect(() => { setFavicon(null); }, []);

  const value = useMemo(() => ({ appName, logoUrl, refresh }), [appName, logoUrl, refresh]);
  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
}

export function useBranding(): Branding {
  const ctx = useContext(BrandingContext);
  if (!ctx) throw new Error('useBranding must be used inside BrandingProvider');
  return ctx;
}
