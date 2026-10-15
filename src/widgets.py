"""Small vector widgets; no external image assets required."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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
    elif kind == 'live':
        painter.setBrush(QColor('#d99b6b'))
        painter.drawEllipse(QPointF(24, 24), 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for radius in (11, 19):
            rect = QRectF(24 - radius, 24 - radius, radius * 2, radius * 2)
            painter.drawArc(rect, -55 * 16, 110 * 16)
            painter.drawArc(rect, 125 * 16, 110 * 16)
    elif kind in ('vk-video', 'vk-live'):
        painter.drawRoundedRect(QRectF(5, 6, 38, 36), 9, 9)
        mark = QPainterPath(QPointF(11, 17))
        mark.cubicTo(12, 25, 15, 31, 20, 31)
        mark.lineTo(20, 17)
        mark.moveTo(27, 17)
        mark.lineTo(27, 31)
        mark.moveTo(35, 17)
        mark.lineTo(27, 24)
        mark.lineTo(36, 31)
        painter.drawPath(mark)
        if kind == 'vk-live':
            painter.setBrush(QColor('#d99b6b'))
            painter.drawEllipse(QPointF(39, 9), 3, 3)
    elif kind == 'twitch':
        mark = QPainterPath(QPointF(9, 7))
        for x, y in ((39, 7), (39, 29), (29, 38), (22, 38), (16, 43), (16, 38), (9, 38), (9, 7)):
            mark.lineTo(x, y)
        painter.drawPath(mark)
        painter.drawLine(QPointF(22, 16), QPointF(22, 27))
        painter.drawLine(QPointF(30, 16), QPointF(30, 27))
    elif kind == 'rutube':
        painter.drawRoundedRect(QRectF(5, 6, 38, 36), 9, 9)
        mark = QPainterPath(QPointF(16, 32))
        mark.lineTo(16, 17)
        mark.lineTo(25, 17)
        mark.cubicTo(33, 17, 33, 25, 25, 25)
        mark.lineTo(16, 25)
        mark.moveTo(25, 25)
        mark.lineTo(32, 32)
        painter.drawPath(mark)
        painter.setBrush(QColor('#d99b6b'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(35, 13), 2, 2)
    painter.end()
    return QIcon(pixmap)


class SourceCard(QPushButton):
    def __init__(self, index, title, description, kind, parent=None):
        super().__init__(parent)
        self.setObjectName('sourceCard')
        self.setMinimumHeight(280)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        icons = QHBoxLayout()
        icons.setSpacing(6)
        services = (('link', 'YouTube'), ('vk-video', 'VK Видео'), ('rutube', 'Rutube'),
                    ('twitch', 'Twitch: записи'), ('vk-live', 'VK Видео Live: записи')) if kind == 'link' else ((kind, title),)
        for icon_kind, service in services:
            icon = QLabel()
            icon.setFixedSize(32, 32)
            icon.setPixmap(line_icon(icon_kind, 32).pixmap(32, 32))
            icon.setAccessibleName(service)
            icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            icons.addWidget(icon)
        icons.addStretch()
        label = QLabel(title)
        label.setObjectName('cardTitle')
        label.setWordWrap(True)
        label.setMinimumHeight(60)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        detail = QLabel(description)
        detail.setObjectName('muted')
        detail.setWordWrap(True)
        detail.setMinimumHeight(72)
        detail.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        number = QLabel(f'{index}  /  ВЫБРАТЬ ИСТОЧНИК')
        number.setObjectName('cardIndex')
        for widget in (number, label, detail):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addLayout(icons)
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
