"""Capture the real Qt pages for visual review without running inference."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from src.gui import MainWindow
from src.pipeline import Result


app = QApplication([])
window = MainWindow()
window.show()
output = Path(__file__).resolve().parents[2] / 'output'
output.mkdir(exist_ok=True)


def capture(name):
    window.fade.stop()
    window.fade_effect.setOpacity(1.0)
    app.processEvents()
    window.grab().save(str(output / f'design-{name}.png'))


capture('home')
window.select_source(True)
window.source.setText('https://www.youtube.com/watch?v=1tCfHLFnXSw')
capture('setup')
window.advanced.show()
capture('settings')
window.navigate(2, animate=False)
window.set_status('Загрузка модели и распознавание речи')
window.update_progress(0.43)
window.wave.start()
window.cancel.setEnabled(True)
window.wave.phase = 1.4
capture('processing')
window.wave.stop()
text = (
    'Это демонстрационный текст для проверки оформления расшифровки. '
    'Настоящая запись появится здесь после завершения распознавания.\n\n'
    'Текст можно скопировать кнопкой справа сверху. Выбранные форматы '
    'сохраняются в папке результатов, а Markdown содержит таймкоды абзацев.'
)
window.completed(Result(None, output / 'demo.md', 'Демонстрация экрана результата', text))
capture('result')
window.resize(860, 720)
window.navigate(0, animate=False)
capture('home-minimum')
window.select_source(True)
window.advanced.show()
capture('settings-minimum')
window.close()
print('Captured 7 UI views')
