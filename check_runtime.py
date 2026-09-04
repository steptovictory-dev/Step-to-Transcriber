from src.runtime import configure_gpu_runtime


configure_gpu_runtime()

import ctranslate2


print('GPU runtime configured')
print(f'CTranslate2: {ctranslate2.__version__}')
print(
    'CUDA compute types:',
    ctranslate2.get_supported_compute_types('cuda'),
)