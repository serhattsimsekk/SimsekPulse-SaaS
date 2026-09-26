-- Migration 002: Multi-Tenant Role-Based Visibility & HR + Chief Driver Modules
-- Adds granular department-based data isolation, HR personnel records, and chief driver shift/vehicle management.

-- ============ PHASE 1: Enhanced Role & Department Definitions ============

-- Predefined roles: super_admin, admin, hr_officer, hr_viewer, driver, chief_driver, operations, fleet_manager, finance, accounting, maintenance
-- Predefined departments: hr, operations, driver, finance, maintenance, executive, audit

-- Ensure driver has tenant_id (for RLS)
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_drivers_tenant ON drivers(tenant_id);

-- ============ PHASE 2: HR Module - Personnel & Compliance ============

-- HR Personnel record (extends driver; only HR/Admin can see full details)
CREATE TABLE IF NOT EXISTS hr_personnel (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    driver_id uuid NOT NULL UNIQUE REFERENCES drivers(id),
    
    -- Personnel info (visible only to HR/Admin)
    personnel_no varchar(50) UNIQUE NOT NULL,
    full_name varchar(160) NOT NULL,
    national_id varchar(50),
    birth_date date,
    phone_personal varchar(30),
    email_personal varchar(160),
    
    -- Employment & Legal
    employment_status varchar(30) DEFAULT 'active', -- active, suspended, terminated, on_leave
    employment_start_date date NOT NULL,
    employment_end_date date,
    contract_type varchar(40) NOT NULL, -- permanent, contract, temporary
    salary_monthly numeric(14,2),
    
    -- Document references (files stored with tenant_id isolation)
    contract_document_uri text,
    identity_document_uri text,
    insurance_document_uri text,
    
    -- Audit trail
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE hr_personnel ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON hr_personnel;
CREATE POLICY tenant_isolation ON hr_personnel USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- HR Document tracking (licenses, insurance, certifications)
CREATE TABLE IF NOT EXISTS hr_personnel_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    personnel_id uuid NOT NULL REFERENCES hr_personnel(id),
    
    document_type varchar(40) NOT NULL, -- driving_license, insurance, national_id, health_cert, training_cert
    document_number varchar(100),
    issue_date date,
    expiry_date date NOT NULL,
    issuing_authority varchar(160),
    document_uri text,
    
    status varchar(30) DEFAULT 'valid', -- valid, expiring_soon (7 days), expired
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE hr_personnel_documents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON hr_personnel_documents;
CREATE POLICY tenant_isolation ON hr_personnel_documents USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- HR Leave & Absence tracking
CREATE TABLE IF NOT EXISTS hr_leave_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    personnel_id uuid NOT NULL REFERENCES hr_personnel(id),
    
    leave_type varchar(40) NOT NULL, -- vacation, sick, personal, maternity, training
    start_date date NOT NULL,
    end_date date NOT NULL,
    total_days integer NOT NULL,
    reason text,
    
    status varchar(30) DEFAULT 'pending', -- pending, approved, rejected, cancelled
    approved_by_user_id uuid REFERENCES users(id),
    approved_at timestamptz,
    rejection_reason text,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE hr_leave_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON hr_leave_requests;
CREATE POLICY tenant_isolation ON hr_leave_requests USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- ============ PHASE 3: Chief Driver Panel - Shift & Vehicle Assignment ============

-- Shift schedule managed by Chief Driver
CREATE TABLE IF NOT EXISTS driver_shifts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    
    driver_id uuid NOT NULL REFERENCES drivers(id),
    vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    
    shift_date date NOT NULL,
    shift_type varchar(30) DEFAULT '8h', -- 8h, 12h, 24h
    shift_start time NOT NULL,
    shift_end time NOT NULL,
    assigned_by_user_id uuid REFERENCES users(id),
    
    status varchar(30) DEFAULT 'scheduled', -- scheduled, in_progress, completed, cancelled
    notes text,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    
    UNIQUE(tenant_id, driver_id, shift_date, shift_start)
);
ALTER TABLE driver_shifts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON driver_shifts;
CREATE POLICY tenant_isolation ON driver_shifts USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- Vehicle assignment log (which driver/vehicle combination at which time)
CREATE TABLE IF NOT EXISTS vehicle_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    
    vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    driver_id uuid NOT NULL REFERENCES drivers(id),
    
    assigned_at timestamptz NOT NULL DEFAULT now(),
    released_at timestamptz,
    
    assignment_reason varchar(80), -- daily_shift, special_trip, maintenance_handoff
    notes text,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE vehicle_assignments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON vehicle_assignments;
CREATE POLICY tenant_isolation ON vehicle_assignments USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- Asset periodic maintenance & inspection schedule (managed by Chief Driver)
CREATE TABLE IF NOT EXISTS vehicle_maintenance_schedule (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    
    vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    maintenance_type varchar(40) NOT NULL, -- inspection, insurance, emission_test, tire_check, oil_change
    
    last_done_date date,
    due_date date NOT NULL,
    interval_months integer,
    
    status varchar(30) DEFAULT 'pending', -- pending, completed, overdue
    notes text,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE vehicle_maintenance_schedule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON vehicle_maintenance_schedule;
CREATE POLICY tenant_isolation ON vehicle_maintenance_schedule USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- ============ PHASE 4: Operasyonel Field Visibility Controls ============

-- Update driver table: isolate fatigue_index and tachograph data (NOT visible to HR)
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS fatigue_percentage numeric(5,2) DEFAULT 0; -- Visible only to Ops/Chief/Admin
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS tachograph_remaining_hours numeric(5,2) DEFAULT 11; -- Visible only to Ops/Chief/Admin

-- Update trip table: add company_id isolation if needed
ALTER TABLE trips ADD COLUMN IF NOT EXISTS visibility_level varchar(30) DEFAULT 'standard'; -- standard, restricted, confidential

-- Update vehicles: insurance & inspection tracking (managed via vehicle_maintenance_schedule now)
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS insurance_expiry date;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS inspection_expiry date;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS last_inspection_date date;

-- ============ PHASE 5: Role-Based Column Masking View (Logical Security Layer) ============

-- Helper view for HR data visibility (only rows the user's role can see)
-- This will be enforced at API layer via SQLAlchemy query filters

-- ============ INDEXES & PERFORMANCE ============

CREATE INDEX IF NOT EXISTS ix_hr_personnel_tenant_status ON hr_personnel(tenant_id, employment_status);
CREATE INDEX IF NOT EXISTS ix_hr_personnel_docs_tenant_expiry ON hr_personnel_documents(tenant_id, expiry_date);
CREATE INDEX IF NOT EXISTS ix_driver_shifts_tenant_date ON driver_shifts(tenant_id, shift_date);
CREATE INDEX IF NOT EXISTS ix_vehicle_assignments_tenant_vehicle ON vehicle_assignments(tenant_id, vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_maint_tenant_due ON vehicle_maintenance_schedule(tenant_id, due_date);

CREATE INDEX IF NOT EXISTS ix_drivers_tenant_status ON drivers(tenant_id, status);

-- ============ AUDIT LOGGING ============

-- All operations on HR tables automatically logged via trigger (to audit_logs)
-- Managed by backend via SQLAlchemy event listeners in services/audit.py
