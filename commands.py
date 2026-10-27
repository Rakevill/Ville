"""Реестр команд и их исполнение.

Глаголы:
  /openset <путь> <алиас>   — зарегистрировать файл/папку/программу
  /open <алиас|путь>        — открыть
  /openlist                 — список зарегистрированного
  /opendel <алиас>          — удалить регистрацию
  /calc <выражение>         — вычислить

Имена глаголов настраиваются в config.verbs — если пользователь
переименовал 'openset' → 'fset', он вводит /fset, а код всё равно
вызывает cmd_openset. Обратный маппинг строится в __init__.
"""
import os
import re
from pathlib import Path

import calc
from parser import parse, ParseError


# алфавит алиасов: буквы, цифры, _ и -, длина 1..32
ALIAS_RE = re.compile(r'^[A-Za-z0-9_\-]{1,32}$')


class CommandError(Exception):
    """Ожидаемая ошибка выполнения команды — показывается пользователю."""
    pass
class ExitRequested(Exception):
    """Сигнал: пользователь запросил выход. Ловится в window.py."""
    pass


class CommandRegistry:
    def __init__(self, config):
        self.config = config
        # {'fset': 'openset', 'open': 'open', ...}
        # ключ — то, что печатает пользователь; значение — суффикс cmd_*
        self._verb_keys = {v: k for k, v in config.verbs.items()}
        # результат последнего /calc — только в памяти, в YAML не пишется
        self._last_ans = None

    # ---------- публичный API ----------
    def execute(self, text: str) -> str:
        """Разобрать и выполнить строку. Возвращает текст для лога
        или пустую строку, если показывать нечего. Бросает CommandError
        для понятных пользователю ошибок."""
        try:
            parsed = parse(text)
        except ParseError as e:
            raise CommandError(str(e))
        if parsed is None:
            return ''

        verb_key = self._verb_keys.get(parsed.verb)
        if verb_key is None:
            raise CommandError(f'Неизвестная команда: /{parsed.verb}')

        handler = getattr(self, f'cmd_{verb_key}', None)
        if handler is None:
            raise CommandError(f'Команда /{parsed.verb} не реализована')

        return handler(parsed.args, parsed.force) or ''

    # ---------- /openset ----------
    def cmd_openset(self, args, force):
        if len(args) < 2:
            raise CommandError(
                'Использование: /openset <путь> <алиас>\n'
                'Пример: /openset "C:\\Users\\me\\Documents" docs'
            )

        path = self._normalize_path(args[0])
        alias = args[1]
        self._validate_alias(alias)

        exists = Path(path).exists()
        if not exists and not force:
            raise CommandError(
                f'Путь не существует: {path}\n'
                f'Зарегистрировать на будущее — добавьте --force'
            )

        table = self.config.shortcuts
        if alias in table and not force:
            current = table[alias]
            if current.lower() != path.lower():
                raise CommandError(
                    f'Алиас "{alias}" уже занят: {current}\n'
                    f'Перезаписать: /openset --force "{path}" {alias}\n'
                    f'Удалить: /opendel {alias}'
                )

        table[alias] = path
        self.config.save()
        return f'Зарегистрировано: {alias} → {path}'

    # ---------- /open ----------
    def cmd_open(self, args, force):
        if not args:
            raise CommandError('Использование: /open <алиас|путь>')

        alias = args[0]
        table = self.config.shortcuts

        if alias in table:
            path = table[alias]
            if not Path(path).exists():
                raise CommandError(
                    f'Путь не найден: {path}\n'
                    f'Алиас сохранён. Удалить: /opendel {alias}'
                )
        else:
            # fallback: пользователь мог ввести путь напрямую
            expanded = os.path.expandvars(alias)
            if not Path(expanded).exists():
                raise CommandError(
                    f'Алиас "{alias}" не зарегистрирован и путь не найден\n'
                    f'Зарегистрировать: /openset "{alias}" <алиас>'
                )
            path = expanded

        try:
            os.startfile(path)  # Windows: как двойной клик в проводнике
        except OSError as e:
            raise CommandError(f'Не удалось открыть {path}: {e}')
        return f'Открыто: {path}'

    # ---------- /openlist ----------
    def cmd_openlist(self, args, force):
        table = self.config.shortcuts
        if not table:
            return 'Список пуст. Добавьте: /openset "<путь>" <алиас>'
        lines = ['Зарегистрировано:']
        for name in sorted(table, key=str.lower):
            path = table[name]
            mark = '' if Path(path).exists() else '  (путь не найден)'
            lines.append(f'  {name} → {path}{mark}')
        return '\n'.join(lines)

    # ---------- /opendel ----------
    def cmd_opendel(self, args, force):
        if not args:
            raise CommandError('Использование: /opendel <алиас>')
        alias = args[0]
        table = self.config.shortcuts
        if alias not in table:
            raise CommandError(f'Алиас "{alias}" не найден')
        del table[alias]
        self.config.save()
        return f'Удалено: {alias}'

    # ---------- /calc ----------
    def cmd_calc(self, args, force):
        # --force для /calc смысла не имеет: если пользователь ввёл
        # /calc --force 2+2, parser вынул флаг, а в args осталось ['2+2'].
        # Просто игнорируем force, считаем выражение.
        if not args:
            raise CommandError('Использование: /calc <выражение>')

        expr = ' '.join(args)
        try:
            result = calc.evaluate(expr, self._last_ans)
            formatted = calc.format_result(result)
        except calc.CalcError as e:
            raise CommandError(str(e))

        self._last_ans = result
        return f'= {formatted}'

    # ---------- /help ----------
    def cmd_help(self, args, force):
        descriptions = {
            'openset':  'зарегистрировать путь под алиасом',
            'open':     'открыть алиас или путь',
            'openlist': 'список зарегистрированного',
            'opendel':  'удалить алиас',
            'calc':     'вычислить (ans, sqrt, pi, ...)',
            'help':     'эта справка',
            'exit':     'закрыть приложение',
        }
        lines = ['Доступные команды:', '']
        for key, user_name in self.config.verbs.items():
            desc = descriptions.get(key, '')
            lines.append(f'  /{user_name:<10} {desc}')
        lines += [
            '',
            'Примеры:',
            '  /openset "C:\\Users\\me\\Documents" docs',
            '  /open docs',
            '  /calc sqrt(2)*pi',
        ]
        return '\n'.join(lines)

    # ---------- /exit ----------
    def cmd_exit(self, args, force):
        raise ExitRequested()

    # ---------- helpers ----------
    @staticmethod
    def _normalize_path(raw: str) -> str:
        """Раскрыть %VAR% и привести к абсолютному пути."""
        expanded = os.path.expandvars(raw)
        try:
            return str(Path(expanded).resolve())
        except OSError as e:
            raise CommandError(f'Путь невалиден: {e}')

    def _validate_alias(self, alias: str) -> None:
        if not ALIAS_RE.match(alias):
            raise CommandError(
                f'Недопустимый алиас "{alias}". '
                f'Разрешены буквы, цифры, _ и -, длина 1–32.'
            )
        if alias in self._verb_keys:
            raise CommandError(
                f'Алиас "{alias}" совпадает с именем команды. Выберите другой.'
            )