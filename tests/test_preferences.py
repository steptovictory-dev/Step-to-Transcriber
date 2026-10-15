"""Appearance switches must preserve the current transcription and settings."""

import ast
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.gui import MainWindow
from src.i18n import PAIRS, set_language, tr


class PreferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QSettings(str(Path(self.directory.name) / 'ui.ini'), QSettings.Format.IniFormat)
        self.window = MainWindow(settings=self.settings)

    def tearDown(self):
        self.window.close()
        set_language('ru')
        self.directory.cleanup()

    def test_toggle_preserves_source_choices_and_result(self):
        self.window.select_source(True)
        self.window.source.setText('https://example.org/Русский')
        self.window.model.setCurrentIndex(1)
        self.window.timestamps.setChecked(False)
        self.window.advanced.show()
        self.window.preview.setPlainText('Источник / Source: original transcript')
        self.window.result_title.setText('Источник')
        self.window.language_switch.click()
        self.window.theme_switch.click()
        self.assertEqual(self.window.start.text(), 'Transcribe  →')
        self.assertEqual(self.window.source.text(), 'https://example.org/Русский')
        self.assertEqual(self.window.model.currentData(), 'large-v3')
        self.assertFalse(self.window.timestamps.isChecked())
        self.assertEqual(self.window.result_title.text(), 'Источник')
        self.assertEqual(self.window.preview.toPlainText(), 'Источник / Source: original transcript')
        self.assertEqual(self.window.pages.currentIndex(), 1)
        self.window.language_switch.click()
        self.assertEqual(self.window.start.text(), 'Расшифровать  →')
        self.window.language_switch.click()
        self.window.close()
        self.window = MainWindow(settings=self.settings)
        self.assertTrue(self.window.theme_switch.isChecked())
        self.assertTrue(self.window.language_switch.isChecked())
        self.assertEqual(self.window.start.text(), 'Transcribe  →')
        self.assertIn('#f2ebdd', self.window.styleSheet())

    def test_live_and_detached_window_follow_both_preferences(self):
        with patch('src.live_gui.LivePage.refresh_devices'):
            self.window.open_live()
            live = self.window.live_window
            live.preview.setPlainText('Не переводить эту речь / leave speech unchanged')
            live.open_transcript_window()
            self.window.language_switch.click()
            self.window.theme_switch.click()
            self.assertEqual(live.start.text(), 'Start transcription')
            self.assertEqual(live.transcript_window.start.text(), 'Start transcription')
            self.assertEqual(live.language.currentData(), None)
            self.assertEqual(live.transcript_window.preview.toPlainText(), live.preview.toPlainText())
            self.assertIn('#f2ebdd', live.transcript_window.styleSheet())
            live.set_status('Распознаём речь')
            self.window.language_switch.click()
            self.assertEqual(live.start.text(), 'Начать расшифровку')
            live.transcript_window.close()

    def test_keyboard_switches_and_dynamic_status(self):
        self.window.show()
        self.window.language_switch.setFocus()
        QTest.keyClick(self.window.language_switch, Qt.Key.Key_Space)
        self.assertEqual(self.window.ui_language, 'en')
        self.window.set_status('Загрузка модели и распознавание речи')
        self.assertEqual(self.window.status.text(), 'Loading model and transcribing speech')
        self.window.update_progress(0.43)
        self.assertEqual(self.window.percent.text(), '43% of current stage')
        self.window.language_switch.click()
        self.assertEqual(self.window.percent.text(), '43% текущего этапа')

    def test_all_static_interface_strings_have_translations(self):
        catalog = dict(PAIRS)
        missing = set()
        for name in ('gui', 'live_gui', 'widgets', 'sharing'):
            tree = ast.parse((Path(__file__).resolve().parents[1] / 'src' / f'{name}.py').read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr'
                        and node.args and isinstance(node.args[0], ast.Constant)):
                    text = node.args[0].value
                    if isinstance(text, str) and re.search('[А-Яа-яЁё]', text) and text not in catalog:
                        missing.add(text)
        self.assertEqual(sorted(missing), [])


if __name__ == '__main__':
    unittest.main()
