"""Save real-device UI previews without starting audio capture."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication
from src.gui import MainWindow


app = QApplication.instance() or QApplication([])
app.setStyle('Fusion')
window = MainWindow()
window.show()
app.processEvents()
directory = Path(__file__).resolve().parents[2] / 'output' / 'live_ui'
directory.mkdir(parents=True, exist_ok=True)
window.fade.stop()
window.fade_effect.setOpacity(1)
window.grab().save(str(directory / 'home.png'))
window.resize(1060, 680)
app.processEvents()
window.grab().save(str(directory / 'home_small.png'))
window.open_live()
app.processEvents()
live = window.live_window
window.fade.stop()
window.fade_effect.setOpacity(1)
window.resize(1240, 760)
app.processEvents()
window.grab().save(str(directory / 'live_ready.png'))
live.open_transcript_window()
app.processEvents()
live.transcript_window.grab().save(str(directory / 'detached_ready.png'))
live.timestamps.setChecked(True)
live.add_paragraph(0, 'Пример отображения: речь из вебинара постепенно появляется в этом окне')
live.add_paragraph(8, 'Таймкоды выключены по умолчанию, их можно включить перед началом сеанса')
live.add_paragraph(16, '[Смена устройства: переподключаем звук, возможен короткий пропуск]')
live.saved_paths([directory.parent / 'live_example.md'])
window.resize(1060, 680)
app.processEvents()
window.grab().save(str(directory / 'live_small.png'))
live.transcript_window.grab().save(str(directory / 'detached_text.png'))
print(directory)
window.close()


