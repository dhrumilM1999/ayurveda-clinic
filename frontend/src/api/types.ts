// Shapes of the data that comes back from the backend API.

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface MyBranch {
  id: string;
  name: string;
  code: string;
  role: { code: string; name: string } | null;
  permissions: string[];
}

export interface Me {
  user: {
    id: string;
    username: string;
    full_name: string;
    is_org_admin: boolean;
    is_doctor: boolean;
    preferred_language: string;
  };
  organization: { id: string; name: string; multi_branch: boolean } | null;
  branches: MyBranch[];
  idle_timeout_minutes: number;
}

export interface Branch {
  id: string;
  name: string;
  code: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
  email: string;
  gstin: string;
  is_active: boolean;
}

export interface RoomType {
  id: string;
  name: string;
  is_active: boolean;
  sort_order: number;
}

export interface Room {
  id: string;
  name: string;
  room_type: string | null;
  room_type_name: string;
  capacity: number;
  notes: string;
  is_active: boolean;
}

export interface Role {
  id: string;
  name: string;
  code: string;
  description: string;
  permissions: string[];
  requires_2fa: boolean;
  is_system: boolean;
  user_count: number;
}

export interface PermissionInfo {
  code: string;
  label: string;
  group: string;
}

export interface BranchRole {
  branch: string;
  role: string;
  branch_name?: string;
  role_name?: string;
}

export interface Staff {
  id: string;
  username: string;
  full_name: string;
  email: string;
  phone: string;
  preferred_language: string;
  designation: string;
  is_doctor: boolean;
  qualification: string;
  registration_number: string;
  is_org_admin: boolean;
  is_active: boolean;
  last_login: string | null;
  branch_roles: BranchRole[];
}

export interface DoctorSchedule {
  id: string;
  doctor: string;
  doctor_name: string;
  weekday: number;
  start_time: string;
  end_time: string;
  slot_minutes: number;
  is_active: boolean;
}

export interface FeatureFlag {
  code: string;
  label: string;
  enabled: boolean;
}

export interface AuditLogEntry {
  id: string;
  created_at: string;
  branch_name: string;
  username: string;
  action: string;
  object_type: string;
  object_id: string;
  object_repr: string;
  changes: Record<string, unknown>;
  ip_address: string | null;
}

// --- Patients (Step 2) ---------------------------------------------------------
export interface MasterRef {
  id: string;
  code: string;
  label: string;
  label_gu: string;
  label_hi: string;
}

export interface MasterValue extends MasterRef {
  category: string;
  sort_order: number;
  is_active: boolean;
}

export interface PatientListItem {
  id: string;
  uhid: string;
  title: MasterRef | null;
  full_name: string;
  first_name: string;
  last_name: string;
  gender: 'male' | 'female' | 'other';
  age_years: number | null;
  mobile_masked: string;
  city: string;
  registration_date: string;
  registered_branch_name: string;
  is_vip: boolean;
  is_foc: boolean;
  has_photo: boolean;
  allergy_count: number;
}

export interface PatientCondition {
  id?: string;
  condition: MasterRef | string;
  since: string;
  notes: string;
}

export interface PatientAllergy {
  id?: string;
  allergy_type: MasterRef | string | null;
  allergen: string;
  severity: 'mild' | 'moderate' | 'severe';
  reaction: string;
}

export interface PatientMedication {
  id?: string;
  name: string;
  dose: string;
  frequency: string;
  since: string;
  notes: string;
}

export interface Patient {
  id: string;
  uhid: string;
  registration_date: string;
  registered_branch_name: string;
  has_photo: boolean;
  title: MasterRef | null;
  first_name: string;
  middle_name: string;
  last_name: string;
  full_name: string;
  date_of_birth: string | null;
  dob_is_estimated: boolean;
  age_years: number | null;
  gender: 'male' | 'female' | 'other';
  blood_group: MasterRef | null;
  marital_status: MasterRef | null;
  preferred_language: string;
  occupation: string;
  guardian_name: string;
  country_code: string;
  mobile: string;
  alternate_mobile: string;
  email: string;
  house: string;
  society: string;
  area: string;
  pincode: string;
  city: string;
  state: string;
  country: string;
  referral_source: MasterRef | null;
  referred_by_name: string;
  referred_by_phone: string;
  emergency_name: string;
  emergency_relation: MasterRef | null;
  emergency_phone: string;
  is_vip: boolean;
  is_foc: boolean;
  past_history?: string;
  family_history?: string;
  surgical_history?: string;
  other_notes?: string;
  conditions?: PatientCondition[];
  allergies: PatientAllergy[];
  medications: PatientMedication[];
  medical_history_hidden?: boolean;
  created_at: string;
  created_by_name: string;
}

