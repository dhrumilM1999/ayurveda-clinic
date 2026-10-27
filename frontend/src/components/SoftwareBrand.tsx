// The software's own brand (name + mark), shown inside the app only: menu, login screen, browser tab.
// It is NOT printed on prescriptions, bills or any other print-out (those carry the clinic's own letterhead).
// The files are in frontend/public/brand/ (made in brand/klinvexa/). The name is in config/clinic.ts (softwareConfig).
import { softwareConfig } from '../config/clinic';

export type SoftwareBrandVariant = 'sider' | 'mark' | 'login' | 'mobile';

export function SoftwareBrand({ variant }: { variant: SoftwareBrandVariant }) {
  const dark = variant === 'mobile'; // on the light login page the dark-text logo is used
  const src = variant === 'mark' ? softwareConfig.markPath : dark ? softwareConfig.logoPath : softwareConfig.logoWhitePath;
  const width = variant === 'mark' ? 36 : variant === 'login' ? 230 : variant === 'mobile' ? 150 : 150;
  return (
    <div className={`software-brand software-brand-${variant}`}>
      <img src={src} width={width} alt={softwareConfig.name} />
    </div>
  );
}
