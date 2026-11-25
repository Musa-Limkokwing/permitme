import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.config.db_config import describe_connection, get_signing_secret, get_supabase_pooler_uri
from database.db_manager import PermitMeDatabaseManager
from src.ui.workstation_app import PermitMeEnterpriseWorkstation


def main():
    app = QApplication(sys.argv)
    try:
        pooler_uri = get_supabase_pooler_uri()
        signing_secret = get_signing_secret()
        conn_meta = describe_connection(pooler_uri)
        db = PermitMeDatabaseManager(pooler_uri)
    except Exception as exc:
        QMessageBox.critical(None, "Startup Configuration Error", str(exc))
        sys.exit(1)

    window = PermitMeEnterpriseWorkstation(
        db=db,
        signing_secret=signing_secret,
        conn_meta=conn_meta,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()