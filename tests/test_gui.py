import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.gui import MainWindow
from src.pipeline import Result


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.preferences_dir = tempfile.TemporaryDirectory()
        self.preferences_path = str(Path(self.preferences_dir.name) / 'preferences.ini')
        self.window = MainWindow(settings=QSettings(self.preferences_path, QSettings.Format.IniFormat))
        self.window.select_source(True)
        self.window.source.setText('https://youtu.be/1tCfHLFnXSw')

    def tearDown(self):
        self.window.close()
        self.preferences_dir.cleanup()

    def test_f11_toggles_fullscreen_and_restores_window_state(self):
        self.window.show()
        self.window.activateWindow()
        QTest.qWait(100)
        for maximized in (False, True):
            if maximized:
                self.window.showMaximized()
            self.app.processEvents()
            for page, field in ((1, self.window.source), (3, self.window.preview)):
                self.window.navigate(page, animate=False)
                field.setFocus()
                QTest.keyClick(field, Qt.Key.Key_F11)
                self.app.processEvents()
                self.assertTrue(self.window.isFullScreen())
                QTest.keyClick(field, Qt.Key.Key_F11)
                self.app.processEvents()
                self.assertFalse(self.window.isFullScreen())
                self.assertEqual(self.window.isMaximized(), maximized)

    def test_output_directory_is_shared_and_survives_home_and_restart(self):
        from src.gui import ROOT
        self.assertEqual(self.window.output.text(), str(ROOT / 'output'))
        chosen = str(Path(self.preferences_dir.name) / 'Расшифровки')
        self.window.output.setText(chosen)
        self.window.go_home()
        self.window.select_source(False)
        self.assertEqual(self.window.output.text(), chosen)
        self.window.select_source(True)
        self.assertEqual(self.window.output.text(), chosen)
        with patch('src.live_gui.LivePage.refresh_devices'):
            self.window.open_live()
            live = self.window.live_window
            self.assertEqual(live.output.text(), chosen)
            changed = str(Path(self.preferences_dir.name) / 'Эфиры')
            live.output.setText(changed)
            self.assertEqual(self.window.output.text(), changed)
            self.window.go_home()
            self.assertEqual(self.window.output.text(), changed)
        self.window.close()
        self.window = MainWindow(settings=QSettings(self.preferences_path, QSettings.Format.IniFormat))
        self.assertEqual(self.window.output.text(), changed)
        self.window.output.clear()
        self.assertEqual(self.window.output_directory(), changed)

    def wait_for_worker(self):
        deadline = time.monotonic() + 10
        while self.window.worker is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertIsNone(self.window.worker)

    def test_worker_result_reaches_preview_and_restores_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            txt = Path(temporary) / 'test.txt'
            txt.write_text('Проверка интерфейса', encoding='utf-8')
            result = Result(txt, txt.with_suffix('.md'), 'Test', 'Проверка интерфейса')
            with patch('src.gui.run_job', return_value=result):
                self.window.start_job()
                self.assertFalse(self.window.start.isEnabled())
                self.wait_for_worker()
            self.assertEqual(self.window.preview.toPlainText(), 'Проверка интерфейса')
            self.assertTrue(self.window.start.isEnabled())
            self.assertTrue(self.window.open_txt.isEnabled())
            self.assertEqual(self.window.pages.currentIndex(), 3)

    def test_worker_failure_restores_controls(self):
        with patch('src.gui.run_job', side_effect=RuntimeError('Test failure')), self.assertLogs(level='ERROR'):
            self.window.start_job()
            self.wait_for_worker()
        self.assertTrue(self.window.start.isEnabled())
        self.assertEqual(self.window.pages.currentIndex(), 2)
        self.assertEqual(self.window.status.text(), 'Test failure')
        self.assertFalse(self.window.retry.isHidden())
        self.assertFalse(self.window.wave.timer.isActive())

    def test_worker_cancels_without_destroying_running_thread(self):
        def fake_job(job, status, progress, cancelled):
            deadline = time.monotonic() + 5
            while not cancelled() and time.monotonic() < deadline:
                time.sleep(0.005)
            raise InterruptedError()

        with patch('src.gui.run_job', side_effect=fake_job):
            self.window.start_job()
            self.window.close()
            self.wait_for_worker()
        self.assertIn('отменена', self.window.status.text())
        self.assertTrue(self.window.start.isEnabled())

    def test_markdown_default_result_can_be_copied_and_reset(self):
        self.assertEqual(self.window.format.currentData(), ('md',))
        self.assertTrue(self.window.timestamps.isChecked())
        self.window.timestamps.setChecked(False)
        result = Result(None, Path('result.md'), 'Test', 'Только Markdown')
        self.window.completed(result)
        self.window.copy_text()
        self.assertEqual(self.app.clipboard().text(), 'Только Markdown')
        self.assertTrue(self.window.open_txt.isHidden())
        self.assertFalse(self.window.open_md.isHidden())
        self.window.format.setCurrentIndex(2)
        self.window.new_button.click()
        self.assertEqual(self.window.pages.currentIndex(), 0)
        self.assertEqual(self.window.format.currentData(), ('md',))
        self.assertEqual(self.window.preview.toPlainText(), '')
        self.assertTrue(self.window.timestamps.isChecked())

    def test_timestamp_choice_is_passed_to_worker_for_both_sources(self):
        for remote in (False, True):
            for enabled in (False, True):
                with self.subTest(remote=remote, enabled=enabled):
                    self.window.select_source(remote)
                    self.window.source.setText('https://youtu.be/BaW_jenozKc' if remote else __file__)
                    self.window.timestamps.setChecked(enabled)
                    with patch.object(self.window, 'inspect_source'), patch('src.gui.Worker') as worker:
                        self.window.start_job()
                        self.assertEqual(worker.call_args.args[0].timestamps, enabled)
                    self.window.worker = None

    def test_source_cards_route_to_correct_setup(self):
        self.window.go_home()
        self.window.file_card.click()
        self.assertEqual(self.window.pages.currentIndex(), 1)
        self.assertFalse(self.window.is_youtube)
        self.assertFalse(self.window.browse.isHidden())
        self.window.go_home()
        self.window.url_card.click()
        self.assertTrue(self.window.is_youtube)
        self.assertTrue(self.window.browse.isHidden())


if __name__ == '__main__':
    unittest.main()
