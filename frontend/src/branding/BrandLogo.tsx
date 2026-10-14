// The clinic logo. A wide logo sits on a white plate (so it is readable on the dark menu and login panel).
// When the clinic has no logo yet, the small default leaf is shown and the screen prints the clinic name next to it.
// ASK FIRST before editing. Sizes are in styles.css (.brand-plate).
import { clinicConfig } from '../config/clinic';
import { useBranding } from './BrandingContext';

export type BrandVariant = 'sider' | 'login' | 'mobile' | 'tv';

export function BrandLogo({ variant }: { variant: BrandVariant }) {
  const { logoUrl, appName } = useBranding();
  if (!logoUrl) return <img src={clinicConfig.logoPath} alt="" className="brand-leaf" />;
  return (
    <span className={`brand-plate brand-plate-${variant}`}>
      <img src={logoUrl} alt={appName} />
    </span>
  );
}
