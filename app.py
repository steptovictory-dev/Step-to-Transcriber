"""Desktop entry point. The original main.py remains the console entry point."""

import logging
import ctypes
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from src.gui import MainWindow


def main():
    logs = Path(__file__).resolve().parent.parent / 'output'
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=logs / 'transcriber.log', encoding='utf-8', level=logging.INFO)
    if sys.platform == 'win32':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Steptovictory.StepToTranscriber')
    app = QApplication(sys.argv)
    app.setApplicationName('Step to Transcriber')
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / 'assets' / 'step-to-transcriber.ico')))
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
