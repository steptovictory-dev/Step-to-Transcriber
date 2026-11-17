# Техническая документация Step to Transcriber

[← Руководство пользователя](../README.md)

## Среда разработки и запуск

Команды выполняются из каталога с `app.py`. Проверенная конфигурация исходного приложения включает Windows 11 x64, Python 3.14.6 x64, NVIDIA GeForce RTX 4060 8 ГБ, faster-whisper 1.2.1, CTranslate2 4.8.2 и PySide6 6.12.0. Зависимости закреплены в [requirements.txt](../requirements.txt) и [requirements-dev.txt](../requirements-dev.txt).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path ..\input, ..\output
.\.venv\Scripts\python.exe app.py
```

CUDA-библиотеки cuBLAS, cuDNN и NVRTC загружаются из пакетов NVIDIA. При запуске из исходников `src/runtime.py` также учитывает стандартный путь CUDA Toolkit 12.8, если он существует. Распознавание выполняется на `cuda` с `float16`. В установленной сборке библиотеки берутся из комплекта приложения. Модели загружаются с Hugging Face при первом использовании и хранятся в пользовательском кэше.

Оригинальная консольная версия доступна через `main.py`. Она использует интерактивные меню и сохраняет Markdown и TXT.

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe main.py "..\input\recording.mp4"
```

## Сборка установщика Windows

