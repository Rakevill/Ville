"""Окно настроек: цвета темы, команды, общие."""
import json
import threading
import tkinter.colorchooser as colorchooser
import autostart
import explorer_menu
import customtkinter as ctk
import keyboard

from theme import themes_dir
from tkinter import messagebox



COLOR_KEYS = [
    ('window_bg',     'Фон окна'),
    ('window_border', 'Рамка окна'),
    ('input_bg',      'Фон поля ввода'),
    ('input_fg',      'Текст ввода'),
    ('list_bg',       'Фон списка'),
    ('list_fg',       'Текст списка'),
    ('list_error',    'Текст ошибок'),
    ('list_hover',    'Подсветка при наведении'),
    ('accent',        'Акцент'),
    ('footer_fg',     'Футер'),
]

VERB_DESCRIPTIONS = {
    'openset':  'зарегистрировать путь',
    'open':     'открыть алиас',
    'openlist': 'список алиасов',
    'opendel':  'удалить алиас',
    'calc':     'калькулятор',
    'help':     'справка',
    'exit':     'выход',
    'settings': 'настройки',
    'clear':    'очистить вывод',
    'restart':  'перезапустить',
}

BG      = '#1e1e2e'
PANEL   = '#181825'
INPUT   = '#313244'
FG      = '#cdd6f4'
MUTED   = '#6c7086'
ACCENT  = '#89b4fa'
SUCCESS = '#40a02b'
DANGER  = '#d20f39'

_MODIFIER_KEYS = {
    'ctrl', 'left ctrl', 'right ctrl',
    'alt', 'left alt', 'right alt', 'alt gr',
    'shift', 'left shift', 'right shift',
    'windows', 'left windows', 'right windows',
    'caps lock', 'num lock', 'scroll lock',
}


