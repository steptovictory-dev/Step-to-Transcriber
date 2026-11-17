"""Desktop entry point. The original main.py remains the console entry point."""

import logging
import ctypes
import sys
from uuid import uuid4

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.gui import MainWindow
from src.paths import DATA, IS_BUNDLED, RESOURCES


def configure_logging(root):
    logs = root / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    legacy = root / 'output' / 'transcriber.log'
    try:
        if legacy.is_file():
            legacy.rename(logs / f'transcriber-previous-{uuid4().hex[:8]}.log')
    except OSError:
        # A running older instance may still hold the old journal open
        pass
    logging.basicConfig(filename=logs / 'transcriber.log', encoding='utf-8', level=logging.INFO)


def main():
    configure_logging(DATA)
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Steptovictory.StepToTranscriber')
    app = QApplication(sys.argv)
    app.setApplicationName('Step to Transcriber')
    app.setWindowIcon(QIcon(str(RESOURCES / 'assets' / 'step-to-transcriber.ico')))
    app.setStyle('Fusion')
    settings = QSettings(str(DATA / 'settings.ini'), QSettings.Format.IniFormat) if IS_BUNDLED else None
    window = MainWindow(settings=settings)
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
