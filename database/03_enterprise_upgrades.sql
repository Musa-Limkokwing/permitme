CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE permitme.credentials
    ADD COLUMN IF NOT EXISTS renewed_from_credential_id BIGINT REFERENCES permitme.credentials(id),
    ADD COLUMN IF NOT EXISTS signature_hmac TEXT,
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revocation_reason TEXT;

ALTER TABLE permitme.audit_logs
    ADD COLUMN IF NOT EXISTS prev_hash TEXT,
    ADD COLUMN IF NOT EXISTS row_hash TEXT;

CREATE OR REPLACE FUNCTION permitme.fn_chained_audit_log()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_prev_hash TEXT;
    v_record_id TEXT;
    v_old_json JSONB;
    v_new_json JSONB;
    v_op TEXT;
    v_payload TEXT;
    v_hash TEXT;
BEGIN
    v_op := TG_OP;

    IF v_op = 'INSERT' THEN
        v_record_id := NEW.id::TEXT;
        v_old_json := NULL;
        v_new_json := to_jsonb(NEW);
    ELSIF v_op = 'UPDATE' THEN
        v_record_id := NEW.id::TEXT;
        v_old_json := to_jsonb(OLD);
        v_new_json := to_jsonb(NEW);
    ELSIF v_op = 'DELETE' THEN
        v_record_id := OLD.id::TEXT;
        v_old_json := to_jsonb(OLD);
        v_new_json := NULL;
    END IF;

    SELECT row_hash
    INTO v_prev_hash
    FROM permitme.audit_logs
    WHERE row_hash IS NOT NULL
    ORDER BY id DESC
    LIMIT 1;

    v_prev_hash := COALESCE(v_prev_hash, 'GENESIS');
    v_payload := CONCAT_WS(
        '|',
        v_prev_hash,
        TG_TABLE_NAME,
        v_record_id,
        v_op,
        COALESCE(v_old_json::TEXT, ''),
        COALESCE(v_new_json::TEXT, '')
    );
    v_hash := encode(digest(v_payload, 'sha256'), 'hex');

    INSERT INTO permitme.audit_logs (
        table_name, record_id, action, old_data, new_data, prev_hash, row_hash
    )
    VALUES (
        TG_TABLE_NAME, v_record_id, v_op, v_old_json, v_new_json, v_prev_hash, v_hash
    );

    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_applications ON permitme.permit_applications;
CREATE TRIGGER trg_audit_applications
AFTER INSERT OR UPDATE OR DELETE ON permitme.permit_applications
FOR EACH ROW
EXECUTE FUNCTION permitme.fn_chained_audit_log();

DROP TRIGGER IF EXISTS trg_audit_credentials ON permitme.credentials;
CREATE TRIGGER trg_audit_credentials
AFTER INSERT OR UPDATE OR DELETE ON permitme.credentials
FOR EACH ROW
EXECUTE FUNCTION permitme.fn_chained_audit_log();

CREATE OR REPLACE VIEW permitme.v_sla_risk_monitor AS
SELECT
    pa.id AS application_id,
    pa.reference_no,
    o.code AS office_code,
    pt.code AS permit_code,
    pt.title AS permit_title,
    app.full_or_business_name AS applicant_name,
    pa.status,
    pa.priority_score,
    pa.sla_due_at,
    CASE
        WHEN pa.sla_due_at IS NULL THEN 'NO_SLA'
        WHEN pa.status IN ('approved', 'rejected', 'revoked') THEN 'CLOSED'
        WHEN pa.sla_due_at < NOW() THEN 'BREACHED'
        WHEN pa.sla_due_at <= NOW() + INTERVAL '24 hours' THEN 'AT_RISK'
        ELSE 'ON_TRACK'
    END AS sla_health,
    ROUND(EXTRACT(EPOCH FROM (COALESCE(pa.sla_due_at, NOW()) - NOW())) / 3600.0, 1) AS hours_until_sla_due
