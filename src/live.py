"""Windows loopback capture and bounded, overlapping local recognition."""

import logging
import queue
import time
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event
from uuid import uuid4

import av
import numpy as np

from src.runtime import configure_gpu_runtime


class DeviceUnavailable(RuntimeError):
    pass


def audio_backend():
    try:
        import pyaudiowpatch
    except ImportError as error:
        raise RuntimeError('Не установлен PyAudioWPatch. Установите зависимости из requirements.txt') from error
    return pyaudiowpatch


def output_devices():
    backend = audio_backend()
    with backend.PyAudio() as audio:
        try:
            default = audio.get_default_wasapi_loopback()['index']
        except OSError:
            default = None
        return [dict(device, default=device['index'] == default)
                for device in audio.get_loopback_device_info_generator()]


@dataclass
class LiveJob:
    device: dict
    output: Path
    formats: tuple[str, ...] = ('md',)
    language: str | None = None
    timestamps: bool = False
    autosave: bool = True


def timestamp(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}'


class SessionWriter:
    """Append and flush each confirmed paragraph, including recovery on failure."""

    def __init__(self, job, stack):
        self.paths = []
        self.streams = []
        self.timestamps = job.timestamps
        if not job.autosave:
            return
        if not job.formats or not set(job.formats) <= {'md', 'txt'}:
            raise ValueError('Выберите Markdown, TXT или оба формата')
        job.output.mkdir(parents=True, exist_ok=True)
        name = f'live_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}'
        self.paths = [job.output / f'{name}.{extension}' for extension in dict.fromkeys(job.formats)]
        self.timestamps = job.timestamps
        self.streams = [stack.enter_context(path.open('x', encoding='utf-8')) for path in self.paths]
        for path, stream in zip(self.paths, self.streams):
            if path.suffix == '.md':
                stream.write(f'# Прямой эфир\n\nНачало: {datetime.now():%d.%m.%Y %H:%M:%S}\n\n'
                             f'Устройство: {job.device["name"]}\n\n')
                if job.timestamps:
                    stream.write('Таймкоды отсчитываются от начала захвата звука\n\n')
                stream.flush()

    def append(self, seconds, text, note=False):
        for path, stream in zip(self.paths, self.streams):
            prefix = f'[{timestamp(seconds)}] ' if self.timestamps else ''
            stream.write(prefix + text + '\n\n')
            stream.flush()


def resample_audio(raw, channels, rate):
    pcm = np.frombuffer(raw, dtype='<i2').reshape(-1, channels)
    mono = pcm.astype(np.float32).mean(axis=1) / 32768.0
    frame = av.AudioFrame.from_ndarray(mono.reshape(1, -1), format='flt', layout='mono')
    frame.sample_rate = rate
    resampler = av.AudioResampler(format='flt', layout='mono', rate=16000)
    frames = resampler.resample(frame) + resampler.resample(None)
    return np.concatenate([item.to_ndarray().reshape(-1) for item in frames]) if frames else np.empty(0, np.float32)


def confirmed_text(segments, window_start, core_start, core_end):
    """Assign words to non-overlapping time intervals using their midpoint."""
    for segment in segments:
        words = [word for word in (segment.words or [])
                 if core_start <= window_start + (word.start + word.end) / 2 < core_end]
        if words:
            text = ''.join(word.word for word in words).strip()
            if text:
                yield max(core_start, window_start + words[0].start), text


def run_live(job, stopped, status, paragraph, meter, saved, model_factory=None, selection=None):
    """Capture callback stays lightweight while recognition consumes bounded audio."""
    backend = audio_backend()
    configure_gpu_runtime()
    if model_factory is None:
        from faster_whisper import WhisperModel
        model_factory = WhisperModel
    status('Загрузка модели turbo, захват начнётся после подготовки')
    model = model_factory('turbo', device='cuda', compute_type='float16')
    if stopped():
        return
    origin = time.monotonic()
    with ExitStack() as stack:
        writer = SessionWriter(job, stack)
        if writer.paths:
            saved(writer.paths)
        selected = selection() if selection else job.device
        waiting = False
        while not stopped():
            try:
                selected = capture_device(selected, model, writer, origin, job.language,
                                          stopped, status, paragraph, meter, selection)
                waiting = False
            except DeviceUnavailable:
                if not selected.get('automatic'):
                    raise
                if not waiting:
                    seconds = time.monotonic() - origin
                    text = '[Выход звука недоступен: ожидаем устройство Windows, возможен пропуск звука]'
                    writer.append(seconds, text, note=True)
                    paragraph(seconds, text)
                    waiting = True
                status('Ожидаем выход звука Windows, сеанс продолжается')
                meter(0.0, 0.0)
                for _ in range(5):
                    if stopped():
                        break
                    time.sleep(0.1)
                selected = selection() if selection else job.device
                continue
            if selected is None:
                break
            seconds = time.monotonic() - origin
            text = '[Смена устройства: переподключаем звук, возможен короткий пропуск]'
            writer.append(seconds, text, note=True)
            paragraph(seconds, text)
        writer.append(time.monotonic() - origin, '[Сеанс завершён]', note=True)
        status('Сеанс завершён, расшифровка сохранена' if job.autosave
               else 'Сеанс завершён, текст доступен в окне без сохранения')


