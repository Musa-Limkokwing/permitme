from typing import Any, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from database.db_manager import PermitMeDatabaseManager
from src.ui.svg_icons import render_svg_icon
from src.ui.workstation_app import PermitMeEmblemWidget, _apply_glass_shadow


class LoginDialog(QDialog):
    """Authenticates workstation operators against permitme.app_users."""

    def __init__(self, db: PermitMeDatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.authenticated_user: Optional[dict[str, Any]] = None

        self.setWindowTitle("PermitMe — Operator Sign In")
        self.setMinimumSize(460, 520)
        self.setModal(True)

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#070D18"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
        self.setPalette(pal)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("LoginCard")
        _apply_glass_shadow(card, blur=32, y_offset=10)
        card.setStyleSheet(
            """
            QFrame#LoginCard {
                background-color: rgba(11, 18, 33, 0.90);
                border: 1px solid rgba(94, 234, 212, 0.35);
                border-radius: 18px;
            }
            QLabel#BrandTitle {
                color: #FFFFFF;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#BrandSub {
                color: #5EEAD4;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#FieldLabel {
                color: #E2E8F0;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#ErrorBanner {
                background-color: rgba(248, 113, 113, 0.16);
                border: 1px solid rgba(248, 113, 113, 0.55);
                border-radius: 10px;
                color: #FCA5A5;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 12px;
            }
            QLineEdit#AuthInput {
                background-color: #091120;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 10px;
                padding: 11px 13px;
                font-size: 13px;
            }
            QLineEdit#AuthInput:focus {
                border: 1.5px solid #5EEAD4;
                background-color: #0D182D;
            }
            QPushButton#SignInBtn {
                background-color: #5EEAD4;
                color: #042F2E;
                border: 1px solid #99F6E4;
                border-radius: 10px;
                padding: 11px 16px;
                font-size: 13.5px;
                font-weight: 800;
            }
            QPushButton#SignInBtn:hover {
                background-color: #99F6E4;
            }
            QPushButton#CancelBtn {
                background-color: #121E33;
                color: #E2E8F0;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#CancelBtn:hover {
                border-color: #5EEAD4;
                color: #FFFFFF;
            }
            """
        )

        lay = QVBoxLayout(card)
        lay.setContentsMargins(26, 26, 26, 24)
        lay.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        emblem = PermitMeEmblemWidget(size=42)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t_lbl = QLabel("PermitMe Sign In")
        t_lbl.setObjectName("BrandTitle")
        s_lbl = QLabel("Civic Licensing & Regulatory Suite")
        s_lbl.setObjectName("BrandSub")
        title_col.addWidget(t_lbl)
        title_col.addWidget(s_lbl)
        hdr.addWidget(emblem)
        hdr.addLayout(title_col, 1)
        lay.addLayout(hdr)

        desc = QLabel(
            "Sign in with your assigned officer credentials to access queues, inspections, and credentials."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #CBD5E1; font-size: 12px;")
        lay.addWidget(desc)

        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("ErrorBanner")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        lay.addWidget(self.error_lbl)

        u_lbl = QLabel("Username")
        u_lbl.setObjectName("FieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setObjectName("AuthInput")
        self.username_input.setPlaceholderText("Enter username (e.g. Musa)")
        self.username_input.returnPressed.connect(self._attempt_login)

        p_lbl = QLabel("Password")
        p_lbl.setObjectName("FieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("AuthInput")
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self._attempt_login)

        lay.addWidget(u_lbl)
        lay.addWidget(self.username_input)
        lay.addWidget(p_lbl)
        lay.addWidget(self.password_input)

        lay.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Exit")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)

        self.login_btn = QPushButton("  Sign In to Workstation")
        self.login_btn.setObjectName("SignInBtn")
        self.login_btn.setIcon(render_svg_icon("verified_badge", size=16, color="#042F2E"))
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._attempt_login)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.login_btn, 1)
        lay.addLayout(btn_row)

        root.addWidget(card)

    def _show_error(self, message: str):
        self.error_lbl.setText(message)
        self.error_lbl.show()

    def _attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self._show_error("Both username and password are required.")
            return

        self.login_btn.setEnabled(False)
        self.error_lbl.hide()
        try:
            rows = (
                self.db.fetch_all(
                    "SELECT user_id, username, full_name, role_title, office_hub "
                    "FROM permitme.fn_authenticate_user(%s, %s);",
                    (username, password),
                )
                or []
            )
            if not rows:
                self._show_error("Invalid username or password, or account is inactive.")
                self.password_input.clear()
                self.password_input.setFocus()
                return

            self.authenticated_user = rows[0]
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Authentication Error", f"Could not verify credentials: {exc}")
        finally:
            self.login_btn.setEnabled(True)