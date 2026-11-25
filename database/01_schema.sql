CREATE SCHEMA IF NOT EXISTS permitme;

CREATE TABLE IF NOT EXISTS permitme.offices (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permitme.staff_users (
    id BIGSERIAL PRIMARY KEY,
    office_id BIGINT REFERENCES permitme.offices(id),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('intake', 'reviewer', 'inspector', 'approver', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permitme.applicants (
    id BIGSERIAL PRIMARY KEY,
    applicant_type TEXT NOT NULL CHECK (applicant_type IN ('individual', 'sole_proprietor', 'business')),
    full_or_business_name TEXT NOT NULL,
    tax_or_reg_id TEXT,
    phone TEXT,
    email TEXT,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permitme.permit_types (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    validity_days INT NOT NULL CHECK (validity_days > 0),
    base_fee NUMERIC(12, 2) NOT NULL CHECK (base_fee >= 0),
    sla_hours INT NOT NULL CHECK (sla_hours > 0),
    required_docs JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS permitme.permit_applications (
    id BIGSERIAL PRIMARY KEY,
    reference_no TEXT NOT NULL UNIQUE,
    applicant_id BIGINT NOT NULL REFERENCES permitme.applicants(id),
    permit_type_id BIGINT NOT NULL REFERENCES permitme.permit_types(id),
    office_id BIGINT NOT NULL REFERENCES permitme.offices(id),
    assigned_staff_id BIGINT REFERENCES permitme.staff_users(id),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (
        status IN (
            'draft', 'submitted', 'rfi_pending', 'under_review',
            'inspection_pending', 'fee_pending', 'approved',
            'rejected', 'expired', 'revoked'
        )
    ),
    priority_score INT NOT NULL DEFAULT 50,
    submitted_at TIMESTAMPTZ,
    sla_due_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permitme.inspection_logs (
    id BIGSERIAL PRIMARY KEY,
    application_id BIGINT NOT NULL REFERENCES permitme.permit_applications(id) ON DELETE CASCADE,
    inspector_id BIGINT REFERENCES permitme.staff_users(id),
    inspection_type TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('passed', 'failed', 'conditional')),
    findings TEXT,
    inspected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permitme.credentials (
    id BIGSERIAL PRIMARY KEY,
    application_id BIGINT NOT NULL UNIQUE REFERENCES permitme.permit_applications(id),
    permit_number TEXT NOT NULL UNIQUE,
    verification_code TEXT NOT NULL UNIQUE,
    fee_amount NUMERIC(12, 2) NOT NULL,
    fee_paid BOOLEAN NOT NULL DEFAULT FALSE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS permitme.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB,
    actor_id BIGINT,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);