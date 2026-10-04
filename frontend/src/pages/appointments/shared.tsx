// Small pieces used by the appointment and queue screens.
import { CheckCircleFilled, MessageOutlined, WhatsAppOutlined } from '@ant-design/icons';
import { Alert, Button, Empty, Select, Space, Spin, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { AppointmentPatient, AppointmentStatus, Page, PatientListItem, PatientNotification, Slot } from '../../api/types';

/** "14:30:00" -> "2:30 PM" */
export function fmtTime(time: string | null | undefined): string {
  return time ? dayjs(`2000-01-01T${time}`).format('h:mm A') : '';
}

export const STATUS_COLORS: Record<AppointmentStatus, string> = {
  booked: 'blue',
  checked_in: 'gold',
  in_consultation: 'green',
  completed: 'default',
  cancelled: 'red',
  no_show: 'default',
};

export function StatusTag({ status }: { status: AppointmentStatus }) {
  const { t } = useTranslation();
  return <Tag color={STATUS_COLORS[status]} style={{ marginInlineEnd: 0 }}>{t(`appointments.status.${status}`)}</Tag>;
}

export function PatientCell({ patient }: { patient: AppointmentPatient }) {
  return (
    <div style={{ lineHeight: 1.35 }}>
      <Typography.Text strong>{patient.full_name}</Typography.Text>
      {patient.is_vip && <Tag color="gold" style={{ marginInlineStart: 6 }}>VIP</Tag>}
      <div className="cell-sub">
        <span className="mono">{patient.uhid}</span> · {patient.mobile_masked}
      </div>
    </div>
  );
}

/** A grid of time buttons. Booked and past times can't be chosen. */
export function SlotPicker({ slots, value, onChange, loading, emptyText }: {
  slots: Slot[];
  value?: string;
  onChange?: (start: string) => void;
  loading?: boolean;
  emptyText?: string;
}) {
  const { t } = useTranslation();
  if (loading) return <div style={{ padding: 16, textAlign: 'center' }}><Spin /></div>;
  if (!slots.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText ?? t('appointments.noSlots')} />;
  const free = slots.filter((s) => s.status === 'free').length;
  return (
    <>
      <div className="slot-grid">
        {slots.map((slot) => (
          <button
            type="button"
            key={slot.start}
            disabled={slot.status !== 'free'}
            className={`slot slot-${slot.status}${value === slot.start ? ' slot-selected' : ''}`}
            onClick={() => onChange?.(slot.start)}
            title={slot.status === 'booked' ? t('appointments.slotBooked') : undefined}
          >
            {fmtTime(slot.start)}
          </button>
        ))}
      </div>
      <div className="cell-sub" style={{ marginTop: 6 }}>{t('appointments.freeSlots', { n: free })}</div>
    </>
  );
}

/** Search a patient by name, patient ID or mobile number. */
export function PatientPicker({ value, onChange, initial }: {
  value?: string;
  onChange?: (id: string) => void;
  initial?: { id: string; label: string };
}) {
  const { t } = useTranslation();
  const [options, setOptions] = useState<{ value: string; label: ReactNode }[]>(
    initial ? [{ value: initial.id, label: initial.label }] : [],
  );
  const [searching, setSearching] = useState(false);
  const timer = useRef<number>();

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const search = (text: string) => {
    window.clearTimeout(timer.current);
    if (text.trim().length < 2) return;
    timer.current = window.setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await api.get<Page<PatientListItem>>('/patients/', { params: { q: text.trim(), page_size: 15 } });
        setOptions(data.results.map((p) => ({
          value: p.id,
          label: (
            <span>
              <b>{p.full_name}</b> <span className="cell-sub">· {p.uhid} · {p.mobile_masked}</span>
            </span>
          ),
        })));
      } finally {
        setSearching(false);
      }
    }, 300);
  };

  return (
    <Select
      showSearch
      value={value}
      onChange={onChange}
      onSearch={search}
      filterOption={false}
      options={options}
      placeholder={t('appointments.searchPatient')}
      notFoundContent={searching ? <Spin size="small" /> : t('appointments.typeToSearch')}
      disabled={!!initial}
    />
  );
}

/** After booking / check-in: what was sent, and the WhatsApp button. */
export function NotificationResult({ notification }: { notification?: PatientNotification }) {
  const { t } = useTranslation();
  if (!notification) return null;
  if (!notification.consent) {
    return <Alert type="warning" showIcon message={t('appointments.noConsent')} />;
  }
  return (
    <div className="notify-box">
      <div className="notify-text"><MessageOutlined /> {notification.message}</div>
      <Space wrap size={8} style={{ marginTop: 10 }}>
        {notification.sms_sent && (
          <Typography.Text type="success"><CheckCircleFilled /> {t('appointments.smsSent')}</Typography.Text>
        )}
        {notification.whatsapp_link && (
          <Button
            icon={<WhatsAppOutlined />}
            className="whatsapp-btn"
            href={notification.whatsapp_link}
            target="_blank"
            rel="noopener noreferrer"
          >
            {t('appointments.sendWhatsapp')}
          </Button>
        )}
      </Space>
    </div>
  );
}
