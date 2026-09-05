from dataclasses import dataclass
from pathlib import Path

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
) -> list[TranscriptSegment]:
    if not audio_path.exists():
        raise FileNotFoundError(f'Файл не найден: {audio_path}')

    model = WhisperModel(
        model_name,
        device='cuda',
        compute_type=compute_type,
    )

    segments, _ = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
    )

    result = []

    for segment in segments:
        result.append(
            TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
            )
        )

    return result