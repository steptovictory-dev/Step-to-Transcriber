"""Shared application workflow, independent of Qt widgets."""

import re
import shutil
import tempfile
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.audio import extract_audio_track, get_audio_track_count
from src.exporters import export_markdown, export_txt, format_timestamp, group_segments
from src.transcriber import TranscriptSegment, transcribe_audio
from src.youtube import download_audio, video_service


@dataclass
class Job:
    source: str
    output: Path
    youtube: bool = False  # Legacy field name: True selects any supported video URL
    track: int = 1
    model: str = 'turbo'
    formats: tuple[str, ...] = ('md',)
    timestamps: bool = True


@dataclass
class Result:
    txt: Path | None
    markdown: Path | None
    title: str
    text: str = ''
    segments: list[TranscriptSegment] | None = None
    source: str | None = None

    def set_timestamps(self, enabled):
        if self.segments is None:
            return
        text = '\n\n'.join(
            (f'[{format_timestamp(segment.start)}] ' if enabled else '') + segment.text
            for segment in group_segments(self.segments))
        # Stage exports beside the originals and retain backups for rollback
        with ExitStack() as stack:
            staged = []
            for path in (self.txt, self.markdown):
                if path is None:
                    continue
                directory = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=path.parent)))
                backup = directory / 'original'
                shutil.copyfile(path, backup)
                updated = directory / path.name
                if path == self.txt:
                    export_txt(self.segments, updated, timestamps=enabled)
                else:
                    export_markdown(self.segments, updated, title=self.title, timestamps=enabled)
                    if self.source:
                        with updated.open('a', encoding='utf-8') as stream:
                            stream.write(f'\nИсточник: {self.source}\n')
                staged.append((updated, path, backup))
            replaced = []
            try:
                for updated, path, backup in staged:
                    updated.replace(path)
                    replaced.append((path, backup))
            except OSError:
                for path, backup in reversed(replaced):
                    backup.replace(path)
                raise
        self.text = text


def run_job(job: Job, status, progress, cancelled) -> Result:
    if not job.formats or not set(job.formats) <= {'md', 'txt'}:
        raise ValueError('Выберите Markdown, TXT или оба формата')
    def check():
        if cancelled():
            raise InterruptedError('Обработка отменена')

    with tempfile.TemporaryDirectory(prefix='transcriber-') as temporary:
        check()
        directory = Path(temporary)
        if job.youtube:
            status(f'Загрузка записи: {video_service(job.source)}')
            media, title = download_audio(job.source, directory, status, progress, cancelled)
            track = 1
        else:
            media = Path(job.source)
            title = media.stem
            track = job.track
        check()
        status('Подготовка аудиодорожки')
        progress(-1)
        count = get_audio_track_count(media)
        if count == 0:
            raise ValueError('В файле нет аудиодорожек')
        audio = directory / 'audio.wav'
        extract_audio_track(media, audio, track)
        check()
        status('Загрузка модели и распознавание речи')
        segments = transcribe_audio(audio, model_name=job.model, progress=progress, cancelled=cancelled)
        check()
        if not segments:
            raise ValueError('Речь не распознана. Проверьте выбранную аудиодорожку')
        status('Сохранение расшифровки')
        safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip(' .')[:100] or 'transcript'
        name = f'{safe_title}_track{track}_{job.model}_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:6]}'
        job.output.mkdir(parents=True, exist_ok=True)
        txt = job.output / f'{name}.txt' if 'txt' in job.formats else None
        markdown = job.output / f'{name}.md' if 'md' in job.formats else None
        staged = []
        if txt:
            staged_txt = directory / 'transcript.txt'
            export_txt(segments, staged_txt, timestamps=job.timestamps)
            staged.append((staged_txt, txt))
        if markdown:
            staged_md = directory / 'transcript.md'
            export_markdown(segments, staged_md, title=title, timestamps=job.timestamps)
            if job.youtube:
                with staged_md.open('a', encoding='utf-8') as stream:
                    stream.write(f'\nИсточник: {job.source}\n')
            staged.append((staged_md, markdown))
        check()
        try:
            for source, destination in staged:
                shutil.copyfile(source, destination)
        except OSError:
            for _, destination in staged:
                destination.unlink(missing_ok=True)
            raise
        progress(1.0)
        text = '\n\n'.join(
            (f'[{format_timestamp(segment.start)}] ' if job.timestamps else '') + segment.text
            for segment in group_segments(segments))
        return Result(txt, markdown, title, text, segments, job.source if job.youtube else None)
