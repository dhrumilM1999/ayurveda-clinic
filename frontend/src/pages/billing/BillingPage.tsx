// Billing: all bills of the branch (OPD and pharmacy), payments, cancel / refund, and the day closing.
// "New OPD bill" is for a patient without an appointment today (e.g. only a dressing or a certificate).
import { PlusOutlined } from '@ant-design/icons';
import { Button, Form, Modal, Select, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../api/client';
import type { AppointmentDoctor } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { PatientPicker } from '../appointments/shared';
import { BillsTab } from '../pharmacy/BillsTab';
import { OpdBillModal, type OpdBillTarget } from './OpdBillModal';

export default function BillingPage() {
  const { t } = useTranslation();
  const { can } = useAuth();
  const [choose, setChoose] = useState(false);
  const [target, setTarget] = useState<OpdBillTarget | null>(null);
  const [version, setVersion] = useState(0);

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('billing.title')}</Typography.Title>
          <div className="cell-sub">{t('billing.subtitle')}</div>
        </div>
        {(can('billing.charge') || can('billing.create')) && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setChoose(true)}>{t('billing.newOpdBill')}</Button>
        )}
      </div>
      <BillsTab series="all" seriesFilter version={version} />
      {choose && <ChoosePatient onClose={(picked) => { setChoose(false); if (picked) setTarget(picked); }} />}
      {target && <OpdBillModal target={target} onClose={(changed) => { setTarget(null); if (changed) setVersion((v) => v + 1); }} />}
    </>
  );
}

function ChoosePatient({ onClose }: { onClose: (target: OpdBillTarget | null) => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [doctors, setDoctors] = useState<AppointmentDoctor[]>([]);
  useEffect(() => {
    api.get<AppointmentDoctor[]>('/appointments/doctors/').then(({ data }) => setDoctors(data)).catch(() => setDoctors([]));
  }, []);
  const next = async () => {
    const v = await form.validateFields();
    onClose({ patient: v.patient, doctor: v.doctor });
  };
  return (
    <Modal open width={520} title={t('billing.newOpdBill')} onCancel={() => onClose(null)} onOk={next}
      okText={t('opd.next')} cancelText={t('common.cancel')} keyboard={false} maskClosable={false} destroyOnHidden>
      <div className="form-help">{t('billing.newOpdBillHelp')}</div>
      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item name="patient" label={t('appointments.patient')} rules={[{ required: true, message: t('common.required') }]}>
          <PatientPicker />
        </Form.Item>
        <Form.Item name="doctor" label={t('appointments.doctor')} extra={t('billing.doctorOptional')}>
          <Select allowClear options={doctors.map((d) => ({ value: d.id, label: d.full_name }))} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
