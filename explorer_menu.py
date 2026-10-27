"""Интеграция с контекстным меню проводника Windows.

Регистрирует пункт «Задать алиас в Ville» для файлов и папок.
HKCU — без прав администратора, только для текущего пользователя.
"""
import os
import sys
import winreg


MENU_LABEL = 'Задать алиас в Ville'
KEY_NAME = 'VilleSetAlias'

# для файлов
FILE_ROOT = r'Software\Classes\*\shell'
# для папок
DIR_ROOT = r'Software\Classes\Directory\shell'


def _command_line() -> str:
    if getattr(sys, 'frozen', False):
        exe = sys.executable
        return f'"{exe}" --set-alias "%1"'
    python = sys.executable
    script = os.path.abspath(sys.argv[0])
    return f'"{python}" "{script}" --set-alias "%1"'


def _icon_path() -> str:
    if getattr(sys, 'frozen', False):
        return sys.executable
    return sys.executable  # python.exe — не идеально, но без .ico лучшее


def _write(root: str) -> None:
    base = f'{root}\\{KEY_NAME}'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, MENU_LABEL)
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, _icon_path())
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f'{base}\\command') as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, _command_line())


def _delete_tree(path: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                            winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                    _delete_tree(f'{path}\\{sub}')
                except OSError:
                    break
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def enable() -> None:
    _write(FILE_ROOT)
    _write(DIR_ROOT)


def disable() -> None:
    _delete_tree(f'{FILE_ROOT}\\{KEY_NAME}')
    _delete_tree(f'{DIR_ROOT}\\{KEY_NAME}')


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            f'{FILE_ROOT}\\{KEY_NAME}\\command',
            0, winreg.KEY_READ,
        ):
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False