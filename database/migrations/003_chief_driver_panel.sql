-- Migration 003: Chief Driver (Baş Şoför) Panel - Shift & Vehicle Management
-- Adds tables for chief driver to manage driver shifts, vehicle assignments, and maintenance schedules

ALTER TABLE drivers ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL DEFAULT gen_random_uuid() REFERENCES tenants(id);
CREATE INDEX IF NOT EXISTS ix_drivers_tenant ON drivers(tenant_id);

-- ============ CHIEF DRIVER SHIFT SCHEDULE ============
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
CREATE POLICY tenant_isolation ON driver_shifts 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_driver_shifts_tenant_date ON driver_shifts(tenant_id, shift_date DESC);
CREATE INDEX IF NOT EXISTS ix_driver_shifts_driver ON driver_shifts(driver_id, shift_date DESC);

-- ============ VEHICLE ASSIGNMENT LOG ============
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
CREATE POLICY tenant_isolation ON vehicle_assignments 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_vehicle_assignments_tenant_vehicle ON vehicle_assignments(tenant_id, vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_assignments_driver ON vehicle_assignments(driver_id, released_at);

-- ============ VEHICLE MAINTENANCE & INSPECTION SCHEDULE ============
CREATE TABLE IF NOT EXISTS vehicle_maintenance_schedule (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    
    vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    maintenance_type varchar(40) NOT NULL, -- inspection, insurance, emission_test, tire_check, oil_change
    
    last_done_date date,
    due_date date NOT NULL,
    interval_months integer,
    
    status varchar(30) DEFAULT 'pending', -- pending, completed, overdue, in_progress
    notes text,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE vehicle_maintenance_schedule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON vehicle_maintenance_schedule;
CREATE POLICY tenant_isolation ON vehicle_maintenance_schedule 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_vehicle_maint_tenant_due ON vehicle_maintenance_schedule(tenant_id, due_date);
CREATE INDEX IF NOT EXISTS ix_vehicle_maint_vehicle_status ON vehicle_maintenance_schedule(vehicle_id, status);

-- ============ VEHICLE PERIODIC DOCUMENTS (Insurance, Inspection, Emission) ============
CREATE TABLE IF NOT EXISTS vehicle_periodic_docs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    
    vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    doc_type varchar(40) NOT NULL, -- insurance, inspection, emission_cert, roadworthiness
    
    issue_date date NOT NULL,
    expiry_date date NOT NULL,
    document_uri text,
    
    status varchar(30) DEFAULT 'valid', -- valid, expiring_soon, expired
    alert_days_before integer DEFAULT 30,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE vehicle_periodic_docs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON vehicle_periodic_docs;
CREATE POLICY tenant_isolation ON vehicle_periodic_docs 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_vehicle_periodic_tenant_expiry ON vehicle_periodic_docs(tenant_id, expiry_date);
CREATE INDEX IF NOT EXISTS ix_vehicle_periodic_vehicle ON vehicle_periodic_docs(vehicle_id, status);

-- ============ DRIVER OPERATIONAL METRICS (Fatigue, Tachograph) ============
-- These fields exist in drivers table but are ONLY visible to chief_driver, operations, and master_admin roles
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS fatigue_percentage numeric(5,2) DEFAULT 0;
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS tachograph_remaining_hours numeric(5,2) DEFAULT 11;
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS last_fatigue_check timestamptz;
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS daily_work_minutes integer DEFAULT 0;
ALTER TABLE drivers ADD COLUMN IF NOT EXISTS weekly_rest_completed boolean DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_drivers_fatigue_percentage ON drivers(tenant_id, fatigue_percentage DESC);
CREATE INDEX IF NOT EXISTS ix_drivers_tachograph ON drivers(tenant_id, tachograph_remaining_hours);
