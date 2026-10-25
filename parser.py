import shlex
from dataclasses import dataclass, field
from typing import List


class ParseError(Exception):
    pass


@dataclass
class ParsedCommand:
    verb: str
    args: List[str] = field(default_factory=list)
    force: bool = False


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def parse(text: str):
    text = text.strip()
    if not text:
        return None
    if text.startswith('/'):
        text = text[1:]
    try:
        tokens = shlex.split(text, posix=False)
    except ValueError as e:
        raise ParseError(f'Ошибка в кавычках: {e}')
    if not tokens:
        return None

    verb = _strip_quotes(tokens[0]).lower()
    args, force = [], False
    for t in tokens[1:]:
        t = _strip_quotes(t)
        if t == '--force':
            force = True
        else:
            args.append(t)
    return ParsedCommand(verb, args, force)