def capture_device(selected, model, writer, origin, language, stopped, status, paragraph, meter, selection):
    backend = audio_backend()
    pending = queue.Queue(maxsize=600)
    overflow = Event()
    capture_issue = Event()

    def capture(data, count, timing, flags):
        if flags:
            capture_issue.set()
        try:
            pending.put_nowait((data, time.monotonic() - origin - count / rate))
        except queue.Full:
            overflow.set()
            return (None, backend.paAbort)
        return (None, backend.paContinue)

    with ExitStack() as stack:
        audio = stack.enter_context(backend.PyAudio())
        if selected.get('automatic'):
            try:
                current = audio.get_default_wasapi_loopback()
            except (OSError, LookupError) as error:
                raise DeviceUnavailable('Устройство Windows по умолчанию недоступно') from error
        else:
            current = next((device for device in audio.get_loopback_device_info_generator()
                            if device['name'] == selected['name']), None)
            if current is None:
                raise DeviceUnavailable('Выбранное устройство отключено. Подключите его или выберите другой выход')
        rate = int(current['defaultSampleRate'])
        channels = int(current['maxInputChannels'])
        frame_bytes = channels * 2
        try:
            stream = audio.open(format=backend.paInt16, channels=channels, rate=rate,
                                input=True, input_device_index=int(current['index']),
                                frames_per_buffer=max(1, rate // 10), stream_callback=capture,
                                start=False)
        except OSError as error:
            raise DeviceUnavailable('Не удалось подключиться к выходу звука Windows') from error
        stack.callback(stream.close)
        raw = bytearray()
        window_start = None
        core_start = None
        next_time = None

        def recognize(final=False):
            nonlocal raw, window_start, core_start, language
            duration = len(raw) / frame_bytes / rate
            if not raw:
                return
            end = window_start + duration
            core_end = end + 0.01 if final else core_start + 8.0
            samples = resample_audio(bytes(raw), channels, rate)
            if len(samples) and np.sqrt(np.mean(samples ** 2)) > 0.00015:
                status('Распознаём речь' if not stopped() else 'Сохраняем оставшийся звук')
                segments, info = model.transcribe(
                    samples, language=language, beam_size=3, vad_filter=True,
                    vad_parameters={'min_silence_duration_ms': 500}, word_timestamps=True,
                    condition_on_previous_text=False,
                )
                for seconds, text in confirmed_text(segments, window_start, core_start, core_end):
                    writer.append(seconds, text)
                    paragraph(seconds, text)
                if language is None and getattr(info, 'language_probability', 0) >= 0.8:
                    language = info.language
            if final:
                raw.clear()
            else:
                keep_start = core_end - 1.0
                consumed = round((keep_start - window_start) * rate)
                del raw[:consumed * frame_bytes]
                window_start += consumed / rate
                core_start = core_end

        def note(seconds, text):
            writer.append(seconds, text, note=True)
            paragraph(seconds, text)

        failure = None
        requested = selected
        switching = False
        draining = False
        stream.start_stream()
        status('Слушаем: ' + current['name'].removesuffix(' [Loopback]'))
        try:
            while True:
                if not draining:
                    requested = selection() if selection else selected
                    switching = requested != selected
                draining = draining or stopped() or switching or overflow.is_set() or capture_issue.is_set()
                stopping = draining
                if stopping and not stream.is_stopped():
                    stream.stop_stream()
                try:
                    data, seconds = pending.get(timeout=0.15)
                except queue.Empty:
                    if stopping:
                        break
                    if selection and selection() != selected:
                        continue
                    if not stream.is_active():
                        raise DeviceUnavailable('Захват звука прервался. Проверьте подключение аудиоустройства')
                    meter(0.0, 0.0)
                    continue
                duration = len(data) / frame_bytes / rate
                if next_time is not None and abs(seconds - next_time) > 0.75:
                    recognize(final=True)
                    note(seconds, '[Разрыв аудиопотока: возможен пропуск звука]')
                    window_start = core_start = None
                if window_start is None:
                    window_start = core_start = max(0.0, seconds)
                raw.extend(data)
                next_time = seconds + duration
                amplitude = np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768.0
                level = float(np.sqrt(np.mean(amplitude ** 2))) if len(amplitude) else 0.0
                meter(level, max(0.0, time.monotonic() - origin - next_time))
                while window_start + len(raw) / frame_bytes / rate >= core_start + 9.0:
                    # Keep one second of context on either side of each core interval
                    length = round((core_start + 9.0 - window_start) * rate) * frame_bytes
                    remainder = raw[length:]
                    del raw[length:]
                    recognize()
                    raw.extend(remainder)
                    if not stopping:
                        status('Слушаем: ' + current['name'].removesuffix(' [Loopback]'))
            recognize(final=True)
            if overflow.is_set():
                raise RuntimeError('Распознавание отстало более чем на минуту. Захват остановлен, часть звука пропущена')
            if capture_issue.is_set() and not switching:
                raise RuntimeError('Windows сообщил о потере аудиоданных. Захват остановлен, возможен пропуск звука')
        except Exception as error:
            failure = error
            logging.exception('Live transcription failed')
            note(time.monotonic() - origin, f'[Сеанс прерван: {error}]')
        finally:
            if not stream.is_stopped():
                stream.stop_stream()
        if failure:
            raise failure
        return requested if switching and not stopped() else None
