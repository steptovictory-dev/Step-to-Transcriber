"""Capture both themes and languages using isolated preferences."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from src.gui import MainWindow
from src.i18n import PAIRS, translate

app = QApplication([])
app.setStyle('Fusion')
out = Path(__file__).resolve().parents[2] / 'output' / 'appearance-review'
out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    window = MainWindow(settings=QSettings(str(Path(directory) / 'ui.ini'), QSettings.Format.IniFormat))
    window.show()

    def capture(name):
        window.fade.stop()
        window.fade_effect.setOpacity(1)
        QTest.qWait(190)
        app.processEvents()
        window.grab().save(str(out / f'{name}.png'))

    for light in (False, True):
        window.theme_switch.setChecked(light)
        for english in (False, True):
            window.language_switch.setChecked(english)
            mode = ('light' if light else 'dark') + ('-en' if english else '-ru')
            window.resize(1240, 760)
            window.navigate(0, animate=False)
            capture(mode + '-home')
            window.select_source(False)
            window.advanced.show()
            window.resize(1060, 760)
            capture(mode + '-setup-minimum')
            print(mode, 'setup:', window.pages.currentWidget().minimumSizeHint().height(), '/', window.pages.height())
            with patch('src.live_gui.LivePage.refresh_devices'):
                window.open_live()
                capture(mode + '-live-minimum')
                live = window.live_window
                print(mode, 'live:', live.minimumSizeHint().height(), '/', window.pages.height())
                live.open_transcript_window()
                app.processEvents()
                live.transcript_window.grab().save(str(out / f'{mode}-detached.png'))
                live.transcript_window.close()
    window.close()
print('Saved 16 UI captures:', out)
