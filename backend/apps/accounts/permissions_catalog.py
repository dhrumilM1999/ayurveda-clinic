"""
SAFE TO EDIT: the list of all permissions, and the starting permissions of each default role.

- A permission code looks like "<module>.<action>", e.g. "billing.create".
- Roles are stored in the database and can be edited on the Roles screen.
  DEFAULT_ROLES is only used when a new organization is created (and by seed_demo).
- After adding a new code here, also add its screen text in frontend/src/i18n/*.json
  under "permissions" (optional; English text below is used as a fallback).
"""

PERMISSIONS = {
    # Dashboard
    "dashboard.view": "See the dashboard",
    # Organization setup
    "branches.view": "See branches",
    "branches.manage": "Add and edit branches",
    "rooms.view": "See rooms",
    "rooms.manage": "Add and edit rooms",
    "staff.view": "See staff",
    "staff.manage": "Add and edit staff, reset passwords",
    "roles.view": "See roles",
    "roles.manage": "Add and edit roles and their permissions",
    "schedules.view": "See doctor schedules",
    "schedules.manage": "Edit doctor schedules",
    "settings.manage": "Change clinic settings and feature switches",
    "audit.view": "See the audit log",
    # Modules built in later steps
    "patients.view": "See patients",
    "patients.create": "Register patients",
    "patients.edit": "Edit patient details",
    "patients.vitals": "Record vitals (BP, pulse, weight)",
    "appointments.view": "See appointments and queue",
    "appointments.manage": "Book, cancel and check in appointments",
    "emr.view": "See full medical history",
    "emr.edit": "Write assessments and diagnosis",
    "prescriptions.view": "See prescriptions",
    "prescriptions.create": "Write prescriptions",
    "medicines.view": "See the medicine list",
    "medicines.manage": "Edit the medicine list",
    "billing.view": "See bills",
    "billing.create": "Create bills and take payments",
    "billing.refund": "Cancel bills and give refunds",
    "pharmacy.view": "See pharmacy stock",
    "pharmacy.dispense": "Dispense medicines",
    "pharmacy.stock": "Add purchases and suppliers, correct stock",
    "therapy.view": "See therapy sessions",
    "therapy.manage": "Schedule and record therapy sessions",
    "reports.view": "See reports",
    "ai.use": "Use AI helpers",
}

ALL_PERMISSION_CODES = frozenset(PERMISSIONS)


DEFAULT_ROLES = {
    "admin": {
        "name": "Admin",
        "description": "Branch administrator: full access in their branch.",
        "requires_2fa": True,
        # Everything except adding branches (only organization admins do that).
        "permissions": sorted(ALL_PERMISSION_CODES - {"branches.manage"}),
    },
    "doctor": {
        "name": "Doctor",
        "description": "Vaidya: patients, assessment, prescriptions.",
        "requires_2fa": True,
        "permissions": [
            "dashboard.view", "schedules.view", "rooms.view",
            "patients.view", "patients.create", "patients.edit", "patients.vitals",
            "appointments.view", "appointments.manage",
            "emr.view", "emr.edit",
            "prescriptions.view", "prescriptions.create",
            "medicines.view", "therapy.view", "therapy.manage",
            "billing.view", "reports.view", "ai.use",
        ],
    },
    "receptionist": {
        "name": "Receptionist",
        "description": "Front desk: registration, appointments, billing.",
        "requires_2fa": False,
        "permissions": [
            "dashboard.view", "schedules.view", "rooms.view",
            "patients.view", "patients.create", "patients.edit", "patients.vitals",
            "appointments.view", "appointments.manage",
            "billing.view", "billing.create",
        ],
    },
    "therapist": {
        "name": "Therapist",
        "description": "Panchakarma therapist: therapy sessions only. Cannot see billing.",
        "requires_2fa": False,
        "permissions": [
            "dashboard.view", "rooms.view",
            "patients.view", "appointments.view",
            "therapy.view", "therapy.manage",
        ],
    },
    "pharmacist": {
        "name": "Pharmacist",
        "description": "Pharmacy: sees prescriptions (not full history) and dispenses.",
        "requires_2fa": False,
        "permissions": [
            "dashboard.view",
            "patients.view", "prescriptions.view",
            "medicines.view", "medicines.manage",
            "pharmacy.view", "pharmacy.dispense", "pharmacy.stock",
        ],
    },
}
