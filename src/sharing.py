"""Share local transcript files through native file drag and drop."""

from pathlib import Path

from src.i18n import tr

from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QDrag
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)


def file_mime(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(tr('Файл не найден. Возможно, он был перемещён или удалён'))
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    return mime


class ShareFileButton(QPushButton):
    def __init__(self, provider, text=None, *, dialog=True):
        super().__init__(tr('Поделиться файлом') if text is None else text)
        self.provider = provider
        self.press_position = None
        self.dragged = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(tr('Перетащите файл в открытый чат или нажмите, чтобы открыть варианты передачи'))
        if dialog:
            self.clicked.connect(self.show_share_dialog)

    def prepare_file(self):
        try:
            path = Path(self.provider()).resolve()
            file_mime(path)
            return path
        except (OSError, ValueError) as error:
            QMessageBox.warning(self.window(), tr('Не удалось подготовить файл'), tr(str(error)))
            return None

    def mousePressEvent(self, event):
        self.dragged = False
        self.press_position = event.position().toPoint() if event.button() == Qt.MouseButton.LeftButton else None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self.press_position is not None and event.buttons() & Qt.MouseButton.LeftButton
                and (event.position().toPoint() - self.press_position).manhattanLength()
                >= QApplication.startDragDistance()):
            self.press_position = None
            self.dragged = True
            self.setDown(False)
            path = self.prepare_file()
            if path is not None:
                drag = QDrag(self)
                drag.setMimeData(file_mime(path))
                drag.exec(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.press_position = None
        if self.dragged:
            self.setDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def show_share_dialog(self):
        path = self.prepare_file()
        if path is None:
            return
        dialog = QDialog(self.window())
        dialog.setWindowTitle(tr('Поделиться файлом'))
        dialog.setObjectName('shell')
        dialog.setMinimumWidth(480)
        dialog.setMaximumWidth(640)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel(path.name)
        title.setProperty('userContent', True)
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        layout.addWidget(title)
        hint = QLabel(tr('Перетащите файл за кнопку ниже в открытый чат ChatGPT\n'
                      'или другое приложение, принимающее файлы'))
        hint.setObjectName('small')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        tile = ShareFileButton(lambda: path, tr('Перетащить файл в чат'), dialog=False)
        layout.addWidget(tile)
        actions = QHBoxLayout()
        copy = QPushButton(tr('Копировать файл'))
        def copy_file():
            try:
                QApplication.clipboard().setMimeData(file_mime(path))
                copy.setText(tr('Файл скопирован'))
            except OSError as error:
                QMessageBox.warning(dialog, tr('Не удалось скопировать файл'), tr(str(error)))
        copy.clicked.connect(copy_file)
        folder = QPushButton(tr('Открыть папку'))
        folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent))))
        actions.addWidget(copy)
        actions.addWidget(folder)
        layout.addLayout(actions)
        note = QLabel(tr('Файл прикрепится только после перетаскивания в чат.\n'
                      'Отправьте сообщение в чате, когда будете готовы'))
        note.setObjectName('small')
        note.setWordWrap(True)
        layout.addWidget(note)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.show()
