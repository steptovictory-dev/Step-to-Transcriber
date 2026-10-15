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

# Each dark-theme token has an explicit warm light-theme counterpart
LIGHT_COLORS = {
    '#eee7dd': '#302b25', '#22211f': '#f2ebdd', '#3b3631': '#d4c6b0',
    '#df9b66': '#995a34', '#d39362': '#995a34', '#f1e9dc': '#302b25',
    '#b0a59b': '#706454', '#d99b6b': '#995a34', '#8d8379': '#7c7060',
    '#332c25': '#eadcc8', '#dfaa7e': '#7b4829', '#574131': '#bba183',
    '#29362a': '#e5ecde', '#b0d49e': '#3f6034', '#628755': '#90a57e',
    '#e6ac7e': '#884b28', '#2b2926': '#faf6ed', '#484039': '#d4c6b0',
    '#35302b': '#eee3d2', '#5b4d40': '#c1ab8e', '#44382e': '#e7d6bc',
    '#c48350': '#995a34', '#514032': '#dcc5a6', '#e4ac7b': '#995a34',
    '#847a70': '#998d7c', '#423a32': '#ddd3c3', '#cf8851': '#995a34',
    '#201a15': '#fff8ec', '#e2a878': '#884b28', '#e1a16d': '#854b2b',
    '#614936': '#dfcbb4', '#ad9480': '#827363', '#c2b3a4': '#70604d',
    '#e9ad7a': '#884b28', '#332c26': '#eaddc9', '#3b322a': '#eadcc8',
    '#63462f': '#995a34', '#a37550': '#884b28', '#654039': '#eee0d7',
    '#a16b59': '#b78d79', '#f3d5c8': '#743d2e', '#7c493e': '#e4c9ba',
    '#cb8b70': '#9d6a51', '#55332e': '#d9baaa', '#8e7058': '#b19472',
    '#24221f': '#f5f0e5', '#efbf98': '#884b28', '#574a40': '#d6c9b6',
    '#514337': '#d4c6b0', '#342c25': '#eee1cb', '#5a4c3e': '#c6b396',
    '#875c3d': '#cfa985', '#443b33': '#d8cdbb', '#69492f': '#d9ba96',
    '#282622': '#f5f0e5', '#4a4036': '#cfbfa7', '#34302a': '#e2d6c1',
    '#6b5745': '#bca17e', '#8e6443': '#b19472', '#f4dfcb': '#fff8ec',
}


def theme_style(mode='dark'):
    if mode != 'light':
        return STYLE
    import re
    return re.sub(r'#[0-9a-fA-F]{6}', lambda match: LIGHT_COLORS.get(match[0].lower(), match[0]), STYLE)
