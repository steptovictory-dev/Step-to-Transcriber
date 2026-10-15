from pathlib import Path

"""Warm stone and copper desktop theme."""

STYLE = '''
QWidget { color: #eee7dd; font-family: "Segoe UI"; font-size: 14px; }
QMainWindow, QWidget#shell { background: #22211f; }
QWidget#page { background: transparent; }
QFrame#header { border-bottom: 1px solid #3b3631; }
QFrame#footer { border-top: 1px solid #3b3631; }
QLabel { background: transparent; }
QLabel#brand { color: #df9b66; font-family: "Georgia"; font-style: italic; font-weight: bold; font-size: 31px; }
QLabel#eyebrow { color: #d39362; font-size: 11px; font-weight: 600; letter-spacing: 3px; }
QLabel#heading { color: #f1e9dc; font-family: "Georgia"; font-style: italic; font-size: 34px; }
QLabel#liveEmptyTitle { color: #f1e9dc; font-family: "Georgia"; font-style: italic; font-size: 28px; }
QLabel#muted { color: #b0a59b; }
QLabel#small { color: #b0a59b; font-size: 12px; }
QLabel#cardTitle { font-size: 22px; font-weight: 600; }
QLabel#cardIndex { color: #d39362; font-size: 12px; letter-spacing: 2px; }
QLabel#badge { background: #332c25; color: #dfaa7e; border: 1px solid #574131; border-radius: 12px; padding: 5px 12px; font-size: 11px; }
QLabel#liveBadge { background: #29362a; color: #b0d49e; border: 1px solid #628755; border-radius: 12px; padding: 5px 12px; font-size: 11px; }
QLabel#step { color: #8d8379; font-size: 12px; }
QLabel#step[active="true"] { color: #e6ac7e; }
QFrame#panel { background: #2b2926; border: 1px solid #484039; border-radius: 14px; }
QPushButton { background: #35302b; border: 1px solid #5b4d40; border-radius: 8px; padding: 11px 19px; font-weight: 600; }
QPushButton:hover { background: #44382e; border-color: #c48350; }
QPushButton:pressed { background: #514032; }
QPushButton:focus { border: 1px solid #e4ac7b; }
QPushButton:disabled { color: #847a70; background: #2b2926; border-color: #423a32; }
QPushButton#primary { background: #cf8851; color: #201a15; border: 1px solid #e2a878; }
QPushButton#primary:hover { background: #e1a16d; }
QPushButton#primary:disabled { background: #614936; border-color: #614936; color: #ad9480; }
QPushButton#quiet { background: transparent; border: 1px solid transparent; color: #c2b3a4; }
QPushButton#quiet:hover { color: #e9ad7a; background: #332c26; }
QPushButton#liveTool { background: transparent; border: 1px solid transparent; padding: 0; border-radius: 7px; }
QPushButton#liveTool:hover { background: #3b322a; border-color: transparent; }
QPushButton#liveTool:pressed { background: #514032; }
QPushButton#liveTool:checked { background: #63462f; border-color: #a37550; }
QPushButton#liveTool:focus { border-color: #e4ac7b; }
QPushButton#liveTool:disabled { background: transparent; border-color: transparent; }
QPushButton#exit { background: #654039; border: 1px solid #a16b59; color: #f3d5c8; }
QPushButton#exit:hover { background: #7c493e; border-color: #cb8b70; }
QPushButton#exit:pressed { background: #55332e; }
QCheckBox { spacing: 9px; background: transparent; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #8e7058; border-radius: 4px; background: #24221f; }
QCheckBox::indicator:checked { image: url(__CHECKMARK__); background: #cf8851; border: 2px solid #efbf98; }
QCheckBox::indicator:disabled { border-color: #574a40; }
QPushButton#sourceCard { text-align: left; background: #2b2926; border: 1px solid #514337; border-radius: 16px; }
QPushButton#sourceCard:hover { background: #342c25; border: 1px solid #d39362; }
QPushButton#sourceCard:focus { border: 1px solid #514337; }
QPushButton#sourceCard:hover:focus { background: #342c25; border: 1px solid #d39362; }
QLineEdit, QComboBox, QPlainTextEdit { background: #24221f; border: 1px solid #5a4c3e; border-radius: 8px; padding: 11px; selection-background-color: #875c3d; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #d39362; }
QLineEdit:disabled, QComboBox:disabled { color: #8d8379; border-color: #443b33; }
QComboBox { min-height: 20px; padding-right: 24px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #2b2926; color: #eee7dd; selection-background-color: #69492f; }
QPlainTextEdit#transcript { font-size: 16px; padding: 20px; background: #282622; border: 1px solid #4a4036; }
QProgressBar { background: #34302a; border: none; border-radius: 4px; min-height: 7px; max-height: 7px; }
QProgressBar::chunk { background: #d39362; border-radius: 4px; }
QScrollBar:vertical { background: #282622; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #6b5745; border-radius: 4px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #342c25; color: #eee7dd; border: 1px solid #8e6443; padding: 6px; }
'''

STYLE = STYLE.replace('__CHECKMARK__', (Path(__file__).resolve().parents[1] / 'assets' / 'checkmark.svg').as_posix())

STYLE += 'QPushButton:checked { background: #63462f; border: 1px solid #d39362; color: #f4dfcb; }'
