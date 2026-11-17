import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from src.gui import MainWindow


DEVICE = {'name': 'Test output', 'index': 1, 'default': True}


class TranscriptWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        settings = QSettings(str(Path(self.directory.name) / 'settings.ini'), QSettings.Format.IniFormat)
        self.window = MainWindow(settings=settings)
        self.window.show()
        self.devices = patch('src.live_gui.output_devices', return_value=[DEVICE])
        self.devices.start()
        self.window.open_live()
        self.app.processEvents()
        self.live = self.window.live_window

    def tearDown(self):
        if self.live.worker:
            self.live.stop_session()
            self.wait_until(lambda: self.live.worker is None)
        self.window.close()
        self.devices.stop()
        self.directory.cleanup()

    def wait_until(self, condition):
        deadline = time.monotonic() + 5
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertTrue(condition())

    def test_text_matches_before_and_after_open_clear_and_reopen(self):
        self.live.add_paragraph(0, 'Начало 🎧')
        self.live.detach.click()
        detached = self.live.transcript_window
        self.assertTrue(detached.preview.isReadOnly())
        self.assertEqual(detached.preview.toPlainText(), self.live.preview.toPlainText())
        selection = detached.preview.textCursor()
        selection.setPosition(0)
        selection.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
        detached.preview.setTextCursor(selection)
        self.live.add_paragraph(8, 'Продолжение')
        self.assertEqual(detached.preview.textCursor().selectedText(), 'Начало')
        self.live.session_timestamps = True
        self.live.add_paragraph(65, 'Абзац с таймкодом')
        self.assertEqual(detached.preview.toPlainText(), self.live.preview.toPlainText())
        detached.copy.click()
        self.assertEqual(self.app.clipboard().text(), self.live.preview.toPlainText())
        detached.close()
        self.live.add_paragraph(75, 'Продолжение после закрытия')
        self.live.detach.click()
        self.assertIs(self.live.transcript_window, detached)
        self.assertEqual(detached.preview.toPlainText(), self.live.preview.toPlainText())
        self.live.preview.clear()
        self.assertEqual(detached.preview.toPlainText(), '')
        self.live.add_paragraph(0, 'Новый сеанс 🎧')
        self.assertEqual(detached.preview.toPlainText(), self.live.preview.toPlainText())

    def test_buttons_control_one_worker_and_closing_text_keeps_session_running(self):
        jobs = []

        def fake_live(job, stopped, status, paragraph, meter, saved, selection):
            jobs.append(job)
            paragraph(8, 'Речь из эфира')
            deadline = time.monotonic() + 4
            while not stopped() and time.monotonic() < deadline:
                time.sleep(0.005)
            paragraph(16, 'Остаток звука')

        self.live.no_save.click()
        self.live.timestamps.setChecked(True)
        self.live.language.setCurrentIndex(1)
        self.live.add_paragraph(0, 'Старый текст')
        self.live.detach.click()
        detached = self.live.transcript_window
        self.assertTrue(detached.timestamps.isChecked())
        with patch('src.live_gui.run_live', side_effect=fake_live):
            detached.start.click()
            self.wait_until(lambda: 'Речь из эфира' in detached.preview.toPlainText())
            self.assertEqual(len(jobs), 1)
            self.assertFalse(jobs[0].autosave)
            self.assertEqual(jobs[0].language, 'ru')
            self.assertTrue(jobs[0].timestamps)
            self.assertNotIn('Старый текст', detached.preview.toPlainText())
            self.assertFalse(detached.start.isEnabled())
            self.assertTrue(detached.stop.isEnabled())
            self.assertFalse(detached.timestamps.isEnabled())
            self.assertFalse(self.live.language.isEnabled())
            worker = self.live.worker
            self.window.showMinimized()
            self.app.processEvents()
            self.assertFalse(detached.isMinimized())
            detached.close()
            self.assertIs(self.live.worker, worker)
            self.assertFalse(worker.isInterruptionRequested())
            self.live.open_transcript_window()
            detached.stop.click()
            self.assertFalse(self.live.stop.isEnabled())
            self.assertFalse(detached.stop.isEnabled())
            self.wait_until(lambda: self.live.worker is None)
            self.assertTrue(detached.start.isEnabled())
            self.assertTrue(detached.timestamps.isEnabled())
            self.assertTrue(self.live.language.isEnabled())
            self.assertIn('Остаток звука', detached.preview.toPlainText())
            self.assertEqual(detached.preview.toPlainText(), self.live.preview.toPlainText())

    def test_timestamp_buttons_stay_in_sync_between_windows(self):
        self.live.detach.click()
        detached = self.live.transcript_window
        self.assertFalse(detached.timestamps.isChecked())
        detached.timestamps.click()
        self.assertTrue(self.live.timestamps.isChecked())
        self.live.timestamps.click()
        self.assertFalse(detached.timestamps.isChecked())
        self.live.timestamps.click()
        detached.close()
        self.live.detach.click()
        self.assertTrue(detached.timestamps.isChecked())
        detached.timestamps.click()
        self.assertFalse(self.live.timestamps.isChecked())

    def test_sharing_live_creates_fixed_snapshot_even_without_autosave(self):
        self.live.no_save.click()
        self.live.detach.click()
        detached = self.live.transcript_window
        self.assertFalse(self.live.share.isEnabled())
        self.assertFalse(detached.share.isEnabled())
        with patch('src.live_gui.ROOT', Path(self.directory.name)):
            with self.assertRaises(ValueError):
                self.live.create_share_file()
            self.live.add_paragraph(0, 'Первый фрагмент 🎧')
            self.assertTrue(self.live.share.isEnabled())
            self.assertTrue(detached.share.isEnabled())
            first = self.live.create_share_file()
            self.live.add_paragraph(8, 'Следующий фрагмент')
            second = detached.share.provider()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_text(encoding='utf-8'), 'Первый фрагмент 🎧\n')
        self.assertEqual(second.read_text(encoding='utf-8').strip(), self.live.preview.toPlainText())
        self.assertEqual(self.live.paths, [])

    def test_main_close_waits_for_session_and_closes_both_windows(self):
        def fake_live(job, stopped, status, paragraph, meter, saved, selection):
            while not stopped():
                time.sleep(0.005)
            paragraph(8, 'Последний фрагмент')

        self.live.no_save.click()
        self.live.detach.click()
        detached = self.live.transcript_window
        with patch('src.live_gui.run_live', side_effect=fake_live):
            detached.start.click()
            self.window.close()
            self.wait_until(lambda: self.live.worker is None and not self.window.isVisible())
        self.assertFalse(detached.isVisible())
        self.assertIn('Последний фрагмент', detached.preview.toPlainText())

    def test_error_reveals_settings_when_main_window_is_minimized(self):
        self.live.detach.click()
        self.window.showMinimized()
        self.live.failed('Проверка ошибки захвата')
        self.app.processEvents()
        self.assertFalse(self.window.isMinimized())
        self.assertEqual(self.window.pages.currentIndex(), 4)
        self.assertIn('Проверка ошибки захвата', self.live.status.text())


if __name__ == '__main__':
    unittest.main()
