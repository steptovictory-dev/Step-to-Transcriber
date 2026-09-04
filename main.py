import argparse
import tempfile
import time
from pathlib import Path

from src.audio import extract_audio_track
from src.exporters import export_markdown, export_txt
from src.transcriber import transcribe_audio


OBS_DIRECTORY = Path.home() / 'Videos'
VIDEO_EXTENSIONS = {'.mp4', '.mkv'}
MAX_VISIBLE_FILES = 10

TRACK_OPTIONS = {
    '1': {
        'number': 1,
        'name': 'Full Mix',
        'description': 'системный звук + микрофон',
    },
    '2': {
        'number': 2,
        'name': 'Lecturer',
        'description': 'только системный звук / преподаватель',
    },
    '3': {
        'number': 3,
        'name': 'Microphone',
        'description': 'только микрофон',
    },
}

MODEL_OPTIONS = {
    '1': {
        'name': 'turbo',
        'description': 'рекомендуемый режим',
    },
    '2': {
        'name': 'large-v3',
        'description': 'не рекомендуется к применению',
    },
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Локальная транскрибация записей OBS через faster-whisper.'
    )

    parser.add_argument(
        'video',
        nargs='?',
        type=Path,
        help=(
            'Путь к видеофайлу OBS. '
            'Если путь не указан, будет предложен выбор файла.'
        ),
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output'),
        help='Папка для результатов. По умолчанию: output.',
    )

    return parser.parse_args()


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f'{seconds:.1f} сек.'

    minutes, seconds = divmod(seconds, 60)

    return f'{int(minutes)} мин. {seconds:.1f} сек.'


def get_recent_recordings(
    directory: Path,
    limit: int = MAX_VISIBLE_FILES,
) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(
            f'Папка с записями не найдена: {directory}'
        )

    recordings = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
    ]

    recordings.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return recordings[:limit]


def choose_video_file() -> Path | None:
    recordings = get_recent_recordings(OBS_DIRECTORY)

    if not recordings:
        raise FileNotFoundError(
            f'В папке {OBS_DIRECTORY} не найдено записей OBS.'
        )

    print()
    print('Выберите запись OBS:')
    print()

    for index, recording in enumerate(recordings, start=1):
        size_mb = recording.stat().st_size / (1024 * 1024)

        print(
            f'{index} — {recording.name} '
            f'({size_mb:.1f} MB)'
        )

    print()
    print('0 — Выйти из программы')
    print()

    while True:
        choice = input(
            f'Файл [0-{len(recordings)}]: '
        ).strip()

        if choice == '0':
            return None

        if choice.isdigit():
            index = int(choice)

            if 1 <= index <= len(recordings):
                return recordings[index - 1].resolve()

        print(
            f'Ошибка: введите число '
            f'от 0 до {len(recordings)}.'
        )


def choose_audio_track() -> int | None:
    print()
    print('Выберите аудиодорожку:')
    print()

    for key, option in TRACK_OPTIONS.items():
        print(
            f'{key} — {option["name"]}: '
            f'{option["description"]}'
        )

    print()
    print('0 — Назад к выбору файла')
    print()

    while True:
        choice = input('Дорожка [0-3]: ').strip()

        if choice == '0':
            return None

        if choice in TRACK_OPTIONS:
            return TRACK_OPTIONS[choice]['number']

        print('Ошибка: введите 0, 1, 2 или 3.')


def choose_model() -> str | None:
    print()
    print('Выберите режим обработки:')
    print()

    for key, option in MODEL_OPTIONS.items():
        print(
            f'{key} — {option["name"]}: '
            f'{option["description"]}'
        )

    print()
    print('0 — Назад к выбору аудиодорожки')
    print()

    while True:
        choice = input('Режим [0-2]: ').strip()

        if choice == '0':
            return None

        if choice in MODEL_OPTIONS:
            return MODEL_OPTIONS[choice]['name']

        print('Ошибка: введите 0, 1 или 2.')


def process_video(
    video_path: Path,
    track_number: int,
    model_name: str,
    output_directory: Path,
) -> None:
    total_start = time.perf_counter()

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    transcript_name = (
        f'{video_path.stem}_'
        f'track{track_number}_'
        f'{model_name}'
    )

    txt_path = output_directory / f'{transcript_name}.txt'
    md_path = output_directory / f'{transcript_name}.md'

    print()
    print('Параметры обработки:')
    print(f'Видео: {video_path}')
    print(f'Аудиодорожка: {track_number}')
    print(f'Модель: {model_name}')
    print()

    with tempfile.TemporaryDirectory() as temp_directory:
        audio_path = Path(temp_directory) / 'audio.wav'

        print('1/3 Извлечение аудиодорожки...')

        audio_start = time.perf_counter()

        extract_audio_track(
            video_path=video_path,
            output_path=audio_path,
            track_number=track_number,
        )

        audio_elapsed = time.perf_counter() - audio_start

        print(
            f'    Готово за '
            f'{format_duration(audio_elapsed)}'
        )

        print()
        print('2/3 Транскрибация...')

        transcription_start = time.perf_counter()

        segments = transcribe_audio(
            audio_path=audio_path,
            model_name=model_name,
        )

        transcription_elapsed = (
            time.perf_counter() - transcription_start
        )

        print(
            f'    Готово за '
            f'{format_duration(transcription_elapsed)}'
        )

        print()
        print('3/3 Сохранение результатов...')

        export_start = time.perf_counter()

        export_txt(
            segments=segments,
            output_path=txt_path,
        )

        export_markdown(
            segments=segments,
            output_path=md_path,
            title=video_path.stem,
        )

        export_elapsed = time.perf_counter() - export_start

        print(
            f'    Готово за '
            f'{format_duration(export_elapsed)}'
        )

    total_elapsed = time.perf_counter() - total_start

    print()
    print('Готово.')
    print(f'Общее время: {format_duration(total_elapsed)}')
    print()
    print(f'TXT: {txt_path}')
    print(f'Markdown: {md_path}')


def main() -> None:
    args = parse_arguments()

    while True:
        if args.video is None:
            video_path = choose_video_file()

            if video_path is None:
                print()
                print('Программа завершена.')
                return
        else:
            video_path = args.video.resolve()

            if not video_path.exists():
                raise FileNotFoundError(
                    f'Видео не найдено: {video_path}'
                )

        while True:
            track_number = choose_audio_track()

            if track_number is None:
                if args.video is None:
                    break

                print()
                print('Программа завершена.')
                return

            while True:
                model_name = choose_model()

                if model_name is None:
                    break

                process_video(
                    video_path=video_path,
                    track_number=track_number,
                    model_name=model_name,
                    output_directory=args.output.resolve(),
                )

                return


if __name__ == '__main__':
    main()