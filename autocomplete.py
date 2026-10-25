"""Подсказки для поля ввода.

Три режима, выбираются автоматически по содержимому поля:

  verb   — ввод '/' или '/op'        → список глаголов
  alias  — '/open <partial>'         → алиасы из shortcuts
  path   — '/openset "<partial>'     → содержимое каталога

Возвращает 'break' из обработчиков ↑/↓/Tab/Esc/Enter, когда подсказка
активна, чтобы приоритет был у автодополнения, а не у истории команд
в window.py. Порядок привязок важен: autocomplete биндится ДО истории.
"""
import os
import re

import customtkinter as ctk


MAX_ITEMS = 8  # больше — не влезает в окно, показываем «… ещё N»


class Autocomplete:
    def __init__(self, parent, entry, output, config, execute_cb, theme):
        self.entry = entry
        self.output = output
        self.config = config
        self.execute_cb = execute_cb
        self.theme = theme

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
        self.labels = []          # CTkLabel-ы видимых пунктов
        self.items = []           # строки для отображения
        self.path_items = []      # словари {name, path, is_dir} для режима path
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

        # 1) путь для /openset — приоритетно, потому что может содержать
        #    пробелы внутри кавычек, а regex для verb/alias на это сломается
        prefix = self._detect_path_prefix(text)
        if prefix is not None:
            entries = self._list_path(prefix)
            if entries:
                self.mode = 'path'
                self.path_items = entries
                self.user_navigated = False
                self._show([
                    e['name'] + (os.sep if e['is_dir'] else '')
                    for e in entries
                ])
            else:
                self._hide()
            return

        # 2) /verb без пробела — подсказка глагола
        m = re.match(r'^/(\w*)$', text)
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

        # 3) /open <partial> — подсказка алиаса
        m = re.match(r'^/(\w+)\s(.*)$', text)
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
        первого аргумента openset-команды. None — не наш случай.

        Примеры:
          '/openset "'                → ''           (показать содержимое CWD)
          '/openset "C:\\Te'          → 'C:\\Te'      (фильтр по Te)
          '/openset "C:\\Users\\me"'  → None          (кавычка закрыта)
          '/openset C:\\Temp'         → 'C:\\Temp'    (без кавычек, до пробела)
          '/openset C:\\Program Files'→ None          (пробел без кавычек — увы)
          '/open "'                   → None          (не openset-глагол)
        """
        m = re.match(r'^/(\w+)\s(.*)$', text)
        if not m:
            return None
        verb, rest = m.groups()
        if verb not in self._openset_verbs:
            return None
        if rest.startswith('"'):
            # ровно одна кавычка = открытая
            return rest[1:] if rest.count('"') == 1 else None
        if rest and ' ' not in rest:
            return rest
        return None

    def _list_path(self, prefix):
        """Содержимое каталога, отфильтрованное по последнему сегменту.
        Папки выше файлов. Любые ошибки ОС → пустой список."""
        try:
            expanded = os.path.expandvars(prefix)
            if not expanded:
                return []
            # 'C:' → 'C:\' (корень диска)
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
        m = re.match(r'^(/\w+)\s', self.entry.get())
        if not m:
            return
        verb_part = m.group(1)

        if item['is_dir']:
            # папка: открывающая кавычка остаётся, добавляем '\'
            # и сразу показываем содержимое
            self._set_input(f'{verb_part}"{item["path"]}{os.sep}')
            self._hide()
            self._update_suggestions()
        else:
            # файл: закрываем кавычку, ставим пробел — можно писать алиас
            self._set_input(f'{verb_part}"{item["path"]}" ')
            self._hide()

    # ============ клавиши ============
    def _on_key(self, event):
        # Навигацию и модификаторы не считаем «вводом» —
        # иначе user_navigated будет сбрасываться и список мигать
        if event.keysym in (
            'Up', 'Down', 'Tab', 'Escape', 'Return',
            'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
            'Alt_L', 'Alt_R',
        ):
            return
        self._update_suggestions()

    def _on_down(self, _):
        if not self.active:
            return                      # отдаём ↓ истории в window.py
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

        # path: Enter = Tab (подставить путь), но не выполнять команду —
        # регистрация ещё не готова (нет алиаса)
        if self.mode == 'path':
            self._complete()
            return 'break'

        # verb: команда не дописана, только дополнить
        if self.mode == 'verb':
            if self.user_navigated and self.items:
                self._complete()
                return 'break'
            self._hide()
            return

        # alias: навигация + Enter = подставить и выполнить
        if self.user_navigated and self.items:
            self._complete()
            self._hide()
            self.execute_cb()
            return 'break'

        # без навигации — обычное выполнение того, что в поле
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
        # клик по алиасу — как Tab+Enter; по verb/path — только подстановка
        if mode == 'alias':
            self._hide()
            self.execute_cb()

    # ============ завершение ============
    def _complete(self):
        if not self.items:
            return
        if self.mode == 'path':
            self._complete_path()
            return
        if self.mode == 'verb':
            # '/openset ' — с пробелом, и сразу подсказка для openset
            self._set_input(f'/{self.items[self.selected]} ')
            self._hide()
            self._update_suggestions()
            return
        # alias
        chosen = self.items[self.selected]
        m = re.match(r'^(/\w+)\s', self.entry.get())
        self._set_input(f'{m.group(1)} {chosen}' if m else chosen)

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
            prefix = '/' if self.mode == 'verb' else '  '
            lbl = ctk.CTkLabel(
                self.frame,
                text=f'{prefix}{name}',
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
            # вставляем перед полем вывода, чтобы не сдвигать поле ввода
            self.frame.pack(fill='x', padx=10, pady=(0, 4),
                            before=self.output)
            self.active = True
        self._highlight()

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