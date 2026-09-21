-- PostgreSQL 15+ / ŞimşekLog başlangıç şeması.
-- ORM karşılığı: database/models.py
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name varchar(160) NOT NULL,
    tax_number varchar(20) UNIQUE, is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS code varchar(40);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_code ON tenants(code) WHERE code IS NOT NULL;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS subscription_status varchar(30) NOT NULL DEFAULT 'pending';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS license_key varchar(120);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS logo_data text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS logo_content_type varchar(100);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_license_key ON tenants(license_key) WHERE license_key IS NOT NULL;
CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    name varchar(160) NOT NULL, username varchar(80) NOT NULL, role varchar(40) NOT NULL,
    department varchar(40),
    password_hash varchar(255), is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, username)
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS department varchar(40);
CREATE TABLE IF NOT EXISTS notification_logs (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), user_id uuid REFERENCES users(id), channel varchar(20) NOT NULL, recipient varchar(120) NOT NULL, title varchar(120) NOT NULL, message text NOT NULL, status varchar(40) NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS backup_runs (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), backup_type varchar(30) NOT NULL, destination varchar(255) NOT NULL, status varchar(30) NOT NULL, size_bytes integer, error_message text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS spreadsheet_workbooks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), name varchar(160) NOT NULL, owner_user_id uuid NOT NULL REFERENCES users(id), workbook_json text NOT NULL DEFAULT '{}', protection_json text NOT NULL DEFAULT '{}', version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS spreadsheet_changes (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), workbook_id uuid NOT NULL REFERENCES spreadsheet_workbooks(id), user_id uuid NOT NULL REFERENCES users(id), sheet_name varchar(120) NOT NULL, cell_ref varchar(30) NOT NULL, value_json text NOT NULL, version integer NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
DO $$
DECLARE item record;
BEGIN
  FOR item IN
    SELECT table_name FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name = 'tenant_id'
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', item.table_name);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', item.table_name);
    EXECUTE format(
      'CREATE POLICY tenant_isolation ON %I USING (tenant_id::text = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))',
      item.table_name
    );
  END LOOP;
