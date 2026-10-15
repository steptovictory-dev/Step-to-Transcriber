"""Exercise the real desktop worker, YouTube download, GPU and MD-only export."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.gui import MainWindow


app = QApplication([])
window = MainWindow()
window.select_source(True)
window.source.setText(sys.argv[1])
window.show()
exit_code = [1]


def finish():
    result = window.result
    if result and result.markdown and result.markdown.is_file() and result.txt is None and result.text:
        if window.pages.currentIndex() == 3 and window.preview.toPlainText() == result.text:
            exit_code[0] = 0
            print(f'Desktop worker OK; Markdown only: {result.markdown}', flush=True)
            window.fade.stop()
            window.fade_effect.setOpacity(1.0)
            window.grab().save(str(result.markdown.parent / 'desktop-smoke-result.png'))
    else:
        print(f'Desktop smoke failed: {window.status.text()}', flush=True)
    window.close()
    app.quit()


def start():
    window.start_job()
    if window.worker:
        window.worker.status.connect(lambda message: print(message, flush=True))
        window.worker.finished.connect(lambda: QTimer.singleShot(250, finish))
    else:
        finish()


QTimer.singleShot(250, start)
app.exec()
sys.exit(exit_code[0])
