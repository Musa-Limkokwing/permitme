import math
import tempfile
from pathlib import Path
from typing import Any, Optional
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QShortcut,
    QTransform,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleFactory,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from database.db_manager import PermitMeDatabaseManager
from src.services.credential_service import CredentialService
from src.ui.svg_icons import render_svg_icon, render_svg_pixmap, write_chevron_svg_file
from src.ui.theme import build_workstation_stylesheet


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None or isinstance(val, bool):
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        try:
            return int(float(str(val).strip()))
        except (TypeError, ValueError):
            return default


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val)


def _cell_text(table: QTableWidget, row: int, col: int) -> str:
    if row < 0 or col < 0 or row >= table.rowCount() or col >= table.columnCount():
        return ""
    item = table.item(row, col)
    return item.text().strip() if item is not None else ""


class DarkComboItemDelegate(QStyledItemDelegate):
    """Custom item painter guaranteeing zero white native macOS popup rows."""

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = option.rect.adjusted(3, 2, -3, -2)
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        if is_hovered:
            bg = QColor("#5EEAD4")
            fg = QColor("#042F2E")
            weight = QFont.Weight.Bold
        elif is_selected:
            bg = QColor("#134E4A")
            fg = QColor("#99F6E4")
            weight = QFont.Weight.Bold
        else:
            bg = QColor("#091120")
            fg = QColor("#F8FAFC")
            weight = QFont.Weight.DemiBold

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 7.0, 7.0)
        painter.fillPath(path, bg)

        font = option.font
        font.setWeight(weight)
        painter.setFont(font)
        painter.setPen(fg)

        text_rect = rect.adjusted(10, 0, -10, 0)
        text = _safe_str(index.data(Qt.ItemDataRole.DisplayRole))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(36, base.height() + 12))


