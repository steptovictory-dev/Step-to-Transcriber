import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from src.pipeline import Job, run_job
from src.transcriber import TranscriptSegment
from src.youtube import DOWNLOAD_FORMAT, normalize_youtube_url, normalize_video_url, video_service


class ApplicationTests(unittest.TestCase):
    def test_download_prefers_audio_else_lowest_video_resolution(self):
        from yt_dlp import YoutubeDL
        video_formats = [
            {'format_id': name, 'url': f'https://example.org/{name}.mp4', 'ext': 'mp4',
             'height': height, 'width': height * 16 // 9, 'vcodec': 'h264', 'acodec': 'aac'}
            for name, height in [('144p', 144), ('360p', 360), ('1080p', 1080)]
        ]
        with YoutubeDL({'quiet': True, 'format': DOWNLOAD_FORMAT}) as downloader:
            info = downloader.process_ie_result({'id': 'test', 'title': 'Test', 'formats': video_formats}, download=False)
            self.assertEqual(info['format_id'], '144p')
            audio = {'format_id': 'audio', 'url': 'https://example.org/audio.m4a',
                     'ext': 'm4a', 'vcodec': 'none', 'acodec': 'aac', 'abr': 128}
            info = downloader.process_ie_result({'id': 'test', 'title': 'Test', 'formats': video_formats + [audio]}, download=False)
            self.assertEqual(info['format_id'], 'audio')

    def test_vk_and_rutube_links(self):
        cases = {
            'https://vk.com/video-123_456?list=abc': 'https://vkvideo.ru/video-123_456',
            'https://vkvideo.ru/video-123_456': 'https://vkvideo.ru/video-123_456',
            'https://m.vk.com/clip-123_456': 'https://vkvideo.ru/video-123_456',
            'https://vk.com/videos-123?z=video-123_456%2Fclub123': 'https://vkvideo.ru/video-123_456',
            'https://rutube.ru/play/embed/3eac3b4561676c17df9132a9a1e62e3e':
                'https://rutube.ru/video/3eac3b4561676c17df9132a9a1e62e3e/',
        }
        from yt_dlp.extractor.vk import VKIE
        from yt_dlp.extractor.rutube import RutubeIE
        for source, expected in cases.items():
            with self.subTest(source=source):
                actual = normalize_video_url(source)
                self.assertEqual(actual, expected)
                extractor = RutubeIE if video_service(actual) == 'Rutube' else VKIE
                self.assertTrue(extractor.suitable(actual))

    def test_saved_broadcast_links_match_the_installed_extractors(self):
        from yt_dlp.extractor.twitch import TwitchVodIE
        from yt_dlp.extractor.vk import VKPlayIE
        record = '33a4e4ce-e3ef-49db-bb14-f006cc6fabc9'
        cases = (
            ('https://www.twitch.tv/videos/635475444?t=1h', 'https://www.twitch.tv/videos/635475444', 'Twitch', TwitchVodIE),
            ('https://m.twitch.tv/riotgames/v/635475444', 'https://www.twitch.tv/videos/635475444', 'Twitch', TwitchVodIE),
            ('https://player.twitch.tv/?parent=example.org&video=v635475444', 'https://www.twitch.tv/videos/635475444', 'Twitch', TwitchVodIE),
            (f'https://live.vkplay.ru/lebwa/record/{record}/records', f'https://live.vkvideo.ru/lebwa/record/{record}', 'VK Видео Live', VKPlayIE),
            (f'https://vkplay.live/lebwa/record/{record}', f'https://live.vkvideo.ru/lebwa/record/{record}', 'VK Видео Live', VKPlayIE),
        )
        for source, expected, service, extractor in cases:
            with self.subTest(source=source):
                self.assertEqual(normalize_video_url(source), expected)
                self.assertEqual(video_service(source), service)
                self.assertTrue(extractor.suitable(expected))

    def test_broadcast_channels_live_links_and_clips_are_rejected(self):
        for url in ('https://www.twitch.tv/riotgames', 'https://www.twitch.tv/directory',
                    'https://www.twitch.tv/riotgames/videos', 'https://www.twitch.tv/riotgames/clip/test',
                    'https://player.twitch.tv/?channel=riotgames', 'https://live.vkvideo.ru/lebwa',
                    'https://vkplay.live/lebwa/records', 'https://live.vkvideo.ru.evil.org/a/record/' + 'a' * 32):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_video_url(url)

    def test_remote_links_reject_channels_and_unrelated_hosts(self):
        for url in ('https://vkvideo.ru/playlist/-123_456', 'https://vk.com/videos-123',
                    'https://rutube.ru/channel/123/', 'https://rutube.ru.evil.org/video/' + 'a' * 32,
                    'https://user:pass@vk.com/video-123_456', 'file:///sample.mp4'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_video_url(url)

    def test_new_services_use_shared_pipeline_and_preserve_source(self):
        for url, service in (
            ('https://vkvideo.ru/video-123_456', 'VK Видео'),
            ('https://rutube.ru/video/3eac3b4561676c17df9132a9a1e62e3e/', 'Rutube'),
            ('https://www.twitch.tv/videos/635475444', 'Twitch'),
            ('https://live.vkvideo.ru/lebwa/record/33a4e4ce-e3ef-49db-bb14-f006cc6fabc9', 'VK Видео Live'),
        ):
            with self.subTest(service=service), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                media = root / 'sample.wav'
                with wave.open(str(media), 'wb') as audio:
                    audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                    audio.writeframes(b'\0\0' * 16000)
                statuses = []
                with patch('src.pipeline.download_audio', return_value=(media, service)) as download, patch(
                    'src.pipeline.transcribe_audio', return_value=[TranscriptSegment(0, 1, 'Hello')]
                ):
                    result = run_job(Job(url, root / 'out', youtube=True), statuses.append,
                                     lambda _: None, lambda: False)
                self.assertEqual(download.call_args.args[0], url)
                self.assertIn(service, statuses[0])
                self.assertIn(url, result.markdown.read_text(encoding='utf-8'))
                self.assertEqual(result.text, '[00:00:00] Hello')

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
            self.assertEqual(result.text, '[00:00:00] Hello')

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
                self.assertEqual(result.text, '[00:00:00] Readable text')
                self.assertEqual(result.txt is not None, 'txt' in formats)
                self.assertEqual(result.markdown is not None, 'md' in formats)

    def test_timestamp_choice_applies_to_preview_and_both_exports_for_each_source(self):
        segments = [TranscriptSegment(65, 66, 'Первый абзац'),
                    TranscriptSegment(110, 111, 'Второй абзац')]
        for remote in (False, True):
            for enabled in (False, True):
                with self.subTest(remote=remote, enabled=enabled), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    media = root / 'sample.wav'
                    source = 'https://youtu.be/BaW_jenozKc' if remote else str(media)
                    with patch('src.pipeline.download_audio', return_value=(media, 'Sample')), patch(
                        'src.pipeline.get_audio_track_count', return_value=1
                    ), patch('src.pipeline.extract_audio_track'), patch(
                        'src.pipeline.transcribe_audio', return_value=segments
                    ):
                        result = run_job(Job(source, root / 'out', youtube=remote,
                                             formats=('md', 'txt'), timestamps=enabled),
                                         lambda _: None, lambda _: None, lambda: False)
                    for content in (result.text, result.txt.read_text(encoding='utf-8'),
                                    result.markdown.read_text(encoding='utf-8')):
                        self.assertEqual('[00:01:05]' in content, enabled)
                        self.assertEqual('[00:01:50]' in content, enabled)
                        self.assertIn('Первый абзац', content)
                        self.assertIn('Второй абзац', content)


if __name__ == '__main__':
    unittest.main()
