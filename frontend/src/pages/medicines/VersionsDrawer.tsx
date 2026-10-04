// Version history of one medicine: what changed, when and by whom.
import { Drawer, Empty, Spin, Tag, Timeline } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { Medicine, MedicineVersion } from '../../api/types';

function show(value: unknown, t: (k: string) => string) {
  if (value === true) return t('common.yes');
  if (value === false) return t('common.no');
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

export function VersionsDrawer({ medicine, onClose }: { medicine: Medicine; onClose: () => void }) {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<MedicineVersion[] | null>(null);

  useEffect(() => {
    api.get<MedicineVersion[]>(`/medicines/${medicine.id}/versions/`).then(({ data }) => setVersions(data)).catch(() => setVersions([]));
  }, [medicine.id]);

  return (
    <Drawer open width={460} title={t('medicines.historyTitle', { name: medicine.name })} onClose={onClose}>
      <div className="cell-sub" style={{ marginBottom: 12 }}>{t('medicines.historyHelp')}</div>
      {versions === null && <Spin />}
      {versions?.length === 0 && <Empty />}
      {versions && versions.length > 0 && (
        <Timeline
          items={versions.map((v, i) => {
            const older = versions[i + 1];
            const changed = older ? Object.keys(v.data).filter((k) => JSON.stringify(v.data[k]) !== JSON.stringify(older.data[k])) : [];
            return {
              color: i === 0 ? 'green' : 'gray',
              children: (
                <div>
                  <div><Tag className="tag-tight">v{v.version}</Tag> <b>{dayjs(v.created_at).format('DD-MM-YYYY HH:mm')}</b></div>
                  <div className="cell-sub">{v.created_by_name || t('medicines.system')}</div>
                  {older ? (
                    <ul className="change-list">
                      {changed.map((k) => (
                        <li key={k}><b>{t(`medicines.fields.${k}`, { defaultValue: k })}:</b> {show(older.data[k], t)} → {show(v.data[k], t)}</li>
                      ))}
                    </ul>
                  ) : <div className="cell-sub">{t('medicines.firstVersion')}</div>}
                </div>
              ),
            };
          })}
        />
      )}
    </Drawer>
  );
}
