"""Laws of the pure queue core: exclusion, FIFO, parallelism, no starvation.

Drives :mod:`python_pkg.phone_lease._queue` directly (no files, no flock) the
way ``locked_update`` does: ``tidy`` first, then one ``take`` or ``leave``.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from python_pkg.phone_lease._model import WHOLE_PHONE, Lease, conflicts
from python_pkg.phone_lease._queue import Book, leave, take, tidy

OWNERS = ("A", "B", "C", "D")
SCOPES = ("pkg:a", "pkg:b", WHOLE_PHONE)
TTL = 10.0
PROPS = settings(max_examples=150, deadline=None, derandomize=True)

step = st.one_of(
    st.tuples(st.just("take"), st.sampled_from(OWNERS), st.sampled_from(SCOPES)),
    st.tuples(st.just("leave"), st.sampled_from(OWNERS), st.sampled_from(SCOPES)),
    st.tuples(st.just("tick"), st.sampled_from(("1", "5", "12", "40")), st.just("")),
)


def _alive(_owner: str) -> bool:
    return True


def _should_grant(book: Book, owner: str, scope: str) -> bool:
    """The rule written the obvious way: nothing foreign in force or ahead."""
    if any(x.owner == owner and x.scope == scope for x in book.leases):
        return True
    mine = next(
        (x.number for x in book.tickets if (x.owner, x.scope) == (owner, scope)),
        None,
    )
    blocked = any(x.owner != owner and conflicts(x.scope, scope) for x in book.leases)
    ahead = any(
        x.owner != owner
        and conflicts(x.scope, scope)
        and (mine is None or x.number < mine)
        for x in book.tickets
    )
    return not blocked and not ahead


def _exclusive(book: Book) -> bool:
    return not any(
        a.owner != b.owner and conflicts(a.scope, b.scope)
        for i, a in enumerate(book.leases)
        for b in book.leases[i + 1 :]
    )


@PROPS
@given(st.lists(step, max_size=40))
def test_grants_follow_the_fifo_rule_and_never_overlap(
    steps: list[tuple[str, str, str]],
) -> None:
    book, now = Book(), 0.0
    for kind, who, scope in steps:
        if kind == "tick":
            now += float(who)
            continue
        owner = who
        tidy(book, now, _alive)
        if kind == "leave":
            leave(book, owner, scope)
            continue
        expected = _should_grant(book, owner, scope)
        got = take(book, Lease("P", owner, 0.0, "", scope), TTL, now)
        assert (got.lease is not None) == expected
        assert (got.position == 0) == expected
        assert _exclusive(book)
        numbers = [x.number for x in book.tickets]
        assert numbers == sorted(set(numbers))


@PROPS
@given(
    st.lists(
        st.tuples(st.sampled_from(OWNERS), st.sampled_from(SCOPES)),
        min_size=1,
        max_size=8,
        unique=True,
    ),
    st.lists(st.floats(1.0, 5.0), min_size=1, max_size=5),
)
def test_every_waiter_is_served_while_holders_keep_refreshing(
    wants: list[tuple[str, str]], gaps: list[float]
) -> None:
    """Adversarial holders refresh every round; drain + TTL still serve all."""
    book, now = Book(), 0.0
    served: set[tuple[str, str]] = set()
    bound = (len(wants) + 1) * (int(TTL) + 2) * 2
    for round_no in range(bound):
        tidy(book, now, _alive)
        for owner, scope in wants:
            got = take(book, Lease("P", owner, 0.0, "", scope), TTL, now)
            if got.lease is not None:
                served.add((owner, scope))
            assert _exclusive(book)
        if served == set(wants):
            break
        now += gaps[round_no % len(gaps)]
    assert served == set(wants)


@PROPS
@given(st.sets(st.sampled_from(("pkg:a", "pkg:b", "pkg:c", "pkg:d")), min_size=1))
def test_different_packages_are_all_granted_at_once(scopes: set[str]) -> None:
    book = Book()
    for i, scope in enumerate(sorted(scopes)):
        got = take(book, Lease("P", f"o{i}", 0.0, "", scope), TTL, 0.0)
        assert got.lease is not None
    assert len(book.leases) == len(scopes)
    assert book.tickets == []
