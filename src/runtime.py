import os
import sys
from pathlib import Path


_DLL_HANDLES = []


def configure_gpu_runtime() -> None:
    if sys.platform != 'win32':
        return

    venv_path = Path(sys.prefix)

    dll_directories = [
        venv_path / 'Lib' / 'site-packages' / 'nvidia' / 'cublas' / 'bin',
        venv_path / 'Lib' / 'site-packages' / 'nvidia' / 'cudnn' / 'bin',
        venv_path / 'Lib' / 'site-packages' / 'nvidia' / 'cuda_nvrtc' / 'bin',
        Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin'),
    ]

    existing_directories = [
        directory
        for directory in dll_directories
        if directory.exists()
    ]

    current_path = os.environ.get('PATH', '')

    os.environ['PATH'] = os.pathsep.join(
        [str(directory) for directory in existing_directories]
        + [current_path]
    )

    for directory in existing_directories:
        handle = os.add_dll_directory(str(directory))
        _DLL_HANDLES.append(handle)