FROM permitme.permit_applications pa
JOIN permitme.offices o ON o.id = pa.office_id
JOIN permitme.permit_types pt ON pt.id = pa.permit_type_id
JOIN permitme.applicants app ON app.id = pa.applicant_id;

CREATE OR REPLACE PROCEDURE permitme.sp_record_inspection(
    p_application_id BIGINT,
    p_inspector_id BIGINT,
    p_inspection_type TEXT,
    p_outcome TEXT,
    p_findings TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_outcome NOT IN ('passed', 'failed', 'conditional') THEN
        RAISE EXCEPTION 'Invalid inspection outcome: %', p_outcome;
    END IF;

    INSERT INTO permitme.inspection_logs (
        application_id, inspector_id, inspection_type, outcome, findings, inspected_at
    )
    VALUES (
        p_application_id, p_inspector_id, p_inspection_type, p_outcome, p_findings, NOW()
    );

    UPDATE permitme.permit_applications
    SET status = CASE
            WHEN p_outcome = 'passed' THEN 'fee_pending'
            WHEN p_outcome = 'conditional' THEN 'rfi_pending'
            ELSE 'rejected'
        END,
        notes = COALESCE(notes || E'\n', '') || '[Inspection ' || p_outcome || ']: ' || COALESCE(p_findings, '')
    WHERE id = p_application_id;
END;
$$;

CREATE OR REPLACE PROCEDURE permitme.sp_renew_credential(
    p_existing_credential_id BIGINT,
    OUT p_new_application_id BIGINT,
    p_actor_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_old_cred permitme.credentials%ROWTYPE;
    v_old_app permitme.permit_applications%ROWTYPE;
    v_validity_days INT;
    v_base_fee NUMERIC(12, 2);
    v_sla_hours INT;
    v_new_ref TEXT;
    v_new_permit_no TEXT;
    v_new_verify_code TEXT;
BEGIN
    SELECT * INTO v_old_cred
    FROM permitme.credentials
    WHERE id = p_existing_credential_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Credential % not found', p_existing_credential_id;
    END IF;

    SELECT * INTO v_old_app
    FROM permitme.permit_applications
    WHERE id = v_old_cred.application_id;

    SELECT validity_days, base_fee, sla_hours
    INTO v_validity_days, v_base_fee, v_sla_hours
    FROM permitme.permit_types
    WHERE id = v_old_app.permit_type_id;

    INSERT INTO permitme.permit_applications (
        reference_no, applicant_id, permit_type_id, office_id,
        assigned_staff_id, status, submitted_at, sla_due_at, notes
    )
    VALUES (
        'TMP-REN-' || EXTRACT(EPOCH FROM NOW())::BIGINT::TEXT,
        v_old_app.applicant_id,
        v_old_app.permit_type_id,
        v_old_app.office_id,
        p_actor_id,
        'approved',
        NOW(),
        NOW() + (v_sla_hours || ' hours')::INTERVAL,
        'Renewal of credential ' || v_old_cred.permit_number
    )
    RETURNING id INTO p_new_application_id;

    v_new_ref := 'PRM-REN-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD(p_new_application_id::TEXT, 6, '0');
    v_new_permit_no := 'LIC-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(p_new_application_id::TEXT, 6, '0');
    v_new_verify_code := 'VER-' || p_new_application_id || '-' || FLOOR(100000 + RANDOM() * 900000)::INT::TEXT;

    UPDATE permitme.permit_applications
    SET reference_no = v_new_ref
    WHERE id = p_new_application_id;

    INSERT INTO permitme.credentials (
        application_id, permit_number, verification_code,
        fee_amount, fee_paid, issued_at, expires_at, is_active,
        renewed_from_credential_id
    )
    VALUES (
        p_new_application_id, v_new_permit_no, v_new_verify_code,
        v_base_fee, TRUE, NOW(), NOW() + (v_validity_days || ' days')::INTERVAL, TRUE,
        v_old_cred.id
    );
END;
$$;