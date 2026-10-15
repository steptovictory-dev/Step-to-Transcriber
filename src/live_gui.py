"""Embedded live-transcription page using the application's copper theme."""

import logging
from pathlib import Path

from PySide6.QtCore import QEvent, QThread, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QSizePolicy, QVBoxLayout, QWidget,
)

from src.gui import button, label
from src.live import LiveJob, output_devices, run_live, timestamp
from src.theme import STYLE


class LiveWorker(QThread):
    status = Signal(str)
    paragraph = Signal(float, str)
    meter = Signal(float, float)
    saved = Signal(object)
    failed = Signal(str)

    def __init__(self, job, parent=None):
        super().__init__(parent)
        self.job = job
        self.requested_device = job.device

    def run(self):
        try:
            run_live(self.job, self.isInterruptionRequested, self.status.emit,
                     self.paragraph.emit, self.meter.emit, self.saved.emit,
                     selection=lambda: self.requested_device)
        except Exception as error:
            logging.exception('Live session failed')
            self.failed.emit(str(error))


class TranscriptWindow(QWidget):
    """Independent text view controlling the existing live session."""

    def __init__(self, live):
        super().__init__(None, Qt.WindowType.Window)
        self.live = live
        self.setObjectName('shell')
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowTitle('Текст эфира / Step to Transcriber')
        self.setWindowIcon(live.host.windowIcon())
        self.setStyleSheet(STYLE)
        self.resize(900, 620)
        self.setMinimumSize(760, 360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        self.preview = QPlainTextEdit()
        self.preview.setObjectName('transcript')
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText('Здесь появится текст эфира')
        self.preview.setPlainText(live.preview.toPlainText())
        layout.addWidget(self.preview, 1)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.start = button('Начать расшифровку', self.start_session, primary=True)
        self.stop = button('Остановить', live.stop.click)
        self.stop.setObjectName('exit')
        self.timestamps = button('Добавить таймкоды', live.timestamps.click)
        self.timestamps.setCheckable(True)
        self.timestamps.setChecked(live.timestamps.isChecked())
        self.timestamps.setToolTip(live.timestamps.toolTip())
        self.copy = button('Копировать текст', live.copy_text)
        actions.addWidget(self.start)
        actions.addWidget(self.stop)
        actions.addStretch()
        actions.addWidget(self.timestamps)
        actions.addWidget(self.copy)
        layout.addLayout(actions)
        live.preview.document().contentsChange.connect(self.sync_text_change)
        live.start.installEventFilter(self)
        live.stop.installEventFilter(self)
        live.timestamps.installEventFilter(self)
        live.timestamps.toggled.connect(self.timestamps.setChecked)
        self.sync_controls()

    def start_session(self):
        self.live.start.click()
        if self.live.worker is None:
            self.show_settings()

    def show_settings(self):
        self.live.host.open_live()
        if self.live.host.isMinimized():
            self.live.host.showNormal()
        else:
            self.live.host.show()
        self.live.host.raise_()
        self.live.host.activateWindow()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.EnabledChange:
            self.sync_controls()
        return super().eventFilter(watched, event)

    def sync_controls(self):
        self.start.setEnabled(self.live.start.isEnabled())
        self.stop.setEnabled(self.live.stop.isEnabled())
        self.timestamps.setEnabled(self.live.timestamps.isEnabled())

    def sync_text_change(self, position, removed, added):
        scrollbar = self.preview.verticalScrollBar()
        previous = scrollbar.value()
        follow = previous >= scrollbar.maximum() - 5
        source = QTextCursor(self.live.preview.document())
        source.setPosition(position)
        source.setPosition(min(position + added, source.document().characterCount() - 1),
                           QTextCursor.MoveMode.KeepAnchor)
        target = QTextCursor(self.preview.document())
        target.setPosition(min(position, target.document().characterCount() - 1))
        target.setPosition(min(position + removed, target.document().characterCount() - 1),
                           QTextCursor.MoveMode.KeepAnchor)
        target.removeSelectedText()
        target.insertFragment(source.selection())
        scrollbar.setValue(scrollbar.maximum() if follow else previous)


class LivePage(QWidget):
    session_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.host = parent
        self.worker = None
        self.transcript_window = None
        self.paths = []
        self.error = False
        self.session_timestamps = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(36, 14, 36, 14)
        outer.setSpacing(18)
        title = QHBoxLayout()
        title.setSpacing(12)
        self.back = button('←  К выбору источника', self.host.go_home)
        title.addWidget(self.back)
        title.addStretch()
        self.detach = button('Открыть в отдельном окне', self.open_transcript_window)
        title.addWidget(self.detach)

        columns = QGridLayout()
        columns.setHorizontalSpacing(24)
        columns.setVerticalSpacing(18)
        columns.setColumnStretch(0, 1)
        columns.setRowStretch(1, 1)
        columns.addLayout(title, 0, 0)
        columns.addWidget(label('ПРЯМОЙ ЭФИР', 'liveBadge'), 0, 1, Qt.AlignmentFlag.AlignRight)
        words = QVBoxLayout()
        words.setSpacing(12)

        self.preview = QPlainTextEdit()
        self.preview.setObjectName('transcript')
        self.preview.setReadOnly(True)
        self.preview.setMinimumWidth(0)
        self.preview.setMinimumHeight(180)
        empty_layout = QVBoxLayout(self.preview.viewport())
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.addStretch()
        self.empty_state = QWidget()
        self.empty_state.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.empty_state.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        empty_text = QVBoxLayout(self.empty_state)
        empty_text.setContentsMargins(0, 0, 0, 0)
        empty_text.setSpacing(14)
        empty_title = label('Живой эфир становится текстом', 'liveEmptyTitle')
        empty_hint = label('Запустите эфир и нажмите «Начать расшифровку»,\n'
                           'чтобы увидеть расшифровку', 'small')
        for item in (empty_title, empty_hint):
            item.setWordWrap(True)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_text.addWidget(item)
        empty_layout.addWidget(self.empty_state)
        empty_layout.addStretch()
        self.preview.textChanged.connect(
            lambda: self.empty_state.setVisible(self.preview.document().isEmpty()))
        words.addWidget(self.preview, 1)
        self.files = label('', 'small')
        self.files.setWordWrap(True)
        self.files.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.files.setMinimumWidth(0)
        self.files.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        words.addWidget(self.files)
        self.files.hide()
        text_actions = QHBoxLayout()
        text_actions.setSpacing(12)
        self.folder = button('Открыть папку', self.open_folder)
        self.folder.setEnabled(False)
        self.copy = button('Копировать текст', self.copy_text)
        text_actions.addWidget(self.folder)
        text_actions.addStretch()
        self.timestamps = button('Добавить таймкоды', lambda: None)
        self.timestamps.setCheckable(True)
        self.timestamps.setToolTip('Таймкоды в окне, копируемом тексте и файлах следующего сеанса')
        text_actions.addWidget(self.timestamps)
        text_actions.addStretch()
        text_actions.addWidget(self.copy)
        words.addLayout(text_actions)
        columns.addLayout(words, 1, 0)

        panel = QFrame()
        panel.setObjectName('panel')
        panel.setFixedWidth(440)
        settings = QVBoxLayout(panel)
        panel.setStyleSheet('QComboBox { padding: 7px 24px 7px 10px; } '
                            'QLineEdit { padding: 9px 10px; } '
                            'QPushButton { padding: 9px 12px; }')
        settings.setContentsMargins(20, 16, 20, 16)
        settings.setSpacing(7)
        settings.addWidget(label('НАСТРОЙКИ ЭФИРА', 'eyebrow'))
        device_group = QVBoxLayout()
        device_group.setSpacing(6)
        device_group.addWidget(label('Звук компьютера', 'small'))
        device_row = QHBoxLayout()
        device_row.setSpacing(10)
        self.device = QComboBox()
        self.device.currentIndexChanged.connect(self.device_changed)
        self.device.setMinimumWidth(0)
        self.device.setMinimumContentsLength(10)
        self.device.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.refresh = button('Обновить', self.refresh_devices)
        device_row.addWidget(self.device, 1)
        device_row.addWidget(self.refresh)
        device_group.addLayout(device_row)
        settings.addLayout(device_group)

        options = QHBoxLayout()
        options.setSpacing(12)
        language_group = QVBoxLayout()
        language_group.setSpacing(6)
        language_group.addWidget(label('Язык речи', 'small'))
        self.language = QComboBox()
        for text, value in (('Автоматически', None), ('Русский', 'ru'), ('English', 'en')):
            self.language.addItem(text, value)
        language_group.addWidget(self.language)
        format_group = QVBoxLayout()
        format_group.setSpacing(6)
        format_group.addWidget(label('Формат файла', 'small'))
        self.formats = QComboBox()
        for text, value in (('Markdown (.md)', ('md',)), ('Текст (.txt)', ('txt',)),
                            ('MD + TXT', ('md', 'txt'))):
            self.formats.addItem(text, value)
        format_group.addWidget(self.formats)
        options.addLayout(language_group, 1)
        options.addLayout(format_group, 1)
        settings.addLayout(options)

        saving = QHBoxLayout()
        saving.setSpacing(10)
        self.autosave = button('Автосохранение', lambda: None)
        self.no_save = button('Не сохранять', lambda: None)
        self.saving_mode = QButtonGroup(self)
        for control in (self.autosave, self.no_save):
            control.setCheckable(True)
            self.saving_mode.addButton(control)
            saving.addWidget(control, 1)
        self.autosave.setChecked(True)
        self.autosave.toggled.connect(self.update_saving_controls)
        settings.addLayout(saving)
        output_group = QVBoxLayout()
        output_group.setSpacing(6)
        output_group.addWidget(label('Папка результатов', 'small'))
        output_row = QHBoxLayout()
        output_row.setSpacing(10)
        self.output = QLineEdit(self.host.output_directory())
        self.output.textChanged.connect(self.host.remember_output_directory)
        self.output.setMinimumWidth(0)
        self.browse = button('Изменить', self.choose_output)
        output_row.addWidget(self.output, 1)
        output_row.addWidget(self.browse)
        output_group.addLayout(output_row)
        settings.addLayout(output_group)
        activity_title = QHBoxLayout()
        activity_title.setSpacing(12)
        activity_title.addWidget(label('УРОВЕНЬ ЗВУКА', 'eyebrow'))
        activity_title.addStretch()
        self.backlog = label('Ожидание начала', 'small')
        activity_title.addWidget(self.backlog)
        settings.addLayout(activity_title)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setValue(0)
        self.level.setTextVisible(False)
        settings.addWidget(self.level)
        self.status = label('Подготовка списка устройств', 'small')
        self.status.setWordWrap(True)
        self.status.setMinimumWidth(0)
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        settings.addWidget(self.status)
        description = label('Весь звук выбранного выхода, включая уведомления\n'
                            'Модель turbo / локальная обработка', 'small')
        description.setWordWrap(True)
        settings.addWidget(description)
        settings.addStretch(1)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.start = button('Начать расшифровку', self.start_session, primary=True)
        self.stop = button('Остановить', self.stop_session)
        self.stop.setObjectName('exit')
        self.stop.setToolTip('Остановить захват и сохранить оставшийся текст')
        self.stop.setEnabled(False)
        actions.addWidget(self.start, 3)
        actions.addWidget(self.stop, 2)
        settings.addLayout(actions)
        columns.addWidget(panel, 1, 1)
        outer.addLayout(columns, 1)

        self.level_timer = QTimer(self)
        self.level_timer.setInterval(250)
        self.level_timer.timeout.connect(self.update_meter)
        self.current_level = 0.0
        self.current_backlog = 0.0
        self.level_updated = 0.0
        self.media_devices = QMediaDevices(self)
        self.media_devices.audioOutputsChanged.connect(self.windows_device_changed)
        QTimer.singleShot(0, self.refresh_devices)

    def open_transcript_window(self):
        if self.transcript_window is None:
            self.transcript_window = TranscriptWindow(self)
        self.transcript_window.show()
        if self.transcript_window.isMinimized():
            self.transcript_window.showNormal()
        self.transcript_window.raise_()
        self.transcript_window.activateWindow()

    def refresh_devices(self):
        if self.worker:
            return
        previous = self.device.currentData()
        self.device.blockSignals(True)
        self.device.clear()
        default_name = QMediaDevices.defaultAudioOutput().description() or 'выход не выбран'
        self.device.addItem('Windows по умолчанию: ' + default_name,
                            {'name': 'Устройство Windows по умолчанию', 'automatic': True,
                             'endpoint': bytes(QMediaDevices.defaultAudioOutput().id()).hex()})
        try:
            devices = output_devices()
            selected = 0
            for index, device in enumerate(devices, start=1):
                name = device['name'].removesuffix(' [Loopback]')
                self.device.addItem(name + (' (Windows по умолчанию)' if device['default'] else ''), device)
            if previous and not previous.get('automatic'):
                selected = next((index for index, device in enumerate(devices, start=1)
                                 if device['name'] == previous['name']), selected)
            self.device.setCurrentIndex(selected)
            self.device.setToolTip(self.device.currentText())
            self.start.setEnabled(bool(devices))
            self.status.setText('Включите звук на выбранном устройстве и нажмите «Начать расшифровку»'
                                if devices else 'Windows не обнаружил выход звука. Подключите наушники или колонки и нажмите «Обновить»')
        except Exception as error:
            self.start.setEnabled(False)
            self.status.setText(str(error))
        finally:
            self.device.blockSignals(False)

    def device_changed(self):
        if self.worker and self.device.currentData():
            self.worker.requested_device = self.device.currentData()
            self.status.setText('Переключаем захват на выбранное устройство')

    def windows_device_changed(self):
        if self.worker:
            selected = self.device.currentData()
            if selected and selected.get('automatic'):
                updated = dict(selected, endpoint=bytes(QMediaDevices.defaultAudioOutput().id()).hex())
                self.device.setItemData(self.device.currentIndex(), updated)
                self.device.setItemText(self.device.currentIndex(), 'Windows по умолчанию: ' +
                                        QMediaDevices.defaultAudioOutput().description())
                self.worker.requested_device = updated
        else:
            self.refresh_devices()

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, 'Папка живых расшифровок', self.output.text())
        if path:
            self.output.setText(path)

    def start_session(self):
        if self.worker or not self.device.currentData():
            return
        if self.host.worker:
            self.status.setText('Дождитесь окончания расшифровки записи')
            return
        if self.autosave.isChecked() and not self.output.text().strip():
            self.status.setText('Выберите папку результатов')
            return
        self.preview.clear()
        self.paths = []
        self.files.clear()
        self.files.hide()
        self.folder.setEnabled(False)
        self.error = False
        self.session_timestamps = self.timestamps.isChecked()
        self.set_running(True)
        job = LiveJob(self.device.currentData(), Path(self.output.text().strip()),
                      self.formats.currentData(), self.language.currentData(), self.session_timestamps,
                      autosave=self.autosave.isChecked())
        self.worker = LiveWorker(job, self)
        self.worker.status.connect(self.set_status)
        self.worker.paragraph.connect(self.add_paragraph)
        self.worker.meter.connect(self.receive_meter)
        self.worker.saved.connect(self.saved_paths)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finished)
        self.status.setText('Подготавливаем модель')
        self.level_timer.start()
        self.worker.start()

    def set_running(self, running):
        for widget in (self.back, self.refresh, self.language, self.formats, self.timestamps, self.autosave, self.no_save):
            widget.setEnabled(not running)
        self.update_saving_controls()
        self.start.setEnabled(not running and self.device.count() > 0)
        self.stop.setEnabled(running)

    def update_saving_controls(self):
        enabled = self.autosave.isChecked() and self.back.isEnabled()
        for control in (self.formats, self.output, self.browse):
            control.setEnabled(enabled)

    def set_status(self, text):
        if self.stop.isEnabled():
            self.status.setText(text)

    def add_paragraph(self, seconds, text):
        scrollbar = self.preview.verticalScrollBar()
        follow = scrollbar.value() >= scrollbar.maximum() - 5
        previous = scrollbar.value()
        prefix = f'[{timestamp(seconds)}] ' if self.session_timestamps else ''
        text = ' '.join(text.split())
        if not text:
            return
        previous_block = self.preview.document().lastBlock().text()
        note = text.startswith('[') and text.endswith(']')
        previous_note = previous_block.startswith('[') and previous_block.endswith(']')
        if previous_block and not self.session_timestamps and not note and not previous_note:
            cursor = QTextCursor(self.preview.document())
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(' ' + text)
        else:
            self.preview.appendPlainText(prefix + text)
        scrollbar.setValue(scrollbar.maximum() if follow else previous)

    def saved_paths(self, paths):
        self.paths = paths
        self.files.setVisible(bool(paths))
        self.files.setText('Файлы сеанса: ' + '\n'.join(str(path) for path in paths))
        self.folder.setEnabled(bool(paths))

    def receive_meter(self, level, backlog):
        import time
        self.current_level = level
        self.current_backlog = backlog
        self.level_updated = time.monotonic()

    def update_meter(self):
        import time
        level = self.current_level if time.monotonic() - self.level_updated < 1.0 else 0.0
        self.level.setValue(min(100, int(level * 400)))
        self.backlog.setText(f'Очередь звука: {self.current_backlog:.0f} с')

    def failed(self, text):
        self.error = True
        self.status.setText(text + ('\nУже полученный текст сохранён в файлах сеанса' if self.paths else ''))
        if self.transcript_window and self.transcript_window.isVisible():
            self.transcript_window.show_settings()

    def stop_session(self):
        if self.worker:
            self.worker.requestInterruption()
            self.stop.setEnabled(False)
            self.status.setText('Останавливаем захват и распознаём оставшийся звук')

    def finished(self):
        self.level_timer.stop()
        self.level.setValue(0)
        self.backlog.setText('Сеанс остановлен')
        self.worker.deleteLater()
        self.worker = None
        self.set_running(False)
        if not self.error:
            self.status.setText('Сеанс завершён, расшифровка сохранена' if self.paths else
                                'Сеанс завершён, текст доступен для копирования' if self.preview.toPlainText() else
                                'Сеанс остановлен до начала захвата')
        self.session_finished.emit()

    def copy_text(self):
        QApplication.clipboard().setText(self.preview.toPlainText())

    def open_folder(self):
        if self.paths:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths[0].parent.resolve())))














