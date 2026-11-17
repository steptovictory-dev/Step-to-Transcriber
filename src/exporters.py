from pathlib import Path

from src.transcriber import TranscriptSegment


PARAGRAPH_DURATION = 30.0
MAX_SILENCE_GAP = 5.0


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f'{hours:02}:{minutes:02}:{seconds:02}'


def group_segments(
    segments: list[TranscriptSegment],
    max_duration: float = PARAGRAPH_DURATION,
    max_silence_gap: float = MAX_SILENCE_GAP,
) -> list[TranscriptSegment]:
    if not segments:
        return []

    grouped_segments = []

    current_start = segments[0].start
    current_end = segments[0].end
    current_text = [segments[0].text]

    for segment in segments[1:]:
        paragraph_duration = segment.end - current_start
        silence_gap = segment.start - current_end

        can_merge = (
            paragraph_duration <= max_duration
            and silence_gap <= max_silence_gap
        )

        if can_merge:
            current_text.append(segment.text)
            current_end = segment.end
        else:
            grouped_segments.append(
                TranscriptSegment(
                    start=current_start,
                    end=current_end,
                    text=' '.join(current_text),
                )
            )

            current_start = segment.start
            current_end = segment.end
            current_text = [segment.text]

    grouped_segments.append(
        TranscriptSegment(
            start=current_start,
            end=current_end,
            text=' '.join(current_text),
        )
    )

    return grouped_segments


def export_txt(
    segments: list[TranscriptSegment],
    output_path: Path,
    timestamps: bool = False,
) -> Path:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped_segments = group_segments(segments)

    with output_path.open(
        'w',
        encoding='utf-8',
    ) as file:
        for segment in grouped_segments:
            prefix = f'[{format_timestamp(segment.start)}] ' if timestamps else ''
            file.write(f'{prefix}{segment.text}\n\n')

    return output_path


def export_markdown(
    segments: list[TranscriptSegment],
    output_path: Path,
    title: str = 'Транскрипция лекции',
    timestamps: bool = True,
) -> Path:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped_segments = group_segments(segments)

    with output_path.open(
        'w',
        encoding='utf-8',
    ) as file:
        file.write(f'# {title}\n\n')

        for segment in grouped_segments:
            prefix = f'**[{format_timestamp(segment.start)}]** ' if timestamps else ''
            file.write(f'{prefix}{segment.text}\n\n')

    return output_path
