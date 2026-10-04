// Full-screen queue for a TV in the waiting room. Open it from the Queue screen ("TV screen").
// On the TV computer: log in, choose the branch, open Queue -> TV screen, press F11 for full screen.
// It shows only the token number and a short name (e.g. "Ramesh P.") to protect privacy.
// SAFE TO EDIT: REFRESH_SECONDS and NEXT_COUNT below.
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { clinicConfig } from '../../config/clinic';
import { useQueue } from './QueuePage';

const REFRESH_SECONDS = 10;
const NEXT_COUNT = 5; // how many waiting tokens to show per doctor

export default function QueueDisplayPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, error } = useQueue(REFRESH_SECONDS);
  const [now, setNow] = useState(dayjs());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(dayjs()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="tv">
      <header className="tv-head">
        <div className="tv-brand">
          <img src={clinicConfig.logoPath} alt="" />
          <div>
            <div className="tv-title">{clinicConfig.appName}</div>
            <div className="tv-sub">{data?.branch_name}</div>
          </div>
        </div>
        <button type="button" className="tv-exit" onClick={() => navigate('/queue')}>{t('queue.exitTv')}</button>
        <div className="tv-clock">
          <div>{now.format('h:mm')}<small>{now.format(' A')}</small></div>
          <div className="tv-sub">{now.format('DD-MM-YYYY')}</div>
        </div>
      </header>

      {error ? <div className="tv-empty">{t('queue.tvOffline')}</div> : null}
      {data && data.doctors.length === 0 && <div className="tv-empty">{t('queue.empty')}</div>}

      <main className="tv-grid">
        {data?.doctors.map((group) => (
          <section className="tv-doctor" key={group.doctor}>
            <h2>{group.doctor_name}</h2>
            <div className="tv-now">
              <div className="tv-label">{t('queue.nowCalling')}</div>
              {group.now.length ? group.now.map((item) => (
                <div key={item.id} className="tv-now-row">
                  <span className="tv-token">{item.token_number ?? '—'}</span>
                  <span className="tv-name">{item.display_name}</span>
                </div>
              )) : <div className="tv-token tv-token-empty">—</div>}
            </div>
            <div className="tv-label">{t('queue.next')}</div>
            <ul className="tv-next">
              {group.waiting.slice(0, NEXT_COUNT).map((item) => (
                <li key={item.id}>
                  <span className="tv-next-token">{item.token_number}</span>
                  <span>{item.display_name}</span>
                </li>
              ))}
              {group.waiting.length === 0 && <li className="tv-dim">{t('queue.noneWaiting')}</li>}
              {group.waiting.length > NEXT_COUNT && (
                <li className="tv-dim">{t('queue.more', { n: group.waiting.length - NEXT_COUNT })}</li>
              )}
            </ul>
          </section>
        ))}
      </main>
    </div>
  );
}
