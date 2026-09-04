from pathlib import Path

from src.transcriber import TranscriptSegment


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f'{hours:02}:{minutes:02}:{seconds:02}'


def export_txt(
    segments: list[TranscriptSegment],
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', encoding='utf-8') as file:
        for segment in segments:
            file.write(f'{segment.text}\n')

    return output_path


def export_markdown(
    segments: list[TranscriptSegment],
    output_path: Path,
    title: str = 'Транскрипция лекции',
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', encoding='utf-8') as file:
        file.write(f'# {title}\n\n')

        for segment in segments:
            timestamp = format_timestamp(segment.start)

            file.write(
                f'**[{timestamp}]** {segment.text}\n\n'
            )

    return output_path