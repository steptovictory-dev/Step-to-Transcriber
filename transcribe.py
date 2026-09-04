import argparse
import tempfile
from pathlib import Path

from src.audio import extract_audio_track
from src.exporters import export_markdown, export_txt
from src.transcriber import transcribe_audio


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
        '--track',
        type=int,
        default=2,
        help='Номер аудиодорожки OBS. По умолчанию: 2.',
    )

    parser.add_argument(
        '--model',
        default='large-v3',
        help='Модель Whisper. По умолчанию: large-v3.',
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output'),
        help='Папка для результатов. По умолчанию: output.',
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    video_path = args.video.resolve()

    if not video_path.exists():
        raise FileNotFoundError(f'Видео не найдено: {video_path}')

    output_directory = args.output.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    transcript_name = video_path.stem

    txt_path = output_directory / f'{transcript_name}.txt'
    md_path = output_directory / f'{transcript_name}.md'

    print(f'Видео: {video_path}')
    print(f'Аудиодорожка: {args.track}')
    print(f'Модель: {args.model}')
    print()

    with tempfile.TemporaryDirectory() as temp_directory:
        audio_path = Path(temp_directory) / 'lecturer.wav'

        print('1/3 Извлечение аудиодорожки...')

        extract_audio_track(
            video_path=video_path,
            output_path=audio_path,
            track_number=args.track,
        )

        print('2/3 Транскрибация...')

        segments = transcribe_audio(
            audio_path=audio_path,
            model_name=args.model,
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