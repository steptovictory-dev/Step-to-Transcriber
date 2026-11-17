import os
import sys
from pathlib import Path

from src.paths import IS_BUNDLED, IS_INSTALLED, RESOURCES


_DLL_HANDLES = []


def configure_gpu_runtime() -> None:
    if sys.platform != 'win32' or _DLL_HANDLES:
        return

    if IS_BUNDLED:
        nvidia = RESOURCES / 'nvidia'
    else:
        nvidia = Path(sys.prefix) / 'Lib' / 'site-packages' / 'nvidia'

    dll_directories = [nvidia / name / 'bin' for name in ('cublas', 'cudnn', 'cuda_nvrtc')]
    if not IS_INSTALLED:
        dll_directories.append(Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin'))

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
