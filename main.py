import argparse
import tempfile
from pathlib import Path

from src.audio import extract_audio_track
from src.exporters import export_markdown, export_txt
from src.transcriber import transcribe_audio


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
        'name': 'large-v3',
        'description': 'максимальное качество',
    },
    '2': {
        'name': 'turbo',
        'description': 'высокая скорость',
    },
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Локальная транскрибация записей OBS через faster-whisper.'
    )

    parser.add_argument(
        'video',
        type=Path,
        help='Путь к видеофайлу OBS.',
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output'),
        help='Папка для результатов. По умолчанию: output.',
    )

    return parser.parse_args()


def choose_audio_track() -> int:
    print('Выберите аудиодорожку:')
    print()

    for key, option in TRACK_OPTIONS.items():
        print(
            f'{key} — {option["name"]}: '
            f'{option["description"]}'
        )

    print()

    while True:
        choice = input('Дорожка [1-3]: ').strip()

        if choice in TRACK_OPTIONS:
            return TRACK_OPTIONS[choice]['number']

        print('Ошибка: введите 1, 2 или 3.')


def choose_model() -> str:
    print()
    print('Выберите режим обработки:')
    print()

    for key, option in MODEL_OPTIONS.items():
        print(
            f'{key} — {option["name"]}: '
            f'{option["description"]}'
        )

    print()

    while True:
        choice = input('Режим [1-2]: ').strip()

        if choice in MODEL_OPTIONS:
            return MODEL_OPTIONS[choice]['name']

        print('Ошибка: введите 1 или 2.')


def main() -> None:
    args = parse_arguments()

    video_path = args.video.resolve()

    if not video_path.exists():
        raise FileNotFoundError(f'Видео не найдено: {video_path}')

    track_number = choose_audio_track()
    model_name = choose_model()

    output_directory = args.output.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    transcript_name = f'{video_path.stem}_{model_name}'

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

        extract_audio_track(
            video_path=video_path,
            output_path=audio_path,
            track_number=track_number,
        )

        print('2/3 Транскрибация...')

        segments = transcribe_audio(
            audio_path=audio_path,
            model_name=model_name,
        )

        print('3/3 Сохранение результатов...')

        export_txt(
            segments=segments,
            output_path=txt_path,
        )

        export_markdown(
            segments=segments,
            output_path=md_path,
            title=video_path.stem,
        )

    print()
    print('Готово.')
    print(f'TXT: {txt_path}')
    print(f'Markdown: {md_path}')


if __name__ == '__main__':
    main()