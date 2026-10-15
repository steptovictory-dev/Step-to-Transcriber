"""Download one YouTube audio stream without FFmpeg conversion."""

import os
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def normalize_youtube_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('Укажите полную ссылку https://www.youtube.com/watch?v=...')
    host = (parsed.hostname or '').lower()
    if host == 'youtu.be':
        video_id = parsed.path.strip('/')
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        else:
            match = re.fullmatch(r'/(?:shorts|live|embed)/([\w-]{11})/?', parsed.path)
            video_id = match.group(1) if match else ''
    else:
        video_id = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Нужна ссылка на одно видео YouTube, а не канал или плейлист')
    return f'https://www.youtube.com/watch?v={video_id}'


def javascript_runtimes() -> dict:
    # Prefer an explicitly configured runtime, then executables on PATH
    local_node = Path(__file__).resolve().parents[1] / 'tools' / 'node.exe'
    node = (os.environ.get('TRANSCRIBER_NODE')
            or (str(local_node) if local_node.is_file() else None)
            or shutil.which('node'))
    if node:
        return {'node': {'path': node}}
    if shutil.which('deno'):
        return {'deno': {}}
    return {}


def download_audio(url: str, directory: Path, status, progress, cancelled) -> tuple[Path, str]:
    url = normalize_youtube_url(url)

    def hook(data):
        if cancelled():
            raise InterruptedError('Загрузка отменена')
        if data['status'] == 'downloading':
            size = data.get('total_bytes') or data.get('total_bytes_estimate')
            if size:
                progress(min(data.get('downloaded_bytes', 0) / size, 1.0))

    def reject_live(info, *, incomplete):
        if info.get('is_live') or info.get('is_upcoming'):
            return 'Прямые эфиры не поддерживаются. Выберите завершённую запись'

    class Logger:
        def debug(self, message):
            pass

        def warning(self, message):
            status(f'YouTube: {message}')

        def error(self, message):
            pass

    options = {
        'format': 'bestaudio/best',
        'outtmpl': str(directory / '%(id)s.%(ext)s'),
        'noplaylist': True,
        'socket_timeout': 20,
        'retries': 2,
        'fragment_retries': 2,
        'progress_hooks': [hook],
        'match_filter': reject_live,
        'logger': Logger(),
        'js_runtimes': javascript_runtimes(),
    }
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
            if cancelled():
                raise InterruptedError('Загрузка отменена')
            if not info:
                raise ValueError('Видео недоступно')
            path = Path(downloader.prepare_filename(info))
            if not path.is_file():
                raise ValueError('Не удалось получить аудиофайл YouTube')
            return path, info.get('title') or info['id']
    except DownloadError as error:
        if cancelled():
            raise InterruptedError('Загрузка отменена') from error
        raise RuntimeError(
            'Не удалось скачать видео YouTube. Проверьте доступность ссылки и сети. '
            'Закрытые видео и материалы с требованием входа могут быть недоступны.\n\n'
            + str(error)
        ) from error
