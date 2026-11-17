"""Explicit network smoke test: download a video and decode its audio in temp."""

import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.audio import extract_audio_track, get_audio_track_count
from src.youtube import download_audio, video_service


if __name__ == '__main__':
    failed = False
    for url in sys.argv[1:]:
        try:
            print(f'Checking {url}', flush=True)
            with tempfile.TemporaryDirectory(prefix='transcriber-smoke-') as temporary:
                folder = Path(temporary)
                media, title = download_audio(url, folder, print, lambda _: None, lambda: False)
                assert get_audio_track_count(media) > 0
                audio = extract_audio_track(media, folder / 'audio.wav', 1)
                with wave.open(str(audio)) as wav:
                    duration = wav.getnframes() / wav.getframerate()
                    assert duration > 0
                print(f'OK: {video_service(url)}; {title}; decoded {duration:.1f}s', flush=True)
        except Exception as error:
            failed = True
            print(f'FAILED: {url}: {error}', flush=True)
    sys.exit(1 if failed else 0)
