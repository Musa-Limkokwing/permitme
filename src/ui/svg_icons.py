from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

SVG_PATHS: dict[str, str] = {
    "shield_logo": """
        <path d="M12 2L4 5.5V11.5C4 16.8 7.4 21.7 12 23C16.6 21.7 20 16.8 20 11.5V5.5L12 2Z"
              stroke="{color}" stroke-width="1.9" fill="{fill}" stroke-linejoin="round"/>
        <path d="M9 12.2L11.1 14.3L15.3 9.8"
              stroke="{accent}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "dashboard": """
        <rect x="3" y="3" width="7" height="8" rx="2" stroke="{color}" stroke-width="1.8" fill="none"/>
        <rect x="14" y="3" width="7" height="5" rx="2" stroke="{color}" stroke-width="1.8" fill="none"/>
        <rect x="14" y="12" width="7" height="9" rx="2" stroke="{color}" stroke-width="1.8" fill="none"/>
        <rect x="3" y="15" width="7" height="6" rx="2" stroke="{color}" stroke-width="1.8" fill="none"/>
    """,
    "clipboard_check": """
        <path d="M9 4H7C5.895 4 5 4.895 5 6V19C5 20.105 5.895 21 7 21H17C18.105 21 19 20.105 19 19V6C19 4.895 18.105 4 17 4H15"
              stroke="{color}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
        <rect x="9" y="2.5" width="6" height="3.5" rx="1.2" stroke="{color}" stroke-width="1.8" fill="none"/>
        <path d="M9 13L11 15L15.5 10.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "verified_badge": """
        <path d="M12 2.5L14.6 4.4L17.8 4.4L18.8 7.5L21.4 9.4L20.4 12.5L21.4 15.6L18.8 17.5L17.8 20.6L14.6 20.6L12 22.5L9.4 20.6L6.2 20.6L5.2 17.5L2.6 15.6L3.6 12.5L2.6 9.4L5.2 7.5L6.2 4.4L9.4 4.4L12 2.5Z"
              stroke="{color}" stroke-width="1.8" stroke-linejoin="round" fill="none"/>
        <path d="M9 12.5L11 14.5L15.2 10.2" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "plus_circle": """
        <circle cx="12" cy="12" r="9" stroke="{color}" stroke-width="1.8" fill="none"/>
        <path d="M12 8.5V15.5M8.5 12H15.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
    """,
    "refresh": """
        <path d="M20 11A8.1 8.1 0 0 0 4.5 9M4 5V9H8" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M4 13A8.1 8.1 0 0 0 19.5 15M20 19V15H16" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "search": """
        <circle cx="11" cy="11" r="6.5" stroke="{color}" stroke-width="1.8" fill="none"/>
        <path d="M16 16L20.5 20.5" stroke="{color}" stroke-width="1.9" stroke-linecap="round"/>
    """,
    "layers": """
        <path d="M12 3L21 8L12 13L3 8L12 3Z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round" fill="none"/>
        <path d="M3 12.5L12 17.5L21 12.5" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <path d="M3 17L12 22L21 17" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "alert_triangle": """
        <path d="M12 3.5L21.2 19.5H2.8L12 3.5Z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round" fill="none"/>
        <path d="M12 9.5V13.8" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="16.8" r="1" fill="{color}"/>
    """,
    "clock": """
        <circle cx="12" cy="12" r="9" stroke="{color}" stroke-width="1.8" fill="none"/>
        <path d="M12 7.5V12.2L15.2 14" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "award": """
        <circle cx="12" cy="9" r="6" stroke="{color}" stroke-width="1.8" fill="none"/>
        <path d="M8.5 14L7 21L12 18.5L17 21L15.5 14" stroke="{color}" stroke-width="1.8" stroke-linejoin="round" fill="none"/>
    """,
    "copy": """
        <rect x="9" y="9" width="11" height="11" rx="2" stroke="{color}" stroke-width="1.8" fill="none"/>
        <path d="M5 15H4C2.895 15 2 14.105 2 13V4C2 2.895 2.895 2 4 2H13C14.105 2 15 2.895 15 4V5"
              stroke="{color}" stroke-width="1.8" stroke-linecap="round" fill="none"/>
    """,
    "chevron_down": """
        <path d="M6 9L12 15L18 9" stroke="{color}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "arrow_right": """
        <path d="M5 12H19M13 6L19 12L13 18" stroke="{color}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
}


def render_svg_pixmap(
    name: str,
    size: int = 20,
    color: str = "#F8FAFC",
    fill: str = "none",
    accent: str = "#34D399",
) -> QPixmap:
    body = SVG_PATHS.get(name, "")
    svg_xml = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none">{body.format(color=color, fill=fill, accent=accent)}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg_xml.encode("utf-8")))
    pixmap = QPixmap(size * 2, size * 2)  # 2x DPR for Retina sharpness
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size * 2, size * 2))
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return pixmap


def render_svg_icon(
    name: str,
    size: int = 18,
    color: str = "#F8FAFC",
    fill: str = "none",
    accent: str = "#34D399",
) -> QIcon:
    return QIcon(render_svg_pixmap(name, size=size, color=color, fill=fill, accent=accent))


def write_chevron_svg_file(target_path: str, color: str = "#94A3B8") -> str:
    svg_xml = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none">'
        f'<path d="M6 9L12 15L18 9" stroke="{color}" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    )
    with open(target_path, "w", encoding="utf-8") as fh:
        fh.write(svg_xml)
    return target_path