export interface DuplicatePatient {
  id: string;
  uhid: string;
  full_name: string;
  gender: string;
  age_years: number | null;
  mobile_masked: string;
  city: string;
}

export interface Vital {
  id: string;
  recorded_at: string;
  bp_systolic: number | null;
  bp_diastolic: number | null;
  pulse: number | null;
  temperature_f: string | null;
  spo2: number | null;
  respiratory_rate: number | null;
  weight_kg: string | null;
  height_cm: string | null;
  bmi: string | null;
  notes: string;
  branch_name: string;
  recorded_by_name: string;
}

export interface PatientDocument {
  id: string;
  document_type: MasterRef | null;
  title: string;
  document_date: string | null;
  notes: string;
  original_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  uploaded_by_name: string;
  branch_name: string;
}

export interface ConsentPurpose {
  id: string;
  code: string;
  title: string;
  title_gu: string;
  title_hi: string;
  description: string;
  description_gu: string;
  description_hi: string;
  is_required: boolean;
  version: number;
}

export interface ConsentStatus {
  purpose: ConsentPurpose;
  granted: boolean | null;
  since: string | null;
  outdated: boolean;
}

export interface ConsentRecord {
  id: string;
  purpose_code: string;
  purpose_title: string;
  purpose_version: number;
  granted: boolean;
  method: string;
  language: string;
  given_by: string;
  notes: string;
  created_at: string;
  recorded_by_name: string;
  branch_name: string;
}

// --- Appointments (Step 3) ---
export type AppointmentStatus = 'booked' | 'checked_in' | 'in_consultation' | 'completed' | 'cancelled' | 'no_show';

export interface AppointmentPatient {
  id: string;
  uhid: string;
  full_name: string;
  first_name: string;
  last_name: string;
  gender: string;
  age_years: number | null;
  mobile_masked: string;
  is_vip: boolean;
}

/** What happened with the SMS / WhatsApp message after booking, check-in, etc. */
export interface PatientNotification {
  consent: boolean;
  sms_sent: boolean;
  whatsapp_link: string;
  message: string;
}

export interface Appointment {
  id: string;
  patient: string;
  patient_detail: AppointmentPatient;
  doctor: string;
  doctor_name: string;
  branch: string;
  branch_name: string;
  date: string;
  start_time: string | null;
  end_time: string | null;
  kind: 'booked' | 'walk_in';
  status: AppointmentStatus;
  token_number: number | null;
  reason: string;
  notes: string;
  checked_in_at: string | null;
  consultation_started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string;
  reschedule_count: number;
  created_at: string;
  notification?: PatientNotification;
}

export interface Slot {
  start: string;
  end: string;
  status: 'free' | 'booked' | 'past';
}

export interface AppointmentDoctor {
  id: string;
  full_name: string;
  sits: boolean;
  timings: string[];
  active_count: number;
}

export interface QueueItem {
  id: string;
  token_number: number | null;
  status: AppointmentStatus;
  kind: 'booked' | 'walk_in';
  start_time: string | null;
  checked_in_at: string | null;
  consultation_started_at: string | null;
  patient_detail: AppointmentPatient;
  display_name: string;
  reason: string;
}

export interface QueueGroup {
  doctor: string;
  doctor_name: string;
  now: QueueItem[];
  waiting: QueueItem[];
  booked_count: number;
  done_count: number;
}

export interface QueueData {
  date: string;
  branch_name: string;
  server_time: string;
  doctors: QueueGroup[];
}