Для сборки 0.1.0 использовались Python 3.14.6 x64, PyInstaller 6.22.3, Inno Setup 6.7.4 и Node.js 24.19.0 x64. Установите Inno Setup и распакуйте официальный ZIP Node.js для Windows x64 после сверки SHA‑256 с `SHASUMS256.txt`. Скрипту нужен каталог с `node.exe` и `LICENSE`. [Inno Setup](https://jrsoftware.org/inno-setup/downloads), [Node.js v24.19.0](https://nodejs.org/en/blog/release/v24.19.0/)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\packaging\build-windows.ps1 -NodeDist 'C:\Tools\node-v24.19.0-win-x64' -Iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' -Version '0.1.0'
```

[Скрипт сборки](../packaging/build-windows.ps1) формирует комплект приложения, сохраняет установщик в `dist` и выводит SHA‑256. [Спецификация PyInstaller](../packaging/windows.spec) настраивает сборку `onedir`, оставляет один согласованный набор CUDA-библиотек и исключает сторонние ICU DLL, чтобы Qt использовал системную ICU. [Сценарий Inno Setup](../packaging/windows.iss) оформляет мастер установки и удаления, создаёт ярлыки и регистрирует деинсталлятор для текущего пользователя.

Из пакетов и архива Node.js включаются доступные лицензионные файлы. Подготовка публичного выпуска включает проверку условий распространения Qt, FFmpeg и NVIDIA. Установщик 0.1.0 без цифровой подписи.

<details>
<summary>Локальный launcher для разработки</summary>

Этот EXE запускает `project/.venv/Scripts/pythonw.exe` и `project/app.py`. Для работы рядом с ним должны находиться исходники и окружение в папке `project`.

```powershell
.\.venv\Scripts\python.exe scripts/build_icon.py
$appIcon = (Resolve-Path assets/step-to-transcriber.ico).Path
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name "Step to Transcriber" --icon "$appIcon" --distpath .. --workpath build/launcher --specpath build launch.py
```

Команда сохраняет launcher на уровень выше. При изменении Python-кода достаточно перезапустить приложение.

</details>

## Устройство проекта

| Компонент | Ответственность |
| --- | --- |
| [app.py](../app.py), [main.py](../main.py), [launch.py](../launch.py) | Вход в GUI, консольная версия и локальный launcher |
| [gui.py](../src/gui.py) | Экраны и действия пользователя, фоновые задачи распознавания |
| [theme.py](../src/theme.py), [i18n.py](../src/i18n.py), [widgets.py](../src/widgets.py) | Темы, локализация и элементы интерфейса |
| [pipeline.py](../src/pipeline.py), [audio.py](../src/audio.py) | Подготовка записи, выбор дорожки и декодирование в моно WAV 16 кГц |
| [transcriber.py](../src/transcriber.py), [exporters.py](../src/exporters.py) | Распознавание речи, группировка сегментов, таймкоды и экспорт |
| [youtube.py](../src/youtube.py) | Проверка URL, загрузка одной записи и выбор JavaScript runtime |
| [live.py](../src/live.py), [live_gui.py](../src/live_gui.py) | WASAPI loopback, распознавание фрагментов, смена выхода и отдельное окно текста |
| [paths.py](../src/paths.py), [runtime.py](../src/runtime.py) | Пути к ресурсам и пользовательским данным, загрузка CUDA DLL |
| [sharing.py](../src/sharing.py) | Копирование и перетаскивание файлов результатов |
| [packaging/](../packaging/), [tests/](../tests/) | Сборка Windows и проверки |

Распознавание выполняется в `QThread`. Сигналы передают прогресс и результат в поток интерфейса. Приложение запускает один сеанс распознавания за раз. Отмена файла обрабатывается между этапами и сегментами. Для живого режима при штатном завершении обрабатывается оставшийся звук.

### Данные и ресурсы

| Данные | Установленное приложение | Запуск из исходников |
| --- | --- | --- |
| Результаты по умолчанию | `%LOCALAPPDATA%\Step to Transcriber\output` | `../output` |
| Журнал | `%LOCALAPPDATA%\Step to Transcriber\logs\transcriber.log` | `../logs/transcriber.log` |
| Настройки интерфейса и последняя папка | `%LOCALAPPDATA%\Step to Transcriber\settings.ini` | Qt INI для `Steptovictory/StepToTranscriber` |
| Модели | Пользовательский кэш Hugging Face | Пользовательский кэш Hugging Face |

Приложение при запуске переносит старый журнал из папки результатов по умолчанию в `logs`, если файл доступен. Исходные записи разработки можно держать в `../input`. Inno Setup по умолчанию устанавливает приложение в `%LOCALAPPDATA%\Programs\Step to Transcriber`, а рабочие данные остаются в пользовательских каталогах. Иконка и ресурсы Qt находятся в [assets/](../assets/).

### Загрузка записей

| Сервис | Поддерживаемые ссылки |
| --- | --- |
| YouTube | `watch?v=…`, `youtu.be/…`, `/shorts/…`, `/live/…` и `/embed/…` для отдельной записи |
| VK Видео | `video<owner>_<id>` на `vk.com`, `vk.ru` и `vkvideo.ru`, ссылки с параметром `z=video…` и `video_ext.php` |
| Rutube | `/video/<id>/` и `/play/embed/<id>/` |
| Twitch | `/videos/<id>`, поддерживаемые старые и мобильные формы VOD, ссылки плеера с `video` |
| VK Видео Live | `/имя/record/идентификатор`, включая прежние домены `vkplay.live` и `live.vkplay.ru` и суффикс `/records` |

Загрузчик выбирает аудиопоток или один совмещённый поток. Свой HLS-загрузчик yt-dlp обрабатывает сегменты. Недоступный сегмент после повторных попыток завершает загрузку ошибкой. Декодирование выполняет PyAV. Скачанная запись и временный WAV удаляются после задачи.

Для YouTube используется `yt-dlp[default]` с EJS. Поиск Node.js идёт по `TRANSCRIBER_NODE`, затем в `tools/node.exe` рядом с ресурсами приложения, затем по `PATH`. Если Node.js не найден, используется Deno из `PATH` при его наличии. Для проверки изменений YouTube обновите зависимость в отдельном окружении разработки и повторите тесты перед обновлением закреплённой версии. [yt-dlp EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS)

### Живой режим

PyAudioWPatch захватывает звук через WASAPI loopback. При выборе выхода Windows по умолчанию Qt отслеживает смену устройства. Переподключение сохраняет модель, текущие выходные файлы и отсчёт времени. Возможный пропуск отмечается в тексте.

Модель `turbo` обрабатывает интервалы примерно по 8 секунд с контекстом на стыках. Слова относятся к интервалу по середине их временного диапазона. Буфер аудио ограничен. При переполнении очереди или потере данных Windows сеанс останавливается с сообщением. Подтверждённые абзацы сразу попадают в открытые файлы, если включено автосохранение. Команда передачи файла создаёт отдельный TXT-снимок в `output/shared` независимо от автосохранения.

## Проверки

### Автоматические тесты

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'
.\.venv\Scripts\python.exe -m pip check
```

Тесты используют подмены распознавания и аудиозахвата. Для проверок загрузчика нужен доступ к локальному HTTP на `127.0.0.1`.

### Ручные проверки

```powershell
.\.venv\Scripts\python.exe tests/smoke_video_download.py "https://vkvideo.ru/videoOWNER_ID" "https://rutube.ru/video/VIDEO_ID/"
.\.venv\Scripts\python.exe tests/smoke_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID"
.\.venv\Scripts\python.exe tests/smoke_desktop.py "https://www.youtube.com/watch?v=VIDEO_ID"
.\.venv\Scripts\python.exe tests/smoke_live.py --seconds 15
```

Первая команда проверяет загрузку и декодирование. Следующие две запускают реальное распознавание YouTube по указанной записи. Последняя проверяет живой режим на текущем выходе Windows. Для контрольной речи можно использовать `tests/synthesize_live_test.ps1` и параметр `--play` со своим WAV. Параметр `--switch-after 10` переключает автоматический выбор на тот же явно выбранный выход.

Сценарии `tests/capture_ui.py`, `tests/capture_preferences.py` и `tests/capture_live_ui.py` сохраняют изображения экранов в `../output` для ручной проверки оформления.

### Что проверено в сборке 0.1.0

- 51 автоматический тест прошёл 17 ноября 2026 года.
- На Windows 11 x64 с RTX 4060 проверены установка, запуск, распознавание контрольного WAV на GPU с уже загруженной `turbo`, экспорт Markdown и удаление. После удаления расшифровка, журнал, настройки и кэшированная модель сохранились.
- Исходная версия ранее прошла проверку реального захвата на Focusrite USB Audio. Полный цикл установки на чистую Windows, первая загрузка модели, эфир и реальные интернет-загрузки из установленной сборки требуют отдельной проверки.

