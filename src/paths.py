import os
import sys
from pathlib import Path


RESOURCES = Path(__file__).resolve().parents[1]
IS_BUNDLED = getattr(sys, 'frozen', False)
IS_INSTALLED = IS_BUNDLED or (RESOURCES / 'installed.flag').is_file()

if IS_INSTALLED:
    local_data = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
    DATA = local_data / 'Step to Transcriber'
else:
    DATA = RESOURCES.parent
