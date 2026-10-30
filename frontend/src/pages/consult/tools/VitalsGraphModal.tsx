// "Graph" window of the check-up screen: the patient's vital signs drawn as small line charts (weight, pulse, BP ...).
// Tick the vital signs to show, pick how far back to look. The readings come from "Record vitals" (Vitals tab).
// SAFE TO EDIT: the words are in src/i18n/*.json under "consultTools"; which vital signs and ranges are offered is in vitalsSeries.ts.
import { Checkbox, Empty, Modal, Segmented, Skeleton } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../../api/client';
import type { Vital } from '../../../api/types';
import { RANGES, VITAL_KEYS, chartPoints, rangeStart, seriesFor, type VitalKey } from './vitalsSeries';

const W = 360;
const H = 130;
const START: VitalKey[] = ['weight_kg', 'pulse', 'temperature_f', 'spo2'];

export function VitalsGraphModal({ patientId, patientName, onClose }: { patientId: string; patientName: string; onClose: () => void }) {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Vital[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [shown, setShown] = useState<VitalKey[]>(START);
  const [range, setRange] = useState('6m');

  useEffect(() => {
    api.get<Vital[]>('/patient-vitals/', { params: { patient: patientId } })
      .then(({ data }) => setRows(data)).catch(() => setFailed(true));
  }, [patientId]);

  const from = useMemo(() => rangeStart(RANGES.find((r) => r.id === range)?.months ?? 0, Date.now()), [range]);

  return (
    <Modal open onCancel={onClose} footer={null} width={1000} centered destroyOnHidden
      title={t('consultTools.graphTitle', { name: patientName })}>
      {failed && <Empty description={t('common.loadFailed')} />}
      {!failed && rows === null && <Skeleton active />}
      {rows !== null && (
        <div className="vg-layout">
          <div className="vg-side">
            <div className="cell-sub" style={{ marginBottom: 6 }}>{t('consultTools.graphShow')}</div>
            <Checkbox.Group value={shown} onChange={(v) => setShown(v as VitalKey[])} className="vg-checks">
              {VITAL_KEYS.map((v) => <Checkbox key={v.key} value={v.key}>{t(`consultTools.vital.${v.key}`)}</Checkbox>)}
            </Checkbox.Group>
          </div>
          <div className="vg-main">
            <Segmented value={range} onChange={(v) => setRange(String(v))} style={{ marginBottom: 10 }}
              options={RANGES.map((r) => ({ value: r.id, label: t(`consultTools.range.${r.id}`) }))} />
            {rows.length === 0 && <Empty description={t('vitals.none')} />}
            <div className="vg-grid">
              {VITAL_KEYS.filter((v) => shown.includes(v.key)).map((v) => {
                const series = seriesFor(rows, v.key, from);
                const pts = chartPoints(series, W, H);
                const last = series[series.length - 1];
                return (
                  <div className="vg-card" key={v.key}>
                    <div className="vg-card-head">
                      <b>{t(`consultTools.vital.${v.key}`)}</b>
                      <span className="cell-sub">{v.unit}</span>
                      {last && <span className="vg-last">{last.value}</span>}
                    </div>
                    {series.length === 0 ? (
                      <div className="cell-sub vg-empty">{t('consultTools.graphNone')}</div>
                    ) : (
                      <>
                        <svg viewBox={`0 0 ${W} ${H}`} className="vg-svg" role="img" aria-label={t(`consultTools.vital.${v.key}`)}>
                          <line x1="0" y1={H - 1} x2={W} y2={H - 1} className="vg-axis" />
                          {pts.length > 1 && <polyline className="vg-line" points={pts.map((p) => `${p.x},${p.y}`).join(' ')} />}
                          {pts.map((p, i) => (
                            <circle key={series[i].at} cx={p.x} cy={p.y} r="3.5" className="vg-dot">
                              <title>{`${dayjs(series[i].at).format('DD-MM-YYYY')}: ${series[i].value} ${v.unit}`}</title>
                            </circle>
                          ))}
                        </svg>
                        <div className="vg-dates cell-sub">
                          <span>{dayjs(series[0].at).format('DD-MM-YYYY')}</span>
                          <span>{series.length > 1 ? dayjs(series[series.length - 1].at).format('DD-MM-YYYY') : ''}</span>
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
