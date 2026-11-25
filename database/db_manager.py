from contextlib import contextmanager
from typing import Any, Optional
import psycopg
from psycopg.rows import dict_row


class PermitMeDatabaseManager:
    def __init__(self, pooler_uri: str):
        self.pooler_uri = pooler_uri

    @contextmanager
    def connection(self):
        with psycopg.connect(self.pooler_uri, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO permitme, public;")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return list(cur.fetchall())

    def call_procedure(self, proc_name: str, params: tuple[Any, ...] = ()) -> None:
        placeholders = ", ".join(["%s"] * len(params))
        sql = f"CALL permitme.{proc_name}({placeholders});"
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    def get_office_queue_summary(self) -> list[dict[str, Any]]:
        return self.fetch_all(
            "SELECT * FROM permitme.v_office_queue_summary ORDER BY office_code, status;"
        )

    def get_expiring_credentials(self) -> list[dict[str, Any]]:
        return self.fetch_all(
            "SELECT * FROM permitme.v_expiring_credentials ORDER BY days_remaining ASC;"
        )

    def submit_application(self, application_id: int, actor_id: Optional[int] = None) -> None:
        self.call_procedure("sp_submit_application", (application_id, actor_id))

    def issue_credential(self, application_id: int, fee_paid: bool = True) -> None:
        self.call_procedure("sp_issue_credential", (application_id, fee_paid))