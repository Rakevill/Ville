"""Конфиг приложения: %APPDATA%\\LauncherLauncher\\config.yaml.

Принцип: DEFAULT_CONFIG — источник истины для всех ключей.
Пользовательский файл поверх него мержится через _deep_merge.
Если пользователь удалил ключ или его нет — берётся из дефолта.
"""
import os
from dataclasses import dataclass
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    # Глаголы: ключ — внутреннее имя (стабильное),
    # значение — то, что печатает пользователь (можно переименовать).
    'verbs': {
        'openset':  'openset',
        'open':     'open',
        'openlist': 'openlist',
        'opendel':  'opendel',
        'calc':     'calc',
        'help':     'help',      # ← новые
        'exit':     'exit',      # ←
    },
    # Зарегистрированные алиасы: {alias: path}
    'shortcuts': {},
    # Окно: позиция, размер, поведение
    'window': {
        'x': 200,
        'y': 200,
        'width': 680,
        'height': 460,
        'always_on_top': True,
        'autohide_on_blur': True,
    },
    # Глобальный хоткей. Если занят другой программой — сменить здесь.
    'hotkey': 'ctrl+alt+space',
    # Имя темы (файл themes/<name>.json)
    'theme': 'default',
    # История команд (максимум 100, обрезается при добавлении)
    'history': [],
}


def config_dir() -> Path:
    """Папка конфига и тем. На Windows — %APPDATA%, иначе — home."""
    base = Path(os.environ.get('APPDATA') or Path.home())
    d = base / 'LauncherLauncher'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _deep_merge(default: dict, user: dict) -> dict:
    """Рекурсивный merge: значения из user перекрывают default,
    но недостающие вложенные ключи берутся из default."""
    result = dict(default)
    for key, value in user.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class Config:
    data: dict
    path: Path

    @classmethod
    def load(cls) -> 'Config':
        p = config_dir() / 'config.yaml'
        user = {}
        if p.exists():
            try:
                with p.open('r', encoding='utf-8') as f:
                    user = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                # Битый YAML — не падаем, работаем на дефолтах.
                # Пользователь может открыть файл и поправить.
                print(f'[config] ошибка чтения {p}: {e}. Используются дефолты.')
                user = {}
        cfg = cls(data=_deep_merge(DEFAULT_CONFIG, user), path=p)
        if not p.exists():
            cfg.save()
        return cfg

    def save(self) -> None:
        with self.path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(
                self.data, f,
                allow_unicode=True,
                sort_keys=False,   # сохраняет порядок ключей из DEFAULT_CONFIG
                default_flow_style=False,
            )

    # ---------- удобные свойства ----------
    @property
    def hotkey(self) -> str:
        return self.data['hotkey']

    @property
    def theme(self) -> str:
        return self.data['theme']

    @property
    def window(self) -> dict:
        return self.data['window']

    @property
    def verbs(self) -> dict:
        return self.data['verbs']

    @property
    def shortcuts(self) -> dict:
        return self.data['shortcuts']

    @property
    def history(self) -> list:
        return self.data['history']