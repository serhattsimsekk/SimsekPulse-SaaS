ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_api_url text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_username varchar(160);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_password text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_api_token text;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS arvento_pin varchar(80);
