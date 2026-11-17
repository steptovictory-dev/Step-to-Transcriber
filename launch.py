"""Small Windows launcher for the installed local project environment."""

import ctypes
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    project = root / 'project'
    python = project / '.venv' / 'Scripts' / 'pythonw.exe'
    script = project / 'app.py'
    if not python.is_file() or not script.is_file():
        ctypes.windll.user32.MessageBoxW(
            None, 'Не найдено окружение проекта. Файл запуска должен находиться рядом с папкой project',
            'Step to Transcriber', 16,
        )
        return 1
    subprocess.Popen([str(python), str(script)], cwd=project, creationflags=subprocess.CREATE_NO_WINDOW)
    return 0


if __name__ == '__main__':
    sys.exit(main())
