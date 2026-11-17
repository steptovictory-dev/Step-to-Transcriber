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
        self.assertTrue(self.window.share.isEnabled())
        self.assertEqual(self.window.share_result_file(), Path('result.md'))
        self.window.copy_text()
        self.assertEqual(self.app.clipboard().text(), 'Только Markdown')
        self.assertTrue((not self.window.open_txt.isVisible()))
        self.assertFalse((not self.window.open_md.isVisible()))
        self.window.format.setCurrentIndex(2)
        self.window.new_button.click()
        self.assertEqual(self.window.pages.currentIndex(), 0)
        self.assertEqual(self.window.format.currentData(), ('md',))
        self.assertEqual(self.window.preview.toPlainText(), '')
        self.assertFalse(self.window.share.isEnabled())
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

    def test_timestamp_buttons_select_one_state_and_reset(self):
        for control, enabled in ((self.window.timestamps_off, False),
                                 (self.window.timestamps_off, False),
                                 (self.window.timestamps, True),
                                 (self.window.timestamps, True)):
            control.click()
            self.assertEqual(self.window.timestamps.isChecked(), enabled)
            self.assertEqual(self.window.timestamps_off.isChecked(), not enabled)
        self.window.timestamps_off.click()
        self.window.go_home()
        self.assertTrue(self.window.timestamps.isChecked())
        self.assertFalse(self.window.timestamps_off.isChecked())

    def test_result_toolbar_updates_text_exports_and_clipboard_for_both_sources(self):
        from src.transcriber import TranscriptSegment
        for remote in (False, True):
            for initial in (False, True):
                with self.subTest(remote=remote, initial=initial), tempfile.TemporaryDirectory() as temporary:
                    self.window.select_source(remote)
                    self.window.timestamps.setChecked(initial)
                    directory = Path(temporary)
                    result = Result(directory / 'test.txt', directory / 'test.md', 'Title',
                                    segments=[TranscriptSegment(65, 66, 'First paragraph'),
                                              TranscriptSegment(110, 111, 'Second paragraph')],
                                    source='https://youtu.be/BaW_jenozKc' if remote else None)
                    result.txt.touch()
                    result.markdown.touch()
                    result.set_timestamps(initial)
                    self.window.completed(result)
                    self.assertEqual(self.window.result_timestamps.isChecked(), initial)
                    for enabled in (not initial, initial):
                        self.window.result_timestamps.click()
                        self.assertEqual(self.window.result_timestamps.isChecked(), enabled)
                        self.assertEqual('[00:01:05]' in self.window.preview.toPlainText(), enabled)
                        self.assertEqual('[00:01:05]' in result.txt.read_text(encoding='utf-8'), enabled)
                        self.assertEqual('**[00:01:05]**' in result.markdown.read_text(encoding='utf-8'), enabled)
                        self.assertIn('# Title', result.markdown.read_text(encoding='utf-8'))
                        if remote:
                            self.assertIn(result.source, result.markdown.read_text(encoding='utf-8'))
                        self.app.processEvents()
                        self.window.copy.click()
                        QTest.qWait(20)
                        self.assertEqual(self.app.clipboard().text(), self.window.preview.toPlainText())
                        self.assertEqual(self.window.copy.text(), '')
                        self.assertEqual(self.window.share_result_file(), result.markdown)

    def test_result_timestamp_failure_restores_toggle_text_and_files(self):
        from src.transcriber import TranscriptSegment
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = Result(directory / 'test.txt', directory / 'test.md', 'Title',
                            segments=[TranscriptSegment(65, 66, 'Preserve this text')])
            result.txt.touch()
            result.markdown.touch()
            result.set_timestamps(True)
            self.window.completed(result)
            originals = {path: path.read_bytes() for path in (result.txt, result.markdown)}
            original_text = self.window.preview.toPlainText()
            replace = Path.replace

            def fail_second_export(source, target):
                if source.name == 'test.md':
                    raise PermissionError('File is locked')
                return replace(source, target)

            with patch.object(Path, 'replace', fail_second_export), patch('src.gui.QMessageBox.warning') as warning:
                self.window.result_timestamps.click()
            warning.assert_called_once()
            self.assertTrue(self.window.result_timestamps.isChecked())
            self.assertEqual(self.window.preview.toPlainText(), original_text)
            self.assertEqual(result.text, original_text)
            for path, original in originals.items():
                self.assertEqual(path.read_bytes(), original)
            self.assertEqual(set(directory.iterdir()), set(originals))

    def test_result_file_menu_and_toolbar_follow_language_and_reset(self):
        self.window.completed(Result(None, Path('test.md'), 'Title', 'Original speech'))
        self.window.language_switch.click()
        self.window.theme_switch.click()
        self.assertEqual(self.window.open_md.text(), 'Open Markdown')
        self.assertEqual(self.window.folder_action.text(), 'Open folder')
        self.assertTrue(self.window.open_md.isVisible())
        self.assertFalse(self.window.open_txt.isVisible())
        self.assertEqual(self.window.preview.toPlainText(), 'Original speech')
        self.window.copy.click()
        self.assertEqual(self.window.copy.toolTip(), 'Copied')
        for control in (self.window.copy, self.window.share, self.window.open_folder,
                        self.window.result_timestamps):
            self.assertEqual(control.text(), '')
            self.assertEqual(control.width(), 38)
            self.assertTrue(control.accessibleName())
        self.window.new_button.click()
        self.assertFalse(self.window.open_folder.isEnabled())
        self.assertFalse(self.window.result_timestamps.isEnabled())
        self.assertFalse(self.window.copy.isEnabled())

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
