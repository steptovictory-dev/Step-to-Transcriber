import logging
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, QThread, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from src.audio import get_audio_track_count
from src.pipeline import Job, run_job
from src.theme import STYLE
from src.widgets import SourceCard, Waveform, line_icon
from src.youtube import normalize_video_url


ROOT = Path(__file__).resolve().parents[2]
GITHUB = 'https://github.com/steptovictory-dev'
MEDIA_FILTER = 'Медиа (*.mp4 *.mkv *.mov *.webm *.mp3 *.wav *.m4a *.flac *.ogg *.opus)'
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
        self.worker = None
        self.live_window = None
        self.result = None
        self.is_youtube = False
        self.close_when_finished = False
        self.outcome = None
        self.setWindowTitle('Step to Transcriber')
        self.setWindowIcon(QIcon(str(ROOT / 'project' / 'assets' / 'step-to-transcriber.ico')))
        self.resize(1240, 760)
        self.setMinimumSize(1060, 680)
        self.fullscreen_shortcut = QShortcut(QKeySequence('F11'), self)
        self.fullscreen_shortcut.setAutoRepeat(False)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)
        shell = QWidget()
        shell.setObjectName('shell')
        self.setCentralWidget(shell)
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName('header')
        row = QHBoxLayout(header)
        row.setContentsMargins(36, 20, 36, 18)
        brand = label('Step to Transcriber', 'brand')
        row.addWidget(brand)
        row.addStretch()
        row.addWidget(label('LOCAL AUDIO STUDIO', 'eyebrow'))
        outer.addWidget(header)

        self.route = QWidget()
        route = QHBoxLayout(self.route)
        route.setSpacing(12)
        route.setContentsMargins(40, 19, 40, 10)
        self.steps = []
        for index, text in enumerate(('Источник', 'Подготовка', 'Обработка', 'Результат')):
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
        footer_row.addWidget(label('Разработчик: Steptovictory', 'small'))
        footer_row.addStretch()
        github = button('GitHub / steptovictory-dev', lambda: QDesktopServices.openUrl(QUrl(GITHUB)))
        github.setObjectName('quiet')
        github.setToolTip(GITHUB)
        footer_row.addWidget(github)
        outer.addWidget(footer)
        self.navigate(0, animate=False)

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
        layout.addWidget(label('АУДИО / ВИДЕО / ЭФИР', 'eyebrow'))
        layout.addWidget(label('Превращаем звук в слова', 'heading'))
        layout.addWidget(label('Выберите файл, ссылку на видео или звук прямого эфира', 'muted'))
        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.file_card = SourceCard('01', 'Файл на компьютере', 'Выберите аудио или видео\nили перетащите файл в окно', 'file')
        self.url_card = SourceCard('02', 'Ссылка на видео', 'YouTube, VK Видео, Rutube\nTwitch, VK Видео Live: записи эфиров', 'link')
        self.live_card = SourceCard('03', 'Прямой эфир', 'Вебинары и стримы\nЗвук компьютера без ссылки', 'live')
        self.live_card.setToolTip('Расшифровка звука компьютера в этом окне')
        self.file_card.clicked.connect(lambda: self.select_source(False))
        self.url_card.clicked.connect(lambda: self.select_source(True))
        self.live_card.clicked.connect(self.open_live)
        cards.addWidget(self.file_card, 1)
        cards.addWidget(self.url_card, 1)
        cards.addWidget(self.live_card, 1)
        layout.addLayout(cards)
        layout.addWidget(label('Обработка на вашем компьютере / язык определяется автоматически', 'small'))
        layout.addStretch(2)
        return page

    def build_setup(self):
        page, layout = self.page()
        top = QHBoxLayout()
        back = button('‹  Выбор источника', self.go_home)
        back.setObjectName('quiet')
        top.addWidget(back)
        top.addStretch()
        self.source_badge = label('ФАЙЛ', 'badge')
        top.addWidget(self.source_badge)
        layout.addLayout(top)
        layout.addWidget(label('Подготовим вашу запись', 'heading'))
        self.setup_hint = label('', 'muted')
        layout.addWidget(self.setup_hint)
        self.settings = QFrame()
        self.settings.setObjectName('panel')
        panel = QVBoxLayout(self.settings)
        panel.setContentsMargins(24, 22, 24, 22)
        panel.setSpacing(17)
        self.input_label = label('ИСХОДНЫЙ ФАЙЛ', 'eyebrow')
        panel.addWidget(self.input_label)
        source_row = QHBoxLayout()
        self.source = QLineEdit()
        self.source.editingFinished.connect(self.inspect_source)
        self.browse = button('Выбрать файл', self.choose_file)
        source_row.addWidget(self.source, 1)
        source_row.addWidget(self.browse)
        panel.addLayout(source_row)
        self.notice = label('Выберите файл для расшифровки', 'small')
        self.notice.setWordWrap(True)
        panel.addWidget(self.notice)
        form = QFormLayout()
        form.setVerticalSpacing(14)
        self.format = QComboBox()
        self.format.addItem('Markdown (.md)', ('md',))
        self.format.addItem('Обычный текст (.txt)', ('txt',))
        self.format.addItem('Markdown + текст (.md и .txt)', ('md', 'txt'))
        form.addRow('Формат результата', self.format)
        self.track = QComboBox()
        self.track.addItem('Дорожка 1 (автоматически)', 1)
        self.track.setEnabled(False)
        self.track_label = label('Аудиодорожка')
        form.addRow(self.track_label, self.track)
        panel.addLayout(form)
        self.more = button('Дополнительные настройки  +', self.toggle_advanced)
        self.more.setObjectName('quiet')
        panel.addWidget(self.more, alignment=Qt.AlignmentFlag.AlignLeft)
        self.advanced = QWidget()
        advanced_form = QFormLayout(self.advanced)
        advanced_form.setContentsMargins(0, 0, 0, 0)
        self.timestamps = QCheckBox('Включить таймкоды')
        self.timestamps.setChecked(True)
        self.timestamps.setToolTip('Таймкоды абзацев в результате, копируемом тексте и файлах MD / TXT')
        advanced_form.addRow('Таймкоды', self.timestamps)
        self.model = QComboBox()
        self.model.addItem('turbo (рекомендуется)', 'turbo')
        self.model.addItem('large-v3 (экспериментальный режим)', 'large-v3')
        advanced_form.addRow('Модель', self.model)
        out_row = QHBoxLayout()
        self.output = QLineEdit(self.output_directory())
        self.output.textChanged.connect(self.remember_output_directory)
        out_row.addWidget(self.output, 1)
        out_row.addWidget(button('Изменить', self.choose_output))
        advanced_form.addRow('Папка результатов', out_row)
        panel.addWidget(self.advanced)
        self.advanced.hide()
        layout.addWidget(self.settings)
        layout.addStretch()
        bottom = QHBoxLayout()
        bottom.addWidget(label('Всё настроено для начала', 'small'))
        bottom.addStretch()
        self.start = button('Расшифровать  →', self.start_job, primary=True)
        bottom.addWidget(self.start)
        layout.addLayout(bottom)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet('QScrollArea, QScrollArea > QWidget > QWidget { background: #22211f; }')
        scroll.setWidget(page)
        return scroll

    def build_processing(self):
        page, layout = self.page()
        layout.addStretch()
        eyebrow = label('СЛУШАЕМ / РАСПОЗНАЁМ / СОХРАНЯЕМ', 'eyebrow')
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(eyebrow)
        self.processing_title = label('Ваша запись становится текстом', 'heading')
        self.processing_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.processing_title)
        self.wave = Waveform()
        layout.addWidget(self.wave)
        self.status = label('Подготовка обработки', 'muted')
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.percent = label('Подготавливаем запись…', 'small')
        self.percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent)
        stages = QHBoxLayout()
        self.stage_labels = []
        for text in ('Источник', 'Аудио', 'Распознавание', 'Сохранение'):
            item = label(text, 'step')
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stage_labels.append(item)
            stages.addWidget(item)
        layout.addLayout(stages)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(90)
        self.details.hide()
        self.details_button = button('Подробности', lambda: self.details.setVisible(self.details.isHidden()))
        self.details_button.setObjectName('quiet')
        layout.addWidget(self.details_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.details)
        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel = button('Отменить обработку', self.cancel_job)
        self.cancel.setEnabled(False)
        self.retry = button('Вернуться к записи', lambda: self.navigate(1))
        self.retry.hide()
        actions.addWidget(self.cancel)
        actions.addWidget(self.retry)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def build_result(self):
        page, layout = self.page()
        layout.addWidget(label('ГОТОВО', 'eyebrow'))
        layout.addWidget(label('Расшифровка закончена', 'heading'))
        self.result_title = label('', 'muted')
        self.result_title.setWordWrap(True)
        layout.addWidget(self.result_title)
        toolbar = QHBoxLayout()
        self.saved_formats = label('', 'small')
        toolbar.addWidget(self.saved_formats)
        toolbar.addStretch()
        self.copy = button('Копировать текст', self.copy_text)
        self.copy.setIcon(line_icon('copy', 20))
        self.copy.setEnabled(False)
        self.copy_reset = QTimer(self)
        self.copy_reset.setSingleShot(True)
        self.copy_reset.timeout.connect(lambda: self.copy.setText('Копировать текст'))
        toolbar.addWidget(self.copy)
        layout.addLayout(toolbar)
        self.preview = QPlainTextEdit()
        self.preview.setObjectName('transcript')
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        files = QHBoxLayout()
        self.open_folder = button('Открыть папку с результатом  ↗', self.open_result_folder)
        self.open_txt = button('Открыть TXT', lambda: self.open_path(self.result.txt))
        self.open_md = button('Открыть Markdown', lambda: self.open_path(self.result.markdown))
        files.addWidget(self.open_folder)
        files.addStretch()
        files.addWidget(self.open_md)
        files.addWidget(self.open_txt)
        layout.addLayout(files)
        bottom = QHBoxLayout()
        self.exit_button = button('Выход из приложения', self.close)
        self.exit_button.setObjectName('exit')
        self.new_button = button('Ещё одна расшифровка  →', self.go_home, primary=True)
        bottom.addWidget(self.exit_button)
        bottom.addStretch()
        bottom.addWidget(self.new_button)
        layout.addLayout(bottom)
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
        self.source.setPlaceholderText('Полная ссылка на видео или запись эфира' if youtube else 'Путь к аудио или видео')
        self.browse.setVisible(not youtube)
        self.track.setVisible(not youtube)
        self.track_label.setVisible(not youtube)
        self.track.clear()
        self.track.addItem('Дорожка 1 (автоматически)', 1)
        self.track.setEnabled(False)
        self.source_badge.setText('ВИДЕО ПО ССЫЛКЕ' if youtube else 'ЛОКАЛЬНЫЙ ФАЙЛ')
        self.input_label.setText('ССЫЛКА НА РОЛИК' if youtube else 'ИСХОДНЫЙ ФАЙЛ')
        self.setup_hint.setText('Видео и завершённые эфиры: запись загрузится автоматически' if youtube else 'Дорожка и язык выбраны автоматически, формат результата можно изменить')
        self.notice.setText('Ссылка на один доступный ролик, без прямых эфиров' if youtube else 'Выберите файл или перетащите его в окно')
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
        self.more.setText('Дополнительные настройки  +')
        self.copy_reset.stop()
        self.copy.setText('Копировать текст')
        self.copy.setEnabled(False)
        self.navigate(0)

    def toggle_advanced(self):
        visible = self.advanced.isHidden()
        self.advanced.setVisible(visible)
        self.more.setText('Скрыть настройки  −' if visible else 'Дополнительные настройки  +')

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Выбрать аудио или видео', str(ROOT / 'input'), MEDIA_FILTER)
        if path:
            self.source.setText(path)
            self.inspect_source()

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, 'Папка результатов', self.output.text())
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
                raise ValueError('Неподдерживаемый формат файла')
            count = get_audio_track_count(path)
            if count == 0:
                raise ValueError('В файле нет аудиодорожек')
            for number in range(1, count + 1):
                self.track.addItem(f'Дорожка {number}' + (' (автоматически)' if count == 1 else ''), number)
            if previous and previous <= count:
                self.track.setCurrentIndex(previous - 1)
            self.track.setEnabled(count > 1)
            self.notice.setText(f'{path.name} / аудиодорожек: {count}' + (' / можно выбрать другую' if count > 1 else ''))
        except Exception as error:
            self.notice.setText(str(error))

    def start_job(self):
        if self.worker is not None:
            return
        if self.live_window and self.live_window.worker:
            QMessageBox.warning(self, 'Идёт прямой эфир', 'Сначала остановите живую расшифровку')
            return
        try:
            source = self.source.text().strip().strip('"')
            if self.is_youtube:
                source = normalize_video_url(source)
            else:
                self.inspect_source()
                if not self.track.count() or not Path(source).is_file():
                    raise ValueError('Выберите доступный медиафайл с аудиодорожкой')
            if not self.output.text().strip():
                raise ValueError('Выберите папку результатов')
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
            self.processing_title.setText('Ваша запись становится текстом')
            self.update_progress(-1)
            self.set_status('Подготовка обработки')
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
            QMessageBox.warning(self, 'Проверьте параметры', str(error))

    @Slot(str)
    def set_status(self, message):
        self.details.appendPlainText(message)
        if message.startswith(('YouTube:', 'VK Видео:', 'Rutube:', 'Twitch:', 'VK Видео Live:')):
            return
        self.status.setText(message)
        stage = 3 if 'Сохранение' in message else 2 if 'модели' in message else 1 if 'аудиодорожки' in message else 0
        for number, widget in enumerate(self.stage_labels):
            widget.setProperty('active', number == stage)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    @Slot(float)
    def update_progress(self, fraction):
        if fraction < 0:
            self.progress.setRange(0, 0)
            self.percent.setText('Подготавливаем запись…')
        else:
            self.progress.setRange(0, 100)
            value = int(fraction * 100)
            self.progress.setValue(value)
            self.percent.setText(f'{value}% текущего этапа')

    @Slot(object)
    def completed(self, result):
        self.result = result
        self.outcome = 'completed'
        self.wave.stop()
        self.preview.setPlainText(result.text)
        self.result_title.setText(result.title)
        self.saved_formats.setText('Сохранено: ' + ' + '.join(name for name, path in (('Markdown', result.markdown), ('TXT', result.txt)) if path))
        self.open_txt.setVisible(result.txt is not None)
        self.open_md.setVisible(result.markdown is not None)
        self.copy.setEnabled(True)
        self.navigate(3)

    @Slot(str)
    def failed(self, message):
        self.outcome = 'failed'
        self.wave.stop()
        self.processing_title.setText('Не удалось завершить расшифровку')
        self.status.setText(message.split('\n\n', 1)[0])
        self.details.appendPlainText(message)
        self.percent.setText('Проверьте источник и попробуйте ещё раз')
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

    @Slot()
    def cancelled(self):
        self.outcome = 'cancelled'
        self.status.setText('Обработка отменена')
        self.notice.setText('Обработка отменена, можно выбрать другую запись')

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
            self.status.setText('Останавливаем обработку, завершаем текущий шаг')

    def copy_text(self):
        QApplication.clipboard().setText(self.preview.toPlainText())
        self.copy.setText('Скопировано')
        self.copy_reset.start(1800)

    def open_result_folder(self):
        if self.result:
            path = self.result.markdown or self.result.txt
            self.open_path(path.parent)

    def open_path(self, path):
        if path and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
            QMessageBox.warning(self, 'Открытие файла', f'Не удалось открыть: {path}')

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
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet('QScrollArea, QScrollArea > QWidget > QWidget { background: #22211f; }')
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(self.live_window)
            self.pages.addWidget(scroll)
        self.navigate(4)

    def live_finished(self):
        if self.close_when_finished:
            self.close()

