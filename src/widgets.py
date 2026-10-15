"""Small vector widgets; no external image assets required."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


def line_icon(kind, size=48):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 48, size / 48)
    painter.setPen(QPen(QColor('#d99b6b'), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if kind == 'file':
        painter.drawRoundedRect(QRectF(8, 8, 30, 33), 4, 4)
        for x, height in ((15, 7), (21, 16), (27, 23), (33, 11)):
            painter.drawLine(QPointF(x, 25 - height / 2), QPointF(x, 25 + height / 2))
    elif kind == 'link':
        painter.drawRoundedRect(QRectF(4, 11, 40, 27), 7, 7)
        painter.drawLine(QPointF(21, 19), QPointF(30, 24))
        painter.drawLine(QPointF(30, 24), QPointF(21, 30))
        painter.drawLine(QPointF(21, 30), QPointF(21, 19))
    elif kind == 'copy':
        painter.drawRoundedRect(QRectF(15, 14, 23, 29), 3, 3)
        painter.drawLine(QPointF(29, 8), QPointF(9, 8))
        painter.drawLine(QPointF(9, 8), QPointF(9, 33))
    painter.end()
    return QIcon(pixmap)


class SourceCard(QPushButton):
    def __init__(self, index, title, description, kind, parent=None):
        super().__init__(parent)
        self.setObjectName('sourceCard')
        self.setMinimumHeight(225)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(27, 24, 27, 24)
        icon = QLabel()
        icon.setPixmap(line_icon(kind, 48).pixmap(48, 48))
        label = QLabel(title)
        label.setObjectName('cardTitle')
        label.setWordWrap(True)
        detail = QLabel(description)
        detail.setObjectName('muted')
        detail.setWordWrap(True)
        number = QLabel(f'{index}  /  ВЫБРАТЬ ИСТОЧНИК')
        number.setObjectName('cardIndex')
        for widget in (icon, number, label, detail):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(icon)
        layout.addStretch()
        layout.addWidget(number)
        layout.addWidget(label)
        layout.addWidget(detail)


class Waveform(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(125)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.advance)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.update()

    def advance(self):
        self.phase += 0.11
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        center = self.width() / 2
        for i in range(41):
            envelope = math.exp(-((i - 20) / 12) ** 2)
            pulse = (0.5 + 0.5 * math.sin(self.phase + i * 0.63)) if self.timer.isActive() else 0.3
            height = 5 + envelope * (18 + 66 * pulse)
            color = QColor('#d39362')
            color.setAlphaF(0.3 + 0.7 * envelope)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(center + (i - 20) * 8 - 2, (self.height() - height) / 2, 4, height), 2, 2)
