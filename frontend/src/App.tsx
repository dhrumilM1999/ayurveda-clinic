// The list of screens (routes). To add a screen: add a <Route> here and an item in config/menu.tsx.
import { App as AntApp, ConfigProvider, Spin } from 'antd';
import enUS from 'antd/locale/en_US';
import hiIN from 'antd/locale/hi_IN';
import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { RequirePermission } from './components/RequirePermission';
import MainLayout from './layout/MainLayout';
import AppointmentsPage from './pages/appointments/AppointmentsPage';
import QueueDisplayPage from './pages/appointments/QueueDisplayPage';
import QueuePage from './pages/appointments/QueuePage';
import AuditLogPage from './pages/AuditLogPage';
import ConsultPage from './pages/consult/ConsultPage';
import MedicinesPage from './pages/medicines/MedicinesPage';
import PharmacyPage from './pages/pharmacy/PharmacyPage';
import BranchesPage from './pages/BranchesPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';
import PatientDetailPage from './pages/patients/PatientDetailPage';
import PatientFormPage from './pages/patients/PatientFormPage';
import PatientsPage from './pages/patients/PatientsPage';
import RolesPage from './pages/RolesPage';
import RoomsPage from './pages/RoomsPage';
import SchedulesPage from './pages/SchedulesPage';
import SettingsPage from './pages/SettingsPage';
import AdditionalSettingsPage from './pages/AdditionalSettingsPage';
import FeesServicesPage from './pages/FeesServicesPage';
import BillingPage from './pages/billing/BillingPage';
import ReportsPage from './pages/ReportsPage';
import VerifyPage from './pages/VerifyPage';
import StaffPage from './pages/StaffPage';
import TemplatesPage from './pages/TemplatesPage';
import { antTheme, applyCssVariables } from './theme';

applyCssVariables();

export default function App() {
  const { me, loading } = useAuth();
  const { i18n } = useTranslation();

  return (
    <ConfigProvider theme={antTheme} locale={i18n.language === 'hi' ? hiIN : enUS}>
      <AntApp>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '30vh' }}>
            <Spin size="large" />
          </div>
        ) : !me ? (
          <Routes>
            {/* Public: the QR code on print-outs opens this without logging in */}
            <Route path="verify/:token" element={<VerifyPage />} />
            <Route path="*" element={<LoginPage />} />
          </Routes>
        ) : (
          <Routes>
            <Route path="verify/:token" element={<VerifyPage />} />
            {/* TV screen for the waiting room: full screen, without the menu */}
            <Route path="queue/display" element={<RequirePermission code="appointments.view"><QueueDisplayPage /></RequirePermission>} />
            <Route element={<MainLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="patients" element={<RequirePermission code="patients.view"><PatientsPage /></RequirePermission>} />
              <Route path="patients/new" element={<RequirePermission code="patients.create"><PatientFormPage /></RequirePermission>} />
              <Route path="patients/:id" element={<RequirePermission code="patients.view"><PatientDetailPage /></RequirePermission>} />
              <Route path="patients/:id/edit" element={<RequirePermission code="patients.edit"><PatientFormPage key="edit" /></RequirePermission>} />
              <Route path="appointments" element={<RequirePermission code="appointments.view"><AppointmentsPage /></RequirePermission>} />
              <Route path="consult" element={<RequirePermission code="emr.view"><ConsultPage /></RequirePermission>} />
              <Route path="consult/:visitId" element={<RequirePermission code="emr.view"><ConsultPage /></RequirePermission>} />
              <Route path="medicines" element={<RequirePermission code="medicines.view"><MedicinesPage /></RequirePermission>} />
              <Route path="billing" element={<RequirePermission code="billing.view"><BillingPage /></RequirePermission>} />
              <Route path="reports" element={<RequirePermission code="reports.view"><ReportsPage /></RequirePermission>} />
              <Route path="pharmacy"element={<RequirePermission code="pharmacy.view"><PharmacyPage /></RequirePermission>} />
              <Route path="queue" element={<RequirePermission code="appointments.view"><QueuePage /></RequirePermission>} />
              <Route path="branches" element={<RequirePermission code="branches.view"><BranchesPage /></RequirePermission>} />
              <Route path="rooms" element={<RequirePermission code="rooms.view"><RoomsPage /></RequirePermission>} />
              <Route path="staff" element={<RequirePermission code="staff.view"><StaffPage /></RequirePermission>} />
              <Route path="roles" element={<RequirePermission code="roles.view"><RolesPage /></RequirePermission>} />
              <Route path="schedules" element={<RequirePermission code="schedules.view"><SchedulesPage /></RequirePermission>} />
              <Route path="templates" element={<RequirePermission code="settings.manage"><TemplatesPage /></RequirePermission>} />
              <Route path="fees-services" element={<RequirePermission code="billing.manage"><FeesServicesPage /></RequirePermission>} />
              <Route path="settings" element={<RequirePermission code="settings.manage"><SettingsPage /></RequirePermission>} />
              <Route path="additional-settings" element={<RequirePermission code="settings.manage"><AdditionalSettingsPage /></RequirePermission>} />
              <Route path="audit-log" element={<RequirePermission code="audit.view"><AuditLogPage /></RequirePermission>} />
              <Route path="login" element={<Navigate to="/" replace />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        )}
      </AntApp>
    </ConfigProvider>
  );
}
