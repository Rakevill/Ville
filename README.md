# Ville

> Панель-лаунчер для Windows с командами в стиле слэш-консоли, автодополнением путей и алиасов, калькулятором и кастомизируемыми темами.

![версия](https://img.shields.io/badge/version-0.0.2--beta-blue)
![платформа](https://img.shields.io/badge/platform-Windows-lightgrey)
![лицензия](https://img.shields.io/badge/license-MIT-green)

## Что это

Ville — это небольшое окно, которое висит на горячей клавише. Нажимаете `Ctrl+Alt+Space` — появляется, печатаете команду, Enter. Нажали ещё раз — скрылось. Вместо мыши и поиска по меню «Пуск» — одна строка ввода.

![screenshot](screenshot.png)

## Установка

### Готовый `.exe` (Python не нужен)

Скачайте `Ville.exe` из [Releases](https://github.com/Rakevill/Ville/releases/latest) и запустите. Программа живёт в трее, окно вызывается по хоткею.

### Из исходников

    git clone https://github.com/Rakevill/Ville.git
    cd Ville
    pip install -r requirements.txt
    python main.py

Требуется Python 3.10+.

## Использование

### Хоткей

`Ctrl+Alt+Space` — показать/скрыть окно.

Если комбинация занята другой программой, поменяйте в `config.yaml` (см. ниже) на `ctrl+shift+space`, `alt+space` или любую свободную.

### Команды

Все команды начинаются со слеша. Слеш не обязателен — `openset` и `/openset` работают одинаково.

| Команда | Что делает |
|---|---|
| `/openset <путь> <алиас>` | Зарегистрировать файл, папку или программу под коротким именем |
| `/open <алиас>` | Открыть зарегистрированное (или прямой путь) |
| `/openlist` | Список всех зарегистрированных алиасов |
| `/opendel <алиас>` | Удалить регистрацию |
| `/calc <выражение>` | Калькулятор |
| `/help` | Справка по командам |
| `/exit` | Закрыть приложение |

### Примеры

    /openset "C:\Users\me\Documents" docs
    /open docs

    /openset "C:\Program Files\Microsoft VS Code\Code.exe" code
    /open code

    /calc 2+2
    /calc sqrt(2)*pi
    /calc (2+3)*4/2
    /calc ans*2

### Калькулятор

Поддерживает:

- Арифметику: `+ - * / // % **`, скобки
- Степень: `2^10` или `2**10`
- Функции: `sqrt, abs, round, min, max, sin, cos, tan, log, log10, exp, floor, ceil, factorial`
- Константы: `pi, e, tau`
- `ans` — результат предыдущего вычисления в текущей сессии

Безопасен: не выполняет произвольный код, только числа и разрешённые операции.

## Автодополнение

- `/` → список всех команд
- `/open <начало>` → список зарегистрированных алиасов
- `/openset "C:\Prog` → список файлов и папок, навигация по файловой системе

Клавиши:

| Клавиша | Действие |
|---|---|
| `↑` `↓` | Выбрать пункт в подсказке / листать историю команд |
| `Tab` | Подставить выбранное в поле ввода |
| `Enter` | Выполнить (с навигацией по подсказке — подставить и выполнить) |
| `Esc` | Скрыть подсказку / скрыть окно |

История команд хранится между запусками — до 100 последних.

## Настройка

### Конфиг

`%APPDATA%\LauncherLauncher\config.yaml`

Открыть из трея: правый клик по иконке → **Открыть конфиг**.

    hotkey: ctrl+alt+space

    verbs:
      openset:  openset
      open:     open
      openlist: openlist
      opendel:  opendel
      calc:     calc
      help:     help
      exit:     exit

    window:
      x: 200
      y: 200
      width: 680
      height: 460
      always_on_top: true
      autohide_on_blur: true
      start_hidden: false

    theme: default

    shortcuts:
      docs: "C:\\Users\\me\\Documents"
      code: "C:\\Program Files\\Microsoft VS Code\\Code.exe"

### Переименование команд

Любой глагол можно переименовать в `verbs`:

    verbs:
      openset: fset        # теперь /fset вместо /openset
      open: o
      calc: c

Это работает и в автодополнении — подсказки сразу показывают новые имена.

### Темы

`%APPDATA%\LauncherLauncher\themes\default.json`

Открыть из трея: правый клик по иконке → **Открыть папку тем**.

Тема — это JSON с цветами, шрифтом и радиусом:

    {
      "name": "Default",
      "window_bg":     "#1e1e2e",
      "window_border": "#45475a",
      "input_bg":      "#313244",
      "input_fg":      "#cdd6f4",
      "list_bg":       "#181825",
      "list_fg":       "#cdd6f4",
      "list_error":    "#f38ba8",
      "accent":        "#89b4fa",
      "footer_fg":     "#6c7086",
      "list_hover":    "#313244",
      "font_family":   "Segoe UI",
      "font_size":     14,
      "font_mono":     "Consolas",
      "corner_radius": 10
    }

Создайте свой файл (`mytheme.json`), поставьте `theme: mytheme` в конфиге, перезапустите. Недостающие ключи автоматически берутся из дефолтной темы — можно переопределить только то, что хочется.

Палитра по умолчанию — [Catppuccin Mocha](https://github.com/catppuccin/catppuccin).

## Сборка `.exe` из исходников

    pip install pyinstaller
    pyinstaller --onefile --windowed --name Ville --icon icon.ico main.py

Готовый файл — `dist\Ville.exe`.

## Трей

Правый клик по иконке в трее:

- **Показать** (или двойной клик) — вызвать окно
- **Открыть конфиг** — открыть `config.yaml`
- **Открыть папку тем** — открыть папку с темами
- **Выход** — закрыть приложение (или команда `/exit`)

## Известные ограничения

- Только Windows.
- Нет автопроверки обновлений — новые версии скачиваются вручную из Releases.
- Иконка трея рисуется программно, без файла `.ico`.
- `keyboard` (глобальный хоткей) иногда конфликтует с антивирусами — если хоткей перестал работать, проверьте карантин.

## Статус

`v0.0.2-beta`. Проект в активной разработке, API команд и формат конфига могут поменяться до `v1.0.0`. Обратная совместимость не гарантируется, но старые конфиги будут мержиться с новыми дефолтами — ничего не потеряется.

Присылайте баги и предложения в [Issues](https://github.com/Rakevill/Ville/issues).

## Лицензия

MIT — см. [LICENSE](LICENSE).