import hashlib
import hmac
from typing import Any, Optional
from database.db_manager import PermitMeDatabaseManager


class CredentialService:
    def __init__(self, db: PermitMeDatabaseManager, signing_secret: str):
        self.db = db
        self.signing_secret = (signing_secret or "permitme-default-signing-secret").encode("utf-8")

    # ---------------- CRYPTOGRAPHIC SIGNING & VERIFICATION ----------------
    def sign_credential(self, permit_number: str, verification_code: str, expires_iso: str) -> str:
        canonical = f"{permit_number.strip()}|{verification_code.strip()}|{expires_iso.strip()}"
        return hmac.new(self.signing_secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_signature(
        self,
        permit_number: str,
        verification_code: str,
        expires_iso: str,
        provided_hmac: str,
    ) -> bool:
        expected = self.sign_credential(permit_number, verification_code, expires_iso)
        return hmac.compare_digest(expected, provided_hmac.strip().lower())

    # ---------------- READ QUERIES (SAFE FALLBACKS) ----------------
    def get_sla_risk_queue(self, limit: int = 200) -> list[dict[str, Any]]:
        sql = """
            SELECT
                pa.id AS application_id,
                pa.reference_no,
                COALESCE(o.code, 'N/A') AS office_code,
                COALESCE(a.full_or_business_name, 'Unknown Applicant') AS applicant_name,
                pa.status,
                CASE
                    WHEN pa.sla_due_at IS NOT NULL AND pa.sla_due_at < NOW() THEN 'BREACHED'
                    ELSE 'AT_RISK'
                END AS sla_health,
                COALESCE(
                    ROUND(EXTRACT(EPOCH FROM (pa.sla_due_at - NOW())) / 3600.0, 1),
                    0
                ) AS hours_until_sla_due
            FROM permitme.permit_applications pa
            LEFT JOIN permitme.offices o ON o.id = pa.office_id
            LEFT JOIN permitme.applicants a ON a.id = pa.applicant_id
            WHERE pa.status NOT IN ('approved', 'rejected', 'withdrawn')
            ORDER BY pa.sla_due_at ASC NULLS LAST, pa.id ASC
            LIMIT %s;
        """
        return self.db.fetch_all(sql, (limit,)) or []

    def get_recent_applications(self, limit: int = 250) -> list[dict[str, Any]]:
        sql = """
            SELECT
                pa.id,
                pa.reference_no,
                COALESCE(a.full_or_business_name, 'Unknown Applicant') AS applicant_name,
                COALESCE(pt.title, 'Permit') AS permit_title,
                pa.status,
                COALESCE(pa.priority_score, 0) AS priority_score
            FROM permitme.permit_applications pa
            LEFT JOIN permitme.applicants a ON a.id = pa.applicant_id
            LEFT JOIN permitme.permit_types pt ON pt.id = pa.permit_type_id
            ORDER BY pa.id ASC
            LIMIT %s;
        """
        return self.db.fetch_all(sql, (limit,)) or []

    def get_recent_credentials(self, limit: int = 250) -> list[dict[str, Any]]:
        sql = """
            SELECT
                c.id,
                c.permit_number,
                c.verification_code,
                COALESCE(a.full_or_business_name, 'Unknown Holder') AS applicant_name,
                c.is_active,
                c.expires_at
            FROM permitme.credentials c
            LEFT JOIN permitme.permit_applications pa ON pa.id = c.application_id
            LEFT JOIN permitme.applicants a ON a.id = pa.applicant_id
            ORDER BY c.id ASC
            LIMIT %s;
        """
        return self.db.fetch_all(sql, (limit,)) or []

    def lookup_credential(self, permit_number: str) -> Optional[dict[str, Any]]:
        sql = """
            SELECT
                c.id,
                c.application_id,
                c.permit_number,
                c.verification_code,
                c.fee_amount,
                c.fee_paid,
                c.issued_at,
                c.expires_at,
                c.is_active,
                c.revoked_at,
                c.revocation_reason,
                c.renewed_from_credential_id,
                COALESCE(a.full_or_business_name, 'Unknown Holder') AS applicant_name,
                COALESCE(pt.title, 'Permit') AS permit_title
            FROM permitme.credentials c
            LEFT JOIN permitme.permit_applications pa ON pa.id = c.application_id
            LEFT JOIN permitme.applicants a ON a.id = pa.applicant_id
            LEFT JOIN permitme.permit_types pt ON pt.id = pa.permit_type_id
            WHERE LOWER(c.permit_number) = LOWER(%s)
            LIMIT 1;
        """
        rows = self.db.fetch_all(sql, (permit_number.strip(),)) or []
        return rows[0] if rows else None

    # ---------------- WRITE WORKFLOWS ----------------
    def record_inspection(
        self,
        application_id: int,
        inspector_id: int,
        inspection_type: str,
        outcome: str,
        findings: str,
    ) -> None:
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "CALL permitme.sp_record_inspection(%s, %s, %s, %s, %s);",
                    (application_id, inspector_id, inspection_type, outcome, findings),
                )

    def renew_credential(self, credential_id: int) -> int:
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.id,
                        pa.applicant_id,
                        pa.permit_type_id,
                        pa.office_id
                    FROM permitme.credentials c
                    JOIN permitme.permit_applications pa ON pa.id = c.application_id
                    WHERE c.id = %s;
                    """,
                    (credential_id,),
                )
                src = cur.fetchone()
                if not src:
                    raise ValueError(f"Credential #{credential_id} was not found.")

                cur.execute(
                    """
                    INSERT INTO permitme.permit_applications (
                        reference_no, applicant_id, permit_type_id, office_id, status, notes
                    )
                    VALUES (
                        'REN-' || EXTRACT(EPOCH FROM NOW())::BIGINT::TEXT || '-' || (FLOOR(RANDOM() * 9000 + 1000))::INT::TEXT,
                        %s, %s, %s, 'draft', %s
                    )
                    RETURNING id;
                    """,
                    (
                        src["applicant_id"],
                        src["permit_type_id"],
                        src["office_id"],
                        f"Renewal initiated from Credential #{credential_id}.",
                    ),
                )
                new_row = cur.fetchone()
                if not new_row or new_row.get("id") is None:
                    raise RuntimeError("Renewal application insert did not return an ID.")
                new_app_id = int(new_row["id"])
                cur.execute("CALL permitme.sp_submit_application(%s, NULL);", (new_app_id,))
                return new_app_id