"""Validate video links and download one media stream without conversion."""

import os
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from src.paths import RESOURCES


DOWNLOAD_FORMAT = 'bestaudio/worst[vcodec!=?none][acodec!=?none]'
SUPPORTED_SERVICES = 'YouTube, VK Видео, Rutube, Twitch или VK Видео Live'


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
    local_node = RESOURCES / 'tools' / 'node.exe'
    node = (os.environ.get('TRANSCRIBER_NODE')
            or (str(local_node) if local_node.is_file() else None)
            or shutil.which('node'))
    if node:
        return {'node': {'path': node}}
    if shutil.which('deno'):
        return {'deno': {}}
    return {}


def normalize_video_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError(f'Укажите полную ссылку https:// на запись: {SUPPORTED_SERVICES}')
    host = (parsed.hostname or '').lower()
    if host in ('youtu.be', 'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        return normalize_youtube_url(value)
    if host in ('twitch.tv', 'www.twitch.tv', 'm.twitch.tv', 'go.twitch.tv', 'player.twitch.tv'):
        match = re.fullmatch(r'/(?:videos|[^/]+/v(?:ideo)?)/(\d+)/?', parsed.path)
        video_id = match.group(1) if match else ''
        if host == 'player.twitch.tv':
            video_id = parse_qs(parsed.query).get('video', [''])[0].removeprefix('v')
        if re.fullmatch(r'\d+', video_id):
            return f'https://www.twitch.tv/videos/{video_id}'
        raise ValueError('Для Twitch нужна ссылка на сохранённую запись twitch.tv/videos/..., а не текущий эфир или канал')
    if host in ('live.vkvideo.ru', 'vkplay.live', 'live.vkplay.ru'):
        match = re.fullmatch(r'/([A-Za-z0-9_-]+)/record/([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})(?:/records)?/?', parsed.path)
        if match:
            return f'https://live.vkvideo.ru/{match.group(1)}/record/{match.group(2).lower()}'
        raise ValueError('Для VK Видео Live нужна ссылка на завершённую запись /имя/record/..., а не текущий эфир или канал')
    if host in ('vk.com', 'www.vk.com', 'm.vk.com', 'vk.ru', 'www.vk.ru',
                'vkvideo.ru', 'www.vkvideo.ru', 'm.vkvideo.ru'):
        match = re.fullmatch(r'/(?:video|clip)(-?\d+_\d+)/?', parsed.path)
        if not match:
            wrapped = parse_qs(parsed.query).get('z', [''])[0]
            match = re.fullmatch(r'(?:video|clip)(-?\d+_\d+)(?:/[^\s]*)?', wrapped)
        if match:
            return f'https://vkvideo.ru/video{match.group(1)}'
        if parsed.path == '/video_ext.php':
            query = parse_qs(parsed.query)
            owner, video = query.get('oid', [''])[0], query.get('id', [''])[0]
            if re.fullmatch(r'-?\d+', owner) and re.fullmatch(r'\d+', video):
                params = {'oid': owner, 'id': video}
                if query.get('hash'):
                    params['hash'] = query['hash'][0]
                return f'https://vkvideo.ru/video_ext.php?{urlencode(params)}'
    if host in ('rutube.ru', 'www.rutube.ru'):
        match = re.fullmatch(r'/(?:video|(?:play/)?embed)/([a-zA-Z0-9]{32})/?', parsed.path)
        if match:
            return f'https://rutube.ru/video/{match.group(1)}/'
    raise ValueError(f'Нужна ссылка на отдельную запись: {SUPPORTED_SERVICES}, а не канал или плейлист')


def video_service(url: str) -> str:
    host = (urlparse(normalize_video_url(url)).hostname or '').lower()
    if host == 'rutube.ru':
        return 'Rutube'
    if host == 'www.twitch.tv':
        return 'Twitch'
    if host == 'live.vkvideo.ru':
        return 'VK Видео Live'
    if host in ('youtube.com', 'www.youtube.com'):
        return 'YouTube'
    return 'VK Видео'


def download_audio(url: str, directory: Path, status, progress, cancelled) -> tuple[Path, str]:
    url = normalize_video_url(url)
    service = video_service(url)
    if cancelled():
        raise InterruptedError('Загрузка отменена')

    def hook(data):
        if cancelled():
            raise InterruptedError('Загрузка отменена')
        if data['status'] == 'finished':
            progress(1.0)
        if data['status'] == 'downloading':
            size = data.get('total_bytes') or data.get('total_bytes_estimate')
            if size:
                progress(min(data.get('downloaded_bytes', 0) / size, 1.0))

    def reject_live(info, *, incomplete):
        if cancelled():
            raise InterruptedError('Загрузка отменена')
        if info.get('is_live') or info.get('is_upcoming') or info.get('live_status') in ('is_live', 'is_upcoming'):
            raise ValueError('Прямые эфиры не поддерживаются. Выберите завершённую запись')
        if info.get('live_status') == 'post_live':
            raise ValueError('Сервис ещё обрабатывает завершённый эфир. Попробуйте позже')

    class Logger:
        def debug(self, message):
            pass

        def warning(self, message):
            status(f'{service}: {message}')

        def error(self, message):
            pass

    options = {
        'format': DOWNLOAD_FORMAT,
        'outtmpl': str(directory / '%(id)s.%(ext)s'),
        'noplaylist': True,
        'socket_timeout': 20,
        'retries': 2,
        'fragment_retries': 2,
        'skip_unavailable_fragments': False,
        'hls_prefer_native': True,
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
            if info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
                raise ValueError('Поддерживается только одно видео')
            path = Path(downloader.prepare_filename(info))
            if not path.is_file():
                raise ValueError(f'Не удалось получить запись {service}')
            return path, info.get('title') or info['id']
    except DownloadError as error:
        if cancelled():
            raise InterruptedError('Загрузка отменена') from error
        network_hint = ''
        if service != 'YouTube' and any(text in str(error).lower() for text in ('timed out', 'timeout', 'connection')):
            network_hint = ' Если используете VPN, попробуйте отключить его или сменить маршрут.'
        raise RuntimeError(
            f'Не удалось скачать видео {service}. Проверьте доступность ссылки и сети. '
            'Закрытые видео и материалы с требованием входа могут быть недоступны.'
            + network_hint + '\n\n'
            + str(error)
        ) from error
