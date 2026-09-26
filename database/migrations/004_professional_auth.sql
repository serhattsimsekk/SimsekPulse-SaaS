-- Migration 004: Professional Authentication & Password Recovery
-- Adds password reset tokens, audit logging, and secure user management

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    user_id uuid NOT NULL REFERENCES users(id),
    
    token_hash varchar(128) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    used_at timestamptz,
    used_ip_address varchar(45),
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON password_reset_tokens;
CREATE POLICY tenant_isolation ON password_reset_tokens 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_password_reset_tenant ON password_reset_tokens(tenant_id, used_at);
CREATE INDEX IF NOT EXISTS ix_password_reset_user ON password_reset_tokens(user_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS auth_audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid REFERENCES tenants(id),
    user_id uuid REFERENCES users(id),
    
    event_type varchar(50) NOT NULL, -- login_success, login_failure, password_change, password_reset, user_created
    username varchar(80),
    email varchar(160),
    ip_address varchar(45),
    user_agent text,
    
    details_json text, -- {"attempt": 1, "reason": "invalid_password", ...}
    status varchar(30) NOT NULL DEFAULT 'success', -- success, failure, pending
    
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_auth_audit_tenant ON auth_audit_log(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_auth_audit_user ON auth_audit_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_auth_audit_event ON auth_audit_log(event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS user_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    user_id uuid NOT NULL REFERENCES users(id),
    
    access_token_hash varchar(128) NOT NULL UNIQUE,
    refresh_token_hash varchar(128),
    
    ip_address varchar(45),
    user_agent text,
    device_info text,
    
    logged_in_at timestamptz NOT NULL DEFAULT now(),
    last_activity_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON user_sessions;
CREATE POLICY tenant_isolation ON user_sessions 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_user_sessions_tenant ON user_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_user ON user_sessions(user_id, revoked_at);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires ON user_sessions(expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS user_password_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    user_id uuid NOT NULL REFERENCES users(id),
    
    password_hash_old varchar(255) NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now(),
    changed_by_user_id uuid REFERENCES users(id),
    ip_address varchar(45),
    
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE user_password_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON user_password_history;
CREATE POLICY tenant_isolation ON user_password_history 
    USING (tenant_id::text = current_setting('app.tenant_id', true)) 
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));
CREATE INDEX IF NOT EXISTS ix_password_history_user ON user_password_history(user_id, changed_at DESC);

ALTER TABLE users ADD COLUMN IF NOT EXISTS last_password_change_at timestamptz DEFAULT now();
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_expires_at timestamptz;
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts integer DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until timestamptz;

CREATE INDEX IF NOT EXISTS ix_users_password_expires ON users(tenant_id, password_expires_at) WHERE password_expires_at IS NOT NULL;