class PermitMeEmblemWidget(QWidget):
    """Custom geometric seal + notched charter frame for PermitMe (bg-teal-300 theme)."""

    def __init__(self, size: int = 38, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        s = float(self._size)
        pad = s * 0.10
        w = s - 2 * pad
        h = s - 2 * pad
        cut = w * 0.24

        plate = QPainterPath()
        plate.moveTo(pad, pad)
        plate.lineTo(pad + w - cut, pad)
        plate.lineTo(pad + w, pad + cut)
        plate.lineTo(pad + w, pad + h)
        plate.lineTo(pad + cut, pad + h)
        plate.lineTo(pad, pad + h - cut)
        plate.closeSubpath()

        grad = QLinearGradient(pad, pad, pad + w, pad + h)
        grad.setColorAt(0.0, QColor("#115E59"))
        grad.setColorAt(1.0, QColor("#0F2942"))

        painter.fillPath(plate, grad)
        painter.setPen(QPen(QColor("#5EEAD4"), 1.6))
        painter.drawPath(plate)

        cx, cy = s * 0.5, s * 0.5
        r_outer = s * 0.24
        poly = QPainterPath()
        points = 8
        for i in range(points * 2):
            radius = r_outer if i % 2 == 0 else r_outer * 0.72
            angle = (math.pi / points) * i - math.pi / 2
            px = cx + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            if i == 0:
                poly.moveTo(QPointF(px, py))
            else:
                poly.lineTo(QPointF(px, py))
        poly.closeSubpath()

        painter.setPen(QPen(QColor("#99F6E4"), 1.25))
        painter.drawPath(poly)

        mark = QPainterPath()
        mark.moveTo(QPointF(cx - s * 0.08, cy + s * 0.01))
        mark.lineTo(QPointF(cx - s * 0.015, cy + s * 0.08))
        mark.lineTo(QPointF(cx + s * 0.10, cy - s * 0.07))
        painter.setPen(
            QPen(
                QColor("#5EEAD4"),
                2.1,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        painter.drawPath(mark)


class CircularProfileAvatarWidget(QWidget):
    """Borderless circular portrait avatar rendering nice_profile.jpg with live presence dot."""

    def __init__(self, image_path: Path, size: int = 44, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._pixmap = QPixmap(str(image_path)) if image_path.exists() else QPixmap()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        s = float(self._size)
        avatar_rect = QRectF(0.0, 0.0, s, s)

        clip_path = QPainterPath()
        clip_path.addEllipse(avatar_rect)
        painter.save()
        painter.setClipPath(clip_path)

        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                int(s),
                int(s),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = (scaled.width() - int(s)) // 2
            oy = (scaled.height() - int(s)) // 2
            painter.drawPixmap(0, 0, scaled, ox, oy, int(s), int(s))
        else:
            painter.fillRect(avatar_rect, QColor("#5EEAD4"))
            painter.setPen(QColor("#042F2E"))
            font = QFont("SF Pro Display", 13, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(avatar_rect, Qt.AlignmentFlag.AlignCenter, "PM")

        painter.restore()

        dot_r = 5.0
        dot_cx = s - dot_r - 1.0
        dot_cy = s - dot_r - 1.0
        painter.setPen(QPen(QColor("#0B1324"), 2.0))
        painter.setBrush(QColor("#5EEAD4"))
        painter.drawEllipse(QPointF(dot_cx, dot_cy), dot_r, dot_r)


def _apply_glass_shadow(widget: QWidget, blur: int = 24, y_offset: int = 6) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(2, 6, 23, 95))
    widget.setGraphicsEffect(shadow)


def _style_combo(combo: QComboBox, items: list[tuple[str, str]]) -> None:
    """Force Fusion style + dark popup container + custom delegate so macOS never renders white."""
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        combo.setStyle(fusion)

    combo.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    combo.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)

    view = QListView(combo)
    if fusion is not None:
        view.setStyle(fusion)
    view.setMouseTracking(True)
    view.setUniformItemSizes(True)
    view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    view.setAutoFillBackground(True)
    view.setItemDelegate(DarkComboItemDelegate(view))

    pal = view.palette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        pal.setColor(group, QPalette.ColorRole.Base, QColor("#091120"))
        pal.setColor(group, QPalette.ColorRole.Window, QColor("#091120"))
        pal.setColor(group, QPalette.ColorRole.AlternateBase, QColor("#091120"))
        pal.setColor(group, QPalette.ColorRole.Text, QColor("#F8FAFC"))
        pal.setColor(group, QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
        pal.setColor(group, QPalette.ColorRole.Highlight, QColor("#5EEAD4"))
        pal.setColor(group, QPalette.ColorRole.HighlightedText, QColor("#042F2E"))
    view.setPalette(pal)

    combo_pal = combo.palette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        combo_pal.setColor(group, QPalette.ColorRole.Button, QColor("#0D182D"))
        combo_pal.setColor(group, QPalette.ColorRole.Base, QColor("#0D182D"))
        combo_pal.setColor(group, QPalette.ColorRole.Window, QColor("#0D182D"))
        combo_pal.setColor(group, QPalette.ColorRole.ButtonText, QColor("#F8FAFC"))
        combo_pal.setColor(group, QPalette.ColorRole.Text, QColor("#F8FAFC"))
        combo_pal.setColor(group, QPalette.ColorRole.Highlight, QColor("#5EEAD4"))
        combo_pal.setColor(group, QPalette.ColorRole.HighlightedText, QColor("#042F2E"))
    combo.setPalette(combo_pal)

    combo.setView(view)

    popup_container = view.parentWidget()
    if popup_container is not None:
        popup_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup_container.setAutoFillBackground(True)
        popup_container.setPalette(pal)
        popup_container.setStyleSheet(
            "background-color: #091120; border: 1.5px solid #5EEAD4; border-radius: 10px;"
        )

    combo.clear()
    for display_text, raw_value in items:
        combo.addItem(display_text, raw_value)


def _build_kpi_card(
    title: str,
    subtitle: str,
    value_label: QLabel,
    accent_hex: str,
    svg_name: str,
) -> QFrame:
    card = QFrame()
    card.setObjectName("KpiCard")
    _apply_glass_shadow(card)

    outer = QHBoxLayout(card)
    outer.setContentsMargins(0, 0, 16, 0)
    outer.setSpacing(14)

    accent_bar = QFrame()
    accent_bar.setFixedWidth(5)
    accent_bar.setStyleSheet(
        f"background-color: {accent_hex}; border-radius: 0px;"
    )
    outer.addWidget(accent_bar)

    content = QVBoxLayout()
    content.setContentsMargins(2, 14, 2, 14)
    content.setSpacing(3)

    t_lbl = QLabel(title)
    t_lbl.setObjectName("KpiTitle")
    s_lbl = QLabel(subtitle)
    s_lbl.setObjectName("SectionHint")

    content.addWidget(t_lbl)
    content.addWidget(value_label)
    content.addWidget(s_lbl)
    outer.addLayout(content)
    outer.addStretch()

    icon_badge = QLabel()
    icon_badge.setFixedSize(40, 40)
    icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_badge.setStyleSheet(
        "background-color: rgba(255, 255, 255, 0.06); "
        "border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 0px;"
    )
    icon_badge.setPixmap(render_svg_pixmap(svg_name, size=20, color=accent_hex))
    outer.addWidget(icon_badge)
    return card


class NewApplicationDialog(QDialog):
    def __init__(
        self,
        applicants: list[dict[str, Any]],
        permit_types: list[dict[str, Any]],
        offices: list[dict[str, Any]],
        db: PermitMeDatabaseManager,
        parent: QWidget,
    ):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("New Permit Application Intake")
        self.setMinimumWidth(500)
        self.setAutoFillBackground(True)
        dlg_pal = self.palette()
        dlg_pal.setColor(QPalette.ColorRole.Window, QColor("#0B1324"))
        dlg_pal.setColor(QPalette.ColorRole.WindowText, QColor("#F8FAFC"))
        self.setPalette(dlg_pal)
        self.setStyleSheet(
            "QDialog { background-color: #0B1324; border: 1.5px solid #5EEAD4; border-radius: 0px; }"
        )
        self._build_ui()
        self._populate_lookups(applicants, permit_types, offices)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)
        emblem = PermitMeEmblemWidget(size=34)
        title_box = QVBoxLayout()
        title_lbl = QLabel("New Permit & License Application")
        title_lbl.setObjectName("SectionHeading")
        sub_lbl = QLabel("Creates an intake record and assigns an SLA timer on submit.")
        sub_lbl.setObjectName("SectionHint")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        hdr_row.addWidget(emblem)
        hdr_row.addLayout(title_box, 1)
        layout.addLayout(hdr_row)

        form = QFormLayout()
        form.setSpacing(12)

        self.applicant_combo = QComboBox()
        self.permit_type_combo = QComboBox()
        self.office_combo = QComboBox()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(85)
        self.notes_edit.setPlaceholderText("Enter premises address, activity description, or intake notes...")

        form.addRow("Applicant / Entity", self.applicant_combo)
        form.addRow("Permit / License Type", self.permit_type_combo)
        form.addRow("Processing Office", self.office_combo)
        form.addRow("Intake Notes", self.notes_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("OutlineBtn")
        cancel_btn.clicked.connect(self.reject)

        self.submit_btn = QPushButton("  Create & Submit Application")
        self.submit_btn.setObjectName("PrimaryBtn")
        self.submit_btn.setIcon(render_svg_icon("plus_circle", size=16, color="#042F2E"))
        self.submit_btn.clicked.connect(self._handle_create)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.submit_btn)
        layout.addLayout(btn_row)

    def _populate_lookups(
        self,
        applicants: list[dict[str, Any]],
        permit_types: list[dict[str, Any]],
        offices: list[dict[str, Any]],
    ):
        app_items = [
            (_safe_str(r.get("full_or_business_name"), f"Applicant #{r.get('id')}"), _safe_str(r.get("id")))
            for r in (applicants or [])
            if r.get("id") is not None
        ]
        ptype_items = [
            (
                f"{_safe_str(r.get('title'), 'Permit')} ({_safe_str(r.get('code'), 'N/A')} • ${ _safe_str(r.get('base_fee'), '0') })",
                _safe_str(r.get("id")),
            )
            for r in (permit_types or [])
            if r.get("id") is not None
        ]
        office_items = [
            (
                f"{_safe_str(r.get('code'), 'OFF')} — {_safe_str(r.get('name'), 'Office')}",
                _safe_str(r.get("id")),
            )
            for r in (offices or [])
            if r.get("id") is not None
        ]

        _style_combo(self.applicant_combo, app_items or [("No applicants available", "")])
        _style_combo(self.permit_type_combo, ptype_items or [("No permit types available", "")])
        _style_combo(self.office_combo, office_items or [("No offices available", "")])

        has_all = bool(app_items and ptype_items and office_items)
        self.submit_btn.setEnabled(has_all)

    def _handle_create(self):
        app_raw = _safe_str(self.applicant_combo.currentData()).strip()
        ptype_raw = _safe_str(self.permit_type_combo.currentData()).strip()
        off_raw = _safe_str(self.office_combo.currentData()).strip()
        notes = self.notes_edit.toPlainText().strip()

        if not (app_raw.isdigit() and ptype_raw.isdigit() and off_raw.isdigit()):
            QMessageBox.warning(
                self,
                "Missing or Invalid Selection",
                "Please select a valid applicant, permit type, and processing office.",
            )
            return

        applicant_id = int(app_raw)
        permit_type_id = int(ptype_raw)
        office_id = int(off_raw)

        self.submit_btn.setEnabled(False)
        try:
            if not self.db.fetch_all("SELECT id FROM permitme.applicants WHERE id = %s;", (applicant_id,)):
                QMessageBox.warning(self, "Invalid Applicant", f"Applicant #{applicant_id} no longer exists.")
                return
            if not self.db.fetch_all("SELECT id FROM permitme.permit_types WHERE id = %s;", (permit_type_id,)):
                QMessageBox.warning(self, "Invalid Permit Type", f"Permit type #{permit_type_id} no longer exists.")
                return
            if not self.db.fetch_all("SELECT id FROM permitme.offices WHERE id = %s;", (office_id,)):
                QMessageBox.warning(self, "Invalid Office", f"Office #{office_id} no longer exists.")
                return

            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO permitme.permit_applications (
                            reference_no, applicant_id, permit_type_id, office_id, status, notes
                        )
                        VALUES (
                            'TMP-' || EXTRACT(EPOCH FROM NOW())::BIGINT::TEXT || '-' || (FLOOR(RANDOM() * 9000 + 1000))::INT::TEXT,
                            %s, %s, %s, 'draft', %s
                        )
                        RETURNING id;
                        """,
                        (applicant_id, permit_type_id, office_id, notes),
                    )
                    row = cur.fetchone()
                    if not row or row.get("id") is None:
                        raise RuntimeError("Application insert succeeded but returned no ID.")
                    new_id = int(row["id"])
                    cur.execute("CALL permitme.sp_submit_application(%s, NULL);", (new_id,))
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Intake Error", f"Could not create application: {exc}")
        finally:
            self.submit_btn.setEnabled(True)


class PermitMeEnterpriseWorkstation(QWidget):
    def __init__(self, db: PermitMeDatabaseManager, signing_secret: str, conn_meta: dict[str, Any]):
        super().__init__()
        self.db = db
        self.cred_service = CredentialService(db, signing_secret)
        self.conn_meta = conn_meta or {}
        self.current_user: dict[str, Any] = (
            self.conn_meta.get("user") if isinstance(self.conn_meta.get("user"), dict) else {}
        )
        self.last_computed_hmac = ""
        self._is_refreshing = False

        # Spinner state for header & main content section (bg-teal-300 #5EEAD4)
        self._spinner_angle = 0
        self._base_spinner_pixmap = render_svg_pixmap("refresh", size=16, color="#5EEAD4")
        self._main_spinner_pixmap = render_svg_pixmap("refresh", size=34, color="#5EEAD4")
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(45)
        self._spinner_timer.timeout.connect(self._advance_spinner)

        # Two-stage timers so spinner starts on instant press/click and stays visible before modal pops in
        self._intake_fetch_timer = QTimer(self)
        self._intake_fetch_timer.setSingleShot(True)
        self._intake_fetch_timer.timeout.connect(self._fetch_and_schedule_new_application_dialog)

        self._pending_intake_data: Optional[tuple[list, list, list]] = None
        self._intake_launch_timer = QTimer(self)
        self._intake_launch_timer.setSingleShot(True)
        self._intake_launch_timer.timeout.connect(self._finish_open_new_application_dialog)

        img_dir = Path(__file__).resolve().parents[1] / "img"
        img_path = img_dir / "permit.jpg"
        self.profile_img_path = img_dir / "nice_profile.jpg"
        self.bg_pixmap = QPixmap(str(img_path)) if img_path.exists() else QPixmap()

        chevron_file = Path(tempfile.gettempdir()) / "permitme_chevron_down.svg"
        write_chevron_svg_file(str(chevron_file), color="#5EEAD4")
        self.setStyleSheet(build_workstation_stylesheet(chevron_file.as_posix()))

        self.setWindowTitle("PermitMe — Civic Licensing & Regulatory Suite")
        self.resize(1340, 840)

        self._build_ui()
        self._bind_shortcuts()
        self._update_pending_action_preview()
        self.refresh_all()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QColor("#0B1324"))

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(5, 10, 20, 145))
        gradient.setColorAt(0.55, QColor(8, 15, 29, 170))
        gradient.setColorAt(1.0, QColor(4, 9, 18, 200))
        painter.fillRect(self.rect(), gradient)

        super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "main_spinner_overlay") and hasattr(self, "pages_container"):
            self.main_spinner_overlay.setGeometry(self.pages_container.rect())

    def _advance_spinner(self):
        self._spinner_angle = (self._spinner_angle + 36) % 360
        transform = QTransform().rotate(self._spinner_angle)
        self.spinner_icon_lbl.setPixmap(
            self._base_spinner_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        )
        self.main_spinner_icon_lbl.setPixmap(
            self._main_spinner_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        )

    def _set_loading(self, active: bool, message: str = "", show_main_spinner: bool = False):
        if active:
            self._spinner_timer.start()
            self.spinner_icon_lbl.show()
            self.loading_text_lbl.setText(message or "Syncing with Supabase...")
            self.loading_text_lbl.show()
            self.sync_btn.setEnabled(False)
            self.new_app_btn.setEnabled(False)
            if show_main_spinner:
                self.main_spinner_msg_lbl.setText(message or "Preparing application intake...")
                self.main_spinner_overlay.setGeometry(self.pages_container.rect())
                self.main_spinner_overlay.show()
                self.main_spinner_overlay.raise_()
                self.main_spinner_overlay.repaint()
                self.main_spinner_icon_lbl.repaint()
            QGuiApplication.processEvents()
        else:
            self._spinner_timer.stop()
            self.spinner_icon_lbl.hide()
            self.loading_text_lbl.hide()
            self.main_spinner_overlay.hide()
            self.sync_btn.setEnabled(True)
            self.new_app_btn.setEnabled(True)

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.refresh_all)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._start_new_application_flow)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self._switch_page(0))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self._switch_page(1))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self._switch_page(2))

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scrim = QWidget()
        scrim.setObjectName("MainScrim")
        outer_layout.addWidget(scrim)

        shell = QHBoxLayout(scrim)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        # 1. Left Translucent Navigation Rail
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        side_lay = QVBoxLayout(sidebar)
        side_lay.setContentsMargins(16, 22, 16, 18)
        side_lay.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        emblem_lbl = PermitMeEmblemWidget(size=38)

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(1)
        brand_title = QLabel("PermitMe")
        brand_title.setObjectName("SidebarBrand")
        brand_tag = QLabel("Civic Licensing Suite")
        brand_tag.setObjectName("SidebarTagline")
        brand_text_col.addWidget(brand_title)
        brand_text_col.addWidget(brand_tag)

        brand_row.addWidget(emblem_lbl)
        brand_row.addLayout(brand_text_col)
        side_lay.addLayout(brand_row)

        self.new_app_btn = QPushButton("  New Application   ⌘N")
        self.new_app_btn.setObjectName("PrimaryBtn")
        self.new_app_btn.setIcon(render_svg_icon("plus_circle", size=17, color="#042F2E"))
        self.new_app_btn.setIconSize(QSize(17, 17))
        self.new_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_app_btn.clicked.connect(self._start_new_application_flow)
        side_lay.addSpacing(8)
        side_lay.addWidget(self.new_app_btn)

        sec_lbl = QLabel("Workspaces")
        sec_lbl.setObjectName("SidebarSectionLabel")
        side_lay.addWidget(sec_lbl)

        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("  Executive Overview", "dashboard", 0),
            ("  Inspections & Licensing", "clipboard_check", 1),
            ("  Credential Verifier", "verified_badge", 2),
        ]
        for label, icon_name, idx in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("NavBtn")
            btn.setIcon(render_svg_icon(icon_name, size=17, color="#CBD5E1"))
            btn.setIconSize(QSize(17, 17))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, i=idx: self._switch_page(i))
            side_lay.addWidget(btn)
            self.nav_buttons.append(btn)

        side_lay.addStretch()

        # Authenticated Operator Profile Card
        display_name = (
            _safe_str(self.current_user.get("full_name")).strip()
            or _safe_str(self.current_user.get("username")).strip()
            or "Regulatory Officer"
        )
        display_role = (
            _safe_str(self.current_user.get("role_title")).strip()
            or "Inspector & Licensing Lead"
        )
        display_hub = (
            _safe_str(self.current_user.get("office_hub")).strip()
            or "FREETOWN HUB"
        )

        profile_box = QFrame()
        profile_box.setObjectName("SidebarProfileBox")
        profile_box.setMinimumWidth(0)
        prof_outer = QVBoxLayout(profile_box)
        prof_outer.setContentsMargins(12, 12, 12, 12)
        prof_outer.setSpacing(8)

        prof_top_row = QHBoxLayout()
        prof_top_row.setSpacing(10)

        avatar_widget = CircularProfileAvatarWidget(self.profile_img_path, size=44)

        prof_text = QVBoxLayout()
        prof_text.setSpacing(2)
        self.prof_name_lbl = QLabel(display_name)
        self.prof_name_lbl.setMinimumWidth(0)
        self.prof_name_lbl.setWordWrap(True)
        self.prof_name_lbl.setStyleSheet("color: #FFFFFF; font-weight: 800; font-size: 12.5px; background: transparent;")

        self.prof_role_lbl = QLabel(display_role)
        self.prof_role_lbl.setMinimumWidth(0)
        self.prof_role_lbl.setWordWrap(True)
        self.prof_role_lbl.setStyleSheet("color: #5EEAD4; font-size: 10.5px; font-weight: 600; background: transparent;")

        prof_text.addWidget(self.prof_name_lbl)
        prof_text.addWidget(self.prof_role_lbl)

        prof_top_row.addWidget(avatar_widget, 0, Qt.AlignmentFlag.AlignVCenter)
        prof_top_row.addLayout(prof_text, 1)
        prof_outer.addLayout(prof_top_row)

        self.hub_pill_lbl = QLabel(f"ON DUTY • {display_hub.upper()}")
        self.hub_pill_lbl.setMinimumWidth(0)
        self.hub_pill_lbl.setWordWrap(True)
        self.hub_pill_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hub_pill_lbl.setStyleSheet(
            "background-color: #5EEAD4; color: #042F2E; "
            "font-size: 9px; font-weight: 800; letter-spacing: 0.4px; "
            "border: none; border-radius: 7px; padding: 4px 6px;"
        )
        prof_outer.addWidget(self.hub_pill_lbl)
        side_lay.addWidget(profile_box)

        shell.addWidget(sidebar)

        # 2. Right Content Column
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        top_header = QFrame()
        top_header.setObjectName("TopHeader")
        hdr_lay = QHBoxLayout(top_header)
        hdr_lay.setContentsMargins(26, 14, 26, 14)
        hdr_lay.setSpacing(12)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        self.page_title_lbl = QLabel("Executive Overview")
        self.page_title_lbl.setObjectName("PageTitle")
        self.page_sub_lbl = QLabel("Real-time agency queue health, SLA compliance, and active permits.")
        self.page_sub_lbl.setObjectName("PageSubtitle")
        title_stack.addWidget(self.page_title_lbl)
        title_stack.addWidget(self.page_sub_lbl)
        hdr_lay.addLayout(title_stack)

        hdr_lay.addStretch()

        self.spinner_icon_lbl = QLabel()
        self.spinner_icon_lbl.setPixmap(self._base_spinner_pixmap)
        self.spinner_icon_lbl.hide()

        self.loading_text_lbl = QLabel("Syncing...")
        self.loading_text_lbl.setStyleSheet(
            "color: #5EEAD4; font-size: 12px; font-weight: 700; "
            "background-color: rgba(94, 234, 212, 0.16); "
            "border: 1px solid rgba(94, 234, 212, 0.45); "
            "border-radius: 8px; padding: 5px 10px;"
        )
        self.loading_text_lbl.hide()

        hdr_lay.addWidget(self.spinner_icon_lbl)
        hdr_lay.addWidget(self.loading_text_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter tables by applicant, reference, permit #...")
        self.search_input.setMinimumWidth(285)
        self.search_input.addAction(
            render_svg_icon("search", size=15, color="#CBD5E1"),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search_input.textChanged.connect(self._apply_live_filter)
        hdr_lay.addWidget(self.search_input)

        self.sync_btn = QPushButton("  Sync Live Data")
        self.sync_btn.setObjectName("OutlineBtn")
        self.sync_btn.setIcon(render_svg_icon("refresh", size=16, color="#5EEAD4"))
        self.sync_btn.setIconSize(QSize(16, 16))
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.clicked.connect(self.refresh_all)
        hdr_lay.addWidget(self.sync_btn)

        right_col.addWidget(top_header)

        # Container holding stacked pages + centered main-section spinner overlay
        self.pages_container = QWidget()
        pages_lay = QVBoxLayout(self.pages_container)
        pages_lay.setContentsMargins(0, 0, 0, 0)
        pages_lay.setSpacing(0)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_overview_page())
        self.pages.addWidget(self._create_workflows_page())
        self.pages.addWidget(self._create_verifier_page())
        pages_lay.addWidget(self.pages)

        self.main_spinner_overlay = QWidget(self.pages_container)
        self.main_spinner_overlay.setStyleSheet("background-color: rgba(7, 13, 24, 0.52);")
        ov_lay = QVBoxLayout(self.main_spinner_overlay)
        ov_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        spinner_card = QFrame()
        spinner_card.setObjectName("MainSpinnerCard")
        _apply_glass_shadow(spinner_card, blur=30, y_offset=8)
        sc_lay = QVBoxLayout(spinner_card)
        sc_lay.setContentsMargins(28, 22, 28, 22)
        sc_lay.setSpacing(10)
        sc_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_spinner_icon_lbl = QLabel()
        self.main_spinner_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_spinner_icon_lbl.setPixmap(self._main_spinner_pixmap)

        self.main_spinner_msg_lbl = QLabel("Loading application intake form...")
        self.main_spinner_msg_lbl.setStyleSheet("color: #FFFFFF; font-size: 13.5px; font-weight: 700;")
        self.main_spinner_sub_lbl = QLabel("Fetching applicants, permit types & offices from Supabase")
        self.main_spinner_sub_lbl.setStyleSheet("color: #CBD5E1; font-size: 11.5px;")

        sc_lay.addWidget(self.main_spinner_icon_lbl)
        sc_lay.addWidget(self.main_spinner_msg_lbl)
        sc_lay.addWidget(self.main_spinner_sub_lbl)
        ov_lay.addWidget(spinner_card)
        self.main_spinner_overlay.hide()

        right_col.addWidget(self.pages_container, 1)

        footer = QFrame()
        footer.setObjectName("StatusFooter")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(26, 8, 26, 8)
        self.status_label = QLabel(f"Signed in as {display_name} ({display_hub}).")
        self.status_label.setStyleSheet("color: #E2E8F0; font-size: 12px; font-weight: 500;")
        f_lay.addWidget(self.status_label)
        right_col.addWidget(footer)

        shell.addLayout(right_col, 1)
        self._switch_page(0)

    def _switch_page(self, index: int):
        if index < 0 or index >= self.pages.count():
            return
        self.pages.setCurrentIndex(index)
        icon_names = ["dashboard", "clipboard_check", "verified_badge"]
        for i, btn in enumerate(self.nav_buttons):
            active = i == index
            btn.setProperty("active", "true" if active else "false")
            btn.setIcon(
                render_svg_icon(icon_names[i], size=17, color="#5EEAD4" if active else "#CBD5E1")
            )
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        meta = [
            ("Executive Overview", "Real-time agency queue health, SLA compliance, and active permits."),
            ("Inspections & Licensing", "Record field inspections, issue approved permits, and process renewals."),
            ("Credential Verifier", "Validate digital permits and verify HMAC-SHA256 cryptographic signatures."),
        ]
        self.page_title_lbl.setText(meta[index][0])
        self.page_sub_lbl.setText(meta[index][1])

    def _style_table(self, table: QTableWidget, headers: list[str]):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

    def _filter_table(self, table: QTableWidget, query: str):
        q = query.strip().lower()
        for r in range(table.rowCount()):
            if not q:
                table.setRowHidden(r, False)
                continue
            match = any(
                q in _cell_text(table, r, c).lower()
                for c in range(table.columnCount())
            )
            table.setRowHidden(r, not match)

    def _apply_live_filter(self, text: str):
        for tbl in (self.queue_table, self.sla_table, self.apps_table, self.creds_table):
            self._filter_table(tbl, text)

    def _start_new_application_flow(self):
        if (
            self.main_spinner_overlay.isVisible()
            or self._intake_fetch_timer.isActive()
            or self._intake_launch_timer.isActive()
            or self._is_refreshing
        ):
            return
        self._set_loading(True, "Loading New Application intake...", show_main_spinner=True)
        self._intake_fetch_timer.start(30)

    def _fetch_and_schedule_new_application_dialog(self):
        try:
            applicants = self.db.fetch_all(
                "SELECT id, full_or_business_name FROM permitme.applicants ORDER BY full_or_business_name;"
            ) or []
            permit_types = self.db.fetch_all(
                "SELECT id, code, title, base_fee FROM permitme.permit_types WHERE is_active = TRUE ORDER BY title;"
            ) or []
            offices = self.db.fetch_all(
                "SELECT id, code, name FROM permitme.offices WHERE is_active = TRUE ORDER BY code;"
            ) or []
            self._pending_intake_data = (applicants, permit_types, offices)
            self._intake_launch_timer.start(320)
        except Exception as exc:
            self._pending_intake_data = None
            self._set_loading(False)
            QMessageBox.critical(self, "Intake Lookup Error", f"Could not load intake lookups: {exc}")

    def _finish_open_new_application_dialog(self):
        data = self._pending_intake_data
        self._pending_intake_data = None
        self._set_loading(False)
        if not data:
            return
        applicants, permit_types, offices = data
        dlg = NewApplicationDialog(applicants, permit_types, offices, self.db, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_all()
            self.status_label.setText("New application created, assigned SLA deadline, and queued.")

    # ---------------- PAGE 0: EXECUTIVE OVERVIEW ----------------
    def _create_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 20, 26, 18)
        layout.setSpacing(18)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)

        self.kpi_total_cases = QLabel("0")
        self.kpi_total_cases.setObjectName("KpiNumberPrimary")
        self.kpi_overdue_cases = QLabel("0")
        self.kpi_overdue_cases.setObjectName("KpiNumberCrimson")
        self.kpi_sla_alerts = QLabel("0")
        self.kpi_sla_alerts.setObjectName("KpiNumberAmber")
        self.kpi_expiring_creds = QLabel("0")
        self.kpi_expiring_creds.setObjectName("KpiNumberTeal")

        kpi_row.addWidget(
            _build_kpi_card("Active Queue Cases", "Across all offices", self.kpi_total_cases, "#5EEAD4", "layers")
        )
        kpi_row.addWidget(
            _build_kpi_card("Overdue SLA Cases", "Immediate escalation", self.kpi_overdue_cases, "#F87171", "alert_triangle")
        )
        kpi_row.addWidget(
            _build_kpi_card("SLA Watchlist", "Breached or < 24h left", self.kpi_sla_alerts, "#FBBF24", "clock")
        )
        kpi_row.addWidget(
            _build_kpi_card("Expiring Credentials", "Within next 30 days", self.kpi_expiring_creds, "#5EEAD4", "award")
        )
        layout.addLayout(kpi_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(12)

        q_card = QFrame()
        q_card.setObjectName("Card")
        _apply_glass_shadow(q_card)
        q_lay = QVBoxLayout(q_card)
        q_lay.setContentsMargins(20, 16, 20, 16)
        q_lay.setSpacing(8)
        q_hdr = QLabel("Department & Office Queue Breakdown")
        q_hdr.setObjectName("SectionHeading")
        q_lay.addWidget(q_hdr)

        self.queue_table = QTableWidget(0, 4)
        self._style_table(self.queue_table, ["Office Code", "Workflow Status", "Case Count", "Overdue SLA"])
        q_lay.addWidget(self.queue_table)
        splitter.addWidget(q_card)

        s_card = QFrame()
        s_card.setObjectName("Card")
        _apply_glass_shadow(s_card)
        s_lay = QVBoxLayout(s_card)
        s_lay.setContentsMargins(20, 16, 20, 16)
        s_lay.setSpacing(6)

        s_hdr = QLabel("Priority SLA Risk Monitor")
        s_hdr.setObjectName("SectionHeading")
        s_sub = QLabel("Click any row to open that case directly in Inspections & Licensing.")
        s_sub.setObjectName("SectionHint")
        s_lay.addWidget(s_hdr)
        s_lay.addWidget(s_sub)

        self.sla_table = QTableWidget(0, 7)
        self._style_table(
            self.sla_table,
            ["App ID", "Reference No", "Office", "Applicant", "Status", "SLA Health", "Hours Left"],
        )
        self.sla_table.cellClicked.connect(self._on_sla_row_clicked)
        s_lay.addWidget(self.sla_table)
        splitter.addWidget(s_card)

        layout.addWidget(splitter, 1)
        return page

    # ---------------- PAGE 1: INSPECTIONS & LICENSING ----------------
    def _create_workflows_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(26, 20, 26, 18)
        layout.setSpacing(18)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        left_card = QFrame()
        left_card.setObjectName("InspectionFormCard")
        _apply_glass_shadow(left_card)
        left_lay = QVBoxLayout(left_card)
        left_lay.setContentsMargins(20, 18, 20, 18)
        left_lay.setSpacing(12)

        banner = QFrame()
        banner.setObjectName("SelectedBanner")
        b_lay = QVBoxLayout(banner)
        b_lay.setContentsMargins(12, 10, 12, 10)
        self.selected_case_lbl = QLabel("No case selected — click any row on the right to autofill.")
        self.selected_case_lbl.setWordWrap(True)
        self.selected_case_lbl.setStyleSheet("color: #99F6E4; font-weight: 700; font-size: 12.5px;")
        b_lay.addWidget(self.selected_case_lbl)
        left_lay.addWidget(banner)

        sec1 = QLabel("Field & Technical Inspection")
        sec1.setObjectName("SectionHeading")
        left_lay.addWidget(sec1)

        form = QFormLayout()
        form.setSpacing(12)
        self.app_id_input = QLineEdit()
        self.app_id_input.setPlaceholderText("e.g. 1 (or click a row on the right)")
        self.app_id_input.textChanged.connect(self._update_pending_action_preview)

        self.inspector_id_input = QLineEdit("1")
        self.inspector_id_input.setPlaceholderText("e.g. 1")

        self.inspection_type_combo = QComboBox()
        _style_combo(
            self.inspection_type_combo,
            [
                ("Site Safety Inspection", "site_safety"),
                ("Pre-License Compliance Audit", "pre_license_audit"),
                ("Hygiene & Cold Chain Check", "hygiene_and_cold_chain"),
                ("Fire & Structural Code Check", "fire_code_compliance"),
                ("Follow-Up Re-Inspection", "re_inspection"),
            ],
        )

        self.outcome_combo = QComboBox()
        _style_combo(
            self.outcome_combo,
            [
                ("Passed — Ready for Fee Settlement", "passed"),
                ("Conditional — Request for Info (RFI)", "conditional"),
                ("Failed — Reject Application", "failed"),
            ],
        )
        self.outcome_combo.currentIndexChanged.connect(self._update_pending_action_preview)

        self.findings_input = QTextEdit()
        self.findings_input.setMaximumHeight(85)
        self.findings_input.setPlaceholderText("Document compliance findings, safety notes, or RFI conditions...")

        form.addRow("Application ID", self.app_id_input)
        form.addRow("Inspector ID", self.inspector_id_input)
        form.addRow("Inspection Type", self.inspection_type_combo)
        form.addRow("Outcome", self.outcome_combo)
        form.addRow("Findings", self.findings_input)
        left_lay.addLayout(form)

        pending_box = QFrame()
        pending_box.setObjectName("PendingActionBanner")
        p_lay = QHBoxLayout(pending_box)
        p_lay.setContentsMargins(12, 9, 12, 9)
        p_lay.setSpacing(10)
        p_icon = QLabel()
        p_icon.setPixmap(render_svg_pixmap("clock", size=16, color="#5EEAD4"))
        self.pending_action_lbl = QLabel("Upcoming: Enter a valid Application ID to preview status transition.")
        self.pending_action_lbl.setWordWrap(True)
        self.pending_action_lbl.setStyleSheet("color: #CCFBF1; font-size: 11.5px; font-weight: 600;")
        p_lay.addWidget(p_icon)
        p_lay.addWidget(self.pending_action_lbl, 1)
        left_lay.addWidget(pending_box)

        insp_btn = QPushButton("  Record Inspection & Advance Case")
        insp_btn.setObjectName("PrimaryBtn")
        insp_btn.setIcon(render_svg_icon("clipboard_check", size=16, color="#042F2E"))
        insp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        insp_btn.clicked.connect(self.handle_record_inspection)
        left_lay.addWidget(insp_btn)

        issue_btn = QPushButton("  Approve & Issue Digital Credential")
        issue_btn.setObjectName("NavyBtn")
        issue_btn.setIcon(render_svg_icon("verified_badge", size=16, color="#5EEAD4"))
        issue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        issue_btn.clicked.connect(self.handle_issue_credential)
        left_lay.addWidget(issue_btn)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); max-height: 1px; margin: 6px 0;")
        left_lay.addWidget(divider)

        sec2 = QLabel("Credential Renewal & Quick Verify")
        sec2.setObjectName("SectionHeading")
        left_lay.addWidget(sec2)

        renew_row = QHBoxLayout()
        self.renew_cred_id_input = QLineEdit()
        self.renew_cred_id_input.setPlaceholderText("Credential ID, e.g. 1")
        renew_btn = QPushButton("  Renew Now")
        renew_btn.setObjectName("OutlineBtn")
        renew_btn.setIcon(render_svg_icon("refresh", size=15, color="#5EEAD4"))
        renew_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        renew_btn.clicked.connect(self.handle_renew_credential)
        renew_row.addWidget(self.renew_cred_id_input, 2)
        renew_row.addWidget(renew_btn, 1)
        left_lay.addLayout(renew_row)

        jump_verify_btn = QPushButton("  Open Selected Permit in Verifier")
        jump_verify_btn.setObjectName("OutlineBtn")
        jump_verify_btn.setIcon(render_svg_icon("arrow_right", size=15, color="#5EEAD4"))
        jump_verify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        jump_verify_btn.clicked.connect(self._jump_to_verifier)
        left_lay.addWidget(jump_verify_btn)

        left_lay.addStretch()
        scroll.setWidget(left_card)
        layout.addWidget(scroll, 2)

        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        apps_card = QFrame()
        apps_card.setObjectName("Card")
        _apply_glass_shadow(apps_card)
        a_lay = QVBoxLayout(apps_card)
        a_lay.setContentsMargins(20, 16, 20, 16)
        a_hdr = QLabel("Applications Registry")
        a_hdr.setObjectName("SectionHeading")
        a_lay.addWidget(a_hdr)

        self.apps_table = QTableWidget(0, 6)
        self._style_table(
            self.apps_table, ["ID", "Reference No", "Applicant", "Permit Type", "Status", "Priority"]
        )
        self.apps_table.cellClicked.connect(self._on_app_row_clicked)
        a_lay.addWidget(self.apps_table)
        right_col.addWidget(apps_card, 1)

        creds_card = QFrame()
        creds_card.setObjectName("Card")
        _apply_glass_shadow(creds_card)
        c_lay = QVBoxLayout(creds_card)
        c_lay.setContentsMargins(20, 16, 20, 16)
        c_hdr = QLabel("Issued Permits & Licenses")
        c_hdr.setObjectName("SectionHeading")
        c_lay.addWidget(c_hdr)

        self.creds_table = QTableWidget(0, 6)
        self._style_table(
            self.creds_table, ["Cred ID", "Permit Number", "Verify Code", "Applicant", "Active", "Expires"]
        )
        self.creds_table.cellClicked.connect(self._on_cred_row_clicked)
        c_lay.addWidget(self.creds_table)
        right_col.addWidget(creds_card, 1)

        layout.addLayout(right_col, 3)
        return page

    # ---------------- PAGE 2: CREDENTIAL VERIFIER ----------------
    def _create_verifier_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 20, 26, 18)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("Card")
        _apply_glass_shadow(card)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(14)

        hdr_row = QHBoxLayout()
        hdr_text = QVBoxLayout()
        hdr = QLabel("Cryptographic Credential Lookup & HMAC-SHA256 Validation")
        hdr.setObjectName("SectionHeading")
        hint = QLabel(
            "Verify permit validity, expiration dates, revocation flags, and tamper-evident HMAC signatures."
        )
        hint.setObjectName("SectionHint")
        hdr_text.addWidget(hdr)
        hdr_text.addWidget(hint)
        hdr_row.addLayout(hdr_text)
        hdr_row.addStretch()

        self.copy_hmac_btn = QPushButton("  Copy Canonical HMAC")
        self.copy_hmac_btn.setObjectName("OutlineBtn")
        self.copy_hmac_btn.setIcon(render_svg_icon("copy", size=15, color="#5EEAD4"))
        self.copy_hmac_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_hmac_btn.clicked.connect(self._copy_hmac_to_clipboard)
        hdr_row.addWidget(self.copy_hmac_btn)
        c_lay.addLayout(hdr_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.permit_no_input = QLineEdit()
        self.permit_no_input.setPlaceholderText("Permit Number (e.g. LIC-2026-000001)")
        self.hmac_input = QLineEdit()
        self.hmac_input.setPlaceholderText("Optional HMAC-SHA256 Hex Signature to verify")
        verify_btn = QPushButton("  Verify Credential")
        verify_btn.setObjectName("PrimaryBtn")
        verify_btn.setIcon(render_svg_icon("verified_badge", size=16, color="#042F2E"))
        verify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        verify_btn.clicked.connect(self.handle_verify_credential)

        input_row.addWidget(self.permit_no_input, 2)
        input_row.addWidget(self.hmac_input, 3)
        input_row.addWidget(verify_btn)
        c_lay.addLayout(input_row)

        self.verify_output = QTextEdit()
        self.verify_output.setReadOnly(True)
        self.verify_output.setStyleSheet(
            "background-color: #09111E; color: #F8FAFC; "
            "border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 12px; "
            "font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 13px; padding: 16px;"
        )
        self.verify_output.setPlaceholderText(
            "Verification certificate and HMAC signature details will appear here..."
        )
        c_lay.addWidget(self.verify_output, 1)

        layout.addWidget(card, 1)
        return page

    # ---------------- VALIDATION HELPERS ----------------
    def _parse_positive_id(self, raw_text: str, field_label: str) -> Optional[int]:
        cleaned = raw_text.strip()
        if not cleaned.isdigit() or int(cleaned) <= 0:
            QMessageBox.warning(
                self,
                f"Invalid {field_label}",
                f"Enter a positive numeric {field_label} (e.g. 1) or select a row from the table.",
            )
            return None
        return int(cleaned)

    def _relation_exists(self, qualified_table: str) -> bool:
        rows = self.db.fetch_all("SELECT to_regclass(%s) AS reg;", (qualified_table,)) or []
        return bool(rows and rows[0].get("reg"))

    def _application_exists(self, app_id: int) -> bool:
        rows = self.db.fetch_all(
            "SELECT id FROM permitme.permit_applications WHERE id = %s;",
            (app_id,),
        )
        return bool(rows)

    def _inspector_exists_if_table_present(self, inspector_id: int) -> bool:
        if not self._relation_exists("permitme.inspectors"):
            return True
        rows = self.db.fetch_all(
            "SELECT id FROM permitme.inspectors WHERE id = %s;",
            (inspector_id,),
        )
        return bool(rows)

    def _credential_exists(self, cred_id: int) -> bool:
        rows = self.db.fetch_all(
            "SELECT id FROM permitme.credentials WHERE id = %s;",
            (cred_id,),
        )
        return bool(rows)

    # ---------------- LIVE PREVIEWS & ROW HANDLERS ----------------
    def _update_pending_action_preview(self):
        raw_id = self.app_id_input.text().strip()
        app_label = f"#{raw_id}" if raw_id.isdigit() and int(raw_id) > 0 else "<valid ID>"
        outcome = _safe_str(self.outcome_combo.currentData(), "passed")
        next_status_map = {
            "passed": "fee_pending (ready for credential issuance)",
            "conditional": "rfi_pending (applicant info required)",
            "failed": "rejected (compliance failure recorded)",
        }
        next_status = next_status_map.get(outcome, "under_review")
        self.pending_action_lbl.setText(
            f"Upcoming on submit: App {app_label} -> {next_status} via sp_record_inspection."
        )

    def _on_sla_row_clicked(self, row: int, _col: int):
        app_id = _cell_text(self.sla_table, row, 0)
        ref_no = _cell_text(self.sla_table, row, 1)
        applicant = _cell_text(self.sla_table, row, 3)
        if not app_id:
            return
        self.app_id_input.setText(app_id)
        self.selected_case_lbl.setText(f"Active Case: #{app_id} ({ref_no}) — {applicant}")
        self._switch_page(1)
        self.status_label.setText(f"Loaded Application #{app_id} ({ref_no}) into Inspections & Licensing.")

    def _on_app_row_clicked(self, row: int, _col: int):
        app_id = _cell_text(self.apps_table, row, 0)
        ref_no = _cell_text(self.apps_table, row, 1)
        applicant = _cell_text(self.apps_table, row, 2)
        if not app_id:
            return
        self.app_id_input.setText(app_id)
        self.selected_case_lbl.setText(f"Active Case: #{app_id} ({ref_no}) — {applicant}")
        self.status_label.setText(f"Selected Application #{app_id} ({ref_no}).")

    def _on_cred_row_clicked(self, row: int, _col: int):
        cred_id = _cell_text(self.creds_table, row, 0)
        permit_no = _cell_text(self.creds_table, row, 1)
        applicant = _cell_text(self.creds_table, row, 3)
        if not cred_id:
            return
        self.renew_cred_id_input.setText(cred_id)
        if permit_no:
            self.permit_no_input.setText(permit_no)
        self.selected_case_lbl.setText(f"Selected Credential #{cred_id} ({permit_no}) — {applicant}")
        self.status_label.setText(f"Loaded Credential #{cred_id} ({permit_no}).")

    def _jump_to_verifier(self):
        self._switch_page(2)
        if self.permit_no_input.text().strip():
            self.handle_verify_credential()

    def _copy_hmac_to_clipboard(self):
        if not self.last_computed_hmac:
            QMessageBox.information(self, "Nothing to Copy", "Verify a credential first to generate its HMAC.")
            return
        QGuiApplication.clipboard().setText(self.last_computed_hmac)
        self.status_label.setText("Canonical HMAC-SHA256 signature copied to clipboard.")

    # ---------------- DATA SYNC & WORKFLOW ACTIONS ----------------
    def refresh_all(self):
        if self._is_refreshing:
            return
        self._is_refreshing = True
        self._set_loading(True, "Syncing queues, SLA risk & credentials...", show_main_spinner=False)
        try:
            q_rows = self.db.get_office_queue_summary() or []
            self.queue_table.setRowCount(len(q_rows))
            total_cases = 0
            total_overdue = 0
            for r, row in enumerate(q_rows):
                c_count = _safe_int(row.get("case_count"), 0)
                o_count = _safe_int(row.get("overdue_count"), 0)
                total_cases += c_count
                total_overdue += o_count
                self.queue_table.setItem(r, 0, QTableWidgetItem(_safe_str(row.get("office_code"), "N/A")))
                self.queue_table.setItem(r, 1, QTableWidgetItem(_safe_str(row.get("status"), "N/A")))
                self.queue_table.setItem(r, 2, QTableWidgetItem(str(c_count)))
                self.queue_table.setItem(r, 3, QTableWidgetItem(str(o_count)))

            sla_rows = self.cred_service.get_sla_risk_queue() or []
            self.sla_table.setRowCount(len(sla_rows))
            for r, row in enumerate(sla_rows):
                health_str = _safe_str(row.get("sla_health"), "UNKNOWN")
                vals = [
                    _safe_str(row.get("application_id")),
                    _safe_str(row.get("reference_no")),
                    _safe_str(row.get("office_code")),
                    _safe_str(row.get("applicant_name")),
                    _safe_str(row.get("status")),
                    health_str,
                    _safe_str(row.get("hours_until_sla_due"), "0"),
                ]
                for c, val in enumerate(vals):
                    item = QTableWidgetItem(val)
                    if c == 5:
                        item.setForeground(
                            QColor("#F87171" if health_str == "BREACHED" else "#FBBF24")
                        )
                    self.sla_table.setItem(r, c, item)

            exp_rows = self.db.get_expiring_credentials() or []

            app_rows = self.cred_service.get_recent_applications() or []
            self.apps_table.setRowCount(len(app_rows))
            for r, row in enumerate(app_rows):
                vals = [
                    _safe_str(row.get("id")),
                    _safe_str(row.get("reference_no")),
                    _safe_str(row.get("applicant_name")),
                    _safe_str(row.get("permit_title")),
                    _safe_str(row.get("status")),
                    _safe_str(row.get("priority_score"), "0"),
                ]
                for c, val in enumerate(vals):
                    self.apps_table.setItem(r, c, QTableWidgetItem(val))

            cred_rows = self.cred_service.get_recent_credentials() or []
            self.creds_table.setRowCount(len(cred_rows))
            for r, row in enumerate(cred_rows):
                exp_raw = row.get("expires_at")
                if hasattr(exp_raw, "strftime"):
                    exp_str = exp_raw.strftime("%Y-%m-%d")
                else:
                    exp_str = _safe_str(exp_raw)[:10]
                is_active = bool(row.get("is_active"))
                vals = [
                    _safe_str(row.get("id")),
                    _safe_str(row.get("permit_number")),
                    _safe_str(row.get("verification_code")),
                    _safe_str(row.get("applicant_name")),
                    "ACTIVE" if is_active else "INACTIVE",
                    exp_str,
                ]
                for c, val in enumerate(vals):
                    item = QTableWidgetItem(val)
                    if c == 4:
                        item.setForeground(QColor("#5EEAD4" if is_active else "#F87171"))
                    self.creds_table.setItem(r, c, item)

            self.kpi_total_cases.setText(str(total_cases))
            self.kpi_overdue_cases.setText(str(total_overdue))
            self.kpi_sla_alerts.setText(str(len(sla_rows)))
            self.kpi_expiring_creds.setText(str(len(exp_rows)))
            self._apply_live_filter(self.search_input.text())
            self.status_label.setText(
                f"Connected • Synced {len(app_rows)} applications & {len(cred_rows)} credentials."
            )
        except Exception as exc:
            self.status_label.setText(f"Sync error: {exc}")
            QMessageBox.critical(self, "Supabase Sync Error", f"Failed to sync live data: {exc}")
        finally:
            self._is_refreshing = False
            self._set_loading(False)

    def handle_record_inspection(self):
        app_id = self._parse_positive_id(self.app_id_input.text(), "Application ID")
        if app_id is None:
            return

        insp_text = self.inspector_id_input.text().strip()
        insp_id = self._parse_positive_id(insp_text or "1", "Inspector ID")
        if insp_id is None:
            return

        insp_type = _safe_str(self.inspection_type_combo.currentData(), "site_safety")
        outcome = _safe_str(self.outcome_combo.currentData(), "passed")
        findings = self.findings_input.toPlainText().strip() or "Routine inspection logged."

        self._set_loading(True, "Validating & recording inspection...")
        try:
            if not self._application_exists(app_id):
                QMessageBox.warning(
                    self,
                    "Application Not Found",
                    f"Application #{app_id} does not exist in permit_applications. "
                    "Select an existing row from the Applications Registry table.",
                )
                return

            if not self._inspector_exists_if_table_present(insp_id):
                QMessageBox.warning(
                    self,
                    "Inspector Not Found",
                    f"Inspector #{insp_id} was not found. Enter a valid Inspector ID.",
                )
                return

            self.cred_service.record_inspection(app_id, insp_id, insp_type, outcome, findings)
            self.findings_input.clear()
            self._set_loading(False)
            self.refresh_all()
            QMessageBox.information(
                self, "Inspection Recorded", f"Logged '{outcome}' inspection for Application #{app_id}."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Inspection Error", f"Could not record inspection: {exc}")
        finally:
            self._set_loading(False)

    def handle_issue_credential(self):
        app_id = self._parse_positive_id(self.app_id_input.text(), "Application ID")
        if app_id is None:
            return

        self._set_loading(True, "Issuing signed credential...")
        try:
            if not self._application_exists(app_id):
                QMessageBox.warning(
                    self,
                    "Application Not Found",
                    f"Application #{app_id} does not exist in permit_applications.",
                )
                return

            self.db.issue_credential(app_id, fee_paid=True)
            self._set_loading(False)
            self.refresh_all()
            QMessageBox.information(
                self, "Credential Issued", f"Credential issued and Application #{app_id} approved."
            )
        except Exception as exc:
            QMessageBox.critical(self, "Issuance Error", f"Could not issue credential: {exc}")
        finally:
            self._set_loading(False)

    def handle_renew_credential(self):
        cred_id = self._parse_positive_id(self.renew_cred_id_input.text(), "Credential ID")
        if cred_id is None:
            return

        self._set_loading(True, "Renewing credential...")
        try:
            if not self._credential_exists(cred_id):
                QMessageBox.warning(
                    self,
                    "Credential Not Found",
                    f"Credential #{cred_id} does not exist in credentials.",
                )
                return

            new_app_id = self.cred_service.renew_credential(cred_id)
            self._set_loading(False)
            self.refresh_all()
            QMessageBox.information(
                self,
                "Credential Renewed",
                f"Renewed Credential #{cred_id} into new Application #{new_app_id}.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Renewal Error", f"Could not renew credential: {exc}")
        finally:
            self._set_loading(False)

    def handle_verify_credential(self):
        permit_no = self.permit_no_input.text().strip()
        provided_hmac = self.hmac_input.text().strip()
        if not permit_no:
            QMessageBox.warning(self, "Missing Input", "Enter a permit number to verify.")
            return

        self._set_loading(True, "Verifying credential & HMAC signature...")
        try:
            rec = self.cred_service.lookup_credential(permit_no)
            if not rec:
                self.last_computed_hmac = ""
                self.verify_output.setPlainText(f"No credential found matching '{permit_no}'.")
                return

            permit_num = _safe_str(rec.get("permit_number"))
            verify_code = _safe_str(rec.get("verification_code"))
            exp_raw = rec.get("expires_at")
            expires_iso = exp_raw.isoformat() if hasattr(exp_raw, "isoformat") else _safe_str(exp_raw)

            computed_sig = self.cred_service.sign_credential(permit_num, verify_code, expires_iso)
            self.last_computed_hmac = computed_sig

            if provided_hmac:
                sig_status = (
                    "VALID (HMAC-SHA256 matches)"
                    if self.cred_service.verify_signature(
                        permit_num, verify_code, expires_iso, provided_hmac
                    )
                    else "INVALID (Signature mismatch)"
                )
            else:
                sig_status = "NOT SUPPLIED (Canonical HMAC-SHA256 displayed below)"

            is_active = bool(rec.get("is_active"))
            fee_paid = bool(rec.get("fee_paid"))

            details = (
                f"PERMIT NUMBER:       {permit_num}\n"
                f"VERIFICATION CODE:   {verify_code}\n"
                f"APPLICANT:           {_safe_str(rec.get('applicant_name'), 'N/A')}\n"
                f"PERMIT TYPE:         {_safe_str(rec.get('permit_title'), 'N/A')}\n"
                f"STATUS:              {'ACTIVE' if is_active else 'INACTIVE'}\n"
                f"FEE SETTLED:         {'YES' if fee_paid else 'PENDING'} (${_safe_str(rec.get('fee_amount'), '0.00')})\n"
                f"EXPIRES AT:          {expires_iso or 'N/A'}\n"
                f"REVOKED AT:          {_safe_str(rec.get('revoked_at'), 'N/A')} ({_safe_str(rec.get('revocation_reason'), 'None')})\n"
                f"RENEWAL LINEAGE:     {_safe_str(rec.get('renewed_from_credential_id'), 'Original Issuance')}\n"
                f"SIGNATURE CHECK:     {sig_status}\n"
                f"-------------------------------------------------------------------\n"
                f"CANONICAL HMAC-SHA256:\n{computed_sig}"
            )
            self.verify_output.setPlainText(details)
        except Exception as exc:
            QMessageBox.critical(self, "Verification Error", f"Could not verify credential: {exc}")
        finally:
            self._set_loading(False)