"""Desktop entry point. The original main.py remains the console entry point."""

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.gui import MainWindow


def main():
    logs = Path(__file__).resolve().parent.parent / 'output'
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=logs / 'transcriber.log', encoding='utf-8', level=logging.INFO)
    app = QApplication(sys.argv)
    app.setApplicationName('Step to Transcriber')
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
