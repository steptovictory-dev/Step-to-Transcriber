"""Small vector widgets; no external image assets required."""

import math

from src.i18n import tr

from PySide6.QtCore import QEasingCurve, QPointF, Property, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLayout, QPushButton, QVBoxLayout, QWidget


class GuitarKnob(QPushButton):
    """Two-position rotary control inspired by amber guitar volume knobs."""

    def __init__(self, left, right, parent=None):
        super().__init__(parent)
        self.left, self.right = left, right
        self.light = False
        self._position = 0.0
        self.setCheckable(True)
        self.setFixedSize(136, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setStyleSheet('QPushButton { border: none; background: transparent; padding: 0; }')
        self.animation = QPropertyAnimation(self, b'position', self)
        self.animation.setDuration(170)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self.animate)

    def get_position(self):
        return self._position

    def set_position(self, value):
        self._position = value
        self.update()

    position = Property(float, get_position, set_position)

    def animate(self, checked):
        self.animation.stop()
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.setChecked(event.key() == Qt.Key.Key_Right)
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = '#995a34' if self.light else '#df9b66'
        muted = '#746957' if self.light else '#a69a8b'
        p.setFont(QFont('Segoe UI', 8, QFont.Weight.DemiBold))
        for text, rect, selected in ((self.left, QRectF(0, 0, 43, 30), not self.isChecked()),
                                     (self.right, QRectF(93, 0, 43, 30), self.isChecked())):
            p.setPen(QColor(ink if selected else muted))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        center = QPointF(68, 14)
        # A soft mounting shadow keeps the circular silhouette clear in both themes
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(65, 40, 17, 40 if self.light else 100))
        p.drawEllipse(QPointF(68, 16), 14, 13)
        amber = QLinearGradient(58, 2, 78, 27)
        amber.setColorAt(0, QColor('#f0dbab'))
        amber.setColorAt(0.3, QColor('#c79a58'))
        amber.setColorAt(0.7, QColor('#956236'))
        amber.setColorAt(1, QColor('#dbb67b'))
        p.setPen(QPen(QColor('#a78350'), 0.8))
        p.setBrush(amber)
        p.drawEllipse(center, 13, 13)
        # Fine radial fluting references the grip around a guitar's control knob
        p.setPen(QPen(QColor('#f8e5bf'), 0.65))
        for index in range(28):
            angle = math.tau * index / 28
            p.drawLine(center + QPointF(math.cos(angle) * 11, math.sin(angle) * 11),
                       center + QPointF(math.cos(angle) * 12, math.sin(angle) * 12))
        face = QRadialGradient(QPointF(64, 9), 17)
        face.setColorAt(0, QColor('#f8e8c4'))
        face.setColorAt(0.55, QColor('#d3ac71'))
        face.setColorAt(1, QColor('#ad7c42'))
        p.setBrush(face)
        p.setPen(QPen(QColor('#8e653b'), 0.7))
        p.drawEllipse(center, 9.5, 9.5)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor('#f9e6be'), 0.65))
        p.drawEllipse(center, 8, 8)
        angle = math.radians(-140 + 100 * self._position)
        direction = QPointF(math.cos(angle), math.sin(angle))
        p.setPen(QPen(QColor('#704323'), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(center + direction * 3, center + direction * 7.5)


class AlignedRow(QLayout):
    """Keep two groups against opposite edges, wrapping when space is limited."""

    def __init__(self, left, right):
        super().__init__()
        self.items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(12)
        for widgets in (left, right):
            group = QWidget()
            layout = QHBoxLayout(group)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            for widget in widgets:
                layout.addWidget(widget)
            self.addWidget(group)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def sizeHint(self):
        sizes = [item.sizeHint() for item in self.items]
        return QSize(sum(size.width() for size in sizes) + self.spacing(),
                     max((size.height() for size in sizes), default=0))

    def minimumSize(self):
        sizes = [item.minimumSize() for item in self.items]
        return QSize(max((size.width() for size in sizes), default=0),
                     max((size.height() for size in sizes), default=0))

    def expandingDirections(self):
        return Qt.Orientation.Horizontal

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        sizes = [item.sizeHint() for item in self.items]
        if width < self.sizeHint().width():
            return sum(size.height() for size in sizes) + self.spacing()
        return self.sizeHint().height()

    def setGeometry(self, rect):
        super().setGeometry(rect)
        if len(self.items) != 2:
            return
        left, right = [item.sizeHint() for item in self.items]
        if rect.width() < self.sizeHint().width():
            self.items[0].setGeometry(QRect(rect.x(), rect.y(), left.width(), left.height()))
            self.items[1].setGeometry(QRect(rect.right() - right.width() + 1,
                                           rect.y() + left.height() + self.spacing(),
                                           right.width(), right.height()))
        else:
            height = max(left.height(), right.height())
            self.items[0].setGeometry(QRect(rect.x(), rect.y() + (height - left.height()) // 2,
                                           left.width(), left.height()))
            self.items[1].setGeometry(QRect(rect.right() - right.width() + 1,
                                           rect.y() + (height - right.height()) // 2,
                                           right.width(), right.height()))


def accent_color():
    return '#995a34' if QApplication.instance().property('ui_theme') == 'light' else '#d99b6b'


def line_icon(kind, size=48):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 48, size / 48)
    painter.setPen(QPen(QColor(accent_color()), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
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
    elif kind == 'detach':
        painter.drawLine(QPointF(28, 8), QPointF(40, 8))
        painter.drawLine(QPointF(40, 8), QPointF(40, 20))
        painter.drawLine(QPointF(40, 8), QPointF(23, 25))
        frame = QPainterPath(QPointF(22, 10))
        for x, y in ((10, 10), (10, 38), (38, 38), (38, 26)):
            frame.lineTo(x, y)
        painter.drawPath(frame)
    elif kind == 'folder':
        folder = QPainterPath(QPointF(6, 15))
        for x, y in ((6, 10), (20, 10), (25, 16), (41, 16), (41, 38), (6, 38), (6, 15)):
            folder.lineTo(x, y)
        painter.drawPath(folder)
    elif kind == 'timestamps':
        painter.drawEllipse(QPointF(24, 24), 17, 17)
        painter.drawLine(QPointF(24, 13), QPointF(24, 24))
        painter.drawLine(QPointF(24, 24), QPointF(32, 29))
    elif kind == 'share':
        for x, y in ((12, 24), (35, 11), (35, 37)):
            painter.drawEllipse(QPointF(x, y), 5, 5)
        painter.drawLine(QPointF(17, 21), QPointF(30, 14))
        painter.drawLine(QPointF(17, 27), QPointF(30, 34))
    elif kind == 'live':
        painter.setBrush(QColor(accent_color()))
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
            painter.setBrush(QColor(accent_color()))
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
        painter.setBrush(QColor(accent_color()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(35, 13), 2, 2)
    painter.end()
    return QIcon(pixmap)


class SourceCard(QPushButton):
    def __init__(self, index, title, description, kind, parent=None):
        super().__init__(parent)
        self.setObjectName('sourceCard')
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setMinimumHeight(280)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        icons = QHBoxLayout()
        icons.setSpacing(6)
        services = (('link', 'YouTube'), ('vk-video', tr('VK Видео')), ('rutube', 'Rutube'),
                    ('twitch', tr('Twitch: записи')), ('vk-live', tr('VK Видео Live: записи'))) if kind == 'link' else ((kind, title),)
        for icon_kind, service in services:
            icon = QLabel()
            icon.setFixedSize(32, 32)
            icon.setProperty('icon_kind', icon_kind)
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
        number = QLabel(tr(f'{index}  /  ВЫБРАТЬ ИСТОЧНИК'))
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
            color = QColor(accent_color())
            color.setAlphaF(0.3 + 0.7 * envelope)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(center + (i - 20) * 8 - 2, (self.height() - height) / 2, 4, height), 2, 2)
