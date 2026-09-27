-- 0002_identity.sql
-- Identity & organization: organizations, users, roles, user_roles.

CREATE TABLE IF NOT EXISTS organizations (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name              text NOT NULL,
    organization_type text NOT NULL
                      CHECK (organization_type IN ('platform','aggregator','recycler','dismantler','collector_group')),
    status            text NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','inactive','suspended')),
    address_line      text,
    city              text,
    state             text,
    postal_code       text,
    country           text NOT NULL DEFAULT 'IN',
    contact_email     text,
    contact_phone     text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   uuid REFERENCES organizations(id) ON DELETE SET NULL,
    email             text UNIQUE,
    phone             text,
    password_hash     text,
    full_name         text,
    preferred_locale  text NOT NULL DEFAULT 'en',
    status            text NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','inactive','suspended')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roles (
    id          smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        text NOT NULL UNIQUE,
    name        text NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_roles (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         smallint NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    organization_id uuid REFERENCES organizations(id) ON DELETE CASCADE,
    granted_at      timestamptz NOT NULL DEFAULT now()
);

-- Uniqueness that treats NULL organization_id (platform-wide role) correctly.
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_roles_org
    ON user_roles (user_id, role_id, organization_id)
    WHERE organization_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_roles_no_org
    ON user_roles (user_id, role_id)
    WHERE organization_id IS NULL;

DROP TRIGGER IF EXISTS trg_organizations_updated_at ON organizations;
CREATE TRIGGER trg_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
