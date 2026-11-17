import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from src.sharing import ShareFileButton, file_mime


class SharingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'Расшифровка с пробелами.txt'
        self.path.write_text('Текст эфира 🎧', encoding='utf-8')
        self.host = QWidget()
        self.button = ShareFileButton(lambda: self.path)
        self.button.setParent(self.host)
        self.button.resize(240, 48)
        self.host.resize(300, 100)
        self.host.show()
        self.app.processEvents()

    def tearDown(self):
        for dialog in self.host.findChildren(QDialog):
            dialog.close()
        self.host.close()
        self.directory.cleanup()

    def test_file_mime_contains_local_file_not_just_path_text(self):
        mime = file_mime(self.path)
        self.assertTrue(mime.hasUrls())
        self.assertTrue(mime.urls()[0].isLocalFile())
        self.assertEqual(Path(mime.urls()[0].toLocalFile()), self.path.resolve())
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'Текст эфира 🎧')

    def test_mouse_drag_exports_copy_of_file_without_opening_dialog(self):
        provider = Mock(return_value=self.path)
        self.button.provider = provider
        QTest.mousePress(self.button, Qt.MouseButton.LeftButton, pos=self.button.rect().center())
        position = QPointF(self.button.rect().center()) + QPointF(40, 0)
        event = QMouseEvent(QEvent.Type.MouseMove, position, position,
                            Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
        with patch('src.sharing.QDrag') as drag:
            self.app.sendEvent(self.button, event)
            mime = drag.return_value.setMimeData.call_args.args[0]
            self.assertEqual(Path(mime.urls()[0].toLocalFile()), self.path.resolve())
            drag.return_value.exec.assert_called_once_with(Qt.DropAction.CopyAction)
        QTest.mouseRelease(self.button, Qt.MouseButton.LeftButton)
        provider.assert_called_once()
        self.assertEqual(self.host.findChildren(QDialog), [])

    def test_click_opens_dialog_with_fixed_file_and_clipboard(self):
        self.button.click()
        dialog = self.host.findChild(QDialog)
        self.assertIsNotNone(dialog)
        tile = dialog.findChild(ShareFileButton)
        self.assertEqual(tile.prepare_file(), self.path.resolve())
        from PySide6.QtWidgets import QPushButton
        copy = next(item for item in dialog.findChildren(QPushButton) if item.text() == 'Копировать файл')
        copy.click()
        mime = self.app.clipboard().mimeData()
        self.assertEqual(Path(mime.urls()[0].toLocalFile()), self.path.resolve())

    def test_missing_file_shows_error_instead_of_starting_share(self):
        self.path.unlink()
        with patch('src.sharing.QMessageBox.warning') as warning:
            self.assertIsNone(self.button.prepare_file())
            warning.assert_called_once()
        self.assertEqual(self.host.findChildren(QDialog), [])


if __name__ == '__main__':
    unittest.main()
