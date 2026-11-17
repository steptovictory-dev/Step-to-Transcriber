"""Exercise real yt-dlp downloads locally without a public service or Whisper."""

import functools
import tempfile
import threading
import unittest
import wave
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import av
import numpy as np
from yt_dlp import YoutubeDL
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import DownloadError

from src.audio import extract_audio_track
from src.youtube import download_audio


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class VideoDownloadTests(unittest.TestCase):
    def test_real_download_decode_and_progress_for_supported_services(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with wave.open(str(folder / 'fixture.wav'), 'wb') as audio:
                audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                audio.writeframes(b'\0\0' * 16000)
            with av.open(str(folder / 'segment.ts'), 'w', format='mpegts') as container:
                stream = container.add_stream('aac', rate=16000)
                stream.layout = 'mono'
                frame = av.AudioFrame.from_ndarray(np.zeros((1, 16000), dtype=np.float32),
                                                  format='fltp', layout='mono')
                frame.sample_rate = 16000
                for packet in stream.encode(frame):
                    container.mux(packet)
                for packet in stream.encode(None):
                    container.mux(packet)
            (folder / 'audio.m3u8').write_text(
                '#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n'
                '#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:2.0,\nsegment.ts\n#EXT-X-ENDLIST\n',
                encoding='utf-8',
            )
            handler = functools.partial(QuietHandler, directory=str(folder))
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            media_url = f'http://127.0.0.1:{server.server_port}/fixture.wav'

            class FixtureIE(InfoExtractor):
                _VALID_URL = r'https://(?:vkvideo\.ru|rutube\.ru|www\.twitch\.tv|live\.vkvideo\.ru)/.*'

                def _real_extract(self, url):
                    if 'rutube' in url or 'twitch' in url:
                        return {'id': 'fixture', 'title': 'Local HLS download', 'formats': [
                            {'format_id': 'hls-144p', 'url': media_url.replace('fixture.wav', 'audio.m3u8'),
                             'ext': 'mp4', 'height': 144, 'vcodec': 'h264', 'acodec': 'aac',
                             'protocol': 'm3u8_native'},
                        ]}
                    media_format = {'format_id': 'audio', 'url': media_url, 'ext': 'wav'}
                    if 'live.vkvideo' not in url:
                        media_format.update(vcodec='none', acodec='pcm_s16le')
                    return {'id': 'fixture', 'title': 'Local download', 'formats': [media_format]}

            class LocalDownloader(YoutubeDL):
                def __init__(self, options):
                    super().__init__({**options, 'ffmpeg_location': str(folder / 'no-ffmpeg')}, auto_init=False)
                    self.add_info_extractor(FixtureIE())

            try:
                urls = ('https://vkvideo.ru/video-123_456',
                        'https://rutube.ru/video/' + 'a' * 32 + '/',
                        'https://www.twitch.tv/videos/635475444',
                        'https://live.vkvideo.ru/lebwa/record/33a4e4ce-e3ef-49db-bb14-f006cc6fabc9')
                for index, url in enumerate(urls):
                    with self.subTest(url=url), patch('src.youtube.YoutubeDL', LocalDownloader):
                        destination = folder / f'case-{index}'
                        destination.mkdir()
                        progress = []
                        media, title = download_audio(url, destination, lambda _: None,
                                                      progress.append, lambda: False)
                        self.assertTrue(media.is_file())
                        if 'vkvideo' in url:
                            self.assertEqual(title, 'Local download')
                            self.assertEqual(media.read_bytes(), (folder / 'fixture.wav').read_bytes())
                        else:
                            self.assertEqual(title, 'Local HLS download')
                        self.assertIn(1.0, progress)
                        decoded = extract_audio_track(media, destination / 'decoded.wav', 1)
                        with wave.open(str(decoded)) as audio:
                            self.assertGreaterEqual(audio.getnframes(), 16000)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_cancelled_download_does_not_contact_service(self):
        with patch('src.youtube.YoutubeDL') as downloader:
            with self.assertRaises(InterruptedError):
                download_audio('https://vkvideo.ru/video-123_456', Path('.'),
                               lambda _: None, lambda _: None, lambda: True)
            downloader.assert_not_called()

    def test_running_and_processing_broadcasts_fail_before_downloading(self):
        for state in ({'is_live': True}, {'live_status': 'is_live'},
                      {'live_status': 'is_upcoming'}, {'live_status': 'post_live'}):
            class MetadataDownloader(YoutubeDL):
                def extract_info(self, url, download=True):
                    return self.process_ie_result({
                        'id': 'live', 'title': 'Live', **state,
                        'formats': [{'url': 'http://127.0.0.1:1/never-requested.wav',
                                     'ext': 'wav', 'vcodec': 'none', 'acodec': 'pcm_s16le'}],
                    }, download=download)

            with self.subTest(state=state), patch('src.youtube.YoutubeDL', MetadataDownloader):
                with self.assertRaises(ValueError):
                    download_audio('https://www.twitch.tv/videos/635475444', Path('.'),
                                   lambda _: None, lambda _: None, lambda: False)

    def test_network_error_explains_service_and_vpn(self):
        with patch('src.youtube.YoutubeDL') as downloader:
            downloader.return_value.__enter__.return_value.extract_info.side_effect = DownloadError('Connection timed out')
            with self.assertRaisesRegex(RuntimeError, 'Rutube.*VPN'):
                download_audio('https://rutube.ru/video/' + 'a' * 32 + '/', Path('.'),
                               lambda _: None, lambda _: None, lambda: False)


if __name__ == '__main__':
    unittest.main()