END $$;
CREATE TABLE IF NOT EXISTS drivers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    employee_no varchar(50), name varchar(160) NOT NULL, phone varchar(30),
    status varchar(30) NOT NULL DEFAULT 'active', shift varchar(50), license_no varchar(50),
    license_expiry date, src_expiry date, penalty_points integer NOT NULL DEFAULT 0,
    blacklisted boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS driver_documents (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), driver_id uuid NOT NULL REFERENCES drivers(id), document_type varchar(40) NOT NULL, document_number varchar(80), expires_on date NOT NULL, document_uri text, status varchar(30) NOT NULL DEFAULT 'valid', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS discipline_records (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), driver_id uuid NOT NULL REFERENCES drivers(id), violation_type varchar(80) NOT NULL, points integer NOT NULL DEFAULT 0, description text, occurred_at timestamptz NOT NULL, status varchar(30) NOT NULL DEFAULT 'open', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS tachograph_violations (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), driver_id uuid NOT NULL REFERENCES drivers(id), violation_type varchar(80) NOT NULL, occurred_at timestamptz NOT NULL, duration_minutes integer NOT NULL DEFAULT 0, severity varchar(20) NOT NULL DEFAULT 'medium', notes text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS rest_breaks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), driver_id uuid NOT NULL REFERENCES drivers(id), started_at timestamptz NOT NULL, ended_at timestamptz, duration_minutes integer NOT NULL DEFAULT 0, break_type varchar(30) NOT NULL DEFAULT 'rest', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS vehicles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    plate varchar(20) NOT NULL, vehicle_type varchar(40) NOT NULL DEFAULT 'tractor',
    brand varchar(80), model varchar(80), model_year integer, vin varchar(50) UNIQUE,
    device_no varchar(80), status varchar(30) NOT NULL DEFAULT 'active', odometer_km integer NOT NULL DEFAULT 0,
    fuel_capacity_l numeric(10,2), consumption_100km numeric(8,2),
    current_driver_id uuid REFERENCES drivers(id), ownership_status varchar(30) NOT NULL DEFAULT 'owned',
    acquisition_cost numeric(14,2), acquisition_date date, depreciation_amount numeric(14,2),
    sale_date date, sale_amount numeric(14,2), created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE (tenant_id, plate)
);
CREATE TABLE IF NOT EXISTS receipt_ocr_records (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), driver_id uuid REFERENCES drivers(id), vehicle_id uuid REFERENCES vehicles(id), receipt_type varchar(30) NOT NULL, filename varchar(255) NOT NULL, content_type varchar(100), file_size_bytes integer NOT NULL DEFAULT 0, raw_text text, extracted_data text, confidence numeric(5,2) NOT NULL DEFAULT 0, status varchar(30) NOT NULL DEFAULT 'processed', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS trailers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    plate varchar(20) NOT NULL, trailer_type varchar(80) NOT NULL, capacity_ton numeric(10,2),
    hex_color varchar(7), status varchar(30) NOT NULL DEFAULT 'available',
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS vehicle_trailer_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    trailer_id uuid NOT NULL REFERENCES trailers(id), driver_id uuid REFERENCES drivers(id),
    started_at timestamptz NOT NULL, ended_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS customers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    name varchar(160) NOT NULL, tax_number varchar(20), contact_name varchar(160),
    contact_phone varchar(30), address text, created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS freight_contracts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    customer_id uuid NOT NULL REFERENCES customers(id), contract_no varchar(60) NOT NULL,
    route varchar(240), unit_price_ton numeric(14,2) NOT NULL, valid_from date NOT NULL,
    valid_to date, status varchar(30) NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS trips (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    vehicle_id uuid NOT NULL REFERENCES vehicles(id), driver_id uuid REFERENCES drivers(id),
    customer_id uuid REFERENCES customers(id), contract_id uuid REFERENCES freight_contracts(id),
    route varchar(240) NOT NULL, cargo_description varchar(240), planned_ton numeric(12,3),
    realized_ton numeric(12,3), status varchar(30) NOT NULL DEFAULT 'assigned',
    started_at timestamptz, completed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Operasyonel alt tablolar; ayrıntılı kolon sözleşmesi ORM modelinde tutulur.
CREATE TABLE IF NOT EXISTS driver_tasks (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), trip_id uuid REFERENCES trips(id), driver_id uuid NOT NULL REFERENCES drivers(id), description text NOT NULL, status varchar(30) NOT NULL DEFAULT 'assigned', due_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS shift_handovers (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), driver_id uuid NOT NULL REFERENCES drivers(id), incoming_driver_id uuid REFERENCES drivers(id), closing_odometer_km integer NOT NULL, fuel_percent numeric(5,2) NOT NULL, fuel_liters numeric(10,2), photo_uri text, notes text, status varchar(30) NOT NULL DEFAULT 'pending', approved_by uuid REFERENCES users(id), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS waybills (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), trip_id uuid REFERENCES trips(id), customer_id uuid REFERENCES customers(id), waybill_no varchar(80) NOT NULL, cargo_ton numeric(12,3) NOT NULL, issued_at timestamptz NOT NULL, document_uri text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS weighbridge_tickets (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), trip_id uuid REFERENCES trips(id), vehicle_id uuid NOT NULL REFERENCES vehicles(id), ticket_no varchar(80) NOT NULL, gross_kg integer NOT NULL, tare_kg integer NOT NULL, net_kg integer NOT NULL, waybill_kg integer, deviation_kg integer, status varchar(40) NOT NULL DEFAULT 'pending', ocr_verified boolean NOT NULL DEFAULT false, image_uri text, weighed_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS wait_events (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), trip_id uuid REFERENCES trips(id), vehicle_id uuid NOT NULL REFERENCES vehicles(id), location_type varchar(30) NOT NULL, location_name varchar(160) NOT NULL, started_at timestamptz NOT NULL, ended_at timestamptz, free_minutes integer NOT NULL DEFAULT 120, rate_per_hour numeric(14,2) NOT NULL DEFAULT 0, demurrage_amount numeric(14,2) NOT NULL DEFAULT 0, status varchar(30) NOT NULL DEFAULT 'open', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS maintenance_issues (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), reported_by_driver_id uuid REFERENCES drivers(id), category varchar(100) NOT NULL, urgency varchar(30) NOT NULL DEFAULT 'normal', parts_needed text, estimated_cost numeric(14,2), layup_days integer NOT NULL DEFAULT 0, status varchar(30) NOT NULL DEFAULT 'open', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS work_orders (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), issue_id uuid REFERENCES maintenance_issues(id), assigned_user_id uuid REFERENCES users(id), labor_cost numeric(14,2), started_at timestamptz, completed_at timestamptz, status varchar(30) NOT NULL DEFAULT 'planned', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS parts (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), sku varchar(80) NOT NULL, name varchar(160) NOT NULL, unit varchar(20) NOT NULL DEFAULT 'piece', stock_quantity numeric(12,2) NOT NULL DEFAULT 0, critical_quantity numeric(12,2) NOT NULL DEFAULT 0, unit_cost numeric(14,2), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS part_movements (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), part_id uuid NOT NULL REFERENCES parts(id), work_order_id uuid REFERENCES work_orders(id), quantity numeric(12,2) NOT NULL, movement_type varchar(20) NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS inspections (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), inspection_type varchar(50) NOT NULL, due_date date NOT NULL, due_odometer_km integer, completed_at timestamptz, status varchar(30) NOT NULL DEFAULT 'upcoming', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_api_url text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_username varchar(160);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_password text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_api_token text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_pin varchar(80);
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS ownership_status varchar(30) NOT NULL DEFAULT 'owned';
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS acquisition_cost numeric(14,2);
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS acquisition_date date;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS depreciation_amount numeric(14,2);
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS sale_date date;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS sale_amount numeric(14,2);
CREATE TABLE IF NOT EXISTS fuel_transactions (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), driver_id uuid REFERENCES drivers(id), liters numeric(12,3) NOT NULL, unit_price numeric(12,3) NOT NULL, odometer_km integer, station varchar(160), receipt_uri text, transaction_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS telemetry_events (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), recorded_at timestamptz NOT NULL, latitude numeric(10,7), longitude numeric(10,7), speed_kmh numeric(8,2), fuel_percent numeric(5,2), engine_on boolean NOT NULL DEFAULT false, payload text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS tyre_incidents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    vehicle_id uuid NOT NULL REFERENCES vehicles(id), driver_id uuid REFERENCES drivers(id),
    trailer_id uuid REFERENCES trailers(id), tire_id uuid REFERENCES tires(id), route varchar(240),
    location varchar(240), cause varchar(50) NOT NULL DEFAULT 'unknown', brand varchar(80),
    model varchar(80), damage_cost numeric(14,2) NOT NULL DEFAULT 0, occurred_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS road_side_assistance_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    incident_id uuid REFERENCES tyre_incidents(id), vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    provider_type varchar(30) NOT NULL, provider_name varchar(160) NOT NULL, location varchar(240),
    cost numeric(14,2) NOT NULL DEFAULT 0, response_minutes integer, status varchar(30) NOT NULL DEFAULT 'completed',
    occurred_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS fuel_anomalies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    vehicle_id uuid NOT NULL REFERENCES vehicles(id), fuel_transaction_id uuid REFERENCES fuel_transactions(id),
    anomaly_type varchar(50) NOT NULL, severity varchar(20) NOT NULL DEFAULT 'medium',
    expected_liters numeric(12,3), actual_liters numeric(12,3), details text, detected_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS customer_tracking_links (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    trip_id uuid NOT NULL REFERENCES trips(id), token_hash varchar(64) UNIQUE NOT NULL,
    expires_at timestamptz NOT NULL, revoked_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS tire_rotations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    tire_id uuid NOT NULL REFERENCES tires(id), vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    from_position varchar(30) NOT NULL, to_position varchar(30) NOT NULL, rotated_at timestamptz NOT NULL,
    odometer_km integer, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS geofences (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), name varchar(120) NOT NULL, geometry_wkt text NOT NULL, is_active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS geofence_events (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), geofence_id uuid NOT NULL REFERENCES geofences(id), vehicle_id uuid NOT NULL REFERENCES vehicles(id), event_type varchar(30) NOT NULL, occurred_at timestamptz NOT NULL, latitude numeric(10,7), longitude numeric(10,7), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS tires (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), position varchar(30) NOT NULL, serial_no varchar(80), brand varchar(80), tread_mm numeric(6,2), status varchar(30) NOT NULL DEFAULT 'active', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS tyre_incidents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    vehicle_id uuid NOT NULL REFERENCES vehicles(id), driver_id uuid REFERENCES drivers(id),
    trailer_id uuid REFERENCES trailers(id), tire_id uuid REFERENCES tires(id), route varchar(240),
    location varchar(240), cause varchar(50) NOT NULL DEFAULT 'unknown', brand varchar(80),
    model varchar(80), damage_cost numeric(14,2) NOT NULL DEFAULT 0, occurred_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS incidents (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), vehicle_id uuid NOT NULL REFERENCES vehicles(id), driver_id uuid REFERENCES drivers(id), incident_type varchar(50) NOT NULL, occurred_at timestamptz NOT NULL, description text NOT NULL, repair_cost numeric(14,2), layup_days integer NOT NULL DEFAULT 0, status varchar(30) NOT NULL DEFAULT 'open', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS subcontractors (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), name varchar(160) NOT NULL, tax_number varchar(20), phone varchar(30), current_balance numeric(14,2) NOT NULL DEFAULT 0, status varchar(30) NOT NULL DEFAULT 'active', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS supplier_settlements (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), subcontractor_id uuid NOT NULL REFERENCES subcontractors(id), trip_id uuid REFERENCES trips(id), amount numeric(14,2) NOT NULL, status varchar(30) NOT NULL DEFAULT 'pending', paid_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS expenses (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), trip_id uuid REFERENCES trips(id), vehicle_id uuid REFERENCES vehicles(id), category varchar(50) NOT NULL, amount numeric(14,2) NOT NULL, currency varchar(3) NOT NULL DEFAULT 'TRY', description text, incurred_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS bids (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), customer_id uuid REFERENCES customers(id), route varchar(240) NOT NULL, requested_ton numeric(12,3) NOT NULL, proposed_amount numeric(14,2), status varchar(30) NOT NULL DEFAULT 'draft', valid_until timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS audit_logs (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid REFERENCES tenants(id), user_id uuid REFERENCES users(id), action varchar(80) NOT NULL, entity_type varchar(80) NOT NULL, entity_id uuid, payload text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS customer_freight_rates (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), customer_id uuid NOT NULL REFERENCES customers(id), route varchar(240), unit_price_ton numeric(14,2) NOT NULL, currency varchar(3) NOT NULL DEFAULT 'TRY', valid_from date NOT NULL, valid_to date, is_active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS contractor_commissions (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id), subcontractor_id uuid NOT NULL REFERENCES subcontractors(id), trip_id uuid REFERENCES trips(id), base_amount numeric(14,2) NOT NULL, commission_rate numeric(6,3) NOT NULL, commission_amount numeric(14,2) NOT NULL, status varchar(30) NOT NULL DEFAULT 'pending', paid_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());

CREATE INDEX IF NOT EXISTS ix_telemetry_vehicle_time ON telemetry_events(vehicle_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_fuel_vehicle_time ON fuel_transactions(vehicle_id, transaction_at DESC);
CREATE INDEX IF NOT EXISTS ix_trips_tenant_status ON trips(tenant_id, status);
DO $$
DECLARE item text;
BEGIN
  FOREACH item IN ARRAY ARRAY['tyre_incidents','road_side_assistance_logs','fuel_anomalies','customer_tracking_links','tire_rotations']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', item);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', item);
    EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id::text = current_setting(''app.tenant_id'', true)) WITH CHECK (tenant_id::text = current_setting(''app.tenant_id'', true))', item);
  END LOOP;
END $$;
CREATE TABLE IF NOT EXISTS asset_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    asset_type varchar(20) NOT NULL, vehicle_id uuid REFERENCES vehicles(id), trailer_id uuid REFERENCES trailers(id),
    document_type varchar(40) NOT NULL, expires_on date NOT NULL, document_uri text,
    status varchar(30) NOT NULL DEFAULT 'valid', created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE asset_documents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON asset_documents;
CREATE POLICY tenant_isolation ON asset_documents USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE TABLE IF NOT EXISTS shift_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    driver_id uuid REFERENCES drivers(id), vehicle_id uuid REFERENCES vehicles(id),
    shift_code varchar(20) NOT NULL, starts_at timestamptz NOT NULL, ends_at timestamptz NOT NULL,
    total_ton numeric(12,3) NOT NULL DEFAULT 0, trip_count integer NOT NULL DEFAULT 0,
    receipt_count integer NOT NULL DEFAULT 0, fuel_liters numeric(12,2) NOT NULL DEFAULT 0,
    distance_km integer NOT NULL DEFAULT 0, report_status varchar(30) NOT NULL DEFAULT 'generated',
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS weighbridge_receipts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid NOT NULL REFERENCES tenants(id),
    shift_log_id uuid REFERENCES shift_logs(id), driver_id uuid REFERENCES drivers(id), vehicle_id uuid REFERENCES vehicles(id),
    filename varchar(255) NOT NULL, receipt_number varchar(80), scale_name varchar(160), ocr_plate varchar(20),
    weighed_ton numeric(12,3), receipt_at timestamptz, raw_text text, confidence numeric(5,2) NOT NULL DEFAULT 0,
    status varchar(40) NOT NULL DEFAULT 'matched', review_reason text,
    created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE shift_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON shift_logs;
CREATE POLICY tenant_isolation ON shift_logs USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
ALTER TABLE weighbridge_receipts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON weighbridge_receipts;
CREATE POLICY tenant_isolation ON weighbridge_receipts USING (tenant_id::text = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
