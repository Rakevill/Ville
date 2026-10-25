"""Безопасный вычислитель выражений.

Не используем eval() — только ast с whitelist узлов, операторов
и функций. Всё, что не разрешено явно, даёт CalcError.

Разрешено:
  числа (int, float), + - * / // % **, скобки, унарные +/-
  функции: sqrt, abs, round, min, max, sin, cos, tan,
           log, log10, exp, floor, ceil, factorial
  константы: pi, e, tau
  ans — результат предыдущего вызова evaluate (передаётся снаружи)
  ^ — синоним ** (привычно пользователю)
"""
import ast
import math
import operator
import re


_BIN_OPS = {
    ast.Add:      operator.add,
    ast.Sub:      operator.sub,
    ast.Mult:     operator.mul,
    ast.Div:      operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod:      operator.mod,
    ast.Pow:      operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_CONSTANTS = {
    'pi':  math.pi,
    'e':   math.e,
    'tau': math.tau,
}


class CalcError(Exception):
    """Ожидаемая ошибка вычисления — показывается пользователю."""
    pass


# ---------- функции ----------
def _safe_factorial(n):
    """math.factorial(1000000) считается минуты — ограничиваем."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError('factorial принимает целое число')
    if n < 0:
        raise ValueError('factorial от отрицательного числа')
    if n > 1000:
        raise ValueError('factorial: n ≤ 1000')
    return math.factorial(n)


_FUNCTIONS = {
    'sqrt':      math.sqrt,
    'abs':       abs,
    'round':     round,
    'min':       min,
    'max':       max,
    'sin':       math.sin,
    'cos':       math.cos,
    'tan':       math.tan,
    'log':       math.log,
    'log10':     math.log10,
    'exp':       math.exp,
    'floor':     math.floor,
    'ceil':      math.ceil,
    'factorial': _safe_factorial,
}


# ---------- ядро ----------
def _eval_node(node, ans):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, ans)

    if isinstance(node, ast.Constant):
        # bool — подкласс int, но для калькулятора это мусор
        if isinstance(node.value, bool):
            raise CalcError('Логические значения не поддерживаются')
        if isinstance(node.value, (int, float)):
            return node.value
        raise CalcError(f'Недопустимая константа: {node.value!r}')

    if isinstance(node, ast.Name):
        name = node.id
        if name == 'ans':
            if ans is None:
                raise CalcError('ans недоступен — нет предыдущего результата')
            return ans
        if name in _CONSTANTS:
            return _CONSTANTS[name]
        raise CalcError(f'Неизвестное имя: {name}')

    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise CalcError(f'Оператор не разрешён: {type(node.op).__name__}')
        left  = _eval_node(node.left,  ans)
        right = _eval_node(node.right, ans)

        # защита от 10**(10**10): Python посчитает, но съест гигабайты
        if isinstance(node.op, ast.Pow):
            if (isinstance(left, (int, float))
                    and isinstance(right, (int, float))
                    and abs(right) > 10000
                    and abs(left) > 1):
                raise CalcError('Слишком большая степень (|показатель| > 10000)')

        try:
            return op(left, right)
        except ZeroDivisionError:
            raise CalcError('Деление на ноль')
        except OverflowError:
            raise CalcError('Слишком большое число')

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise CalcError('Унарный оператор не разрешён')
        return op(_eval_node(node.operand, ans))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalcError('Вызов функции не разрешён')
        fname = node.func.id
        if fname not in _FUNCTIONS:
            raise CalcError(f'Функция не разрешена: {fname}')
        if node.keywords:
            raise CalcError('Именованные аргументы не поддерживаются')
        args = [_eval_node(a, ans) for a in node.args]
        try:
            return _FUNCTIONS[fname](*args)
        except (ValueError, TypeError) as e:
            raise CalcError(f'{fname}(): {e}')

    raise CalcError(f'Недопустимая конструкция: {type(node).__name__}')


def evaluate(expr, ans=None):
    """Посчитать выражение. Бросает CalcError при любой проблеме.

    ans — результат предыдущего вызова (или None, если его не было).
    """
    expr = expr.strip()
    if not expr:
        raise CalcError('Пустое выражение')

    # ^ → **, но только если рядом нет * (иначе 2**3 стало бы 2****3)
    expr = re.sub(r'(?<!\*)\^(?!\*)', '**', expr)

    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise CalcError(f'Синтаксическая ошибка: {e.msg}')

    return _eval_node(tree, ans)


def format_result(value):
    """Привести результат к строке для лога. Бросает CalcError,
    если получилось не число (nan/inf) — в норме до этого
    не доходит из-за OverflowError выше, но оставляем на всякий."""
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CalcError('Результат не является числом')
        # 4.0 → 4, но 3.14 остаётся
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return f'{value:.10g}'
    return str(value)