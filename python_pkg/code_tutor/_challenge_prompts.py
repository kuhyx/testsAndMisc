"""Static prompt and notice strings for the coding challenge.

Split out of :mod:`python_pkg.code_tutor._challenge` to keep it under the
250-line cap. These are pure data with no collaborators, so nothing patches
them and they can live anywhere.
"""

from __future__ import annotations

_NO_AI_NOTICE = (
    "[bold yellow]⚠  No AI assistance -- write this yourself.[/bold yellow]\n"
    "Your own explanation (and the tests below) are your only reference."
)

_MAX_TEST_ATTEMPTS = 2

_TEST_JUDGE_SYSTEM = (
    "You are a code tutor evaluating whether a student's tests adequately"
    " cover a function.\n\n"
    "PASS if the tests:\n"
    "  - Include at least 2 meaningfully different test cases with distinct inputs\n"
    "  - Use assertions that verify the actual return value or observable behavior\n"
    "  - Would catch an obviously wrong implementation (e.g. one that always"
    ' returns "")\n\n'
    "FAIL only if:\n"
    "  - There is only one trivial test case\n"
    "  - Assertions are always-true or don't check the function's real output\n"
    "  - All tests are essentially the same scenario with trivially different data\n\n"
    "Do NOT require error/edge-case tests for pure transformation functions that"
    " have no error handling.  2+ meaningful happy-path cases with distinct"
    " inputs is enough.\n\n"
    "Respond with valid JSON only, no other text:\n"
    '{"verdict": "PASS" | "FAIL",'
    ' "gap": "<one sentence on the specific missing scenario,'
    ' or empty string on PASS>"}'
)
