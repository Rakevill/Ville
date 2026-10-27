"""Окно настроек: цвета темы и переименование команд."""
import json
import tkinter.colorchooser as colorchooser
from tkinter import messagebox

import customtkinter as ctk

from theme import themes_dir


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
}

BG     = '#1e1e2e'
PANEL  = '#181825'
INPUT  = '#313244'
FG     = '#cdd6f4'
MUTED  = '#6c7086'
ACCENT = '#89b4fa'
SUCCESS = '#40a02b'


def _apply_win_rounding(window):
    """Win11: скруглить углы через DWM. Win10 1809+: тёмный тайтлбар.
    На старых Windows — тихо ничего не делает."""
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT
        if not hwnd:
            return
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
        pref = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref),
        )
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark),
        )
    except Exception:
        pass


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, config, theme, on_apply):
        super().__init__(parent)
        self.config_data = config
        self.theme = theme
        self.on_apply = on_apply

        self.title('Ville — Настройки')
        self.geometry('620x680')
        self.minsize(560, 520)
        self.configure(fg_color=BG)
        self.attributes('-topmost', True)

        self._theme_draft = dict(theme.data)
        self._color_widgets = {}
        self._verb_entries = {}

        tabs = ctk.CTkTabview(
            self,
            fg_color=BG,
            segmented_button_fg_color=PANEL,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT,
            text_color=FG,
        )
        tabs.pack(fill='both', expand=True, padx=12, pady=(12, 6))
        tabs.add('Внешний вид')
        tabs.add('Команды')
        self._build_appearance(tabs.tab('Внешний вид'))
        self._build_commands(tabs.tab('Команды'))

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

        # скругляем углы окна после того, как оно отрисовалось
        self.after(50, lambda: _apply_win_rounding(self))

    # ---------- внешний вид ----------
    def _build_appearance(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color=PANEL, corner_radius=8)
        scroll.pack(fill='both', expand=True, padx=4, pady=4)

        ctk.CTkLabel(
            scroll, text='Цвета темы',
            font=('Segoe UI', 13, 'bold'), text_color=FG, anchor='w',
        ).pack(fill='x', padx=8, pady=(8, 6))

        for key, label in COLOR_KEYS:
            self._add_color_row(scroll, key, label)

        ctk.CTkLabel(
            scroll, text='Размеры',
            font=('Segoe UI', 13, 'bold'), text_color=FG, anchor='w',
        ).pack(fill='x', padx=8, pady=(16, 6))

        self._add_number_row(scroll, 'font_size', 'Размер шрифта')
        self._add_number_row(scroll, 'corner_radius', 'Радиус закругления')

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

        ctk.CTkButton(
            row, text='Изменить', width=90,
            fg_color=INPUT, text_color=FG, hover_color=PANEL,
            command=lambda k=key: self._pick_color(k),
        ).pack(side='left')

        self._color_widgets[key] = (swatch, hex_label)

    def _add_number_row(self, parent, key, label):
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=8, pady=3)

        ctk.CTkLabel(row, text=label, anchor='w', width=200,
                     text_color=FG).pack(side='left')

        entry = ctk.CTkEntry(row, width=80,
                             fg_color=INPUT, text_color=FG, border_width=0)
        entry.insert(0, str(self._theme_draft.get(key, 0)))
        entry.pack(side='left')

        self._color_widgets[key] = (None, entry)

    def _pick_color(self, key):
        current = self._theme_draft.get(key, '#000000')
        _, hex_color = colorchooser.askcolor(
            color=current, title=f'Цвет: {key}',
        )
        if not hex_color:
            return
        self._theme_draft[key] = hex_color
        swatch, hex_label = self._color_widgets[key]
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
            wraplength=480, justify='left',
            text_color=MUTED, anchor='w',
        ).pack(fill='x', padx=8, pady=(8, 12))

        for key, user_name in dict(self.config_data.verbs).items():
            row = ctk.CTkFrame(scroll, fg_color='transparent')
            row.pack(fill='x', padx=8, pady=4)

            ctk.CTkLabel(row, text=VERB_DESCRIPTIONS.get(key, key),
                         anchor='w', width=200,
                         text_color=FG).pack(side='left')

            ctk.CTkLabel(row, text='/', width=12,
                         text_color=MUTED).pack(side='left')

            entry = ctk.CTkEntry(row, width=180,
                                 fg_color=INPUT, text_color=FG, border_width=0)
            entry.insert(0, user_name)
            entry.pack(side='left')
            self._verb_entries[key] = entry

    # ---------- сохранение ----------
    def _save(self):
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
            _, entry = self._color_widgets[key]
            try:
                value = int(entry.get())
                if value < 1:
                    raise ValueError
                self._theme_draft[key] = value
            except ValueError:
                self._error('Размеры должны быть целыми положительными числами')
                return

        theme_path = themes_dir() / f'{self.config_data.theme}.json'
        try:
            existing = {}
            if theme_path.exists():
                existing = json.loads(theme_path.read_text(encoding='utf-8'))
            existing.update(self._theme_draft)
            theme_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except OSError as e:
            self._error(f'Не удалось сохранить тему: {e}')
            return

        self.config_data.data['verbs'] = new_verbs
        try:
            self.config_data.save()
        except OSError as e:
            self._error(f'Не удалось сохранить конфиг: {e}')
            return

        try:
            self.on_apply(self._theme_draft, new_verbs)
        except Exception as e:
            self._error(f'Сохранено, но применение упало: {e}')
            return

        # не закрываем окно — показываем обратную связь
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

    def _error(self, text):
        messagebox.showerror('Ошибка', text, parent=self)