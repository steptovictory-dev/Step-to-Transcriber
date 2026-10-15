"""Interface translations, independent of the language spoken in recordings."""

import re

LANGUAGE = 'ru'

# Braced fields preserve paths, device names and numeric values verbatim
PAIRS = [
    ('Файл не найден: {path}', 'File not found: {path}'),
    ('Номер аудиодорожки должен быть не меньше 1.', 'Audio track number must be at least 1.'),
    ('В файле только {count} аудиодорожек, запрошена дорожка {track}.', 'The file has only {count} audio tracks; track {track} was requested.'),
    ('Выберите Markdown, TXT или оба формата', 'Choose Markdown, TXT or both formats'),
    ('Укажите полную ссылку https://www.youtube.com/watch?v=...', 'Enter the full URL https://www.youtube.com/watch?v=...'),
    ('Нужна ссылка на одно видео YouTube, а не канал или плейлист', 'Enter a link to a single YouTube video, rather than a channel or playlist'),
    ('Укажите полную ссылку https:// на запись: {services}', 'Enter a full https:// recording URL: {services}'),
    ('Для Twitch нужна ссылка на сохранённую запись twitch.tv/videos/..., а не текущий эфир или канал', 'For Twitch, use a saved recording URL twitch.tv/videos/... rather than a live stream or channel'),
    ('Для VK Видео Live нужна ссылка на завершённую запись /имя/record/..., а не текущий эфир или канал', 'For VK Video Live, use a past recording URL /name/record/... rather than a live stream or channel'),
    ('Нужна ссылка на отдельную запись: {services}, а не канал или плейлист', 'Enter a single recording URL: {services}, rather than a channel or playlist'),
    ('Загрузка отменена', 'Download cancelled'), ('Прямые эфиры не поддерживаются. Выберите завершённую запись', 'Live stream URLs are not supported. Choose a completed recording'),
    ('Сервис ещё обрабатывает завершённый эфир. Попробуйте позже', 'The service is still processing the recording. Try again later'),
    ('Видео недоступно', 'Video unavailable'), ('Поддерживается только одно видео', 'Only one video is supported'),
    ('Не удалось получить запись {service}', 'Could not retrieve the {service} recording'),
    ('Не удалось скачать видео {service}. Проверьте доступность ссылки и сети. Закрытые видео и материалы с требованием входа могут быть недоступны.', 'Could not download the {service} video. Check the link and your network connection. Private videos and content requiring sign-in may be unavailable.'),
    ('Не удалось скачать видео {service}. Проверьте доступность ссылки и сети. Закрытые видео и материалы с требованием входа могут быть недоступны. Если используете VPN, попробуйте отключить его или сменить маршрут.', 'Could not download the {service} video. Check the link and your network connection. Private videos and content requiring sign-in may be unavailable. If using a VPN, try disabling it or changing the route.'),
    ('Не установлен PyAudioWPatch. Установите зависимости из requirements.txt', 'PyAudioWPatch is missing. Install the dependencies from requirements.txt'),
    ('Устройство Windows по умолчанию недоступно', 'The default Windows audio device is unavailable'),
    ('Выбранное устройство отключено. Подключите его или выберите другой выход', 'The selected device is disconnected. Connect it or choose another output'),
    ('Не удалось подключиться к выходу звука Windows', 'Could not connect to the Windows audio output'),
    ('Захват звука прервался. Проверьте подключение аудиоустройства', 'Audio capture was interrupted. Check the audio device connection'),
    ('Распознавание отстало более чем на минуту. Захват остановлен, часть звука пропущена', 'Transcription fell behind by over a minute. Capture stopped and some audio was skipped'),
    ('Windows сообщил о потере аудиоданных. Захват остановлен, возможен пропуск звука', 'Windows reported audio data loss. Capture stopped and some audio may be missing'),
    ('Windows не обнаружил выход звука. Подключите наушники или колонки и нажмите «Обновить»', 'Windows found no audio output. Connect headphones or speakers and click “Refresh”'),
    ('Включите звук на выбранном устройстве и нажмите «Начать расшифровку»', 'Play audio on the selected device and click “Start transcription”'),
    ('Дождитесь окончания расшифровки записи', 'Wait for the recording transcription to finish'),
    ('Останавливаем обработку, завершаем текущий шаг', 'Cancelling processing, finishing the current step'),
    ('Открытие файла', 'Open file'), ('Не удалось открыть: {path}', 'Could not open: {path}'),
    ('Папка живых расшифровок', 'Live transcripts folder'),
    ('Переключаем захват на выбранное устройство', 'Switching capture to the selected device'),
    ('Медиа (*.mp4 *.mkv *.mov *.webm *.mp3 *.wav *.m4a *.flac *.ogg *.opus)', 'Media (*.mp4 *.mkv *.mov *.webm *.mp3 *.wav *.m4a *.flac *.ogg *.opus)'),
    ('Источник', 'Source'), ('Подготовка', 'Setup'), ('Обработка', 'Processing'), ('Результат', 'Result'),
    ('0{n}  Источник', '0{n}  Source'), ('0{n}  Подготовка', '0{n}  Setup'),
    ('0{n}  Обработка', '0{n}  Processing'), ('0{n}  Результат', '0{n}  Result'),
    ('Разработчик: Steptovictory', 'Developed by Steptovictory'),
    ('АУДИО / ВИДЕО / ЭФИР', 'AUDIO / VIDEO / LIVE'),
    ('Превращаем звук в слова', 'Turning sound into words'),
    ('Выберите файл, ссылку на видео или звук прямого эфира', 'Choose a file, a video link or live computer audio'),
    ('Файл на компьютере', 'Local file'), ('Ссылка на видео', 'Video link'), ('Прямой эфир', 'Live audio'),
    ('Выберите аудио или видео\nили перетащите файл в окно', 'Choose audio or video\nor drop a file into the window'),
    ('YouTube, VK Видео, Rutube\nTwitch, VK Видео Live: записи эфиров', 'YouTube, VK Video, Rutube\nTwitch, VK Video Live: recordings'),
    ('Вебинары и стримы\nЗвук компьютера без ссылки', 'Webinars and streams\nComputer audio, no link needed'),
    ('Расшифровка звука компьютера в этом окне', 'Transcribe computer audio in this window'),
    ('Обработка на вашем компьютере / язык определяется автоматически', 'Processed on your computer / speech language detected automatically'),
    ('{n}  /  ВЫБРАТЬ ИСТОЧНИК', '{n}  /  SELECT SOURCE'),
    ('VK Видео', 'VK Video'), ('Twitch: записи', 'Twitch: recordings'), ('VK Видео Live: записи', 'VK Video Live: recordings'),
    ('‹  Выбор источника', '‹  Choose source'), ('ФАЙЛ', 'FILE'), ('Подготовим вашу запись', 'Prepare your recording'),
    ('ИСХОДНЫЙ ФАЙЛ', 'SOURCE FILE'), ('Выбрать файл', 'Browse files'),
    ('Выберите файл для расшифровки', 'Choose a file to transcribe'),
    ('Обычный текст (.txt)', 'Plain text (.txt)'), ('Markdown + текст (.md и .txt)', 'Markdown + text (.md and .txt)'),
    ('Формат результата', 'Output format'), ('Дорожка 1 (автоматически)', 'Track 1 (automatic)'),
    ('Аудиодорожка', 'Audio track'), ('Дополнительные настройки  +', 'More settings  +'),
    ('Скрыть настройки  −', 'Hide settings  −'), ('Вкл', 'On'), ('Выкл', 'Off'), ('Таймкоды', 'Timestamps'),
    ('Таймкоды абзацев в результате, копируемом тексте и файлах MD / TXT', 'Paragraph timestamps in the result, copied text and MD / TXT files'),
    ('Выключить таймкоды', 'Disable timestamps'), ('Не добавлять таймкоды в текст и файлы результата', 'Omit timestamps from the result text and files'),
    ('turbo (рекомендуется)', 'turbo (recommended)'), ('large-v3 (экспериментальный режим)', 'large-v3 (experimental)'),
    ('Модель', 'Model'), ('Изменить', 'Change'), ('Папка результатов', 'Output folder'),
    ('Всё настроено для начала', 'Ready when you are'), ('Расшифровать  →', 'Transcribe  →'),
    ('СЛУШАЕМ / РАСПОЗНАЁМ / СОХРАНЯЕМ', 'LISTEN / TRANSCRIBE / SAVE'),
    ('Ваша запись становится текстом', 'Your recording becomes text'), ('Подготовка обработки', 'Preparing transcription'),
    ('Подготавливаем запись…', 'Preparing recording…'), ('Аудио', 'Audio'), ('Распознавание', 'Transcription'),
    ('Сохранение', 'Saving'), ('Подробности', 'Details'), ('Отменить обработку', 'Cancel transcription'),
    ('Вернуться к записи', 'Back to recording'), ('ГОТОВО', 'DONE'), ('Расшифровка закончена', 'Transcription complete'),
    ('Копировать текст', 'Copy text'), ('Открыть папку с результатом  ↗', 'Open output folder  ↗'),
    ('Открыть TXT', 'Open TXT'), ('Открыть Markdown', 'Open Markdown'), ('Выход из приложения', 'Exit application'),
    ('Ещё одна расшифровка  →', 'Transcribe another  →'),
    ('Полная ссылка на видео или запись эфира', 'Full link to a video or stream recording'), ('Путь к аудио или видео', 'Path to audio or video'),
    ('ВИДЕО ПО ССЫЛКЕ', 'VIDEO LINK'), ('ЛОКАЛЬНЫЙ ФАЙЛ', 'LOCAL FILE'), ('ССЫЛКА НА РОЛИК', 'VIDEO URL'),
    ('Видео и завершённые эфиры: запись загрузится автоматически', 'Videos and past streams: the recording downloads automatically'),
    ('Дорожка и язык выбраны автоматически, формат результата можно изменить', 'Track and speech language are automatic; choose your output format'),
    ('Ссылка на один доступный ролик, без прямых эфиров', 'Link to one available video or past stream'),
    ('Выберите файл или перетащите его в окно', 'Choose a file or drop it into the window'),
    ('Сначала завершите расшифровку', 'Complete a transcription first'), ('Файл результата недоступен', 'Output file is unavailable'),
    ('Выбрать аудио или видео', 'Choose audio or video'), ('Неподдерживаемый формат файла', 'Unsupported file format'),
    ('В файле нет аудиодорожек', 'The file contains no audio tracks'), ('Дорожка {n}', 'Track {n}'),
    (' (автоматически)', ' (automatic)'), ('Дорожка {n} (автоматически)', 'Track {n} (automatic)'),
    ('{file} / аудиодорожек: {count}', '{file} / audio tracks: {count}'),
    ('{file} / аудиодорожек: {count} / можно выбрать другую', '{file} / audio tracks: {count} / choose any track'),
    (' / можно выбрать другую', ' / choose any track'), ('Идёт прямой эфир', 'Live session in progress'),
    ('Сначала остановите живую расшифровку', 'Stop live transcription first'),
    ('Выберите доступный медиафайл с аудиодорожкой', 'Choose an available media file with an audio track'),
    ('Выберите папку результатов', 'Choose an output folder'), ('Проверьте параметры', 'Check your settings'),
    ('{value}% текущего этапа', '{value}% of current stage'),
    ('Не удалось завершить расшифровку', 'Transcription failed'), ('Проверьте источник и попробуйте ещё раз', 'Check the source and try again'),
    ('Обработка отменена', 'Transcription cancelled'), ('Обработка отменена, можно выбрать другую запись', 'Transcription cancelled; choose another recording'),
    ('Текст скопирован', 'Text copied'), ('Скопировано', 'Copied'), ('Отменяем обработку…', 'Cancelling transcription…'),
    ('Текст эфира / Step to Transcriber', 'Live transcript / Step to Transcriber'),
    ('Здесь появится текст эфира', 'Live transcript will appear here'), ('Начать расшифровку', 'Start transcription'),
    ('Остановить', 'Stop'), ('Добавить таймкоды', 'Add timestamps'), ('Поделиться', 'Share'),
    ('Открыть в отдельном окне', 'Open in separate window'), ('ПРЯМОЙ ЭФИР', 'LIVE AUDIO'),
    ('Живой эфир становится текстом', 'Live audio becomes text'),
    ('Запустите эфир и нажмите «Начать расшифровку»,\nчтобы увидеть расшифровку', 'Play a stream and click “Start transcription”\nto see the transcript'),
    ('Открыть папку', 'Open folder'), ('Таймкоды в окне, копируемом тексте и файлах следующего сеанса', 'Timestamps in the next session’s display, copied text and files'),
    ('Открыть папку с файлами текущего эфира', 'Open the current live session’s folder'),
    ('Включить таймкоды в тексте и файлах следующего сеанса', 'Enable timestamps in the next session’s text and files'),
    ('Поделиться файлом', 'Share file'), ('Поделиться TXT-снимком расшифровки: нажмите или перетащите в чат', 'Share a TXT snapshot: click or drag into a chat'),
    ('Копировать всю расшифровку в буфер обмена', 'Copy the entire transcript to the clipboard'),
    ('Открыть текст эфира в отдельном окне', 'Open the live transcript in a separate window'),
    ('Таймкоды включены. Нажмите, чтобы выключить для следующего сеанса', 'Timestamps enabled. Click to disable for the next session'),
    ('НАСТРОЙКИ ЭФИРА', 'LIVE SETTINGS'), ('Звук компьютера', 'Computer audio'), ('Обновить', 'Refresh'),
    ('Язык речи', 'Speech language'), ('Автоматически', 'Automatic'), ('Русский', 'Russian'),
    ('Формат файла', 'File format'), ('Текст (.txt)', 'Text (.txt)'), ('Автосохранение', 'Autosave'),
    ('Не сохранять', 'Do not save'), ('УРОВЕНЬ ЗВУКА', 'AUDIO LEVEL'), ('Ожидание начала', 'Waiting to start'),
    ('Подготовка списка устройств', 'Loading audio devices'),
    ('Весь звук выбранного выхода, включая уведомления\nМодель turbo / локальная обработка', 'All audio from the selected output, including notifications\nturbo model / local processing'),
    ('Остановить захват и сохранить оставшийся текст', 'Stop capture and save the remaining text'),
    ('выход не выбран', 'no output selected'), ('Windows по умолчанию: ', 'Windows default: '),
    ('Windows по умолчанию: {device}', 'Windows default: {device}'),
    ('Устройство Windows по умолчанию', 'Default Windows audio device'), (' (Windows по умолчанию)', ' (Windows default)'),
    ('{device} (Windows по умолчанию)', '{device} (Windows default)'),
    ('Выходы звука не найдены', 'No audio outputs found'), ('Выберите выход звука и начните расшифровку', 'Choose an audio output and start transcription'),
    ('Сначала дождитесь завершения расшифровки записи', 'Wait for the recording transcription to finish'),
    ('Подготавливаем модель', 'Preparing model'), ('Файлы сеанса: ', 'Session files: '),
    ('Файлы сеанса: {paths}', 'Session files: {paths}'), ('Очередь звука: {seconds} с', 'Audio queue: {seconds} s'),
    ('\nУже полученный текст сохранён в файлах сеанса', '\nThe transcript so far has been saved in the session files'),
    ('Останавливаем захват и распознаём оставшийся звук', 'Stopping capture and transcribing remaining audio'),
    ('Сеанс остановлен', 'Session stopped'), ('Сеанс завершён, расшифровка сохранена', 'Session complete, transcript saved'),
    ('Сеанс завершён, текст доступен для копирования', 'Session complete, text ready to copy'),
    ('Сеанс остановлен до начала захвата', 'Session stopped before capture began'), ('Пока нет текста для передачи', 'No text to share yet'),
    ('Файл не найден. Возможно, он был перемещён или удалён', 'File not found. It may have been moved or deleted'),
    ('Перетащите файл в открытый чат или нажмите, чтобы открыть варианты передачи', 'Drag the file into an open chat or click for sharing options'),
    ('Не удалось подготовить файл', 'Could not prepare the file'),
    ('Перетащите файл за кнопку ниже в открытый чат ChatGPT\nили другое приложение, принимающее файлы', 'Drag the button below into an open ChatGPT chat\nor another application that accepts files'),
    ('Перетащить файл в чат', 'Drag file into chat'), ('Копировать файл', 'Copy file'), ('Файл скопирован', 'File copied'),
    ('Не удалось скопировать файл', 'Could not copy the file'),
    ('Файл прикрепится только после перетаскивания в чат.\nОтправьте сообщение в чате, когда будете готовы', 'Drag the file into the chat to attach it.\nSend the message when you are ready'),
    ('Загрузка записи: {service}', 'Downloading recording: {service}'), ('Подготовка аудиодорожки', 'Preparing audio track'),
    ('Загрузка модели и распознавание речи', 'Loading model and transcribing speech'), ('Сохранение расшифровки', 'Saving transcript'),
    ('Речь не распознана. Проверьте выбранную аудиодорожку', 'No speech detected. Check the selected audio track'),
    ('Загрузка модели turbo, захват начнётся после подготовки', 'Loading turbo model; capture starts when ready'),
    ('Ожидаем выход звука Windows, сеанс продолжается', 'Waiting for Windows audio output; session remains active'),
    ('Распознаём речь', 'Transcribing speech'), ('Сохраняем оставшийся звук', 'Saving remaining audio'),
    ('Слушаем: {device}', 'Listening: {device}'),
    ('Сеанс завершён, текст доступен в окне без сохранения', 'Session complete, text available in the window without saving'),
    ('Тёмная / светлая тема', 'Dark / light theme'), ('Язык интерфейса: русский / английский', 'Interface language: Russian / English'),
]


