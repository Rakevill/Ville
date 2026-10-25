"""Темы оформления (token-темы).

Тема — это JSON-файл с набором ключей (цвета, шрифт, радиусы).
Дефолтная тема создаётся при первом запуске в
%APPDATA%\\LauncherLauncher\\themes\\default.json — её можно
править руками, чтобы менять внешний вид без правки кода.

Пользовательские темы кладутся в ту же папку под другим именем,
активируются через `theme: <имя>` в config.yaml.

Если в теме не хватает ключа — он берётся из DEFAULT_THEME,
поэтому «сломанная» тема не роняет приложение.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path


# Все ключи, которые используют window.py и autocomplete.py.
# При добавлении нового ключа — добавляйте его и сюда, иначе
# тема без этого ключа будет использовать значение отсюда.
DEFAULT_THEME = {
    'name': 'Default',

    # Окно
    'window_bg': '#1e1e2e',
    'window_border': '#45475a',

    # Поле ввода
    'input_bg': '#313244',
    'input_fg': '#cdd6f4',

    # Панель вывода и подсказок
    'list_bg': '#181825',
    'list_fg': '#cdd6f4',
    'list_error': '#f38ba8',

    # Акцент (выделение в автодополнении)
    'accent': '#89b4fa',

    # Шрифт и форма
    'font_family': 'Segoe UI',
    'font_size': 14,
    'corner_radius': 10,
}


def themes_dir() -> Path:
    """Папка с темами. Создаётся, если её нет. Дефолтную тему
    кладём туда же при первом запуске, чтобы пользователь мог
    её открыть и скопировать как основу для своей."""
    base = Path(os.environ.get('APPDATA') or Path.home())
    d = base / 'LauncherLauncher' / 'themes'
    d.mkdir(parents=True, exist_ok=True)

    default_file = d / 'default.json'
    if not default_file.exists():
        default_file.write_text(
            json.dumps(DEFAULT_THEME, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
    return d


def list_themes() -> list[str]:
    """Имена доступных тем (без расширения .json), по алфавиту.
    Используется, если позже захотите показать выбор темы в трее
    или в окне настроек."""
    return sorted(p.stem for p in themes_dir().glob('*.json'))


@dataclass
class Theme:
    """Загруженная тема. Использование:

        theme = Theme.load('default')
        color = theme['window_bg']
        font  = (theme['font_family'], theme['font_size'])
    """
    data: dict

    @classmethod
    def load(cls, name: str) -> 'Theme':
        path = themes_dir() / f'{name}.json'
        if not path.exists():
            # молча откатываемся на дефолт — лучше так, чем упасть
            path = themes_dir() / 'default.json'

        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as e:
            # Битый JSON — тоже не падаем, используем полностью дефолт.
            # В консоль пишем — пригодится при отладке своей темы.
            print(f'[theme] Не удалось прочитать {path.name}: {e}. '
                  f'Используется дефолтная тема.')
            raw = {}

        # Мерж: пользовательские значения поверх дефолта.
        # Отсутствующие ключи берутся из DEFAULT_THEME.
        return cls(data={**DEFAULT_THEME, **raw})

    def __getitem__(self, key: str):
        return self.data[key]

    def get(self, key: str, default=None):
        return self.data.get(key, default)