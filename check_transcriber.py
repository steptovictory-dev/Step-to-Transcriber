from pathlib import Path

from src.transcriber import transcribe_audio


audio_path = Path('output/lecturer_test.wav')

segments = transcribe_audio(
    audio_path=audio_path,
    model_name='large-v3',
)

print(f'Получено сегментов: {len(segments)}')
print()

for segment in segments[:20]:
    print(
        f'[{segment.start:7.1f} → {segment.end:7.1f}] '
        f'{segment.text}'
    )