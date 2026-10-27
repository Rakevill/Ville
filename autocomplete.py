"""Подсказки для поля ввода.

Три режима, выбираются автоматически по содержимому поля:

  verb   — ввод '/' или '/op'        → список глаголов
  alias  — '/open <partial>'         → алиасы из shortcuts
  path   — '/openset "<partial>'     → содержимое каталога

Возвращает 'break' из обработчиков ↑/↓/Tab/Esc/Enter, когда подсказка
активна, чтобы приоритет был у автодополнения, а не у истории команд
в window.py. Порядок привязок важен: autocomplete биндится ДО истории.

Команды принимаются и со слешем, и без него — если пользователь начал
ввод без '/', подсказки всё равно работают, а подстановка сохраняет
стиль пользователя (со слешем или без).
"""
import os
import re

import customtkinter as ctk


MAX_ITEMS = 12 # Максимальное число глаголов (подсказок)


class Autocomplete:
    def __init__(self, parent, entry, output, config, execute_cb, theme,
                 on_state_change=None):
        self.entry = entry
        self.output = output
        self.config = config
        self.execute_cb = execute_cb
        self.theme = theme
        self.on_state_change = on_state_change

        # Ищем по ВНУТРЕННИМ ключам (open, openset), а не по именам,
        # которые видит пользователь: при /openset→fset переименовании
        # внутренний ключ остаётся 'openset', и автодополнение работает.
        self._open_verbs    = {v for k, v in config.verbs.items() if k == 'open'}
        self._openset_verbs = {v for k, v in config.verbs.items() if k == 'openset'}

        self.frame = ctk.CTkFrame(
            parent,
            fg_color=theme['list_bg'],
            corner_radius=theme['corner_radius'],
            border_width=0,
        )
        self.labels = []
        self.items = []
        self.path_items = []
        self.selected = 0
        self.active = False
        self.user_navigated = False
        self.mode = None          # 'verb' | 'alias' | 'path'

        entry.bind('<KeyRelease>', self._on_key)
        entry.bind('<Down>',       self._on_down)
        entry.bind('<Up>',         self._on_up)
        entry.bind('<Tab>',        self._on_tab)
        entry.bind('<Return>',     self._on_enter,  add='+')
        entry.bind('<Escape>',     self._on_escape, add='+')

    # ============ маршрутизация ============
    def _update_suggestions(self):
        text = self.entry.get()
        # Работаем с нормализованной строкой (со слешем),
        # а _complete читает entry.get() — там оригинал, со стилем.
        norm = text if text.startswith('/') else '/' + text if text else text

        # 1) путь для /openset — приоритетно
        prefix = self._detect_path_prefix(norm)
        if prefix is not None:
            entries = self._list_path(prefix)
            if entries:
                self.mode = 'path'
                self.path_items = entries
                self.user_navigated = False
                self._show([
                    f"{'📁' if e['is_dir'] else '📄'} {e['name']}"
                    + (os.sep if e['is_dir'] else '')
                    for e in entries
                ])
            else:
                self._hide()
            return

        # 2) /verb без пробела
        m = re.match(r'^/(\w*)$', norm)
        if m:
            partial = m.group(1).lower()
            verbs = sorted(set(self.config.verbs.values()))
            matches = [v for v in verbs if v.lower().startswith(partial)]
            if matches:
                self.mode = 'verb'
                self.user_navigated = False
                self._show(matches)
            else:
                self._hide()
            return

        # 3) /open <partial>
        m = re.match(r'^/(\w+)\s(.*)$', norm)
        if m:
            verb, partial = m.group(1).lower(), m.group(2)
            if verb in self._open_verbs:
                aliases = sorted(self.config.shortcuts.keys())
                matches = [a for a in aliases
                           if a.lower().startswith(partial.lower())]
                if matches:
                    self.mode = 'alias'
                    self.user_navigated = False
                    self._show(matches)
                else:
                    self._hide()
                return

        self._hide()

    # ============ пути ============
    def _detect_path_prefix(self, text):
        """Вернуть путь-префикс, если курсор в незакрытой кавычке
        первого аргумента openset-команды. text — со слешем."""
        m = re.match(r'^/(\w+)\s(.*)$', text)
        if not m:
            return None
        verb, rest = m.groups()
        if verb not in self._openset_verbs:
            return None
        if rest.startswith('"'):
            return rest[1:] if rest.count('"') == 1 else None
        if rest and ' ' not in rest:
            return rest
        return None

    def _list_path(self, prefix):
        try:
            expanded = os.path.expandvars(prefix)
            if not expanded:
                return []
            if re.match(r'^[A-Za-z]:$', expanded):
                parent_dir, partial = expanded + os.sep, ''
            elif expanded.endswith((os.sep, '/')):
                parent_dir, partial = expanded, ''
            else:
                parent_dir = os.path.dirname(expanded) or '.'
                partial    = os.path.basename(expanded)

            entries = []
            with os.scandir(parent_dir) as it:
                for e in it:
                    if not e.name.lower().startswith(partial.lower()):
                        continue
                    try:
                        is_dir = e.is_dir()
                    except OSError:
                        is_dir = False
                    entries.append({
                        'name':   e.name,
                        'path':   os.path.join(parent_dir, e.name),
                        'is_dir': is_dir,
                    })
            entries.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return entries
        except (OSError, PermissionError, ValueError):
            return []

    def _complete_path(self):
        if not self.path_items:
            return
        item = self.path_items[self.selected]
        m = re.match(r'^(/?)(\w+)\s', self.entry.get())
        if not m:
            return
        slash, verb_part = m.group(1), m.group(2)

        if item['is_dir']:
            self._set_input(f'{slash}{verb_part} "{item["path"]}{os.sep}')
            self._hide()
            self._update_suggestions()
        else:
            self._set_input(f'{slash}{verb_part} "{item["path"]}" ')
            self._hide()

    # ============ клавиши ============
    def _on_key(self, event):
        if event.keysym in (
            'Up', 'Down', 'Tab', 'Escape', 'Return',
            'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
            'Alt_L', 'Alt_R',
        ):
            return
        self._update_suggestions()

    def _on_down(self, _):
        if not self.active:
            return
        self.user_navigated = True
        self.selected = (self.selected + 1) % len(self.items)
        self._highlight()
        return 'break'

    def _on_up(self, _):
        if not self.active:
            return
        self.user_navigated = True
        self.selected = (self.selected - 1) % len(self.items)
        self._highlight()
        return 'break'

    def _on_tab(self, _):
        if not self.active:
            return
        self._complete()
        return 'break'

    def _on_enter(self, _):
        if not self.active:
            return
        if self.mode == 'path':
            self._complete()
            return 'break'
        if self.mode == 'verb':
            if self.user_navigated and self.items:
                # пользователь явно выбрал — подставить и выполнить
                raw = self.entry.get()
                slash = '/' if raw.startswith('/') else ''
                self._set_input(f'{slash}{self.items[self.selected]}')
                self._hide()
                self.execute_cb()
                return 'break'
            if len(self.items) == 1:
                # единственное — тоже выполнить
                raw = self.entry.get()
                slash = '/' if raw.startswith('/') else ''
                self._set_input(f'{slash}{self.items[0]}')
                self._hide()
                self.execute_cb()
                return 'break'
            # несколько без навигации — как Tab
            self._complete()
            return 'break'
        # alias: выполнить, если навигация была ИЛИ совпадение единственное
        if self.items and (self.user_navigated or len(self.items) == 1):
            self._complete()
            self._hide()
            self.execute_cb()
            return 'break'
        self._hide()

    def _on_escape(self, _):
        if self.active:
            self._hide()
            return 'break'

    def _on_click(self, index):
        self.selected = index
        self.user_navigated = True
        mode = self.mode
        self._complete()
        if mode == 'alias':
            self._hide()
            self.execute_cb()

    def _on_hover(self, index):
        if index == self.selected or index >= len(self.labels):
            return
        self.labels[index].configure(fg_color=self.theme['list_hover'])

    def _on_unhover(self):
        for i, lbl in enumerate(self.labels):
            if i != self.selected:
                lbl.configure(fg_color='transparent')

    # ============ завершение ============
    def _complete(self):
        if not self.items:
            return
        if self.mode == 'path':
            self._complete_path()
            return
        if self.mode == 'verb':
            raw = self.entry.get()
            slash = '/' if raw.startswith('/') else ''
            self._set_input(f'{slash}{self.items[self.selected]} ')
            self._hide()
            self._update_suggestions()
            return
        # alias
        chosen = self.items[self.selected]
        m = re.match(r'^(/?)(\w+)\s', self.entry.get())
        if m:
            self._set_input(f'{m.group(1)}{m.group(2)} {chosen}')
        else:
            self._set_input(chosen)

    def _set_input(self, text):
        self.entry.delete(0, 'end')
        self.entry.insert(0, text)
        self.entry.icursor('end')

    # ============ отрисовка ============
    def _show(self, items):
        self.items = items
        if self.selected >= len(items):
            self.selected = 0
        for lbl in self.labels:
            lbl.destroy()
        self.labels = []

        for i, name in enumerate(items[:MAX_ITEMS]):
            if self.mode == 'verb':
                display = f'/{name}'
            else:
                display = f'  {name}'
            lbl = ctk.CTkLabel(
                self.frame,
                text=display,
                anchor='w',
                height=26,
                font=(self.theme['font_family'],
                      self.theme['font_size'] - 1),
                text_color=self.theme['list_fg'],
                fg_color='transparent',
                corner_radius=6,
            )
            lbl.pack(fill='x', padx=4, pady=1)
            lbl.bind('<Button-1>', lambda e, idx=i: self._on_click(idx))
            lbl.bind('<Enter>',    lambda e, idx=i: self._on_hover(idx))
            lbl.bind('<Leave>',    lambda e: self._on_unhover())
            self.labels.append(lbl)

        if len(items) > MAX_ITEMS:
            ctk.CTkLabel(
                self.frame,
                text=f'  … ещё {len(items) - MAX_ITEMS}',
                anchor='w',
                text_color=self.theme['list_fg'],
                font=(self.theme['font_family'],
                      self.theme['font_size'] - 2),
            ).pack(fill='x', padx=4)

        if not self.active:
            self.frame.pack(fill='x', padx=10, pady=(0, 4),
                            before=self.output)
            self.active = True
        self._highlight()
        if self.on_state_change:
            self.on_state_change()

    def _highlight(self):
        for i, lbl in enumerate(self.labels):
            if i == self.selected:
                lbl.configure(fg_color=self.theme['accent'],
                              text_color=self.theme['window_bg'])
            else:
                lbl.configure(fg_color='transparent',
                              text_color=self.theme['list_fg'])

    def _hide(self):
        if not self.active:
            return
        self.frame.pack_forget()
        self.active = False
        self.items = []
        self.path_items = []
        self.user_navigated = False
        self.mode = None
        if self.on_state_change:
            self.on_state_change()