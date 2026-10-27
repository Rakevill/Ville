"""Точка входа: глобальный хоткей, трей, главное окно.

Потоки:
- Главный       — Tk mainloop (всё, что касается виджетов)
- keyboard      — свой поток, вызывает _toggle_from_other_thread
- pystray       — свой поток, вызывает _toggle_from_other_thread / _request_shutdown

Из чужих потоков напрямую к виджетам НЕ обращаемся — только через
window.after(0, ...), иначе Tkinter падает или ведёт себя непредсказуемо.
"""
import os
import sys
import threading

import keyboard
import pystray
from PIL import Image, ImageDraw

from commands import CommandRegistry
from config import Config
from theme import Theme, themes_dir
from window import LauncherWindow
from instance import acquire_single_instance

def main():
    if not acquire_single_instance():
        # уже запущен — тихо выходим
        sys.exit(0)
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()


class App:
    def __init__(self):
        self.config = Config.load()
        self.theme = Theme.load(self.config.theme)
        self.registry = CommandRegistry(self.config)
        self.window = LauncherWindow(
            self.config, self.theme, self.registry,
            on_exit=self.shutdown,
        )
        self.tray = None
        self._hotkey_handle = None

    # ---------- показ / скрытие ----------
    def toggle(self):
        """Только из главного Tk-потока."""
        if self.window.winfo_viewable():
            self.window.withdraw()
        else:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_input()
            if self.config.window.get('always_on_top', True):
                self.window.attributes('-topmost', True)

    def _toggle_from_other_thread(self):
        """Безопасный вызов toggle из keyboard/pystray."""
        try:
            self.window.after(0, self.toggle)
        except Exception:
            # окно уже уничтожено — тихо игнорируем
            pass

    # ---------- хоткей ----------
    def _setup_hotkey(self):
        combo = self.config.hotkey
        try:
            self._hotkey_handle = keyboard.add_hotkey(
                combo,
                self._toggle_from_other_thread,
                suppress=False,
            )
        except Exception as e:
            print(f'[hotkey] Не удалось зарегистрировать "{combo}": {e}')
            print('[hotkey] Комбинация занята? Поменяйте в config.yaml. '
                  'Пока доступ только через трей.')

    # ---------- трей ----------
    def _tray_image(self):
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(
            [6, 6, 58, 58], radius=12,
            fill=self.theme['window_bg'],
            outline=self.theme['accent'],
            width=3,
        )
        # точка в центре — простая и читаемая, без шрифтов
        d.ellipse([27, 27, 37, 37], fill=self.theme['accent'])
        return img

    def _setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem(
                'Показать',
                lambda *_: self._toggle_from_other_thread(),
                default=True,
            ),
            pystray.MenuItem('Открыть конфиг', self._open_config),
            pystray.MenuItem('Открыть папку тем', self._open_themes),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Выход', self._request_shutdown),
        )
        self.tray = pystray.Icon(
            'launcher', self._tray_image(), 'Launcher', menu,
        )
        threading.Thread(
            target=self.tray.run, daemon=True, name='tray',
        ).start()

    def _open_config(self, *_):
        # сначала пробуем открыть сам файл в редакторе по умолчанию,
        # если не получилось (нет ассоциации) — открываем папку
        try:
            os.startfile(self.config.path)
        except OSError:
            os.startfile(self.config.path.parent)

    def _open_themes(self, *_):
        os.startfile(themes_dir())

    # ---------- жизненный цикл ----------
    def _request_shutdown(self, *_):
        """Из трея — в Tk-поток."""
        self.window.after(0, self.shutdown)

    def run(self):
        # опционально стартовать скрытым (для автозапуска с Windows)
        if self.config.window.get('start_hidden', False):
            self.window.withdraw()

        try:
            self._setup_tray()
            self._setup_hotkey()
            self.window.mainloop()
        finally:
            # сработает и при нормальном выходе,
            # и при исключении внутри mainloop
            self._cleanup()

    def shutdown(self):
        # разрушение окна завершает mainloop → finally → _cleanup
        try:
            self.window.destroy()
        except Exception:
            pass

    def _cleanup(self):
        """Идемпотентно: можно вызывать сколько угодно раз."""
        # снимаем все глобальные хоткеи
        try:
            keyboard.remove_all_hotkeys()
        except Exception:
            pass
        self._hotkey_handle = None

        # останавливаем трей-поток
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception:
                pass
            self.tray = None

        # добиваем окно, если destroy не был вызван явно
        try:
            if self.window.winfo_exists():
                self.window.destroy()
        except Exception:
            pass


def main():
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == '__main__':
    main()