from src.runtime import configure_gpu_runtime


configure_gpu_runtime()

from faster_whisper import WhisperModel


audio_path = 'lecturer.wav'

model = WhisperModel(
    'tiny',
    device='cuda',
    compute_type='float16',
)

segments, info = model.transcribe(
    audio_path,
    language='ru',
    beam_size=1,
)

print(f'Язык: {info.language}')
print(f'Длительность: {info.duration:.1f} сек.')
print()

for segment in segments:
    print(
        f'[{segment.start:6.1f} → {segment.end:6.1f}] '
        f'{segment.text.strip()}'
    )