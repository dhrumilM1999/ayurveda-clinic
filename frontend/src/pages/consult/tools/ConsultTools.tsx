// The quick-tool buttons in the check-up header: + Appt, + Patient, Send Order, Patient Report, Graph (as in Healthray).
// Send Order (a lab order slip) is shown only when Additional settings -> "Lab test order slip" is on: most clinics have no lab connected.
// Each opens its own window; nothing here changes the check-up itself.
// SAFE TO EDIT: the words are in src/i18n/*.json under "consultTools".
import { BarChartOutlined, CalendarOutlined, ExperimentOutlined, FileTextOutlined, UserAddOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../../auth/AuthContext';
import { BookAppointmentModal } from '../../appointments/BookAppointmentModal';
import { PatientReportModal } from './PatientReportModal';
import { SendOrderModal } from './SendOrderModal';
import { VitalsGraphModal } from './VitalsGraphModal';

type Tool = 'appt' | 'order' | 'report' | 'graph' | null;

export function ConsultTools({ patientId, patientName, uhid, visitId }: { patientId: string; patientName: string; uhid: string; visitId: string }) {
  const { t } = useTranslation();
  const { can, hasFeature } = useAuth();
  const [tool, setTool] = useState<Tool>(null);

  return (
    <>
      {can('appointments.manage') && (
        <Button size="small" icon={<CalendarOutlined />} onClick={() => setTool('appt')}>{t('consultTools.addAppt')}</Button>
      )}
      {can('patients.create') && (
        // a new patient is registered in a new browser tab, so this check-up stays open and keeps saving
        <Button size="small" icon={<UserAddOutlined />} onClick={() => window.open('/patients/new', '_blank', 'noopener')}>
          {t('consultTools.addPatient')}
        </Button>
      )}
      {can('emr.view') && (
        <>
          {hasFeature('lab_orders') && (
            <Button size="small" icon={<ExperimentOutlined />} onClick={() => setTool('order')}>{t('consultTools.sendOrder')}</Button>
          )}
          <Button size="small" icon={<FileTextOutlined />} onClick={() => setTool('report')}>{t('consultTools.patientReport')}</Button>
          <Button size="small" icon={<BarChartOutlined />} onClick={() => setTool('graph')}>{t('consultTools.graph')}</Button>
        </>
      )}
      <BookAppointmentModal open={tool === 'appt'} kind="booked" patient={{ id: patientId, label: `${patientName} · ${uhid}` }}
        onClose={() => setTool(null)} />
      {tool === 'order' && <SendOrderModal visitId={visitId} patientId={patientId} patientName={patientName} onClose={() => setTool(null)} />}
      {tool === 'report' && <PatientReportModal patientId={patientId} patientName={patientName} onClose={() => setTool(null)} />}
      {tool === 'graph' && <VitalsGraphModal patientId={patientId} patientName={patientName} onClose={() => setTool(null)} />}
    </>
  );
}
