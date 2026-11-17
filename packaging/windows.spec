import os
import sys
from importlib.metadata import distribution, distributions
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata


project = Path(SPECPATH).parent
assets = project / 'assets'
node = Path(os.environ['TRANSCRIBER_NODE_DIST'])
datas = [
    (str(assets / 'step-to-transcriber.ico'), 'assets'),
    (str(assets / 'checkmark.svg'), 'assets'),
    (str(node / 'node.exe'), 'tools'),
    (str(node / 'LICENSE'), 'notices/Node.js'),
]
datas += collect_data_files('faster_whisper')
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.is_file():
    datas.append((str(python_license), 'notices/Python'))
for package in ('huggingface-hub', 'hf-xet', 'yt-dlp', 'yt-dlp-ejs'):
    datas += copy_metadata(package)

# Keep the entire cuDNN runtime on a single version. CTranslate2's wheel also
# carries a cudnn64_9.dll with a different version from the NVIDIA wheel.
gpu_packages = {
    'nvidia-cublas-cu12': ('cublas64_', 'cublasLt64_'),
    'nvidia-cudnn-cu12': ('cudnn',),
    'nvidia-cuda-nvrtc-cu12': ('nvrtc',),
}
gpu_files = {}
gpu_binaries = []
for name, prefixes in gpu_packages.items():
    wheel = distribution(name)
    libraries = [
        item for item in wheel.files
        if item.suffix == '.dll' and item.name.startswith(prefixes)
    ]
    if not libraries:
        raise RuntimeError(f'No NVIDIA runtime DLLs found in {name}')
    for item in libraries:
        source = str(wheel.locate_file(item))
        gpu_binaries.append((source, item.parent.as_posix()))
        gpu_files[item.name.lower()] = Path(*item.parts)

for wheel in distributions():
    for item in wheel.files or ():
        if not any(part.endswith(('.dist-info', '.egg-info')) for part in item.parts):
            continue
        if item.name.lower().startswith(('license', 'licence', 'copying', 'notice', 'copyright', 'authors')):
            folder = Path('notices', wheel.metadata['Name'], *item.parts[1:-1])
            datas.append((str(wheel.locate_file(item)), str(folder)))

analysis = Analysis(
    [str(project / 'app.py')],
    pathex=[str(project)],
    binaries=gpu_binaries + [
        entry for entry in collect_dynamic_libs('ctranslate2')
        if Path(entry[0]).name.lower() not in gpu_files
    ],
    datas=datas,
    hiddenimports=['huggingface_hub._snapshot_download', 'hf_xet', 'PySide6.QtSvg'],
)
def keep_binary(destination):
    path = Path(destination)
    name = path.name.lower()
    # Qt uses the Windows ICU ABI. A third-party ICU on the build PATH can
    # shadow the system DLL with a same-named library that has different exports.
    if name in {'icu.dll', 'icuuc.dll', 'icuin.dll'} or name.startswith('icudt'):
        return False
    return name not in gpu_files or path == gpu_files[name]


analysis.binaries = [entry for entry in analysis.binaries if keep_binary(entry[0])]
missing_gpu_files = set(gpu_files.values()) - {Path(entry[0]) for entry in analysis.binaries}
if missing_gpu_files:
    raise RuntimeError(f'NVIDIA libraries missing from bundle: {sorted(map(str, missing_gpu_files))}')

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='Step to Transcriber',
    upx=False,
    console=False,
    icon=str(assets / 'step-to-transcriber.ico'),
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    upx=False,
    name='Step to Transcriber',
)
