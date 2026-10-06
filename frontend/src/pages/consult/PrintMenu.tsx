// "Print" menu on the check-up screen: prescription, detailed prescription (full check-up summary),
// follow-up card, Prakriti report, certificate, and
// WhatsApp share of the prescription. Unsaved changes are saved first, so the print-out is up to date.
// Everything opens in a popup on the same screen.
import { DownOutlined, PrinterOutlined } from '@ant-design/icons';
import { App, Button, DatePicker, Dropdown, Form, Input, Modal, Segmented, Select } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { AppointmentDoctor } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { DocumentModal } from '../../components/BillPreview';

type Open = { kind: 'prescription' | 'follow-up-card' | 'prakriti' | 'certificate'; id: string; title: string; detail?: boolean } | null;

export function PrintMenu({ visitId, rxId, hasFollowUp, patientName, language, doctorId, diagnoses, beforePrint }: {
  visitId: string;
  rxId?: string;
  hasFollowUp: boolean;
  patientName: string;
  language?: string;
  doctorId: string;
  diagnoses: string[];
  /** Save unsaved changes first; false = saving failed */
  beforePrint: () => Promise<boolean>;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [open, setOpen] = useState<Open>(null);
  const [certificate, setCertificate] = useState(false);

  const show = async (next: NonNullable<Open>) => {
    if (await beforePrint()) setOpen(next);
  };

  const share = async () => {
    if (!rxId || !(await beforePrint())) return;
    try {
      const { data } = await api.post<{ consent: boolean; link: string }>(`/documents/prescription/${rxId}/whatsapp/`);
      if (!data.consent) message.warning(t('print.noConsent'));
      else if (data.link) window.open(data.link, '_blank', 'noopener');
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  };

  const items = [
    { key: 'prescription', label: t('print.prescription'), disabled: !rxId },
    ...(can('emr.view') ? [{ key: 'prescription-detailed', label: t('print.prescriptionDetailed'), disabled: !rxId }] : []),
    { key: 'follow-up-card', label: t('print.followUpCard'), disabled: !hasFollowUp },
    { key: 'prakriti', label: t('print.prakriti') },
    ...(can('emr.edit') ? [{ key: 'certificate', label: t('print.certificate') }] : []),
    { type: 'divider' as const },
    { key: 'whatsapp', label: t('print.whatsapp'), disabled: !rxId },
  ];

  const onClick = ({ key }: { key: string }) => {
    if (key === 'prescription' && rxId) show({ kind: 'prescription', id: rxId, title: t('print.prescriptionOf', { name: patientName }) });
    if (key === 'prescription-detailed' && rxId) {
      show({ kind: 'prescription', id: rxId, title: t('print.prescriptionDetailedOf', { name: patientName }), detail: true });
    }
    if (key === 'follow-up-card') show({ kind: 'follow-up-card', id: visitId, title: t('print.followUpCard') });
    if (key === 'prakriti') show({ kind: 'prakriti', id: visitId, title: t('print.prakriti') });
    if (key === 'certificate') beforePrint().then((ok) => ok && setCertificate(true));
    if (key === 'whatsapp') share();
  };

  return (
    <>
      <Dropdown trigger={['click']} menu={{ items, onClick }}>
        <Button size="small" icon={<PrinterOutlined />}>{t('print.menu')} <DownOutlined /></Button>
      </Dropdown>
      {open && <DocumentModal kind={open.kind} id={open.id} title={open.title} language={language} detail={open.detail} onClose={() => setOpen(null)} />}
      {certificate && (
        <CertificateModal visitId={visitId} doctorId={doctorId} diagnoses={diagnoses}
          onClose={(id) => { setCertificate(false); if (id) setOpen({ kind: 'certificate', id, title: t('print.certificate') }); }} />
      )}
    </>
  );
}

type Kind = 'medical' | 'fitness' | 'general';

function CertificateModal({ visitId, doctorId, diagnoses, onClose }: {
  visitId: string;
  doctorId: string;
  diagnoses: string[];
  onClose: (certificateId?: string) => void;
}) {
  const { t } = useTranslation();
  const { message, modal } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [doctors, setDoctors] = useState<AppointmentDoctor[]>([]);
  const [patientId, setPatientId] = useState<string>();
  const kind: Kind = Form.useWatch('kind', form) ?? 'medical';

  useEffect(() => {
    api.get<{ patient: string }>(`/visits/${visitId}/`).then(({ data }) => setPatientId(data.patient)).catch(() => undefined);
    api.get<AppointmentDoctor[]>('/appointments/doctors/').then(({ data }) => setDoctors(data)).catch(() => setDoctors([]));
  }, [visitId]);

  const save = async () => {
    const v = await form.validateFields();
    const day = (d?: Dayjs) => (d ? d.format('YYYY-MM-DD') : null);
    modal.confirm({
      title: t('opd.confirmTitle'), content: t('print.certificateConfirm'), okText: t('common.yes'), cancelText: t('common.no'),
      onOk: async () => {
        setSaving(true);
        try {
          const { data } = await api.post<{ id: string }>('/certificates/', {
            patient: patientId, doctor: v.doctor, visit: visitId, kind: v.kind, diagnosis: v.diagnosis ?? '',
            rest_from: v.kind === 'medical' ? day(v.rest?.[0]) : null, rest_to: v.kind === 'medical' ? day(v.rest?.[1]) : null,
            fit_from: v.kind === 'fitness' ? day(v.fit_from) : null, remarks: v.remarks ?? '',
          });
          onClose(data.id);
        } catch (err) {
          message.error(errorMessage(err, t('common.saveFailed')));
        } finally {
          setSaving(false);
        }
      },
    });
  };

  return (
    <Modal open width={560} title={t('print.certificate')} onCancel={() => onClose()} onOk={save} confirmLoading={saving}
      okText={t('print.makeCertificate')} cancelText={t('common.cancel')} keyboard={false} maskClosable={false} destroyOnHidden>
      <div className="form-help">{t('print.certificateHelp')}</div>
      <Form form={form} layout="vertical" requiredMark={false}
        initialValues={{ kind: 'medical', doctor: doctorId, diagnosis: diagnoses.join(', '), rest: [dayjs(), dayjs().add(2, 'day')], fit_from: dayjs() }}>
        <Form.Item name="kind">
          <Segmented options={(['medical', 'fitness', 'general'] as const).map((k) => ({ value: k, label: t(`print.certificateKinds.${k}`) }))} />
        </Form.Item>
        <Form.Item name="doctor" label={t('appointments.doctor')} rules={[{ required: true, message: t('common.required') }]}>
          <Select options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} />
        </Form.Item>
        <Form.Item name="diagnosis" label={t('print.diagnosis')}><Input maxLength={300} /></Form.Item>
        {kind === 'medical' && (
          <Form.Item name="rest" label={t('print.restDates')} rules={[{ required: true, message: t('common.required') }]}>
            <DatePicker.RangePicker format="DD-MM-YYYY" style={{ width: '100%' }} />
          </Form.Item>
        )}
        {kind === 'fitness' && (
          <Form.Item name="fit_from" label={t('print.fitFrom')} rules={[{ required: true, message: t('common.required') }]}>
            <DatePicker format="DD-MM-YYYY" style={{ width: '100%' }} />
          </Form.Item>
        )}
        <Form.Item name="remarks" label={t('print.remarks')}><Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} maxLength={500} /></Form.Item>
      </Form>
    </Modal>
  );
}
