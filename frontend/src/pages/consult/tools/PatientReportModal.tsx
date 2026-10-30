// "Patient Report" window of the check-up screen: what was written at the patient's check-ups between two dates.
// Pick the dates, tick the parts to show (complaints, diagnosis, medicines ...). Newest check-up first, all branches.
// SAFE TO EDIT: the words are in src/i18n/*.json under "consultTools"; the list of parts is PARTS below.
import { Checkbox, DatePicker, Empty, Modal, Skeleton, Space } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import type { PatientReportVisit } from '../../../api/types';

export const PARTS = ['complaints', 'history', 'examination', 'diagnosis', 'rx', 'investigations', 'advice', 'followUp'] as const;
type Part = (typeof PARTS)[number];

/** Does this check-up have anything to show for this part? (so empty parts are not printed as blank headings) */
export function hasPart(v: PatientReportVisit, part: Part): boolean {
  switch (part) {
    case 'complaints': return v.complaints.length > 0;
    case 'history': return !!v.history_notes.trim();
    case 'examination': return !!v.examination_notes.trim();
    case 'diagnosis': return v.diagnoses.length > 0;
    case 'rx': return v.rx.length > 0;
    case 'investigations': return v.investigations.length > 0;
    case 'advice': return v.advice.length > 0 || !!v.advice_notes.trim();
    case 'followUp': return !!v.follow_up_date;
  }
}

export function PatientReportModal({ patientId, patientName, onClose }: { patientId: string; patientName: string; onClose: () => void }) {
  const { t } = useTranslation();
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs().subtract(6, 'month'), dayjs()]);
  const [parts, setParts] = useState<Part[]>([...PARTS]);
  const [rows, setRows] = useState<PatientReportVisit[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setRows(null);
    setError('');
    api.get<PatientReportVisit[]>('/visits/report/', {
      params: { patient: patientId, from: range[0].format('YYYY-MM-DD'), to: range[1].format('YYYY-MM-DD') },
    }).then(({ data }) => setRows(data)).catch((err) => setError(errorMessage(err, t('common.loadFailed'))));
  }, [patientId, range, t]);

  return (
    <Modal open onCancel={onClose} footer={null} width={900} centered destroyOnHidden
      title={t('consultTools.reportTitle', { name: patientName })}>
      <Space wrap style={{ marginBottom: 10 }}>
        <DatePicker.RangePicker allowClear={false} format="DD-MM-YYYY" value={range} disabledDate={(d) => d.isAfter(dayjs(), 'day')}
          onChange={(v) => { if (v?.[0] && v[1]) setRange([v[0], v[1]]); }} />
      </Space>
      <div style={{ marginBottom: 12 }}>
        <Checkbox.Group value={parts} onChange={(v) => setParts(v as Part[])}
          options={PARTS.map((p) => ({ value: p, label: t(`consultTools.part.${p}`) }))} />
      </div>
      {error && <Empty description={error} />}
      {!error && rows === null && <Skeleton active />}
      {rows !== null && rows.length === 0 && <Empty description={t('consultTools.reportNone')} />}
      <div className="pr-list">
        {rows?.map((v) => (
          <div className="pr-visit" key={v.id}>
            <div className="pr-head">
              <b>{dayjs(v.visit_date).format('DD-MM-YYYY')}</b>
              <span className="cell-sub">{[v.doctor_name, v.branch_name].filter(Boolean).join(' · ')}</span>
              {v.status === 'draft' && <span className="cell-sub">{t('consultTools.notCompleted')}</span>}
            </div>
            {PARTS.filter((p) => parts.includes(p) && hasPart(v, p)).map((p) => (
              <div className="pr-part" key={p}>
                <span className="pr-label">{t(`consultTools.part.${p}`)}</span>
                <div>
                  {p === 'complaints' && v.complaints.join(', ')}
                  {p === 'history' && v.history_notes}
                  {p === 'examination' && v.examination_notes}
                  {p === 'diagnosis' && <b>{v.diagnoses.join(', ')}</b>}
                  {p === 'rx' && (
                    <ul className="pr-rx">
                      {v.rx.map((r, i) => (
                        <li key={`${r.medicine}-${i}`}>{[r.medicine, r.dose, r.frequency, r.timing, r.duration].filter(Boolean).join(' · ')}</li>
                      ))}
                    </ul>
                  )}
                  {p === 'investigations' && v.investigations.map((x) => `${x.test} (${t(`investigations.status.${x.status}`, { defaultValue: x.status })})`).join(', ')}
                  {p === 'advice' && [v.advice.join(', '), v.advice_notes].filter(Boolean).join(' — ')}
                  {p === 'followUp' && dayjs(v.follow_up_date).format('DD-MM-YYYY')}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </Modal>
  );
}
