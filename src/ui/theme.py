def build_workstation_stylesheet(chevron_svg_uri: str) -> str:
    return f"""
QWidget {{
    color: #F8FAFC;
    font-family: "SF Pro Display", "Inter", "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
}}

/* Main canvas overlay so permit.jpg + dark gradient remain visible */
QWidget#MainScrim {{
    background-color: rgba(7, 13, 24, 0.24);
}}

/* Left Translucent Midnight Sidebar */
QFrame#Sidebar {{
    background-color: rgba(8, 14, 27, 0.84);
    border-right: 1px solid rgba(255, 255, 255, 0.12);
    min-width: 268px;
    max-width: 268px;
}}

QLabel#SidebarBrand {{
    color: #FFFFFF;
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.4px;
}}

QLabel#SidebarTagline {{
    color: #5EEAD4;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#SidebarSectionLabel {{
    color: #94A3B8;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.3px;
    text-transform: uppercase;
    padding-left: 10px;
    margin-top: 12px;
    margin-bottom: 2px;
}}

QPushButton#NavBtn {{
    background-color: rgba(255, 255, 255, 0.03);
    color: #E2E8F0;
    border: 1px solid transparent;
    border-radius: 11px;
    padding: 11px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#NavBtn:hover {{
    background-color: rgba(94, 234, 212, 0.12);
    border: 1px solid rgba(94, 234, 212, 0.28);
    color: #FFFFFF;
}}

QPushButton#NavBtn[active="true"] {{
    background-color: rgba(94, 234, 212, 0.24);
    border: 1px solid rgba(94, 234, 212, 0.65);
    color: #FFFFFF;
    font-weight: 700;
}}

/* Borderless Unique Profile Card (bg-teal-300 / #5EEAD4 accent wash, no outline) */
QFrame#SidebarProfileBox {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(94, 234, 212, 0.22),
        stop:0.55 rgba(15, 23, 42, 0.80),
        stop:1 rgba(13, 148, 136, 0.26)
    );
    border: none;
    border-radius: 16px;
}}

QFrame#TopHeader {{
    background-color: rgba(9, 16, 30, 0.58);
    border-bottom: 1px solid rgba(255, 255, 255, 0.11);
}}

QLabel#PageTitle {{
    color: #FFFFFF;
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.3px;
}}

QLabel#PageSubtitle {{
    color: #CBD5E1;
    font-size: 12px;
}}

/* Frosted Glass Cards, Inspection Form Card & Main Loading Overlay */
QFrame#Card {{
    background-color: rgba(11, 18, 33, 0.52);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 16px;
}}

QFrame#InspectionFormCard {{
    background-color: rgba(10, 17, 32, 0.84);
    border: 1px solid rgba(94, 234, 212, 0.32);
    border-radius: 16px;
}}

QFrame#KpiCard {{
    background-color: rgba(11, 18, 33, 0.54);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 0px;
}}

QFrame#MainSpinnerCard {{
    background-color: #0B1324;
    border: 1px solid #5EEAD4;
    border-radius: 18px;
}}

QFrame#SelectedBanner {{
    background-color: rgba(94, 234, 212, 0.18);
    border: 1px solid rgba(94, 234, 212, 0.50);
    border-radius: 11px;
}}

QFrame#PendingActionBanner {{
    background-color: rgba(94, 234, 212, 0.14);
    border: 1px solid rgba(94, 234, 212, 0.38);
    border-radius: 11px;
}}

QLabel#SectionHeading {{
    color: #FFFFFF;
    font-size: 14.5px;
    font-weight: 700;
}}

QLabel#SectionHint {{
    color: #CBD5E1;
    font-size: 12px;
}}

QLabel#KpiTitle {{
    color: #E2E8F0;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.7px;
    text-transform: uppercase;
}}

QLabel#KpiNumberPrimary {{
    color: #FFFFFF;
    font-size: 29px;
    font-weight: 800;
}}

QLabel#KpiNumberTeal {{
    color: #5EEAD4;
    font-size: 29px;
    font-weight: 800;
}}

QLabel#KpiNumberAmber {{
    color: #FBBF24;
    font-size: 29px;
    font-weight: 800;
}}

QLabel#KpiNumberCrimson {{
    color: #F87171;
    font-size: 29px;
    font-weight: 800;
}}

/* Buttons — bg-teal-300 (#5EEAD4) Primary Theme */
QPushButton#PrimaryBtn {{
    background-color: #5EEAD4;
    color: #042F2E;
    border: 1px solid #99F6E4;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 800;
}}

QPushButton#PrimaryBtn:hover {{
    background-color: #99F6E4;
    color: #022C22;
}}

QPushButton#PrimaryBtn:pressed {{
    background-color: #2DD4BF;
}}

QPushButton#NavyBtn {{
    background-color: #11323A;
    color: #CCFBF1;
    border: 1px solid #5EEAD4;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 700;
}}

QPushButton#NavyBtn:hover {{
    background-color: #17444E;
    color: #FFFFFF;
}}

QPushButton#OutlineBtn {{
    background-color: #121E33;
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.24);
    border-radius: 10px;
    padding: 9px 15px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#OutlineBtn:hover {{
    background-color: #182C3E;
    border-color: #5EEAD4;
    color: #FFFFFF;
}}

/* Text Inputs */
QLineEdit, QTextEdit {{
    background-color: #0C1628;
    color: #F8FAFC;
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 13px;
    selection-background-color: #5EEAD4;
    selection-color: #042F2E;
}}

QLineEdit:hover, QTextEdit:hover {{
    border-color: rgba(94, 234, 212, 0.55);
}}

QLineEdit:focus, QTextEdit:focus {{
    border: 1.5px solid #5EEAD4;
    background-color: #0F1C32;
}}

/* Dropdown Control — Strictly Dark Slate, Zero White Surface on macOS */
QComboBox {{
    background-color: #0D182D;
    color: #F8FAFC;
    border: 1px solid rgba(94, 234, 212, 0.55);
    border-radius: 10px;
    padding: 9px 38px 9px 12px;
    min-height: 22px;
    font-size: 13px;
    font-weight: 700;
}}

QComboBox:hover {{
    background-color: #13233F;
    border-color: #5EEAD4;
    color: #FFFFFF;
}}

QComboBox:on, QComboBox:focus {{
    background-color: #13233F;
    border: 1.5px solid #5EEAD4;
    color: #FFFFFF;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 34px;
    border-left: 1px solid rgba(94, 234, 212, 0.35);
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
    background-color: #112636;
}}

QComboBox::down-arrow {{
    image: url("{chevron_svg_uri}");
    width: 14px;
    height: 14px;
}}

/* Dropdown Popup Container & Items — Dark Slate Only */
QComboBox QAbstractItemView,
QComboBox QListView,
QComboBoxPrivateContainer {{
    background-color: #091120;
    color: #F8FAFC;
    border: 1.5px solid #5EEAD4;
    border-radius: 10px;
    padding: 5px;
    outline: 0px;
    selection-background-color: #5EEAD4;
    selection-color: #042F2E;
}}

QComboBox QAbstractItemView::item,
QComboBox QListView::item {{
    background-color: #091120;
    color: #F8FAFC;
    padding: 10px 12px;
    margin: 2px 0px;
    border-radius: 7px;
    min-height: 24px;
    font-weight: 600;
}}

QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:hover {{
    background-color: #5EEAD4;
    color: #042F2E;
    font-weight: 800;
}}

QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected {{
    background-color: #134E4A;
    color: #99F6E4;
    font-weight: 800;
}}

/* Translucent Glass Data Tables */
QTableWidget {{
    background-color: rgba(8, 13, 25, 0.42);
    alternate-background-color: rgba(255, 255, 255, 0.03);
    gridline-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    outline: 0px;
    selection-background-color: #0D9488;
    selection-color: #FFFFFF;
}}

QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}}

QTableWidget::item:hover {{
    background-color: rgba(94, 234, 212, 0.22);
}}

QHeaderView::section {{
    background-color: #0E182B;
    color: #CBD5E1;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 2px;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.24);
    border-radius: 4px;
    min-height: 28px;
}}

QScrollBar::handle:vertical:hover {{
    background: #5EEAD4;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QFrame#StatusFooter {{
    background-color: rgba(8, 14, 27, 0.72);
    border-top: 1px solid rgba(255, 255, 255, 0.10);
}}

/* Dark Modal Dialog Surface (Sharp Corners, Never White) */
QDialog {{
    background-color: #0B1324;
    color: #F8FAFC;
    border: 1.5px solid #5EEAD4;
    border-radius: 0px;
}}
"""