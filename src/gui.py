import logging
from pathlib import Path

from src.i18n import retranslate, set_language, tr

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, QSize, QThread, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QFrame, QGraphicsOpacityEffect,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.audio import get_audio_track_count
from src.pipeline import Job, run_job
from src.sharing import ShareFileButton
from src.theme import theme_style
from src.widgets import AlignedRow, GuitarKnob, SourceCard, Waveform, line_icon
from src.youtube import normalize_video_url


ROOT = Path(__file__).resolve().parents[2]
GITHUB = 'https://github.com/steptovictory-dev'
MEDIA_FILTER = tr('Медиа (*.mp4 *.mkv *.mov *.webm *.mp3 *.wav *.m4a *.flac *.ogg *.opus)')
MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.webm', '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.opus'}


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(False)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName('primary')
    widget.clicked.connect(callback)
    return widget


class Worker(QThread):
    status = Signal(str)
    progress = Signal(float)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job

    def run(self):
        try:
            self.completed.emit(run_job(self.job, self.status.emit, self.progress.emit, self.isInterruptionRequested))
        except InterruptedError:
            self.cancelled.emit()
        except Exception as error:
            logging.exception('Transcription failed')
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.preferences = settings if settings is not None else QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope,
            'Steptovictory', 'StepToTranscriber')
        self.ui_language = self.preferences.value('ui_language', 'ru', type=str)
        self.ui_theme = self.preferences.value('ui_theme', 'dark', type=str)
        self.ui_language = self.ui_language if self.ui_language in ('ru', 'en') else 'ru'
        self.ui_theme = self.ui_theme if self.ui_theme in ('dark', 'light') else 'dark'
        set_language(self.ui_language)
        QApplication.instance().setProperty('ui_theme', self.ui_theme)
        self.worker = None
        self.live_window = None
        self.result = None
        self.is_youtube = False
        self.close_when_finished = False
        self.outcome = None
        self.setWindowTitle('Step to Transcriber')
        self.setWindowIcon(QIcon(str(ROOT / 'project' / 'assets' / 'step-to-transcriber.ico')))
        self.setMinimumSize(1060, 760)
        self.resize(1240, 760)
        self.fullscreen_shortcut = QShortcut(QKeySequence('F11'), self)
        self.fullscreen_shortcut.setAutoRepeat(False)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.setAcceptDrops(True)
        self.setStyleSheet(theme_style(self.ui_theme))
        shell = QWidget()
        shell.setObjectName('shell')
        self.setCentralWidget(shell)
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName('header')
        row = QHBoxLayout(header)
        row.setContentsMargins(36, 8, 36, 4)
        brand = label('Step to Transcriber', 'brand')
        row.addWidget(brand)
        row.addStretch()
        studio = QVBoxLayout()
        studio.setSpacing(14)
        studio.addWidget(label('LOCAL AUDIO STUDIO', 'eyebrow'), alignment=Qt.AlignmentFlag.AlignHCenter)
        switches = QVBoxLayout()
        switches.setSpacing(10)
        self.theme_switch = GuitarKnob('DARK', 'LIGHT')
        self.language_switch = GuitarKnob('RU', 'EN')
        self.theme_switch.setChecked(self.ui_theme == 'light')
        self.language_switch.setChecked(self.ui_language == 'en')
        for control, hint in ((self.language_switch, tr('Язык интерфейса: русский / английский')),
                              (self.theme_switch, tr('Тёмная / светлая тема'))):
            control.setToolTip(hint)
            control.setAccessibleName(hint)
            switches.addWidget(control, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setTabOrder(self.language_switch, self.theme_switch)
        self.theme_switch.toggled.connect(self.change_theme)
        self.language_switch.toggled.connect(self.change_language)
        studio.addLayout(switches)
        row.addLayout(studio)
        outer.addWidget(header)

        self.route = QWidget()
        route = QHBoxLayout(self.route)
        route.setSpacing(12)
        route.setContentsMargins(40, 0, 40, 7)
        self.steps = []
        for index, text in enumerate((tr('Источник'), tr('Подготовка'), tr('Обработка'), tr('Результат'))):
            step = label(f'0{index + 1}  {text}', 'step')
            self.steps.append(step)
            route.addWidget(step)
            if index < 3:
                route.addWidget(label('/', 'small'))
        route.addStretch()
        outer.addWidget(self.route)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_home())
        self.pages.addWidget(self.build_setup())
        self.pages.addWidget(self.build_processing())
        self.pages.addWidget(self.build_result())
        outer.addWidget(self.pages, 1)
        self.fade_effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(self.fade_effect)
        self.fade = QPropertyAnimation(self.fade_effect, b'opacity', self)
        self.fade.setDuration(210)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        footer = QFrame()
        footer.setObjectName('footer')
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(36, 12, 36, 12)
        footer_row.addWidget(label(tr('Разработчик: Steptovictory'), 'small'))
        footer_row.addStretch()
        github = button('GitHub / steptovictory-dev', lambda: QDesktopServices.openUrl(QUrl(GITHUB)))
        github.setObjectName('quiet')
        github.setToolTip(GITHUB)
        footer_row.addWidget(github)
        outer.addWidget(footer)
        self.navigate(0, animate=False)
        self.apply_appearance()

    def apply_appearance(self):
        QApplication.instance().setProperty('ui_theme', self.ui_theme)
        self.setStyleSheet(theme_style(self.ui_theme))
        for control in (self.theme_switch, self.language_switch):
            control.light = self.ui_theme == 'light'
            control.update()
        # The transcript window is top-level, so it needs its own stylesheet
        if self.live_window and self.live_window.transcript_window:
            self.live_window.transcript_window.setStyleSheet(theme_style(self.ui_theme))
        for widget in self.findChildren(QWidget):
            kind = widget.property('icon_kind')
            if kind:
                if isinstance(widget, QLabel):
                    widget.setPixmap(line_icon(kind, 32).pixmap(32, 32))
                elif isinstance(widget, QPushButton):
                    widget.setIcon(line_icon(kind, 28))

    def change_theme(self, light):
        self.ui_theme = 'light' if light else 'dark'
        self.preferences.setValue('ui_theme', self.ui_theme)
        self.preferences.sync()
        self.apply_appearance()

    def change_language(self, english):
        self.ui_language = 'en' if english else 'ru'
        set_language(self.ui_language)
        self.preferences.setValue('ui_language', self.ui_language)
        self.preferences.sync()
        retranslate(self)
        for action, text in ((self.open_md, 'Открыть Markdown'), (self.open_txt, 'Открыть TXT'),
                             (self.folder_action, 'Открыть папку')):
            action.setText(tr(text))
        if self.live_window and self.live_window.transcript_window:
            retranslate(self.live_window.transcript_window)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.restoreGeometry(self.windowed_geometry)
        else:
            self.windowed_geometry = self.saveGeometry()
            self.showFullScreen()

    def page(self):
        page = QWidget()
        page.setObjectName('page')
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 12, 40, 24)
        layout.setSpacing(16)
        return page, layout

    def build_home(self):
        page, layout = self.page()
        layout.addStretch(1)
        layout.addWidget(label(tr('АУДИО / ВИДЕО / ЭФИР'), 'eyebrow'))
        layout.addWidget(label(tr('Превращаем звук в слова'), 'heading'))
        layout.addWidget(label(tr('Выберите файл, ссылку на видео или звук прямого эфира'), 'muted'))
        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.file_card = SourceCard('01', tr('Файл на компьютере'), tr('Выберите аудио или видео\nили перетащите файл в окно'), 'file')
        self.url_card = SourceCard('02', tr('Ссылка на видео'), tr('YouTube, VK Видео, Rutube\nTwitch, VK Видео Live: записи эфиров'), 'link')
        self.live_card = SourceCard('03', tr('Прямой эфир'), tr('Вебинары и стримы\nЗвук компьютера без ссылки'), 'live')
        self.live_card.setToolTip(tr('Расшифровка звука компьютера в этом окне'))
        self.file_card.clicked.connect(lambda: self.select_source(False))
        self.url_card.clicked.connect(lambda: self.select_source(True))
        self.live_card.clicked.connect(self.open_live)
        cards.addWidget(self.file_card, 1)
        cards.addWidget(self.url_card, 1)
        cards.addWidget(self.live_card, 1)
        layout.addLayout(cards)
        layout.addWidget(label(tr('Обработка на вашем компьютере / язык определяется автоматически'), 'small'))
        layout.addStretch(2)
        return page

    def build_setup(self):
        page, layout = self.page()
        layout.setContentsMargins(40, 10, 40, 10)
        layout.setSpacing(8)
        top = QHBoxLayout()
        back = button(tr('‹  Выбор источника'), self.go_home)
        back.setObjectName('quiet')
        top.addWidget(back)
        top.addStretch()
        layout.addLayout(top)
        layout.addWidget(label(tr('Подготовим вашу запись'), 'heading'))
        self.setup_hint = label('', 'muted')
        layout.addWidget(self.setup_hint)
        self.settings = QFrame()
        self.settings.setObjectName('panel')
        self.settings.setStyleSheet('QLineEdit { padding: 7px 11px; } '
                                   'QComboBox { padding: 7px 24px 7px 11px; } '
                                   'QPushButton { padding: 7px 19px; }')
        panel = QVBoxLayout(self.settings)
        panel.setContentsMargins(24, 12, 24, 12)
        panel.setSpacing(7)
        self.input_label = label(tr('ИСХОДНЫЙ ФАЙЛ'), 'eyebrow')
        panel.addWidget(self.input_label)
        source_row = QHBoxLayout()
        self.source = QLineEdit()
        self.source.editingFinished.connect(self.inspect_source)
        self.browse = button(tr('Выбрать файл'), self.choose_file)
        source_row.addWidget(self.source, 1)
        source_row.addWidget(self.browse)
        panel.addLayout(source_row)
        self.notice = label(tr('Выберите файл для расшифровки'), 'small')
        self.notice.setWordWrap(True)
        panel.addWidget(self.notice)
        form = QFormLayout()
        form.setVerticalSpacing(8)
        self.format = QComboBox()
        self.format.addItem('Markdown (.md)', ('md',))
        self.format.addItem(tr('Обычный текст (.txt)'), ('txt',))
        self.format.addItem(tr('Markdown + текст (.md и .txt)'), ('md', 'txt'))
        form.addRow(tr('Формат результата'), self.format)
        self.track = QComboBox()
        self.track.addItem(tr('Дорожка 1 (автоматически)'), 1)
        self.track.setEnabled(False)
        self.track_label = label(tr('Аудиодорожка'))
        form.addRow(self.track_label, self.track)
        panel.addLayout(form)
        self.more = button(tr('Дополнительные настройки  +'), self.toggle_advanced)
        self.more.setObjectName('quiet')
        panel.addWidget(self.more, alignment=Qt.AlignmentFlag.AlignLeft)
        self.advanced = QWidget()
        advanced_form = QGridLayout(self.advanced)
        advanced_form.setContentsMargins(0, 0, 0, 0)
        advanced_form.setHorizontalSpacing(14)
        advanced_form.setVerticalSpacing(8)
        self.timestamps = button(tr('Вкл'), lambda: None)
        self.timestamps.setCheckable(True)
        self.timestamps.setObjectName('timestampToggle')
        self.timestamps.setFixedSize(86, 30)
        self.timestamps.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.timestamps.setAccessibleName(tr('Таймкоды'))
        self.timestamps.setStyleSheet(
            'QPushButton { padding: 3px 14px; border-radius: 15px; }')
        self.timestamps.setChecked(True)
        self.timestamps.setToolTip(tr('Таймкоды абзацев в результате, копируемом тексте и файлах MD / TXT'))
        self.timestamps_off = button(tr('Выкл'), lambda: self.timestamps.setChecked(False))
        self.timestamps_off.setCheckable(True)
        self.timestamps_off.setFixedSize(86, 30)
        self.timestamps_off.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.timestamps_off.setAccessibleName(tr('Выключить таймкоды'))
        self.timestamps_off.setToolTip(tr('Не добавлять таймкоды в текст и файлы результата'))
        self.timestamps_off.setStyleSheet(self.timestamps.styleSheet())
        self.timestamps.toggled.connect(lambda enabled: self.timestamps_off.setChecked(not enabled))
        self.timestamps.clicked.connect(lambda: self.timestamps.setChecked(True))
        self.timestamps_off.clicked.connect(lambda: self.timestamps_off.setChecked(True))
        timestamp_controls = QHBoxLayout()
        timestamp_controls.setContentsMargins(0, 0, 0, 0)
        timestamp_controls.setSpacing(6)
        timestamp_controls.addWidget(self.timestamps)
        timestamp_controls.addWidget(self.timestamps_off)
        timestamp_controls.addStretch()
        advanced_form.addWidget(label(tr('Таймкоды')), 0, 0)
        advanced_form.addLayout(timestamp_controls, 0, 1)
        self.model = QComboBox()
        self.model.addItem(tr('turbo (рекомендуется)'), 'turbo')
        self.model.addItem(tr('large-v3 (экспериментальный режим)'), 'large-v3')
        advanced_form.addWidget(label(tr('Модель')), 1, 0)
        advanced_form.addWidget(self.model, 1, 1)
        advanced_form.setColumnStretch(1, 1)
        out_row = QHBoxLayout()
        self.output = QLineEdit(self.output_directory())
        self.output.textChanged.connect(self.remember_output_directory)
        out_row.addWidget(self.output, 1)
        out_row.addWidget(button(tr('Изменить'), self.choose_output))
        advanced_form.addWidget(label(tr('Папка результатов')), 2, 0)
        advanced_form.addLayout(out_row, 2, 1)
        panel.addWidget(self.advanced)
        self.advanced.hide()
        layout.addWidget(self.settings)
        layout.addStretch()
        bottom = QHBoxLayout()
        bottom.addWidget(label(tr('Всё настроено для начала'), 'small'))
        bottom.addStretch()
        self.start = button(tr('Расшифровать  →'), self.start_job, primary=True)
        bottom.addWidget(self.start)
        layout.addLayout(bottom)
        return page

    def build_processing(self):
        page, layout = self.page()
        layout.addStretch()
        eyebrow = label(tr('СЛУШАЕМ / РАСПОЗНАЁМ / СОХРАНЯЕМ'), 'eyebrow')
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)
        self.processing_title = label(tr('Ваша запись становится текстом'), 'heading')
        self.processing_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.processing_title)
        self.wave = Waveform()
        layout.addWidget(self.wave)
        self.status = label(tr('Подготовка обработки'), 'muted')
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.percent = label(tr('Подготавливаем запись…'), 'small')
        self.percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent)
        stages = QHBoxLayout()
        self.stage_labels = []
        for text in (tr('Источник'), tr('Аудио'), tr('Распознавание'), tr('Сохранение')):
            item = label(text, 'step')
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stage_labels.append(item)
            stages.addWidget(item)
        layout.addLayout(stages)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(90)
        self.details.hide()
        self.details_button = button(tr('Подробности'), lambda: self.details.setVisible(self.details.isHidden()))
        self.details_button.setObjectName('quiet')
        layout.addWidget(self.details_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.details)
        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel = button(tr('Отменить обработку'), self.cancel_job)
        self.cancel.setEnabled(False)
        self.retry = button(tr('Вернуться к записи'), lambda: self.navigate(1))
        self.retry.hide()
        actions.addWidget(self.cancel)
        actions.addWidget(self.retry)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def build_result(self):
        page, layout = self.page()
        layout.addWidget(label(tr('ГОТОВО'), 'eyebrow'))
        self.result_heading = label(tr('Расшифровка закончена'), 'heading')
        self.share = ShareFileButton(self.share_result_file)
        self.share.setEnabled(False)
        self.copy = button(tr('Копировать текст'), self.copy_text)
        self.copy.setEnabled(False)
        self.copy_reset = QTimer(self)
        self.copy_reset.setSingleShot(True)
        self.copy_reset.timeout.connect(lambda: self.copy.setToolTip(tr('Копировать всю расшифровку в буфер обмена')))
        self.result_toolbar = QWidget()
        toolbar = QHBoxLayout(self.result_toolbar)
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(4)
        self.open_folder = button('', self.show_result_files)
        self.result_timestamps = button('', self.toggle_result_timestamps)
        self.result_timestamps.setCheckable(True)
        for control, kind, name, hint in (
            (self.open_folder, 'folder', tr('Файлы результата'), tr('Открыть файл или папку с результатом')),
            (self.result_timestamps, 'timestamps', tr('Таймкоды'),
             tr('Включить или выключить таймкоды в тексте и файлах результата')),
            (self.share, 'share', tr('Поделиться файлом'),
             tr('Перетащите файл в открытый чат или нажмите, чтобы открыть варианты передачи')),
            (self.copy, 'copy', tr('Копировать текст'), tr('Копировать всю расшифровку в буфер обмена')),
        ):
            control.setText('')
            control.setObjectName('liveTool')
            control.setIcon(line_icon(kind, 28))
            control.setProperty('icon_kind', kind)
            control.setIconSize(QSize(24, 24))
            control.setFixedSize(38, 38)
            control.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            control.setAccessibleName(name)
            control.setToolTip(hint)
            control.setEnabled(False)
            toolbar.addWidget(control)
        layout.addLayout(AlignedRow([self.result_heading], [self.result_toolbar]))
        self.result_title = label('', 'muted')
        self.result_title.setProperty('userContent', True)
        self.result_title.setWordWrap(True)
        layout.addWidget(self.result_title)
        self.preview = QPlainTextEdit()
        self.preview.setObjectName('transcript')
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        self.result_files = QMenu(self)
        self.open_md = self.result_files.addAction(tr('Открыть Markdown'), lambda: self.open_path(self.result.markdown))
        self.open_txt = self.result_files.addAction(tr('Открыть TXT'), lambda: self.open_path(self.result.txt))
        self.result_files.addSeparator()
        self.folder_action = self.result_files.addAction(tr('Открыть папку'), self.open_result_folder)
        self.exit_button = button(tr('Выход из приложения'), self.close)
        self.exit_button.setObjectName('exit')
        self.new_button = button(tr('Ещё одна расшифровка  →'), self.go_home, primary=True)
        layout.addLayout(AlignedRow([self.exit_button], [self.new_button]))
        return page

    def navigate(self, index, animate=True):
        self.fade.stop()
        self.pages.setCurrentIndex(index)
        self.route.setVisible(index < 4)
        for number, step in enumerate(self.steps):
            step.setProperty('active', number == index)
            step.style().unpolish(step)
            step.style().polish(step)
        if animate and self.isVisible():
            self.fade.setStartValue(0.0)
            self.fade.setEndValue(1.0)
            self.fade.start()
        else:
            self.fade_effect.setOpacity(1.0)

    def select_source(self, youtube):
        if self.worker or (self.live_window and self.live_window.worker):
            return
        self.is_youtube = youtube
        self.source.clear()
        self.source.setPlaceholderText(tr('Полная ссылка на видео или запись эфира') if youtube else tr('Путь к аудио или видео'))
        self.browse.setVisible(not youtube)
        self.track.setVisible(not youtube)
        self.track_label.setVisible(not youtube)
        self.track.clear()
        self.track.addItem(tr('Дорожка 1 (автоматически)'), 1)
        self.track.setEnabled(False)
        self.input_label.setText(tr('ССЫЛКА НА РОЛИК') if youtube else tr('ИСХОДНЫЙ ФАЙЛ'))
        self.setup_hint.setText(tr('Видео и завершённые эфиры: запись загрузится автоматически') if youtube else tr('Дорожка и язык выбраны автоматически, формат результата можно изменить'))
        self.notice.setText(tr('Ссылка на один доступный ролик, без прямых эфиров') if youtube else tr('Выберите файл или перетащите его в окно'))
        self.navigate(1)
        self.source.setFocus()

    def go_home(self):
        if self.worker or (self.live_window and self.live_window.worker):
            return
        self.result = None
        self.source.clear()
        self.preview.clear()
        self.format.setCurrentIndex(0)
        self.model.setCurrentIndex(0)
        self.timestamps.setChecked(True)
        self.advanced.hide()
        self.more.setText(tr('Дополнительные настройки  +'))
        self.copy_reset.stop()
        self.copy.setToolTip(tr('Копировать всю расшифровку в буфер обмена'))
        for control in (self.copy, self.share, self.open_folder, self.result_timestamps):
            control.setEnabled(False)
        self.result_timestamps.setChecked(False)
        self.navigate(0)

    def show_result_files(self):
        if self.result is not None:
            self.result_files.popup(self.open_folder.mapToGlobal(self.open_folder.rect().bottomLeft()))

    def toggle_result_timestamps(self, enabled):
        if self.result is None or self.result.segments is None:
            return
        try:
            self.result.set_timestamps(enabled)
        except OSError as error:
            self.result_timestamps.setChecked(not enabled)
            QMessageBox.warning(self, tr('Не удалось обновить таймкоды'), str(error))
            return
        scroll = self.preview.verticalScrollBar().value()
        self.preview.setPlainText(self.result.text)
        self.preview.verticalScrollBar().setValue(scroll)

    def share_result_file(self):
        if self.result is None:
            raise ValueError(tr('Сначала завершите расшифровку'))
        path = self.result.markdown or self.result.txt
        if path is None:
            raise ValueError(tr('Файл результата недоступен'))
        return path

    def toggle_advanced(self):
        visible = self.advanced.isHidden()
        self.advanced.setVisible(visible)
        self.more.setText(tr('Скрыть настройки  −') if visible else tr('Дополнительные настройки  +'))

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Выбрать аудио или видео'), str(ROOT / 'input'), tr(MEDIA_FILTER))
        if path:
            self.source.setText(path)
            self.inspect_source()

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, tr('Папка результатов'), self.output.text())
        if path:
            self.output.setText(path)

    def output_directory(self):
        return self.preferences.value('output_directory', str(ROOT / 'output'), type=str)

    def remember_output_directory(self, path):
        if not path.strip():
            return
        self.preferences.setValue('output_directory', path)
        self.preferences.sync()
        for field in (self.output, self.live_window.output if self.live_window else None):
            if field is not None and field.text() != path:
                field.blockSignals(True)
                field.setText(path)
                field.blockSignals(False)

    def inspect_source(self):
        if self.is_youtube or not self.source.text().strip():
            return
        previous = self.track.currentData()
        self.track.clear()
        try:
            path = Path(self.source.text().strip().strip('"'))
            if path.suffix.lower() not in MEDIA_EXTENSIONS:
                raise ValueError(tr('Неподдерживаемый формат файла'))
            count = get_audio_track_count(path)
            if count == 0:
                raise ValueError(tr('В файле нет аудиодорожек'))
            for number in range(1, count + 1):
                self.track.addItem(tr(f'Дорожка {number}') + (tr(' (автоматически)') if count == 1 else ''), number)
            if previous and previous <= count:
                self.track.setCurrentIndex(previous - 1)
            self.track.setEnabled(count > 1)
            self.notice.setText(tr(f'{path.name} / аудиодорожек: {count}') + (tr(' / можно выбрать другую') if count > 1 else ''))
        except Exception as error:
            self.notice.setText(tr(str(error)))

    def start_job(self):
        if self.worker is not None:
            return
        if self.live_window and self.live_window.worker:
            QMessageBox.warning(self, tr('Идёт прямой эфир'), tr('Сначала остановите живую расшифровку'))
            return
        try:
            source = self.source.text().strip().strip('"')
            if self.is_youtube:
                source = normalize_video_url(source)
            else:
                self.inspect_source()
                if not self.track.count() or not Path(source).is_file():
                    raise ValueError(tr('Выберите доступный медиафайл с аудиодорожкой'))
            if not self.output.text().strip():
                raise ValueError(tr('Выберите папку результатов'))
            job = Job(source, Path(self.output.text().strip()), self.is_youtube,
                      self.track.currentData() or 1, self.model.currentData(), self.format.currentData(),
                      timestamps=self.timestamps.isChecked())
            self.result = None
            self.outcome = None
            self.preview.clear()
            self.details.clear()
            self.details.hide()
            self.retry.hide()
            self.cancel.show()
            self.cancel.setEnabled(True)
            self.start.setEnabled(False)
            self.new_button.setEnabled(False)
            self.processing_title.setText(tr('Ваша запись становится текстом'))
            self.update_progress(-1)
            self.set_status(tr('Подготовка обработки'))
            self.navigate(2)
            self.wave.start()
            self.worker = Worker(job, self)
            self.worker.status.connect(self.set_status)
            self.worker.progress.connect(self.update_progress)
            self.worker.completed.connect(self.completed)
            self.worker.failed.connect(self.failed)
            self.worker.cancelled.connect(self.cancelled)
            self.worker.finished.connect(self.finished)
            self.worker.start()
        except Exception as error:
            QMessageBox.warning(self, tr('Проверьте параметры'), tr(str(error)))

    @Slot(str)
    def set_status(self, message):
        self.details.appendPlainText(tr(message))
        if message.startswith(('YouTube:', 'VK Видео:', 'Rutube:', 'Twitch:', 'VK Видео Live:')):
            return
        self.status.setText(tr(message))
        stage = 3 if 'Сохранение' in message else 2 if 'модели' in message else 1 if 'аудиодорожки' in message else 0
        for number, widget in enumerate(self.stage_labels):
            widget.setProperty('active', number == stage)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    @Slot(float)
    def update_progress(self, fraction):
        if fraction < 0:
            self.progress.setRange(0, 0)
            self.percent.setText(tr('Подготавливаем запись…'))
        else:
            self.progress.setRange(0, 100)
            value = int(fraction * 100)
            self.progress.setValue(value)
            self.percent.setText(tr(f'{value}% текущего этапа'))

    @Slot(object)
    def completed(self, result):
        self.result = result
        self.outcome = 'completed'
        self.wave.stop()
        self.preview.setPlainText(result.text)
        self.result_title.setText(result.title)
        self.open_txt.setVisible(result.txt is not None)
        self.open_md.setVisible(result.markdown is not None)
        self.open_folder.setEnabled(result.txt is not None or result.markdown is not None)
        self.result_timestamps.setChecked(self.timestamps.isChecked())
        self.result_timestamps.setEnabled(result.segments is not None)
        self.copy_reset.stop()
        self.copy.setToolTip(tr('Копировать всю расшифровку в буфер обмена'))
        self.copy.setEnabled(True)
        self.share.setEnabled(result.txt is not None or result.markdown is not None)
        self.navigate(3)

    @Slot(str)
    def failed(self, message):
        self.outcome = 'failed'
        self.wave.stop()
        self.processing_title.setText(tr('Не удалось завершить расшифровку'))
        self.status.setText(tr(message.split('\n\n', 1)[0]))
        self.details.appendPlainText(tr(message))
        self.percent.setText(tr('Проверьте источник и попробуйте ещё раз'))
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

    @Slot()
    def cancelled(self):
        self.outcome = 'cancelled'
        self.status.setText(tr('Обработка отменена'))
        self.notice.setText(tr('Обработка отменена, можно выбрать другую запись'))

    @Slot()
    def finished(self):
        self.wave.stop()
        self.start.setEnabled(True)
        self.cancel.setEnabled(False)
        self.new_button.setEnabled(True)
        self.worker.deleteLater()
        self.worker = None
        if self.outcome == 'cancelled':
            self.navigate(1)
        elif self.outcome == 'failed':
            self.cancel.hide()
            self.retry.show()
        if self.close_when_finished:
            self.close()

    def cancel_job(self):
        if self.worker:
            self.worker.requestInterruption()
            self.cancel.setEnabled(False)
            self.status.setText(tr('Останавливаем обработку, завершаем текущий шаг'))

    def copy_text(self):
        QApplication.clipboard().setText(self.preview.toPlainText())
        self.copy.setToolTip(tr('Скопировано'))
        self.copy_reset.start(1800)

    def open_result_folder(self):
        if self.result:
            path = self.result.markdown or self.result.txt
            self.open_path(path.parent)

    def open_path(self, path):
        if path and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            QMessageBox.warning(self, tr('Открытие файла'), tr(f'Не удалось открыть: {path}'))

    def dragEnterEvent(self, event):
        if self.worker is None and not (self.live_window and self.live_window.worker) and (event.mimeData().hasUrls() or event.mimeData().hasText()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if self.worker is not None or (self.live_window and self.live_window.worker):
            return
        urls = event.mimeData().urls()
        local = bool(urls and urls[0].isLocalFile())
        self.select_source(not local)
        self.source.setText(urls[0].toLocalFile() if local else urls[0].toString() if urls else event.mimeData().text().strip())
        if local:
            self.inspect_source()
        event.acceptProposedAction()

    def closeEvent(self, event):
        if self.live_window and self.live_window.worker:
            self.close_when_finished = True
            self.live_window.stop_session()
            if self.worker:
                self.cancel_job()
            event.ignore()
            return
        if self.worker is not None:
            self.close_when_finished = True
            self.cancel_job()
            event.ignore()
        else:
            if self.live_window and self.live_window.transcript_window:
                self.live_window.transcript_window.close()
            event.accept()

    def open_live(self):
        if self.worker:
            return
        if self.live_window is None:
            from src.live_gui import LivePage
            self.live_window = LivePage(self)
            self.live_window.session_finished.connect(self.live_finished)
            self.pages.addWidget(self.live_window)
        self.navigate(4)

    def live_finished(self):
        if self.close_when_finished:
            self.close()

