import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PySide6.QtWidgets import QApplication

from src.live import DeviceUnavailable, LiveJob, SessionWriter, confirmed_text, resample_audio, run_live
from src.gui import MainWindow


DEVICE = {'name': 'Test output [Loopback]', 'index': 1, 'defaultSampleRate': 16000,
          'maxInputChannels': 1, 'isLoopbackDevice': True, 'default': True}


class LiveTests(unittest.TestCase):
    def test_resampling_stereo_preserves_duration_and_amplitude(self):
        signal = np.full((48000, 2), 8192, dtype='<i2')
        result = resample_audio(signal.tobytes(), 2, 48000)
        self.assertEqual(result.shape, (16000,))
        self.assertAlmostEqual(float(result[100:-100].mean()), 0.25, places=4)

    def test_overlap_words_belong_to_exactly_one_interval(self):
        words = [SimpleNamespace(start=7.5, end=8.5, word=' граница'),
                 SimpleNamespace(start=8.5, end=9.0, word=' хвост')]
        segments = [SimpleNamespace(words=words)]
        self.assertEqual(list(confirmed_text(iter(segments), 0, 0, 8)), [])
        self.assertEqual(list(confirmed_text(iter(segments), 0, 8, 16)), [(8, 'граница хвост')])

    def test_writer_flushes_before_session_ends_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            job = LiveJob(DEVICE, Path(directory), ('md', 'txt'), timestamps=True)
            first = SessionWriter(job, stack)
            first.append(8, 'Уже сохранённая речь')
            second = SessionWriter(job, stack)
            self.assertNotEqual(first.paths, second.paths)
            self.assertIn('[00:00:08] Уже сохранённая речь', first.paths[0].read_text(encoding='utf-8'))
            self.assertEqual(first.paths[1].read_text(encoding='utf-8').strip(), '[00:00:08] Уже сохранённая речь')

    def test_disabled_autosave_creates_no_directory_or_files(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            destination = Path(directory) / 'must_not_exist'
            writer = SessionWriter(LiveJob(DEVICE, destination, autosave=False), stack)
            writer.append(8, 'Текст только в окне')
            writer.append(16, '[Сеанс завершён]', note=True)
            self.assertEqual(writer.paths, [])
            self.assertFalse(destination.exists())

    def test_timestamps_are_off_by_default_in_both_formats(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            writer = SessionWriter(LiveJob(DEVICE, Path(directory), ('md', 'txt')), stack)
            writer.append(8, 'Текст без таймкода')
            writer.append(16, '[Смена устройства]', note=True)
            for path in writer.paths:
                text = path.read_text(encoding='utf-8')
                self.assertIn('Текст без таймкода', text)
                self.assertNotIn('[00:00:', text)

    def test_device_switch_keeps_one_model_one_file_and_flushes_tail(self):
        state = {'selection': dict(DEVICE), 'stop': False, 'opened': 0, 'models': 0}

        class Stream:
            def __init__(self, callback):
                self.callback = callback
                self.stopped = True

            def start_stream(self):
                self.stopped = False
                state['opened'] += 1
                self.callback(np.full(16000, 500, dtype='<i2').tobytes(), 16000, {}, 0)
                if state['opened'] == 1:
                    state['selection'] = dict(DEVICE, name='Second output')
                else:
                    state['stop'] = True

            def is_stopped(self):
                return self.stopped

            def is_active(self):
                return not self.stopped

            def stop_stream(self):
                self.stopped = True

            def close(self):
                self.stopped = True

        class Audio:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get_loopback_device_info_generator(self):
                return iter([DEVICE, dict(DEVICE, name='Second output')])

            def open(self, **kwargs):
                return Stream(kwargs['stream_callback'])

        class Model:
            def __init__(self, *args, **kwargs):
                state['models'] += 1

            def transcribe(self, samples, **kwargs):
                word = SimpleNamespace(start=0.1, end=0.5, word=' Проверка')
                return iter([SimpleNamespace(words=[word])]), SimpleNamespace(language='ru', language_probability=1)

        backend = SimpleNamespace(PyAudio=Audio, paInt16=8, paContinue=0, paAbort=2)
        paragraphs = []
        paths = []
        with tempfile.TemporaryDirectory() as directory, patch('src.live.audio_backend', return_value=backend):
            run_live(LiveJob(DEVICE, Path(directory)), lambda: state['stop'], lambda text: None,
                     lambda seconds, text: paragraphs.append(text), lambda *args: None,
                     paths.extend, model_factory=Model, selection=lambda: state['selection'])
            self.assertEqual(state['models'], 1)
            self.assertEqual(state['opened'], 2)
            self.assertEqual(paragraphs.count('Проверка'), 2)
            self.assertEqual(len(paths), 1)
            text = paths[0].read_text(encoding='utf-8')
            self.assertIn('Смена устройства', text)
            self.assertIn('Сеанс завершён', text)

    def test_missing_default_output_waits_in_same_session_until_stopped(self):
        state = {'stop': False}
        paragraphs = []

        def status(text):
            if text.startswith('Ожидаем'):
                state['stop'] = True

        with tempfile.TemporaryDirectory() as directory, \
                patch('src.live.capture_device', side_effect=DeviceUnavailable()), \
                patch('src.live.audio_backend'):
            run_live(LiveJob({'name': 'Windows default', 'automatic': True}, Path(directory)),
                     lambda: state['stop'], status, lambda seconds, text: paragraphs.append(text),
                     lambda *args: None, lambda paths: None, model_factory=lambda *args, **kwargs: object())
            self.assertEqual(len(paragraphs), 1)
            text = next(Path(directory).glob('*.md')).read_text(encoding='utf-8')
            self.assertIn('ожидаем устройство Windows', text)
            self.assertIn('Сеанс завершён', text)


class LiveGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_embedded_page_default_device_and_safe_close(self):
        with patch('src.live_gui.output_devices', return_value=[DEVICE]):
            main = MainWindow()
            main.show()
            main.open_live()
            self.app.processEvents()
            window = main.live_window
            self.assertFalse(window.isWindow())
            self.assertIs(window.window(), main)
            self.assertEqual(main.pages.currentIndex(), 4)
            main.open_live()
            self.assertIs(main.live_window, window)
            self.assertEqual(main.pages.count(), 5)
            window.back.click()
            self.assertEqual(main.pages.currentIndex(), 0)
            main.open_live()
            self.assertTrue(window.device.currentData()['automatic'])
            self.assertFalse(window.timestamps.isChecked())
            self.assertTrue(window.autosave.isChecked())
            window.no_save.click()
            self.assertFalse(window.autosave.isChecked())
            self.assertFalse(window.output.isEnabled())
            self.assertFalse(window.formats.isEnabled())
            self.assertFalse(window.browse.isEnabled())
            window.autosave.click()
            self.assertTrue(window.output.isEnabled())
            window.add_paragraph(8, 'Без таймкодов')
            self.assertNotIn('[00:00:08]', window.preview.toPlainText())
            window.session_timestamps = True
            window.add_paragraph(16, 'С таймкодами')
            self.assertIn('[00:00:16] С таймкодами', window.preview.toPlainText())

            def fake_live(job, stopped, status, paragraph, meter, saved, **kwargs):
                paragraph(0, 'Живой текст')
                deadline = time.monotonic() + 3
                while not stopped() and time.monotonic() < deadline:
                    time.sleep(0.005)

            with patch('src.live_gui.run_live', side_effect=fake_live):
                window.start_session()
                self.assertTrue(window.device.isEnabled())
                self.assertFalse(window.back.isEnabled())
                main.go_home()
                main.select_source(True)
                self.assertEqual(main.pages.currentIndex(), 4)
                self.assertFalse(window.output.isEnabled())
                with patch('src.live_gui.QMediaDevices.defaultAudioOutput') as default_output:
                    default_output.return_value.id.return_value = b'new-default'
                    default_output.return_value.description.return_value = 'New default output'
                    window.windows_device_changed()
                    self.assertEqual(window.worker.requested_device['endpoint'], b'new-default'.hex())
                    self.assertTrue(window.worker.requested_device['automatic'])
                window.device.setCurrentIndex(1)
                self.assertEqual(window.worker.requested_device['name'], DEVICE['name'])
                main.close()
                deadline = time.monotonic() + 5
                while window.worker and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.005)
                self.assertIsNone(window.worker)
                self.assertIn('Живой текст', window.preview.toPlainText())
                self.assertFalse(main.isVisible())
                self.assertFalse(window.isVisible())


if __name__ == '__main__':
    unittest.main()

