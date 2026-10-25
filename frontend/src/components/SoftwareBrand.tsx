// The software's own brand (name + mark), shown inside the app only: menu, login screen, browser tab.
// It is NOT printed on prescriptions, bills or any other print-out (those carry the clinic's own letterhead).
// The files are in frontend/public/brand/. The name is in config/clinic.ts (softwareConfig).
import { useTranslation } from 'react-i18next';
import { softwareConfig } from '../config/clinic';

export type SoftwareBrandVariant = 'sider' | 'mark' | 'login' | 'mobile';

export function SoftwareBrand({ variant }: { variant: SoftwareBrandVariant }) {
  const { t } = useTranslation();
  const [first, second] = softwareConfig.nameParts;
  const size = variant === 'login' ? 44 : variant === 'mobile' ? 34 : 32;
  return (
    <div className={`software-brand software-brand-${variant}`} title={`${softwareConfig.name} - ${t('layout.softwareTagline')}`}>
      <img src={softwareConfig.markPath} width={size} height={size} alt={softwareConfig.name} />
      {variant !== 'mark' && (
        <div>
          <div className="software-brand-name"><span>{first}</span><span className="software-brand-name-2">{second}</span></div>
          {variant !== 'mobile' && <div className="software-brand-sub">{t('layout.softwareTagline')}</div>}
        </div>
      )}
    </div>
  );
}
