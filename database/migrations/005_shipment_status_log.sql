-- Kargo/sevkiyat durum geçmişi tablosu.
-- shipment_id, ayrı bir "shipments" tablosu henüz bulunmadığından dış
-- sistemden/trip-waybill akışından gelen opak bir kimlik olarak tutulur;
-- bu yüzden shipments tablosuna FOREIGN KEY kısıtlaması eklenmemiştir.
-- driver_id ise mevcut drivers tablosuna referans verir.
CREATE TABLE IF NOT EXISTS shipment_status_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    shipment_id uuid NOT NULL,
    driver_id uuid REFERENCES drivers(id),
    status varchar(40) NOT NULL,
    latitude numeric(10,7),
    longitude numeric(10,7),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_shipment_status_logs_tenant_shipment
    ON shipment_status_logs (tenant_id, shipment_id);
CREATE INDEX IF NOT EXISTS ix_shipment_status_logs_driver
    ON shipment_status_logs (driver_id);

ALTER TABLE shipment_status_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON shipment_status_logs;
CREATE POLICY tenant_isolation ON shipment_status_logs
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
