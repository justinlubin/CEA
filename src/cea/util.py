from typing import TypeVar

T = TypeVar("T")


def flatten(xss: list[list[T]]) -> list[T]:
    ret = []
    for xs in xss:
        ret.extend(xs)
    return ret
