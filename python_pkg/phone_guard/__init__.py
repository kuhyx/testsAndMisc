"""Keep several Claude sessions from interrupting each other on one phone.

Two parts: :mod:`vd_state` answers "which virtual display is whose" from the
state ``phone_vd.sh`` keeps, and :mod:`hook` is the PreToolUse hook that stops
a raw ``adb`` command from touching the real screen (or another session's app)
without the matching :mod:`python_pkg.phone_lease` lease.
"""

from __future__ import annotations
