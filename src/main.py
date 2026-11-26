import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
from database.db_manager import PermitMeDatabaseManager
from src.ui.login_dialog import LoginDialog
from src.ui.workstation_app import PermitMeEnterpriseWorkstation


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

    app = QApplication(sys.argv)
    app.setApplicationName("PermitMe — Civic Licensing & Regulatory Suite")

    db_url = (
        os.getenv("SUPABASE_POOLER_URI", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )
    signing_secret = os.getenv(
        "PERMITME_SIGNING_SECRET", "permitme-default-signing-secret"
    ).strip()

    if not db_url:
        QMessageBox.critical(
            None,
            "Configuration Missing",
            "Neither SUPABASE_POOLER_URI nor DATABASE_URL is set in .env.",
        )
        return 1

    try:
        db = PermitMeDatabaseManager(db_url)
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Database Connection Failed",
            f"Could not connect to PostgreSQL / Supabase:\n{exc}",
        )
        return 1

    login_dlg = LoginDialog(db)
    if login_dlg.exec() != QDialog.DialogCode.Accepted or not login_dlg.authenticated_user:
        return 0

    conn_meta = {
        "user": login_dlg.authenticated_user,
    }

    window = PermitMeEnterpriseWorkstation(db, signing_secret, conn_meta)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())