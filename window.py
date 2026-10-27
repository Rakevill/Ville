"""Главное окно лаунчера.

Без системной рамки, перетаскивается за любое место,
скрывается по Escape и по потере фокуса, хранит позицию в конфиге.
"""
import time

import customtkinter as ctk

from autocomplete import Autocomplete
from commands import ExitRequested

__version__ = 'v0.0.1-beta'


class LauncherWindow(ctk.CTk):
    def __init__(self, config, theme, registry, on_exit=None):
        super().__init__()
        self.config = config
        self.theme = theme
        self.registry = registry
        self.on_exit = on_exit

        # ---------- окно ----------
        w = config.window
        x, y = self._validate_position(w['x'], w['y'])
        self.geometry(f'{w["width"]}x{w["height"]}+{x}+{y}')
        self.overrideredirect(True)
        self.attributes('-topmost', bool(w['always_on_top']))
        self.configure(fg_color=theme['window_bg'])
        self._opened_at = time.monotonic()

        # ---------- фрейм-подложка ----------
        self.frame = ctk.CTkFrame(
            self,
            fg_color=theme['window_bg'],
            border_color=theme['window_border'],
            border_width=1,
            corner_radius=theme['corner_radius'],
        )
        self.frame.pack(fill='both', expand=True, padx=1, pady=1)

        # ---------- строка ввода с промптом ----------
        input_row = ctk.CTkFrame(self.frame, fg_color='transparent', height=40)
        input_row.pack(fill='x', padx=10, pady=(10, 6))
        input_row.pack_propagate(False)

        ctk.CTkLabel(
            input_row,
            text='›',
            font=(theme['font_family'], theme['font_size'] + 6),
            text_color=theme['accent'],
            width=16,
        ).pack(side='left', padx=(2, 6))

        self.input = ctk.CTkEntry(
            input_row,
            placeholder_text='/openset "C:\\path" alias',
            fg_color=theme['input_bg'],
            text_color=theme['input_fg'],
            border_width=0,
            corner_radius=theme['corner_radius'],
            font=(theme['font_family'], theme['font_size']),
            height=40,
        )
        self.input.pack(side='left', fill='x', expand=True)
        self.input.bind('<Return>', self._on_enter)
        self.input.bind('<Escape>', lambda e: self.withdraw())

        # ---------- поле вывода ----------
        self.output = ctk.CTkTextbox(
            self.frame,
            fg_color=theme['list_bg'],
            text_color=theme['list_fg'],
            border_width=0,
            corner_radius=theme['corner_radius'],
            font=(theme.get('font_mono', 'Consolas'), theme['font_size'] - 1),
        )
        self.output.pack(fill='both', expand=True, padx=10, pady=(0, 6))
        self.output.tag_config('error', foreground=theme['list_error'])

        # ---------- футер ----------
        footer = ctk.CTkFrame(self.frame, fg_color='transparent', height=20)
        footer.pack(fill='x', padx=10, pady=(0, 8))

        self.hints = ctk.CTkLabel(
            footer,
            text='↑↓ история  ·  Tab доп.  ·  Enter вып.  ·  Esc скрыть',
            font=(theme['font_family'], theme['font_size'] - 3),
            text_color=theme['footer_fg'],
            anchor='w',
        )
        self.hints.pack(side='left')

        ctk.CTkLabel(
            footer,
            text=__version__,
            font=(theme['font_family'], theme['font_size'] - 3),
            text_color=theme['footer_fg'],
        ).pack(side='right')

        # ---------- автодополнение ----------
        self.autocomplete = Autocomplete(
            parent=self.frame,
            entry=self.input,
            output=self.output,
            config=config,
            execute_cb=self._execute_current,
            theme=theme,
            on_state_change=self._update_footer_hint,
        )

        # ---------- история ----------
        self.history = list(self.config.data.get('history', []))
        self.history_idx = len(self.history)
        self.history_draft = ''
        self.input.bind('<Up>',   self._on_history_up,   add='+')
        self.input.bind('<Down>', self._on_history_down, add='+')

        # ---------- перетаскивание ----------
        self._dx = self._dy = 0
        for widget in (self.frame, input_row, self.output):
            widget.bind('<Button-1>', self._drag_start)
            widget.bind('<B1-Motion>', self._drag_move)

        # ---------- потеря фокуса ----------
        self.bind('<FocusOut>', self._on_blur)

        self.focus_input()

    # ========== показ / фокус ==========
    def focus_input(self):
        self._opened_at = time.monotonic()
        self.input.focus_set()
        self.input.select_range(0, 'end')

    def _update_footer_hint(self):
        if self.autocomplete.active:
            text = '↑↓ выбор  ·  Tab вставить  ·  Enter выполнить  ·  Esc скрыть'
        else:
            text = '↑↓ история  ·  Tab доп.  ·  Enter вып.  ·  Esc скрыть'
        self.hints.configure(text=text)

    # ========== выполнение ==========
    def _on_enter(self, _=None):
        self._execute_current()

    def _execute_current(self):
        text = self.input.get().strip()
        if not text:
            return
        self._add_history(text)
        try:
            result = self.registry.execute(text)
            if result:
                self._append(result)
        except ExitRequested:
            if self.on_exit:
                self.on_exit()
            else:
                self.destroy()
            return
        except Exception as e:
            self._append(f'Ошибка: {e}', error=True)
        self.input.delete(0, 'end')
        self.history_idx = len(self.history)
        self.history_draft = ''

    def _append(self, text: str, error: bool = False):
        self.output.insert('end', text + '\n', 'error' if error else '')
        self.output.see('end')

    # ========== история ==========
    def _add_history(self, text: str):
        if self.history and self.history[-1] == text:
            return
        self.history.append(text)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        self.config.data['history'] = self.history
        self.config.save()

    def _on_history_up(self, _):
        if self.autocomplete.active:
            return
        if not self.history:
            return 'break'
        if self.history_idx == len(self.history):
            self.history_draft = self.input.get()
        self.history_idx = max(0, self.history_idx - 1)
        self._set_input(self.history[self.history_idx])
        return 'break'

    def _on_history_down(self, _):
        if self.autocomplete.active:
            return
        if not self.history:
            return 'break'
        self.history_idx = min(len(self.history), self.history_idx + 1)
        if self.history_idx == len(self.history):
            self._set_input(self.history_draft)
        else:
            self._set_input(self.history[self.history_idx])
        return 'break'

    def _set_input(self, text: str):
        self.input.delete(0, 'end')
        self.input.insert(0, text)
        self.input.icursor('end')

    # ========== перетаскивание ==========
    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.winfo_x() + (e.x - self._dx)
        y = self.winfo_y() + (e.y - self._dy)
        self.geometry(f'+{x}+{y}')

    # ========== скрытие по потере фокуса ==========
    def _on_blur(self, _):
        if not self.config.window.get('autohide_on_blur', True):
            return
        self.after(150, self._maybe_hide)

    def _maybe_hide(self):
        if not self.winfo_viewable():
            return
        if time.monotonic() - self._opened_at < 0.5:
            return
        if self.focus_get() is not None:
            return
        self.config.data['window']['x'] = self.winfo_x()
        self.config.data['window']['y'] = self.winfo_y()
        self.config.save()
        self.withdraw()

    # ========== тема ==========
    def apply_theme(self, new_theme):
        self.theme = new_theme
        self.configure(fg_color=new_theme['window_bg'])
        self.frame.configure(
            fg_color=new_theme['window_bg'],
            border_color=new_theme['window_border'],
        )
        self.input.configure(
            fg_color=new_theme['input_bg'],
            text_color=new_theme['input_fg'],
        )
        self.output.configure(
            fg_color=new_theme['list_bg'],
            text_color=new_theme['list_fg'],
        )
        self.output.tag_config('error', foreground=new_theme['list_error'])
        self.hints.configure(text_color=new_theme['footer_fg'])
        self.autocomplete.theme = new_theme
        if self.autocomplete.active:
            self.autocomplete._show(self.autocomplete.items)

    # ========== валидация позиции ==========
    def _validate_position(self, x: int, y: int):
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
        except Exception:
            return x, y
        if not (0 <= x < sw - 50 and 0 <= y < sh - 50):
            return 100, 100
        return x, y