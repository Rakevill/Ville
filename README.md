# Ville

Панель-лаунчер для Windows: глобальный хоткей, команды в стиле слэш-консоли,
автодополнение путей и алиасов, кастомизируемые темы.

## Установка

    pip install -r requirements.txt

## Запуск

    python main.py

Хоткей по умолчанию: `Ctrl+Alt+Space`.

## Команды

- `/openset <путь> <алиас>` — зарегистрировать файл, папку или программу
- `/open <алиас>` — открыть зарегистрированное
- `/openlist` — список зарегистрированного
- `/opendel <алиас>` — удалить регистрацию
- `/calc <выражение>` — калькулятор (`/calc sqrt(2)*pi`, `/calc ans*2`)

Пример:

    /openset "C:\Users\me\Documents" docs
    /open docs

## Конфигурация

Файл: `%APPDATA%\LauncherLauncher\config.yaml`

Темы: `%APPDATA%\LauncherLauncher\themes\default.json`

## Лицензия

MIT — см. [LICENSE](LICENSE).