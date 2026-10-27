"""Точка входа: IPC, трей, хоткей, окно."""
import sys
import threading

import keyboard
import pystray
from PIL import Image, ImageDraw

from commands import CommandRegistry
from config import Config
from instance import (
    acquire_single_instance,
    start_ipc_server,
    try_activate_existing,
)
from theme import Theme, themes_dir
from window import LauncherWindow
from settings import SettingsWindow

__version__ = 'v0.0.3-beta'


class App:
    def __init__(self):
        self.config = Config.load()
        self.theme = Theme.load(self.config.theme)
        self.registry = CommandRegistry(self.config)
        self.window = LauncherWindow(
            self.config, self.theme, self.registry,
            on_exit=self.shutdown,
            on_settings=self._show_settings,
        )
        self.tray = None
        self._settings_window = None

    def toggle(self):
        if self.window.winfo_viewable():
            self.window.withdraw()
        else:
            self.show_window()


    def _show_about(self, *_):
        from tkinter import messagebox
        self.window.after(0, lambda: messagebox.showinfo(
            'О программе',
            f'Ville {__version__}\n\n'
            'Панель-лаунчер для Windows.\n\n'
            'Код написан преимущественно с помощью AI-ассистента\n'
            '(Claude, Anthropic) и отредактирован вручную.\n\n'
            'Лицензия: MIT\n'
            'https://github.com/Rakevill/Ville',
            parent=self.window,
        ))
    
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

    def _setup_hotkey(self):
        combo = self.config.hotkey
        try:
            keyboard.add_hotkey(combo, self._toggle_from_other_thread, suppress=False)
        except Exception as e:
            print(f'[hotkey] Не удалось зарегистрировать "{combo}": {e}')

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
            pystray.MenuItem('О программе', self._show_about),
            pystray.Menu.SEPARATOR,
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
        import os
        try:
            os.startfile(self.config.path)
        except OSError:
            os.startfile(self.config.path.parent)

    def _open_themes(self, *_):
        import os
        os.startfile(themes_dir())

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
            self.window, self.config, self.theme, self._apply_settings,
        )
        self._settings_window.protocol(
            'WM_DELETE_WINDOW', self._on_settings_closed,
        )

    def _on_settings_closed(self):
        if self._settings_window is not None:
            try:
                self._settings_window.destroy()
            except Exception:
                pass
        self._settings_window = None

    def _apply_settings(self, new_theme_data, new_verbs):
        self.theme.data = new_theme_data
        self.window.apply_theme(self.theme)

        self.registry._verb_keys = {v: k for k, v in new_verbs.items()}

        ac = self.window.autocomplete
        ac._open_verbs = {v for k, v in new_verbs.items() if k == 'open'}
        ac._openset_verbs = {v for k, v in new_verbs.items() if k == 'openset'}

    def _request_shutdown(self, *_):
        self.window.after(0, self.shutdown)

    def run(self):
        if self.config.window.get('start_hidden', False):
            self.window.withdraw()
        try:
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


def main():
    if not acquire_single_instance():
        try_activate_existing()
        sys.exit(0)

    app = App()
    start_ipc_server(app._show_from_other_thread)

    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == '__main__':
    main()