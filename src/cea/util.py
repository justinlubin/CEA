from typing import ParamSpec, TypeVar, Callable

P = ParamSpec("P")
T = TypeVar("T")


def flatten(xss: list[list[T]]) -> list[T]:
    ret = []
    for xs in xss:
        ret.extend(xs)
    return ret


def override(f: Callable[P, T]) -> Callable[P, T]:
    return f


def string_width(s: str) -> int:
    if not s:
        return 0

    return max(len(line) for line in s.splitlines())
