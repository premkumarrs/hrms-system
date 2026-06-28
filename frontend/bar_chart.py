from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QRectF


class BarChartWidget(QWidget):
    """A minimal bar chart painted with QPainter (no external deps)."""

    def __init__(self, parent=None, title=None):
        super().__init__(parent)
        self.title = title or ""
        self.data = []  # list of (label, value)
        self.setMinimumHeight(220)

    def set_title(self, title):
        self.title = title or ""
        self.update()

    def set_data(self, data):
        # Keep at most 12 bars for readability.
        self.data = list(data)[:12]
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#121212"))

        if not self.data:
            painter.setPen(QColor("#888888"))
            painter.drawText(
                rect, Qt.AlignmentFlag.AlignCenter,
                "No chartable data for this report."
            )
            painter.end()
            return

        margin_left = 40
        margin_bottom = 40
        margin_top = 36 if self.title else 20
        width = rect.width() - margin_left - 20
        height = rect.height() - margin_bottom - margin_top

        if self.title:
            title_font = QFont()
            title_font.setPointSize(10)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.setPen(QColor("#cccccc"))
            painter.drawText(
                QRectF(margin_left, 4, width, 24),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.title,
            )
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)

        max_value = max((v for _, v in self.data), default=0) or 1

        count = len(self.data)
        slot = width / count
        bar_width = slot * 0.6

        painter.setPen(QColor("#444444"))
        painter.drawLine(
            margin_left, rect.height() - margin_bottom,
            margin_left + width, rect.height() - margin_bottom
        )

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        for i, (label, value) in enumerate(self.data):
            bar_height = (value / max_value) * height
            x = margin_left + i * slot + (slot - bar_width) / 2
            y = rect.height() - margin_bottom - bar_height

            painter.fillRect(
                QRectF(x, y, bar_width, bar_height),
                QColor("#5b8def")
            )

            painter.setPen(QColor("#dddddd"))
            painter.drawText(
                QRectF(x - slot * 0.2, y - 16, slot * 0.8 + bar_width, 14),
                Qt.AlignmentFlag.AlignCenter,
                self._fmt(value)
            )

            text = str(label)
            if len(text) > 10:
                text = text[:9] + "…"
            painter.drawText(
                QRectF(margin_left + i * slot, rect.height() - margin_bottom + 4,
                       slot, margin_bottom - 6),
                Qt.AlignmentFlag.AlignCenter,
                text
            )

        painter.end()

    def _fmt(self, value):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return f"{value:.1f}" if isinstance(value, float) else str(value)