def _apply_win_rounding(window):
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)
        if not hwnd:
            return
        pref = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
    except Exception:
        pass


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, theme, on_apply, on_reset=None):
        super().__init__(parent)
        self.config_data = config
        self.theme = theme
        self.on_apply = on_apply
        self.on_reset = on_reset

        self.title('Ville — Настройки')
        self.geometry('640x740')
        self.minsize(580, 580)
        self.configure(fg_color=BG)
        self.attributes('-topmost', True)

        self._theme_draft = dict(theme.data)
        self._color_widgets = {}
        self._verb_entries = {}
        self._hotkey_listening = False
        self._original_hotkey = config.hotkey

        tabs = ctk.CTkTabview(
            self, fg_color=BG,
            segmented_button_fg_color=PANEL,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT,
            text_color=FG,
        )
        tabs.pack(fill='both', expand=True, padx=12, pady=(12, 6))
        tabs.add('Внешний вид')
        tabs.add('Команды')
        tabs.add('Общие')
        self._build_appearance(tabs.tab('Внешний вид'))
        self._build_commands(tabs.tab('Команды'))
        self._build_general(tabs.tab('Общие'))

        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(fill='x', padx=12, pady=(0, 12))

        self.save_btn = ctk.CTkButton(
            bottom, text='Сохранить', width=130,
            fg_color=ACCENT, text_color=BG, hover_color=ACCENT,
            command=self._save,
        )
        self.save_btn.pack(side='right', padx=(6, 0))

        ctk.CTkButton(
            bottom, text='Готово', width=100,
            fg_color=INPUT, text_color=FG, hover_color=PANEL,
            command=self.destroy,
        ).pack(side='right')

        ctk.CTkButton(
            bottom, text='Сброс…', width=90,
            fg_color=DANGER, text_color=FG, hover_color='#a30d2d',
            command=self._reset,
        ).pack(side='left')

        self.after(50, lambda: _apply_win_rounding(self))
        # Esc закрывает только окно настроек, не трогая лаунчер
        self.bind('<Escape>', lambda e: self.destroy())

    # ---------- внешний вид ----------
    def _build_appearance(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=PANEL, corner_radius=8)
        scroll.pack(fill='both', expand=True, padx=4, pady=4)

        ctk.CTkLabel(scroll, text='Цвета темы',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x', padx=8, pady=(8, 6))
        for key, label in COLOR_KEYS:
            self._add_color_row(scroll, key, label)

        ctk.CTkLabel(scroll, text='Размеры',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x', padx=8, pady=(16, 6))
        self._add_number_row(scroll, 'font_size', 'Размер шрифта', min_value=8)
        self._add_number_row(scroll, 'corner_radius', 'Радиус закругления', min_value=0)

    def _add_color_row(self, parent, key, label):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=8, pady=3)
        ctk.CTkLabel(row, text=label, anchor='w', width=200,
                     text_color=FG).pack(side='left')
        value = self._theme_draft.get(key, '#000000')
        swatch = ctk.CTkLabel(row, text='', width=40, height=24,
                              fg_color=value, corner_radius=4)
        swatch.pack(side='left', padx=(0, 8))
        hex_label = ctk.CTkLabel(row, text=value, width=90, anchor='w',
                                 text_color=MUTED, font=('Consolas', 11))
        hex_label.pack(side='left', padx=(0, 8))
        ctk.CTkButton(row, text='Изменить', width=90,
                      fg_color=INPUT, text_color=FG, hover_color=PANEL,
                      command=lambda k=key: self._pick_color(k)).pack(side='left')
        self._color_widgets[key] = (swatch, hex_label, None)

    def _add_number_row(self, parent, key, label, min_value=0):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=8, pady=3)
        ctk.CTkLabel(row, text=label, anchor='w', width=200,
                     text_color=FG).pack(side='left')
        entry = ctk.CTkEntry(row, width=80, fg_color=INPUT,
                             text_color=FG, border_width=0)
        entry.insert(0, str(self._theme_draft.get(key, min_value)))
        entry.pack(side='left')
        self._color_widgets[key] = (None, entry, min_value)

    def _pick_color(self, key):
        current = self._theme_draft.get(key, '#000000')
        # снимаем topmost на время диалога — иначе Windows ведёт себя странно
        self.attributes('-topmost', False)
        try:
            _, hex_color = colorchooser.askcolor(
                color=current,
                title=f'Цвет: {key}',
                parent=self,          # ← модальный диалог для окна настроек
            )
        finally:
            # возвращаем topmost и поднимаем окно наверх
            self.attributes('-topmost', True)
            self.lift()
            self.focus_force()

        if not hex_color:
            return
        self._theme_draft[key] = hex_color
        swatch, hex_label, _ = self._color_widgets[key]
        swatch.configure(fg_color=hex_color)
        hex_label.configure(text=hex_color)

    # ---------- команды ----------
    def _build_commands(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=PANEL, corner_radius=8)
        scroll.pack(fill='both', expand=True, padx=4, pady=4)
        ctk.CTkLabel(
            scroll,
            text='Какое имя вводить в поле. Внутренняя логика не меняется — '
                 'меняется только то, что печатает пользователь.',
            wraplength=480, justify='left', text_color=MUTED, anchor='w',
        ).pack(fill='x', padx=8, pady=(8, 12))
        for key, user_name in dict(self.config_data.verbs).items():
            row = ctk.CTkFrame(scroll, fg_color='transparent')
            row.pack(fill='x', padx=8, pady=4)
            ctk.CTkLabel(row, text=VERB_DESCRIPTIONS.get(key, key),
                         anchor='w', width=200, text_color=FG).pack(side='left')
            ctk.CTkLabel(row, text='/', width=12,
                         text_color=MUTED).pack(side='left')
            entry = ctk.CTkEntry(row, width=180, fg_color=INPUT,
                                 text_color=FG, border_width=0)
            entry.insert(0, user_name)
            entry.pack(side='left')
            self._verb_entries[key] = entry

    # ---------- общие ----------
    def _build_general(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=PANEL, corner_radius=8)
        scroll.pack(fill='both', expand=True, padx=4, pady=4)

        ctk.CTkLabel(scroll, text='Запуск',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x', padx=8, pady=(8, 6))

        self._autostart_var = ctk.BooleanVar(value=autostart.is_enabled())
        ctk.CTkCheckBox(
            scroll, text='Запускать вместе с Windows',
            variable=self._autostart_var,
            font=('Segoe UI', 12),
            text_color=FG, fg_color=ACCENT, hover_color=ACCENT,
            checkmark_color=BG,
        ).pack(fill='x', padx=12, pady=4)

        ctk.CTkLabel(
            scroll,
            text='При автозапуске окно не открывается — лаунчер ждёт хоткея в трее.',
            wraplength=480, justify='left', text_color=MUTED, anchor='w',
            font=('Segoe UI', 10),
        ).pack(fill='x', padx=12, pady=(0, 12))

        ctk.CTkLabel(
            scroll, text='Поведение окна',
            font=('Segoe UI', 13, 'bold'), text_color=FG, anchor='w',
        ).pack(fill='x', padx=8, pady=(16, 6))

        self._autohide_var = ctk.BooleanVar(
            value=self.config_data.window.get('autohide_on_blur', True)
        )
        ctk.CTkCheckBox(
            scroll, text='Скрывать при клике вне окна',
            variable=self._autohide_var,
            font=('Segoe UI', 12),
            text_color=FG, fg_color=ACCENT, hover_color=ACCENT,
            checkmark_color=BG,
        ).pack(fill='x', padx=12, pady=4)

        ctk.CTkLabel(
            scroll,
            text='Если выключено — окно закрывается только по Escape '
                'или повторному нажатию хоткея.',
            wraplength=480, justify='left', text_color=MUTED, anchor='w',
            font=('Segoe UI', 10),
        ).pack(fill='x', padx=12, pady=(0, 12))

        ctk.CTkLabel(scroll, text='Проводник',
                    font=('Segoe UI', 13, 'bold'),
                    text_color=FG, anchor='w').pack(fill='x', padx=8, pady=(16, 6))

        self._explorer_var = ctk.BooleanVar(value=explorer_menu.is_enabled())
        ctk.CTkCheckBox(
            scroll, text='Пункт «Задать алиас в Ville» в контекстном меню',
            variable=self._explorer_var,
            font=('Segoe UI', 12),
            text_color=FG, fg_color=ACCENT, hover_color=ACCENT,
            checkmark_color=BG,
        ).pack(fill='x', padx=12, pady=4)

        ctk.CTkLabel(
            scroll,
            text='Правый клик по файлу или папке в проводнике → '
                '«Задать алиас в Ville» → ввести имя.',
            wraplength=480, justify='left', text_color=MUTED, anchor='w',
            font=('Segoe UI', 10),
        ).pack(fill='x', padx=12, pady=(0, 12))

        ctk.CTkLabel(scroll, text='Горячая клавиша',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x', padx=8, pady=(8, 6))

        row = ctk.CTkFrame(scroll, fg_color='transparent')
        row.pack(fill='x', padx=12, pady=4)

        self._hotkey_var = ctk.StringVar(value=self.config_data.hotkey)
        self._hotkey_entry = ctk.CTkEntry(
            row, textvariable=self._hotkey_var, width=280,
            fg_color=INPUT, text_color=FG, border_width=0,
            font=('Consolas', 12),
        )
        self._hotkey_entry.pack(side='left')
        self._hotkey_entry.bind('<Button-1>', lambda e: self._capture_hotkey_start())

        ctk.CTkLabel(
            row, text='← кликните, чтобы изменить',
            text_color=MUTED, font=('Segoe UI', 10),
        ).pack(side='left', padx=(8, 0))

        ctk.CTkLabel(
            scroll,
            text='Клик по полю — затем нажмите комбинацию. '
                 'Enter — подтвердить, Esc — отмена.',
            wraplength=480, justify='left', text_color=MUTED, anchor='w',
            font=('Segoe UI', 10),
        ).pack(fill='x', padx=12, pady=(4, 12))

    # ---------- захват хоткея ----------
    def _capture_hotkey_start(self):
        if self._hotkey_listening:
            return
        self._hotkey_listening = True
        self._original_hotkey = self.config_data.hotkey
        self._hotkey_var.set('Нажмите комбинацию…')
        try:
            self._hotkey_entry.configure(state='disabled')
        except Exception:
            pass
        threading.Thread(target=self._capture_hotkey_worker, daemon=True).start()

    def _capture_hotkey_worker(self):
        try:
            combo = keyboard.read_hotkey(suppress=False)
        except Exception:
            combo = None

        if not self.winfo_exists():
            return

        if combo is None or combo.lower() == 'esc':
            self.after(0, lambda: self._finish_hotkey(self._original_hotkey))
            return

        self.after(0, lambda c=combo: self._hotkey_var.set(
            f'{c}   [Enter — ОК, Esc — отмена]'
        ))

        try:
            while True:
                key = keyboard.read_key(suppress=False).lower()
                if not self.winfo_exists():
                    return
                if key == 'enter':
                    self.after(0, lambda c=combo: self._finish_hotkey(c))
                    return
                if key == 'esc':
                    self.after(0, lambda: self._finish_hotkey(self._original_hotkey))
                    return
                if key in _MODIFIER_KEYS:
                    continue
        except Exception:
            self.after(0, lambda: self._finish_hotkey(self._original_hotkey))

    def _finish_hotkey(self, value):
        self._hotkey_var.set(value)
        self._hotkey_listening = False
        try:
            self._hotkey_entry.configure(state='normal')
        except Exception:
            pass

    # ---------- сохранение ----------
    def _save(self):
        if self._hotkey_listening:
            self._error('Дождитесь окончания записи хоткея (Enter или Esc)')
            return

        new_verbs = {}
        seen = set()
        existing_aliases = {a.lower() for a in self.config_data.shortcuts}
        for key, entry in self._verb_entries.items():
            name = entry.get().strip().lstrip('/')
            if not name:
                self._error(f'«{VERB_DESCRIPTIONS.get(key, key)}»: имя не может быть пустым')
                return
            if not name.replace('-', '').replace('_', '').isalnum():
                self._error(f'«{name}»: разрешены только буквы, цифры, _ и -')
                return
            if name.lower() in seen:
                self._error(f'Имя «{name}» используется дважды')
                return
            if name.lower() in existing_aliases:
                self._error(f'«{name}» уже занято как алиас')
                return
            seen.add(name.lower())
            new_verbs[key] = name

        for key in ('font_size', 'corner_radius'):
            _, entry, min_value = self._color_widgets[key]
            try:
                value = int(entry.get())
            except ValueError:
                self._error(f'«{key}»: должно быть целое число')
                return
            if value < min_value:
                self._error(f'«{key}»: минимум {min_value}')
                return
            self._theme_draft[key] = value

        new_hotkey = self._hotkey_var.get().strip().lower()
        if not new_hotkey or '[' in new_hotkey:
            self._error('Хоткей не задан')
            return
        try:
            keyboard.parse_hotkey(new_hotkey)
        except (ValueError, KeyError) as e:
            self._error(f'Некорректный хоткей «{new_hotkey}»: {e}')
            return

        want_explorer = bool(self._explorer_var.get())
        if want_explorer != explorer_menu.is_enabled():
            try:
                if want_explorer:
                    explorer_menu.enable()
                else:
                    explorer_menu.disable()
            except OSError as e:
                self._error(f'Не удалось изменить меню проводника: {e}')
                return

        want_autostart = bool(self._autostart_var.get())
        if want_autostart != autostart.is_enabled():
            if not autostart.set_enabled(want_autostart):
                self._error('Не удалось изменить автозапуск (нет доступа к реестру)')
                return

        theme_path = themes_dir() / f'{self.config_data.theme}.json'
        try:
            existing = {}
            if theme_path.exists():
                existing = json.loads(theme_path.read_text(encoding='utf-8'))
            existing.update(self._theme_draft)
            theme_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False),
                encoding='utf-8')
        except OSError as e:
            self._error(f'Не удалось сохранить тему: {e}')
            return

        self.config_data.data['window']['autohide_on_blur'] = bool(self._autohide_var.get())
        self.config_data.data['verbs'] = new_verbs
        self.config_data.data['hotkey'] = new_hotkey
        try:
            self.config_data.save()
        except OSError as e:
            self._error(f'Не удалось сохранить конфиг: {e}')
            return

        try:
            self.on_apply(self._theme_draft, new_verbs, new_hotkey)
        except Exception as e:
            self._error(f'Сохранено, но применение упало: {e}')
            return

        self._show_saved_feedback()

    def _show_saved_feedback(self):
        original_text = self.save_btn.cget('text')
        self.save_btn.configure(text='✓ Сохранено', fg_color=SUCCESS)
        def restore():
            try:
                self.save_btn.configure(text=original_text, fg_color=ACCENT)
            except Exception:
                pass
        self.after(1500, restore)

    # ---------- сброс ----------
    def _reset(self):
        if self.on_reset is None:
            return
        if not messagebox.askyesno(
            'Сброс к заводским настройкам',
            'Сбросить все настройки?\n\n'
            'Будут сброшены: цвета, команды, хоткей, автозапуск.\n'
            'Зарегистрированные алиасы (файлы/папки) НЕ удаляются.\n\n'
            'Приложение перезапустится.',
            parent=self,
        ):
            return
        self.on_reset()

    def _error(self, text):
        messagebox.showerror('Ошибка', text, parent=self)