CREATE OR REPLACE VIEW permitme.v_office_queue_summary AS
SELECT
    o.code AS office_code,
    o.name AS office_name,
    a.status,
    COUNT(*) AS case_count,
    COUNT(*) FILTER (
        WHERE a.sla_due_at IS NOT NULL
          AND a.sla_due_at < NOW()
          AND a.status NOT IN ('approved', 'rejected', 'revoked')
    ) AS overdue_count
FROM permitme.permit_applications a
JOIN permitme.offices o ON o.id = a.office_id
GROUP BY o.code, o.name, a.status;

CREATE OR REPLACE VIEW permitme.v_expiring_credentials AS
SELECT
    c.permit_number,
    c.verification_code,
    app.full_or_business_name AS applicant_name,
    pt.title AS permit_title,
    c.expires_at,
    EXTRACT(DAY FROM (c.expires_at - NOW()))::INT AS days_remaining
FROM permitme.credentials c
JOIN permitme.permit_applications pa ON pa.id = c.application_id
JOIN permitme.applicants app ON app.id = pa.applicant_id
JOIN permitme.permit_types pt ON pt.id = pa.permit_type_id
WHERE c.is_active = TRUE
  AND c.expires_at <= NOW() + INTERVAL '30 days';

CREATE OR REPLACE FUNCTION permitme.fn_update_application_priority()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := NOW();
    IF NEW.status IN ('inspection_pending', 'rfi_pending') THEN
        NEW.priority_score := 80;
    ELSIF NEW.sla_due_at IS NOT NULL AND NEW.sla_due_at <= NOW() + INTERVAL '24 hours' THEN
        NEW.priority_score := 95;
    ELSIF NEW.status = 'submitted' THEN
        NEW.priority_score := 65;
    ELSE
        NEW.priority_score := 50;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_app_priority ON permitme.permit_applications;
CREATE TRIGGER trg_app_priority
BEFORE INSERT OR UPDATE ON permitme.permit_applications
FOR EACH ROW
EXECUTE FUNCTION permitme.fn_update_application_priority();

CREATE OR REPLACE PROCEDURE permitme.sp_submit_application(
    p_application_id BIGINT,
    p_actor_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sla_hours INT;
    v_ref TEXT;
BEGIN
    SELECT pt.sla_hours
    INTO v_sla_hours
    FROM permitme.permit_applications pa
    JOIN permitme.permit_types pt ON pt.id = pa.permit_type_id
    WHERE pa.id = p_application_id;

    IF v_sla_hours IS NULL THEN
        RAISE EXCEPTION 'Application % not found', p_application_id;
    END IF;

    v_ref := 'PRM-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD(p_application_id::TEXT, 6, '0');

    UPDATE permitme.permit_applications
    SET reference_no = COALESCE(reference_no, v_ref),
        status = 'submitted',
        submitted_at = COALESCE(submitted_at, NOW()),
        sla_due_at = NOW() + (v_sla_hours || ' hours')::INTERVAL,
        assigned_staff_id = COALESCE(assigned_staff_id, p_actor_id)
    WHERE id = p_application_id;
END;
$$;

CREATE OR REPLACE PROCEDURE permitme.sp_issue_credential(
    p_application_id BIGINT,
    p_fee_paid BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_validity_days INT;
    v_base_fee NUMERIC(12, 2);
    v_permit_no TEXT;
    v_verify_code TEXT;
BEGIN
    SELECT pt.validity_days, pt.base_fee
    INTO v_validity_days, v_base_fee
    FROM permitme.permit_applications pa
    JOIN permitme.permit_types pt ON pt.id = pa.permit_type_id
    WHERE pa.id = p_application_id;

    IF v_validity_days IS NULL THEN
        RAISE EXCEPTION 'Application % not found', p_application_id;
    END IF;

    v_permit_no := 'LIC-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(p_application_id::TEXT, 6, '0');
    v_verify_code := 'VER-' || p_application_id || '-' || FLOOR(100000 + RANDOM() * 900000)::INT::TEXT;

    INSERT INTO permitme.credentials (
        application_id, permit_number, verification_code,
        fee_amount, fee_paid, issued_at, expires_at, is_active
    )
    VALUES (
        p_application_id, v_permit_no, v_verify_code,
        v_base_fee, p_fee_paid, NOW(), NOW() + (v_validity_days || ' days')::INTERVAL, TRUE
    )
    ON CONFLICT (application_id) DO UPDATE
    SET fee_paid = EXCLUDED.fee_paid,
        issued_at = NOW(),
        expires_at = EXCLUDED.expires_at,
        is_active = TRUE;

    UPDATE permitme.permit_applications
    SET status = CASE WHEN p_fee_paid THEN 'approved' ELSE 'fee_pending' END
    WHERE id = p_application_id;
END;
$$;