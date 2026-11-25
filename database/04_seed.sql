INSERT INTO permitme.offices (code, name, jurisdiction)
VALUES
    ('HQ-01', 'Central Licensing & Permits Hub', 'Metro District'),
    ('INS-02', 'Field Safety & Compliance Directorate', 'Regional Zone')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permitme.staff_users (office_id, full_name, email, role)
SELECT o.id, 'Amina Sesay', 'amina.sesay@permitme.gov', 'inspector'
FROM permitme.offices o WHERE o.code = 'INS-02'
ON CONFLICT (email) DO NOTHING;

INSERT INTO permitme.applicants (applicant_type, full_or_business_name, tax_or_reg_id, phone, email, is_verified)
VALUES
    ('business', 'Atlantic Cold Chain Ltd', 'REG-884210', '+232-76-000101', 'ops@atlanticcoldchain.example', TRUE),
    ('sole_proprietor', 'Kadiatu Bangura Bakery', 'TIN-440912', '+232-77-000202', 'kadiatu@bangurabakery.example', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO permitme.permit_types (code, title, validity_days, base_fee, sla_hours, required_docs)
VALUES
    ('BL-GEN', 'Commercial Operating License', 365, 250.00, 72, '["business_reg", "tax_clearance", "premises_lease"]'::jsonb),
    ('FP-SAF', 'Food & Cold Storage Safety Permit', 180, 150.00, 48, '["hygiene_plan", "equipment_log"]'::jsonb)
ON CONFLICT (code) DO NOTHING;

INSERT INTO permitme.permit_applications (
    reference_no, applicant_id, permit_type_id, office_id, status, sla_due_at, notes
)
SELECT
    'PRM-20261123-000001',
    app.id,
    pt.id,
    o.id,
    'inspection_pending',
    NOW() + INTERVAL '6 hours',
    'Priority cold-room compliance inspection'
FROM permitme.applicants app
CROSS JOIN permitme.permit_types pt
CROSS JOIN permitme.offices o
WHERE app.full_or_business_name = 'Atlantic Cold Chain Ltd'
  AND pt.code = 'FP-SAF'
  AND o.code = 'INS-02'
  AND NOT EXISTS (
      SELECT 1 FROM permitme.permit_applications WHERE reference_no = 'PRM-20261123-000001'
  );