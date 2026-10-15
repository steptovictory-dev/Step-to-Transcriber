import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from src.gui import MainWindow
from src.pipeline import Result


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.select_source(True)
        self.window.source.setText('https://youtu.be/1tCfHLFnXSw')

    def tearDown(self):
        self.window.close()

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