def set_language(language):
    global LANGUAGE
    LANGUAGE = language if language in ('ru', 'en') else 'ru'


def _pattern(template):
    parts = re.split(r'(\{\w+\})', template)
    return re.compile(''.join('(.*?)' if part.startswith('{') else re.escape(part)
                              for part in parts), re.DOTALL)


_RULES = [(ru, en, _pattern(ru), _pattern(en)) for ru, en in PAIRS]
_EN = dict(PAIRS)
_RU = {en: ru for ru, en in PAIRS}


def translate(value, language=None):
    """Translate only catalogued UI messages, preserving template values."""
    language = language or LANGUAGE
    direct = (_EN if language == 'en' else _RU).get(value)
    if direct is not None:
        return direct
    for ru, en, ru_pattern, en_pattern in _RULES:
        source, target = (ru_pattern, en) if language == 'en' else (en_pattern, ru)
        match = source.fullmatch(value)
        if match:
            values = iter(match.groups())
            return re.sub(r'\{\w+\}', lambda _: next(values), target)
    return value


def tr(value):
    return translate(value) if LANGUAGE == 'en' else value


def retranslate(root):
    """Update interface chrome without touching input values or transcripts."""
    from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QLineEdit, QPlainTextEdit, QWidget
    for widget in [root, *root.findChildren(QWidget)]:
        for getter, setter in [('toolTip', 'setToolTip'), ('accessibleName', 'setAccessibleName'),
                               ('windowTitle', 'setWindowTitle')]:
            getattr(widget, setter)(translate(getattr(widget, getter)()))
        if isinstance(widget, (QLabel, QAbstractButton)) and not widget.property('userContent'):
            widget.setText(translate(widget.text()))
        if isinstance(widget, (QLineEdit, QPlainTextEdit)):
            widget.setPlaceholderText(translate(widget.placeholderText()))
        if isinstance(widget, QComboBox):
            previous = widget.blockSignals(True)
            for index in range(widget.count()):
                widget.setItemText(index, translate(widget.itemText(index)))
            widget.blockSignals(previous)
