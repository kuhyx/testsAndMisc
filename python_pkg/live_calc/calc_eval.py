"""Safe arithmetic evaluator for the live-calc zsh widget.

Read one expression from ``sys.argv[1]`` and write its formatted numeric result
to stdout, or write nothing on any error, unsafe input, overflow, or timeout.

The expression is parsed into an AST and evaluated by walking a strict
whitelist of node types, so it can never import modules, access attributes, or
execute arbitrary code. CPU and wall-clock time are capped so that a runaway
expression typed live (for example ``9**9**9``) cannot freeze the shell.

Used by ``calc-live.zsh``; kept as a standalone module so the repository's
Python tooling (ruff, mypy, pylint, bandit) applies to it.
"""

from __future__ import annotations

import ast
import contextlib
import math
import operator
import resource
import signal
import sys
from typing import TYPE_CHECKING, NoReturn, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType

Number: TypeAlias = int | float

# Whitelisted callables, addressed by the name used in the expression.
_FUNCTIONS: dict[str, Callable[..., Number]] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "ln": math.log,
    "log": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "deg": math.degrees,
    "rad": math.radians,
    "min": min,
    "max": max,
}

# Whitelisted constants.
_CONSTANTS: dict[str, float] = {"pi": math.pi, "e": math.e, "tau": math.tau}

# Binary and unary operators, addressed by AST node type.
_BINARY_OPS: dict[type[ast.operator], Callable[[Number, Number], Number]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[Number], Number]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MAX_EXPONENT = 10_000  # refuse a ** b for very large b before computing
_MAX_FACTORIAL_ARG = 10_000  # factorial grows astronomically fast
_MAX_INT_DIGITS = 25  # longer ints are shown in scientific form
_FLOAT_PRECISION = 12  # significant digits for float results
_SCI_PRECISION = 6  # significant digits for the scientific fallback
_CPU_LIMIT_SECONDS = 1  # hard kernel CPU cap (SIGXCPU terminates)
_WALL_LIMIT_SECONDS = 0.4  # soft wall-clock cap (SIGALRM)


class _CalcError(Exception):
    """Raised when the input is not a permitted arithmetic expression."""


def _raise_timeout(_signum: int, _frame: FrameType | None) -> NoReturn:
    """SIGALRM handler: abort a too-slow evaluation via a catchable exception."""
    raise TimeoutError


def _apply_limits() -> None:
    """Cap CPU and wall-clock time so a runaway expression cannot hang the shell."""
    with contextlib.suppress(ValueError, OSError):
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (_CPU_LIMIT_SECONDS, _CPU_LIMIT_SECONDS),
        )
    with contextlib.suppress(ValueError, OSError):
        signal.signal(signal.SIGALRM, _raise_timeout)
        signal.setitimer(signal.ITIMER_REAL, _WALL_LIMIT_SECONDS)


def _eval_constant(node: ast.Constant) -> Number:
    """Return a numeric literal value, rejecting booleans and other types."""
    if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
        raise _CalcError
    return node.value


def _eval_name(node: ast.Name) -> Number:
    """Return the value of a whitelisted constant name (pi, e, tau)."""
    try:
        return _CONSTANTS[node.id]
    except KeyError as exc:
        raise _CalcError from exc


def _eval_unaryop(node: ast.UnaryOp) -> Number:
    """Evaluate a unary plus/minus operation."""
    try:
        func = _UNARY_OPS[type(node.op)]
    except KeyError as exc:
        raise _CalcError from exc
    return func(_eval(node.operand))


def _eval_binop(node: ast.BinOp) -> Number:
    """Evaluate a binary operation, guarding against explosive exponents."""
    try:
        func = _BINARY_OPS[type(node.op)]
    except KeyError as exc:
        raise _CalcError from exc
    left = _eval(node.left)
    right = _eval(node.right)
    if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
        raise _CalcError
    return func(left, right)


def _eval_call(node: ast.Call) -> Number:
    """Evaluate a call to a whitelisted function, bounding factorial growth."""
    if not isinstance(node.func, ast.Name) or node.keywords:
        raise _CalcError
    try:
        func = _FUNCTIONS[node.func.id]
    except KeyError as exc:
        raise _CalcError from exc
    args = [_eval(arg) for arg in node.args]
    if node.func.id == "factorial" and (
        not args or not isinstance(args[0], int) or args[0] > _MAX_FACTORIAL_ARG
    ):
        raise _CalcError
    return func(*args)


def _eval(node: ast.AST) -> Number:
    """Recursively evaluate one whitelisted AST node."""
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        return _eval_constant(node)
    if isinstance(node, ast.Name):
        return _eval_name(node)
    if isinstance(node, ast.UnaryOp):
        return _eval_unaryop(node)
    if isinstance(node, ast.BinOp):
        return _eval_binop(node)
    if isinstance(node, ast.Call):
        return _eval_call(node)
    raise _CalcError


def _format(value: Number) -> str:
    """Format a numeric result compactly, or return '' if it cannot be shown."""
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        text = str(value)
        if len(text) <= _MAX_INT_DIGITS:
            return text
        try:
            return format(float(value), f".{_SCI_PRECISION}g")
        except OverflowError:
            return ""
    if math.isnan(value) or math.isinf(value):
        return ""
    return format(value, f".{_FLOAT_PRECISION}g")


def evaluate(expression: str) -> str:
    """Evaluate ``expression`` and return its formatted result, or '' on failure.

    Args:
        expression: The arithmetic expression. ``^`` is treated as power.

    Returns:
        The formatted result, or an empty string for any invalid, unsafe, or
        non-terminating input.
    """
    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
        return _format(_eval(tree))
    except (
        _CalcError,
        SyntaxError,
        ArithmeticError,
        ValueError,
        TypeError,
        RecursionError,
        TimeoutError,
        MemoryError,
    ):
        return ""


def main() -> int:
    """Read ``argv[1]``, evaluate it under resource limits, and print the result."""
    _apply_limits()
    args = sys.argv[1:]
    if not args:
        return 0
    result = evaluate(args[0])
    if result:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
