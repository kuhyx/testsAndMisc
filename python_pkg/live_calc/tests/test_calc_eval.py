"""Tests for the live-calc safe arithmetic evaluator.

The public surface is ``evaluate``; most branches are reached through it so the
tests double as behaviour documentation. A handful of internal helpers
(``_format``, ``_apply_limits``, ``_raise_timeout``, ``main``) are exercised
directly where a branch cannot be triggered through ``evaluate`` alone.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from python_pkg.live_calc import calc_eval
from python_pkg.live_calc.calc_eval import (
    _apply_limits,
    _format,
    _raise_timeout,
    evaluate,
    main,
)

_MOD = "python_pkg.live_calc.calc_eval"


class TestArithmetic:
    """Core arithmetic, operators and the calculator-style ``^`` power."""

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            ("2+2", "4"),
            ("20*(3+4)", "140"),
            ("10-3", "7"),
            ("7/2", "3.5"),
            ("7//2", "3"),
            ("10%3", "1"),
            ("2^10", "1024"),  # ^ is rewritten to **
            ("2**10", "1024"),
            ("+5", "5"),
            ("-5", "-5"),
            ("3/2", "1.5"),
        ],
    )
    def test_evaluates(self, expr: str, expected: str) -> None:
        """Each operator yields the expected formatted result."""
        assert evaluate(expr) == expected


class TestFunctionsAndConstants:
    """Whitelisted functions and named constants."""

    def test_sqrt(self) -> None:
        """sqrt(4) is 2."""
        assert evaluate("sqrt(4)") == "2"

    def test_nested_call(self) -> None:
        """Functions compose and trig works against pi."""
        assert evaluate("sin(pi/2)") == "1"

    def test_constant_pi(self) -> None:
        """The constant pi resolves to math.pi."""
        assert evaluate("pi") == format(math.pi, ".12g")

    def test_min_max(self) -> None:
        """Multi-argument builtins are allowed."""
        assert evaluate("max(2, 9, 4)") == "9"

    def test_factorial_ok(self) -> None:
        """A small factorial is computed."""
        assert evaluate("factorial(5)") == "120"


class TestRejected:
    """Inputs that must yield '' (invalid, unsafe, or unsupported)."""

    @pytest.mark.parametrize(
        "expr",
        [
            "",  # empty
            "ls -la",  # not an expression at all
            "2+",  # SyntaxError
            "x",  # unknown name
            "sqrt",  # function name without a call
            "foo(2)",  # unknown function
            "True",  # bool literal rejected
            "'a'",  # string literal rejected
            "5 & 3",  # unsupported binary operator
            "~5",  # unsupported unary operator
            "(1+1)(2)",  # call target is not a plain name
            "round(2.5, ndigits=1)",  # keyword arguments rejected
            "[1, 2]",  # unsupported node type (list)
            "factorial()",  # factorial needs an argument
            "factorial(2.5)",  # factorial argument must be int
        ],
    )
    def test_returns_empty(self, expr: str) -> None:
        """Anything that is not a permitted arithmetic expression yields ''."""
        assert evaluate(expr) == ""


class TestRunawayGuards:
    """Bounds that stop a live keystroke from computing forever."""

    def test_huge_exponent_refused(self) -> None:
        """A ** b with an enormous b is refused before computing."""
        assert evaluate("2^99999") == ""

    def test_huge_factorial_refused(self) -> None:
        """factorial of a huge argument is refused up front."""
        assert evaluate("factorial(99999)") == ""


class TestFormatting:
    """Number formatting, including the int/scientific/float branches."""

    def test_big_int_uses_scientific(self) -> None:
        """Integers longer than the digit cap fall back to scientific form."""
        assert evaluate("10^30") == format(1e30, ".6g")

    def test_overflowing_int_yields_empty(self) -> None:
        """An int too large to convert to float formats to ''."""
        assert evaluate("10^400") == ""

    def test_infinity_yields_empty(self) -> None:
        """A float overflow to infinity formats to ''."""
        assert evaluate("1e308*10") == ""

    def test_format_bool_is_int(self) -> None:
        """_format coerces bool to its int value (reached only directly)."""
        assert _format(value=True) == "1"

    def test_format_nan_yields_empty(self) -> None:
        """_format rejects NaN."""
        assert _format(float("nan")) == ""

    def test_format_inf_yields_empty(self) -> None:
        """_format rejects infinity."""
        assert _format(float("inf")) == ""

    def test_format_plain_float(self) -> None:
        """A finite float is formatted with the float precision."""
        assert _format(1.5) == "1.5"


class TestTimeoutHandler:
    """The SIGALRM handler and the resource-limit installer."""

    def test_raise_timeout_raises(self) -> None:
        """The handler converts an alarm into a catchable TimeoutError."""
        with pytest.raises(TimeoutError):
            _raise_timeout(0, None)

    def test_apply_limits_installs(self) -> None:
        """Limits are installed via setrlimit/signal/setitimer."""
        with (
            patch(f"{_MOD}.resource.setrlimit") as set_rlimit,
            patch(f"{_MOD}.signal.signal") as set_signal,
            patch(f"{_MOD}.signal.setitimer") as set_timer,
        ):
            _apply_limits()
        set_rlimit.assert_called_once()
        set_signal.assert_called_once()
        set_timer.assert_called_once()

    def test_apply_limits_survives_unavailable(self) -> None:
        """If the platform rejects the limits, the error is swallowed."""
        with (
            patch(f"{_MOD}.resource.setrlimit", side_effect=OSError),
            patch(f"{_MOD}.signal.signal", side_effect=ValueError),
            patch(f"{_MOD}.signal.setitimer"),
        ):
            _apply_limits()  # must not raise


class TestMain:
    """The command-line entry point (argv -> stdout)."""

    def test_no_argument(self, capsys: pytest.CaptureFixture[str]) -> None:
        """With no expression argument, nothing is printed and rc is 0."""
        with (
            patch(f"{_MOD}._apply_limits"),
            patch.object(calc_eval.sys, "argv", ["calc_eval"]),
        ):
            assert main() == 0
        assert capsys.readouterr().out == ""

    def test_valid_expression(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A valid expression is evaluated and written to stdout."""
        with (
            patch(f"{_MOD}._apply_limits"),
            patch.object(calc_eval.sys, "argv", ["calc_eval", "2+2"]),
        ):
            assert main() == 0
        assert capsys.readouterr().out == "4"

    def test_invalid_expression_writes_nothing(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An invalid expression produces no output."""
        with (
            patch(f"{_MOD}._apply_limits"),
            patch.object(calc_eval.sys, "argv", ["calc_eval", "ls -la"]),
        ):
            assert main() == 0
        assert capsys.readouterr().out == ""
