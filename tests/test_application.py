import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from src.pipeline import Job, run_job
from src.transcriber import TranscriptSegment
from src.youtube import normalize_youtube_url


class ApplicationTests(unittest.TestCase):
    def test_video_links_are_canonical_and_do_not_download_playlist(self):
        expected = 'https://www.youtube.com/watch?v=BaW_jenozKc'
        for url in (
            'https://youtu.be/BaW_jenozKc?t=10',
            'https://www.youtube.com/watch?v=BaW_jenozKc&list=PLsomething',
            'https://m.youtube.com/shorts/BaW_jenozKc',
            'https://youtube.com/live/BaW_jenozKc',
        ):
            with self.subTest(url=url):
                self.assertEqual(normalize_youtube_url(url), expected)

    def test_unrelated_hosts_and_non_video_urls_are_rejected(self):
        for url in ('file:///etc/passwd', 'https://youtube.com.evil.org/watch?v=BaW_jenozKc',
                    'https://www.youtube.com/playlist?list=123', 'https://youtube.com/@channel',
                    'https://user:pass@youtube.com/watch?v=BaW_jenozKc', ''):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_youtube_url(url)

    def test_local_pipeline_decodes_real_audio_and_preserves_previous_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'sample.wav'
            with wave.open(str(media), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0\0' * 16000)
            segments = [TranscriptSegment(0, 1, 'Тестовая расшифровка')]
            with patch('src.pipeline.transcribe_audio', return_value=segments):
                job = Job(str(media), root / 'output', formats=('md', 'txt'))
                first = run_job(job, lambda _: None, lambda _: None, lambda: False)
                second = run_job(job, lambda _: None, lambda _: None, lambda: False)
            self.assertNotEqual(first.txt, second.txt)
            self.assertIn('Тестовая расшифровка', first.txt.read_text(encoding='utf-8'))
            self.assertIn('**[00:00:00]**', first.markdown.read_text(encoding='utf-8'))

    def test_cancellation_does_not_publish_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(InterruptedError):
                run_job(Job('unused', root / 'output'), lambda _: None, lambda _: None, lambda: True)
            self.assertFalse((root / 'output').exists())

    def test_youtube_uses_downloaded_audio_and_records_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / 'download.wav'
            with wave.open(str(media), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0\0' * 16000)
            url = 'https://www.youtube.com/watch?v=BaW_jenozKc'
            with patch('src.pipeline.download_audio', return_value=(media, 'Title: test?')), patch(
                'src.pipeline.transcribe_audio', return_value=[TranscriptSegment(0, 1, 'Hello')]
            ):
                result = run_job(Job(url, root / 'out', youtube=True), lambda _: None, lambda _: None, lambda: False)
            self.assertIn(url, result.markdown.read_text(encoding='utf-8'))
            self.assertNotIn('?', result.markdown.name)
            self.assertIsNone(result.txt)
            self.assertEqual(result.text, 'Hello')

    def test_selected_formats_are_the_only_files_published(self):
        for formats in (('md',), ('txt',), ('md', 'txt')):
            with self.subTest(formats=formats), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                media = root / 'sample.wav'
                with wave.open(str(media), 'wb') as audio:
                    audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                    audio.writeframes(b'\0\0' * 16000)
                with patch('src.pipeline.transcribe_audio', return_value=[TranscriptSegment(0, 1, 'Readable text')]):
                    result = run_job(Job(str(media), root / 'out', formats=formats), lambda _: None, lambda _: None, lambda: False)
                self.assertEqual({p.suffix for p in (root / 'out').iterdir()}, {'.' + f for f in formats})
                self.assertEqual(result.text, 'Readable text')
                self.assertEqual(result.txt is not None, 'txt' in formats)
                self.assertEqual(result.markdown is not None, 'md' in formats)


if __name__ == '__main__':
    unittest.main()
