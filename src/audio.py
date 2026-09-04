from pathlib import Path
import wave

import av


def extract_audio_track(
    video_path: Path,
    output_path: Path,
    track_number: int = 2,
    sample_rate: int = 16000,
) -> Path:
    if not video_path.exists():
        raise FileNotFoundError(f'Файл не найден: {video_path}')

    if track_number < 1:
        raise ValueError('Номер аудиодорожки должен быть не меньше 1.')

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with av.open(str(video_path)) as container:
        audio_streams = container.streams.audio

        if track_number > len(audio_streams):
            raise ValueError(
                f'В файле только {len(audio_streams)} аудиодорожек, '
                f'запрошена дорожка {track_number}.'
            )

        audio_stream = audio_streams[track_number - 1]

        resampler = av.AudioResampler(
            format='s16',
            layout='mono',
            rate=sample_rate,
        )

        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            for frame in container.decode(audio_stream):
                for resampled_frame in resampler.resample(frame):
                    audio = resampled_frame.to_ndarray()
                    wav_file.writeframes(audio.tobytes())

            for resampled_frame in resampler.resample(None):
                audio = resampled_frame.to_ndarray()
                wav_file.writeframes(audio.tobytes())

    return output_path