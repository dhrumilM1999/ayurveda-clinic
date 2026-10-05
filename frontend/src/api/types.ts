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
  drug_licence_no: string;
  upi_vpa: string;
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

/** An optional extra feature, switched on/off for the whole organization (Additional settings). */
export interface AdditionalFeature {
  code: string;
  group: string;
  label: string;
  /** Another additional feature this one needs ('' = none) */
  requires: string;
  /** What the admin chose */
  switched_on: boolean;
  /** Really working (switched on, and what it needs is on too) */
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

// --- Check-up / EMR (Step 4) ---
export type Lang3 = { en: string; gu: string; hi: string };

export interface ExamField {
  key: string;
  type: 'choice' | 'multi' | 'number' | 'text';
  label: Lang3;
  unit?: string;
  min?: number;
  max?: number;
  options?: { value: string; label: Lang3 }[];
}

export interface ExamTemplate {
  id: string;
  code: string;
  version: number;
  kind: 'form' | 'questionnaire';
  name: string;
  name_gu: string;
  name_hi: string;
  description: Partial<Lang3>;
  fields: ExamField[];
  sort_order: number;
  is_active?: boolean;
}

export interface PrakritiResult {
  vata?: number;
  pitta?: number;
  kapha?: number;
  type?: string;
  answered: number;
  total: number;
  visit_date?: string;
}

export interface VisitExam {
  id: string;
  template: string;
  template_code: string;
  template_version: number;
  values: Record<string, unknown>;
  result: PrakritiResult | Record<string, never>;
  /** The questions as they were when this exam was filled in */
  template_fields: ExamField[];
  updated_at: string;
}

export interface VisitPhoto {
  id: string;
  visit: string;
  visit_date: string;
  kind: 'before' | 'after' | 'progress';
  caption: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface Complaint {
  label: string;
  code?: string;
  duration?: number | null;
  duration_unit?: 'days' | 'weeks' | 'months' | 'years';
  severity?: '' | 'mild' | 'moderate' | 'severe';
  /** Symptom score 0 (none) to 10 (worst), for progress tracking */
  score?: number | null;
  notes?: string;
}

export interface Diagnosis {
  label: string;
  code?: string;
  system?: '' | 'icd10' | 'icd11' | 'namaste';
  kind: 'provisional' | 'final';
  master?: string;
}

export interface Visit {
  id: string;
  patient: string;
  patient_detail: AppointmentPatient;
  doctor: string;
  doctor_name: string;
  branch: string;
  branch_name: string;
  appointment: string | null;
  token_number: number | null;
  visit_date: string;
  status: 'draft' | 'completed';
  completed_at: string | null;
  complaints: Complaint[];
  history_notes: string;
  examination_notes: string;
  diagnoses: Diagnosis[];
  advice: string[];
  advice_notes: string;
  follow_up_date: string | null;
  follow_up_notes: string;
  exams: VisitExam[];
  photos: VisitPhoto[];
  prakriti: PrakritiResult | null;
  created_at: string;
  updated_at: string;
}

export interface VisitListItem {
  id: string;
  patient: string;
  visit_date: string;
  status: 'draft' | 'completed';
  doctor_name: string;
  branch_name: string;
  complaints: string[];
  diagnoses: string[];
  scores: Record<string, number>;
  photo_count: number;
  follow_up_date: string | null;
}

// --- Medicines and prescriptions (Step 5) ---
export type MedicineKind = 'classical' | 'proprietary';
export type MedicineFlag = 'schedule_e1' | 'contains_metals' | 'pregnancy_caution' | 'child_caution';

export interface Medicine {
  id: string;
  kind: MedicineKind;
  name: string;
  name_gu: string;
  name_hi: string;
  synonyms: string;
  generic_name: string;
  category: MasterRef | null;
  dosage_form: MasterRef | null;
  composition: string;
  pack_type: MasterRef | null;
  units_per_pack: string | null;
  allow_loose: boolean;
  selling_price: string | null;
  barcode: string;
  reference: string;
  manufacturer: string;
  classical_equivalent: string | null;
  classical_equivalent_name: string;
  ayush_licence_no: string;
  hsn_code: string;
  gst_rate: string;
  mrp: string | null;
  pack_size: string;
  default_dose: string;
  dose_unit: MasterRef | null;
  default_frequency: string;
  default_timing: MasterRef | null;
  default_anupana: MasterRef | null;
  schedule_e1: boolean;
  contains_metals: boolean;
  pregnancy_caution: boolean;
  child_caution: boolean;
  safety_notes: string;
  is_sample: boolean;
  is_active: boolean;
  version: number;
  branch_price: string | null;
  branch_active: boolean;
  updated_at: string;
}

export interface MedicineVersion {
  version: number;
  data: Record<string, unknown>;
  created_at: string;
  created_by_name: string;
}

export interface ImportResult {
  created: number;
  updated: number;
  unchanged: number;
  errors: { row: number; message: string }[];
  rows: { row: number; name: string; kind: MedicineKind; status: 'created' | 'updated' | 'unchanged' }[];
  dry_run: boolean;
}

export interface RxLine {
  id?: string;
  medicine: string | null;
  medicine_name: string;
  medicine_kind?: string;
  medicine_version?: number | null;
  dosage_form?: string;
  dose: string;
  dose_unit: string;
  frequency: string;
  timing: string;
  anupana: string;
  duration: number | null;
  duration_unit: 'days' | 'weeks' | 'months';
  quantity: string;
  instructions: string;
  medicine_flags?: MedicineFlag[];
}

export interface RxWarning {
  level: 'danger' | 'warning';
  rule: string;
  medicine: string;
  message: string;
}

export interface Prescription {
  id: string;
  visit: string;
  visit_date: string;
  patient: string;
  patient_detail: AppointmentPatient;
  doctor: string;
  doctor_name: string;
  branch_name: string;
  status: 'draft' | 'final';
  notes: string;
  finalized_at: string | null;
  items: RxLine[];
  warnings: RxWarning[];
  created_at: string;
  updated_at: string;
}

export interface PrescriptionTemplate {
  id: string;
  name: string;
  diagnosis: MasterRef | null;
  items: RxLine[];
  notes: string;
  is_active: boolean;
  updated_at: string;
}

// --- Pharmacy ---
export interface Rack {
  id: string;
  code: string;
  name: string;
  shelves: number;
  sort_order: number;
  is_active: boolean;
  product_count: number;
}

export interface Supplier {
  id: string;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  gstin: string;
  drug_licence_no: string;
  address: string;
  state: string;
  payment_terms_days: number | null;
  is_active: boolean;
}

export interface StockBatch {
  id: string;
  medicine: string;
  medicine_name: string;
  batch_no: string;
  mfg_date: string | null;
  expiry_date: string | null;
  mrp: string;
  selling_price: string | null;
  sale_price: string;
  purchase_rate: string | null;
  gst_rate: string;
  barcode: string;
  supplier_name: string;
  quantity: string;
}

export interface StockRow {
  medicine: string;
  name: string;
  kind: MedicineKind;
  generic_name: string;
  manufacturer: string;
  category: string;
  pack_size: string;
  barcode: string;
  available: string;
  usable: string;
  near_expiry_quantity: string;
  nearest_expiry: string | null;
  reorder_level: string | null;
  location: string;
  rack: string | null;
  shelf: string;
  bin: string;
  low: boolean;
  out: boolean;
  expiring: boolean;
  expired: boolean;
}

export type MovementKind = 'opening' | 'purchase' | 'free' | 'dispense' | 'sale_return' | 'purchase_return'
  | 'damaged' | 'expired' | 'adjust' | 'verification';

export interface StockMovement {
  id: string;
  medicine: string;
  medicine_name: string;
  batch_no: string;
  kind: MovementKind;
  quantity: string;
  balance_after: string;
  reason: string;
  reference: string;
  reference_label: string;
  by: string;
  created_at: string;
}

export interface Ledger {
  opening: string;
  closing: string;
  by_kind: Partial<Record<MovementKind, string>>;
  lines: StockMovement[];
}

export interface StockAlerts {
  low: number;
  out: number;
  expiring: number;
  expired: number;
}

export interface ScanResult {
  medicine: string;
  name: string;
  pack_size: string;
  location: string;
  scanned_batch: string | null;
  batches: StockBatch[];
}

export interface PurchaseItemRecord {
  id: string;
  medicine: string;
  medicine_name: string;
  batch: string;
  batch_no: string;
  mfg_date: string | null;
  expiry_date: string | null;
  quantity: string;
  free_quantity: string;
  purchase_rate: string | null;
  discount_percent: string;
  gst_rate: string;
  mrp: string;
  selling_price: string | null;
  taxable_amount: string;
  gst_amount: string;
  amount: string;
}

export interface PurchaseRecord {
  id: string;
  supplier: string | null;
  supplier_name: string;
  invoice_no: string;
  invoice_date: string;
  is_opening: boolean;
  taxable_amount: string;
  discount_amount: string;
  gst_amount: string;
  other_charges: string;
  round_off: string;
  total_amount: string;
  notes: string;
  items: PurchaseItemRecord[];
  created_by_name: string;
  created_at: string;
}

export interface PurchaseReturnRecord {
  id: string;
  supplier: string | null;
  supplier_name: string;
  return_date: string;
  reference: string;
  reason: string;
  total_amount: string;
  items: { id: string; medicine_name: string; batch_no: string; quantity: string; rate: string; amount: string }[];
  created_by_name: string;
  created_at: string;
}

export type DispenseStatus = 'pending' | 'partly' | 'done';

export interface DispenseQueueRow {
  id: string;
  patient_detail: AppointmentPatient;
  doctor_name: string;
  token_number: number | null;
  finalized_at: string | null;
  item_count: number;
  status: DispenseStatus;
}

export interface DispenseLine {
  id: string;
  medicine: string | null;
  medicine_name: string;
  dosage_form: string;
  pack_size: string;
  pack_type: string;
  allow_loose: boolean;
  units_per_pack: string | null;
  unit_label: string;
  location: string;
  dose: string;
  dose_unit: string;
  frequency: string;
  timing: string;
  anupana: string;
  duration: number | null;
  duration_unit: 'days' | 'weeks' | 'months';
  instructions: string;
  given: string | null;
  batches: StockBatch[];
}

export interface DispenseDetail {
  id: string;
  patient_detail: AppointmentPatient;
  doctor_name: string;
  notes: string;
  status: DispenseStatus;
  allergies: string[];
  sales: { id: string; invoice: string | null; number: string; total: string }[];
  lines: DispenseLine[];
}

export interface SaleItem {
  id: string;
  medicine_name: string;
  batch_no: string;
  quantity: string;
  loose_units: string | null;
  returned_quantity: string;
  amount: string;
}

export interface SaleRow {
  id: string;
  patient_detail: AppointmentPatient;
  created_at: string;
  total_amount: string;
  by: string;
  invoice: string | null;
  number: string;
  invoice_status: InvoiceStatus | '';
  items?: SaleItem[];
}

export interface StockCheckItem {
  id: string;
  batch: string;
  medicine_name: string;
  batch_no: string;
  expiry_date: string | null;
  system_quantity: string;
  counted_quantity: string | null;
  difference: string | null;
  location: string;
}

export interface StockCheck {
  id: string;
  title: string;
  rack: string | null;
  rack_code: string;
  status: 'open' | 'completed';
  notes: string;
  completed_at: string | null;
  created_at: string;
  created_by_name: string;
  item_count: number;
  counted_count: number;
  mismatch_count: number;
  items?: StockCheckItem[];
}

// --- Billing ---
export type InvoiceStatus = 'unpaid' | 'partly_paid' | 'paid' | 'cancelled';
export type PaymentMode = 'cash' | 'upi' | 'card';

export interface InvoiceLine {
  id: string;
  kind: string;
  description: string;
  batch_no: string;
  expiry_date: string | null;
  hsn_code: string;
  quantity: string;
  unit_label: string;
  unit_price: string;
  discount_percent: string;
  gst_rate: string;
  taxable_amount: string;
  cgst_amount: string;
  sgst_amount: string;
  total_amount: string;
  credited_quantity: string;
}

export interface CreditNoteRecord {
  id: string;
  number: string;
  note_date: string;
  invoice: string;
  invoice_number: string;
  customer_name: string;
  reason: string;
  total_amount: string;
  refund_mode: PaymentMode | 'none';
  refund_amount: string;
  created_at: string;
}

export interface InvoicePayment {
  id: string;
  mode: PaymentMode;
  amount: string;
  reference: string;
  paid_at: string;
  received_by: string;
}

export interface InvoiceRecord {
  id: string;
  number: string;
  /** OP = OPD bill, PH = pharmacy bill */
  series: string;
  care_type?: 'OPD' | 'IPD' | 'PHARMACY';
  doctor_name?: string;
  invoice_date: string;
  customer_name: string;
  patient_detail: AppointmentPatient | null;
  total_amount: string;
  paid_amount: string;
  credited_amount: string;
  refunded_amount: string;
  balance: string;
  status: InvoiceStatus;
  print_count: number;
  created_at: string;
  // Only in the detail view
  gross_amount?: string;
  discount_amount?: string;
  taxable_amount?: string;
  cgst_amount?: string;
  sgst_amount?: string;
  round_off?: string;
  cancel_reason?: string;
  lines?: InvoiceLine[];
  payments?: InvoicePayment[];
  credit_notes?: CreditNoteRecord[];
  created_by_name?: string;
  appointment?: string | null;
  visit?: string | null;
}

// --- OPD billing ---------------------------------------------------------------------------------
export interface ServiceCharge {
  id: string;
  name: string;
  name_gu: string;
  name_hi: string;
  category: MasterRef | null;
  price: string;
  gst_rate: string;
  sac_code: string;
  is_active: boolean;
  sort_order: number;
  is_sample: boolean;
  branch_price: string | null;
  branch_active: boolean;
  effective_price: string | null;
}

export interface ConsultationFeeRow {
  doctor: string;
  doctor_name: string;
  new_case_fee: string | null;
  follow_up_fee: string | null;
  follow_up_days: number;
  is_set: boolean;
}

export type VisitKind = 'new' | 'follow_up';

export interface OpdSuggestion {
  appointment: string | null;
  visit: string | null;
  patient_detail: AppointmentPatient;
  doctor: string | null;
  doctor_name: string;
  consultation: {
    visit_kind: VisitKind;
    fee: string;
    fee_set: boolean;
    last_visit: string | null;
    follow_up_days: number;
    description: string;
  } | null;
  consultation_billed: boolean;
  bill: InvoiceRecord | null;
}

export interface DashboardToday {
  date: string;
  is_doctor: boolean;
  opd?: OpdCounts;
  my_opd?: OpdCounts;
  next_patients?: { appointment: string; token_number: number | null; patient: string; uhid: string; status: string; reason: string }[];
  money?: { opd: string; pharmacy: string; total: string; due_today: string; unpaid_bills: number; bills_today: number };
}

export interface OpdCounts {
  booked: number;
  waiting: number;
  with_doctor: number;
  seen: number;
  not_arrived: number;
  no_show: number;
  cancelled: number;
  walk_ins: number;
  new_cases: number;
  follow_ups: number;
  follow_ups_due: number;
}

export interface DaySummary {
  date: string;
  invoice_count: number;
  billed: string;
  taxable: string;
  cgst: string;
  sgst: string;
  discount: string;
  received: Record<PaymentMode, string>;
  refunds: Record<PaymentMode, string>;
  credit_notes: number;
  credited: string;
  cash_in_hand: string;
  still_due: string;
}
