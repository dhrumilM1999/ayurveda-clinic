// Medicine days and follow-up days on the check-up screen.
// Choosing medicine days also sets the follow-up to the same number of days - unless the doctor has
// changed the follow-up separately. Changing the follow-up never changes the medicine days.
import { LinkOutlined } from '@ant-design/icons';
import { Button, InputNumber, Space, Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import { DAY_CHOICES } from '../../utils/dosage';

export function DaysChips({ value, onChange, disabled }: { value: number | null; onChange: (days: number | null) => void; disabled?: boolean }) {
  const { t } = useTranslation();
  const custom = value !== null && !DAY_CHOICES.includes(value);
  return (
    <Space size={4} wrap>
      {DAY_CHOICES.map((d) => (
        <Button key={d} size="small" type={value === d ? 'primary' : 'default'} disabled={disabled}
          onClick={() => onChange(value === d ? null : d)}>{t('rx.daysShort', { n: d })}</Button>
      ))}
      <InputNumber size="small" min={1} max={3650} precision={0} disabled={disabled} placeholder={t('rx.customDays')}
        value={custom ? value : undefined} style={{ width: 96 }} suffix={t('rx.daysUnit')}
        onChange={(v) => onChange(v ? Number(v) : null)} />
    </Space>
  );
}

export function DaysBar({ medicineDays, followUpDays, onMedicineDays, onFollowUpDays, readOnly, followUpReadOnly }: {
  medicineDays: number | null;
  followUpDays: number | null;
  onMedicineDays: (days: number | null) => void;
  onFollowUpDays: (days: number | null) => void;
  readOnly?: boolean;
  followUpReadOnly?: boolean;
}) {
  const { t } = useTranslation();
  const linked = medicineDays !== null && followUpDays === medicineDays;
  return (
    <div className="days-bar">
      <div className="days-row">
        <span className="days-label">{t('rx.medicineDays')}</span>
        <DaysChips value={medicineDays} onChange={onMedicineDays} disabled={readOnly} />
      </div>
      <div className="days-row">
        <span className="days-label">{t('rx.followUpDays')}</span>
        <Space size={6} wrap>
          <InputNumber size="small" min={1} max={3650} precision={0} disabled={followUpReadOnly} value={followUpDays ?? undefined}
            style={{ width: 110 }} suffix={t('rx.daysUnit')} onChange={(v) => onFollowUpDays(v ? Number(v) : null)} />
          {linked ? (
            <Tooltip title={t('rx.linkedHelp')}><span className="cell-sub"><LinkOutlined /> {t('rx.sameAsMedicine')}</span></Tooltip>
          ) : medicineDays !== null && !followUpReadOnly ? (
            <Button size="small" type="link" icon={<LinkOutlined />} onClick={() => onFollowUpDays(medicineDays)}>
              {t('rx.makeSame', { n: medicineDays })}
            </Button>
          ) : null}
        </Space>
      </div>
    </div>
  );
}
