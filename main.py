"""Точка входа: IPC, трей, хоткей, окно."""
import ctypes
import os
import subprocess
import sys
import threading
import explorer_menu
import keyboard
import pystray
from PIL import Image, ImageDraw

import autostart
from commands import CommandRegistry
from config import Config
from instance import (
    acquire_single_instance,
    release_single_instance,
    start_ipc_server,
    try_activate_existing,
)
from settings import SettingsWindow
from theme import Theme, themes_dir
from window import LauncherWindow
from set_alias_dialog import SetAliasDialog

__version__ = 'v0.0.3-beta'


class App:
    def __init__(self, start_hidden=False):
        self.config = Config.load()
        self.theme = Theme.load(self.config.theme)
        self.registry = CommandRegistry(self.config)
        self.tray = None
        self._settings_window = None
        self._restart_requested = False
        self._set_alias_dialog = None
        self.start_hidden = start_hidden

        self.window = LauncherWindow(
            self.config, self.theme, self.registry,
            on_exit=self.shutdown,
            on_settings=self._show_settings,
            on_restart=self.restart,
            is_extra_foreground=self._is_settings_foreground,
        )

    # ---------- показ / скрытие ----------
    def toggle(self):
        if self.window.winfo_viewable():
            self.window.withdraw()
        else:
            self.show_window()

    def show_window(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_input()
        if self.config.window.get('always_on_top', True):
            self.window.attributes('-topmost', True)

    def _toggle_from_other_thread(self):
        try:
            self.window.after(0, self.toggle)
        except Exception:
            pass

    def _show_from_other_thread(self):
        try:
            self.window.after(0, self.show_window)
        except Exception:
            pass

    # ---------- хоткей ----------
    def _setup_hotkey(self):
        combo = self.config.hotkey
        try:
            keyboard.add_hotkey(combo, self._toggle_from_other_thread, suppress=False)
        except Exception as e:
            print(f'[hotkey] Не удалось зарегистрировать "{combo}": {e}')

    # ---------- трей ----------
    def _tray_image(self):
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([6, 6, 58, 58], radius=12,
                            fill=self.theme['window_bg'],
                            outline=self.theme['accent'], width=3)
        d.ellipse([27, 27, 37, 37], fill=self.theme['accent'])
        return img

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Показать', lambda *_: self._toggle_from_other_thread(), default=True),
            pystray.MenuItem('Настройки…', self._open_settings),
            pystray.MenuItem('Открыть конфиг', self._open_config),
            pystray.MenuItem('Открыть папку тем', self._open_themes),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Выход', self._request_shutdown),
        )
        self.tray = pystray.Icon('launcher', self._tray_image(),
                                 f'Ville {__version__}', menu)
        threading.Thread(target=self.tray.run, daemon=True, name='tray').start()

    def _open_config(self, *_):
        try:
            os.startfile(self.config.path)
        except OSError:
            os.startfile(self.config.path.parent)

    def _open_themes(self, *_):
        os.startfile(themes_dir())

    def _request_shutdown(self, *_):
        self.window.after(0, self.shutdown)

    # ---------- настройки ----------
    def _open_settings(self, *_):
        self.window.after(0, self._show_settings)

    def _show_settings(self):
        if self._settings_window is not None:
            try:
                self._settings_window.focus_force()
                return
            except Exception:
                self._settings_window = None
        self._settings_window = SettingsWindow(
            self.window, self.config, self.theme,
            self._apply_settings,
            on_reset=self.reset_to_defaults,
        )
        self._settings_window.protocol(
            'WM_DELETE_WINDOW', self._on_settings_closed,
        )
        self._settings_window.after(50, self._focus_settings)

    def _focus_settings(self):
        if self._settings_window is None:
            return
        try:
            self._settings_window.focus_force()
            self._settings_window.lift()
        except Exception:
            pass

    def _on_settings_closed(self):
        if self._settings_window is not None:
            try:
                self._settings_window.destroy()
            except Exception:
                pass
        self._settings_window = None
        self.window.after(30, self._restore_launcher_focus)

    def _restore_launcher_focus(self):
        try:
            if not self.window.winfo_viewable():
                return
            self.window.focus_force()
            self.window.focus_input()
        except Exception:
            pass

    def _is_settings_foreground(self) -> bool:
        if self._settings_window is None:
            return False
        try:
            shwnd = ctypes.windll.user32.GetAncestor(
                self._settings_window.winfo_id(), 2,
            )
            return shwnd == ctypes.windll.user32.GetForegroundWindow()
        except Exception:
            return False

    def _apply_settings(self, new_theme_data, new_verbs, new_hotkey):
        self.theme.data = new_theme_data
        self.window.apply_theme(self.theme)

        self.registry._verb_keys = {v: k for k, v in new_verbs.items()}

        ac = self.window.autocomplete
        ac._open_verbs = {v for k, v in new_verbs.items() if k == 'open'}
        ac._openset_verbs = {v for k, v in new_verbs.items() if k == 'openset'}

        try:
            keyboard.remove_all_hotkeys()
        except Exception:
            pass
        try:
            keyboard.add_hotkey(new_hotkey, self._toggle_from_other_thread, suppress=False)
        except Exception as e:
            print(f'[hotkey] Не удалось зарегистрировать "{new_hotkey}": {e}')

    # ---------- перезапуск / сброс ----------
    def restart(self):
        self._restart_requested = True
        self.shutdown()

    def reset_to_defaults(self):
        try:
            if self.config.path.exists():
                self.config.path.unlink()
        except OSError as e:
            print(f'[reset] Не удалось удалить конфиг: {e}')
            return
        try:
            theme_path = themes_dir() / 'default.json'
            if theme_path.exists():
                theme_path.unlink()
        except OSError as e:
            print(f'[reset] Не удалось удалить тему: {e}')
        autostart.set_enabled(False)
        self.restart()

    # ---------- жизненный цикл ----------
    def run(self):
        if self.start_hidden or self.config.window.get('start_hidden', False):
            self.window.withdraw()
        try:
            if explorer_menu.is_enabled():
                try:
                    explorer_menu.enable()   # обновить путь
                except OSError:
                    pass
            self._setup_tray()
            self._setup_hotkey()
            self.window.mainloop()
        finally:
            self._cleanup()

    def shutdown(self):
        try:
            self.window.destroy()
        except Exception:
            pass

    def _cleanup(self):
        try:
            keyboard.remove_all_hotkeys()
        except Exception:
            pass
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.tray = None
        try:
            if self.window.winfo_exists():
                self.window.destroy()
        except Exception:
            pass
        release_single_instance()

    def _handle_ipc_message(self, msg: str):
        if msg.startswith('set-alias|'):
            path = msg[len('set-alias|'):]
            self.window.after(0, lambda p=path: self.show_set_alias_dialog(p))
        elif msg == 'show':
            self._show_from_other_thread()

    def show_set_alias_dialog(self, path: str):
        if self._set_alias_dialog is not None:
            try:
                self._set_alias_dialog.destroy()
            except Exception:
                pass
            self._set_alias_dialog = None

        self.show_window()

        self._set_alias_dialog = SetAliasDialog(
            self.window, path,
            existing_aliases=list(self.config.shortcuts.keys()),
            on_accept=self._save_alias_from_dialog,
        )
        self._set_alias_dialog.protocol(
            'WM_DELETE_WINDOW', self._on_alias_dialog_closed,
        )

    def _on_alias_dialog_closed(self):
        if self._set_alias_dialog is not None:
            try:
                self._set_alias_dialog.destroy()
            except Exception:
                pass
        self._set_alias_dialog = None
        self.window.after(30, self._restore_launcher_focus)

    def _save_alias_from_dialog(self, name: str):
        from pathlib import Path
        dialog = self._set_alias_dialog
        if dialog is None:
            return
        try:
            normalized = str(Path(dialog.path).resolve())
        except Exception:
            normalized = dialog.path

        if not Path(normalized).exists():
            raise ValueError(f'Путь не существует: {normalized}')

        self.config.shortcuts[name] = normalized
        self.config.save()

        try:
            self.window._append(f'Зарегистрировано: {name} → {normalized}')
        except Exception:
            pass


def _spawn_new_instance():
    if getattr(sys, 'frozen', False):
        args = [sys.executable] + sys.argv[1:]
    else:
        args = [sys.executable, sys.argv[0]] + sys.argv[1:]
    try:
        subprocess.Popen(args, close_fds=True)
    except OSError as e:
        print(f'[restart] Не удалось перезапустить: {e}')


def main():
    start_hidden = '--start-hidden' in sys.argv

    set_alias_path = None
    if '--set-alias' in sys.argv:
        idx = sys.argv.index('--set-alias')
        if idx + 1 < len(sys.argv):
            set_alias_path = sys.argv[idx + 1].strip('"')

    if not acquire_single_instance():
        if set_alias_path:
            try_activate_existing(f'set-alias|{set_alias_path}')
        else:
            try_activate_existing('show')
        sys.exit(0)

    app = App(start_hidden=start_hidden)
    start_ipc_server(app._handle_ipc_message)

    if set_alias_path:
        app.window.after(200, lambda p=set_alias_path: app.show_set_alias_dialog(p))

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()

    if app._restart_requested:
        _spawn_new_instance()


if __name__ == '__main__':
    main()