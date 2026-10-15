from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.runtime import configure_gpu_runtime


configure_gpu_runtime()

from faster_whisper import WhisperModel


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


def transcribe_audio(
    audio_path: Path,
    model_name: str = 'turbo',
    language: str | None = None,
    compute_type: str = 'float16',
    progress: Callable[[float], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[TranscriptSegment]:
    if not audio_path.exists():
        raise FileNotFoundError(f'Файл не найден: {audio_path}')

    model = WhisperModel(
        model_name,
        device='cuda',
        compute_type=compute_type,
    )

    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
    )

    result = []

    for segment in segments:
        if cancelled and cancelled():
            raise InterruptedError('Обработка отменена')
        result.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
            )
        )
        if progress and info.duration:
            progress(min(segment.end / info.duration, 1.0))

    return result
