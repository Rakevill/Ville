"""Диалог ввода имени алиаса (из контекстного меню проводника)."""
import os
from tkinter import messagebox

import customtkinter as ctk


BG     = '#1e1e2e'
PANEL  = '#181825'
INPUT  = '#313244'
FG     = '#cdd6f4'
MUTED  = '#6c7086'
ACCENT = '#89b4fa'


class SetAliasDialog(ctk.CTkToplevel):
    def __init__(self, parent, path, existing_aliases, on_accept):
        super().__init__(parent)
        self.path = path
        self.existing_aliases = {a.lower() for a in existing_aliases}
        self.on_accept = on_accept

        self.title('Ville — Задать алиас')
        self.geometry('500x240')
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.attributes('-topmost', True)

        ctk.CTkLabel(self, text='Путь:', anchor='w',
                     text_color=MUTED, font=('Segoe UI', 11)
                     ).pack(fill='x', padx=16, pady=(16, 2))

        ctk.CTkLabel(
            self, text=path, anchor='w', text_color=FG,
            font=('Consolas', 11), wraplength=460, justify='left',
        ).pack(fill='x', padx=16)

        ctk.CTkLabel(self, text='Имя для команды /open:', anchor='w',
                     text_color=FG, font=('Segoe UI', 12)
                     ).pack(fill='x', padx=16, pady=(14, 4))

        self.entry = ctk.CTkEntry(
            self, width=460, height=36,
            fg_color=INPUT, text_color=FG, border_width=0,
            font=('Consolas', 12),
        )
        self.entry.pack(padx=16)

        base = os.path.splitext(os.path.basename(path.rstrip('\\/')))[0]
        suggested = base.lower().replace(' ', '_')[:32]
        if suggested and suggested.replace('-', '').replace('_', '').isalnum():
            self.entry.insert(0, suggested)
            self.entry.select_range(0, 'end')

        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(fill='x', padx=16, pady=(16, 16))

        ctk.CTkButton(btns, text='Отмена', width=100,
                      fg_color=INPUT, text_color=FG, hover_color=PANEL,
                      command=self.destroy).pack(side='right', padx=(6, 0))

        ctk.CTkButton(btns, text='Сохранить', width=120,
                      fg_color=ACCENT, text_color=BG, hover_color=ACCENT,
                      command=self._save).pack(side='right')

        self.bind('<Return>', lambda e: self._save())
        self.bind('<Escape>', lambda e: self.destroy())
        self.after(50, self.entry.focus_force)

    def _save(self):
        name = self.entry.get().strip().lstrip('/')
        if not name:
            messagebox.showerror('Ошибка', 'Имя не может быть пустым', parent=self)
            return
        if not name.replace('-', '').replace('_', '').isalnum():
            messagebox.showerror('Ошибка',
                                 'Разрешены только буквы, цифры, _ и -',
                                 parent=self)
            return
        if name.lower() in self.existing_aliases:
            messagebox.showerror('Ошибка',
                                 f'Алиас «{name}» уже занят', parent=self)
            return
        try:
            self.on_accept(name)
        except Exception as e:
            messagebox.showerror('Ошибка', str(e), parent=self)
            return
        self.destroy()