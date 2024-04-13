from dataclasses import dataclass
from typing import Final

import re

################################################################################
## S-Expressions


BREAK: Final = "$BREAK"


@dataclass(frozen=True)
class SAtom:
    val: str


@dataclass(frozen=True)
class SList:
    elems: list["SExp"]


SExp = SAtom | SList


def without_list_breaks(sexp: SExp) -> SExp:
    match sexp:
        case SAtom(_):
            return sexp

        case SList(elems):
            new_elems = []
            for e in elems:
                if e == SAtom(BREAK):
                    continue
                new_elems.append(without_list_breaks(e))
            return SList(new_elems)


################################################################################
## Parse exceptions


@dataclass
class UnexpectedEnd:
    pass


@dataclass
class CannotParseAtom:
    atom: str


@dataclass
class ExpectedEnd:
    remaining: str


ParseExceptionKind = UnexpectedEnd | CannotParseAtom | ExpectedEnd


@dataclass
class ParseException(Exception):
    line: int
    kind: ParseExceptionKind


################################################################################
## Parsing


ATOM_REGEX: Final = re.compile(r"[A-Za-z0-9$_=<>*/+-]+")


def _error_prefix(line: int) -> str:
    return f"Line {line}: "


def _skip_whitespace(s: str, line: int) -> tuple[str, int]:
    res = re.search(r"[^\s]", s)
    if not res:
        return "", line + s.count("\n")
    return s[res.start() :], line + s[: res.start()].count("\n")


# Precondition: s has no whitespace at the start
def _parse_helper(s: str, line: int) -> tuple[SExp, str, int]:
    if s[0] == "(":
        s = s[1:]
        elems = []
        while True:
            s, line = _skip_whitespace(s, line)
            if not s:
                raise ParseException(line, UnexpectedEnd())
            if s[0] == ")":
                s = s[1:]
                break
            elem, s, line = _parse_helper(s, line)
            elems.append(elem)
        return SList(elems), s, line
    elif s[0] == '"':
        end = s.find('"', 1)
        return SAtom(s[: end + 1]), s[end + 1 :], line
    else:
        m = re.match(ATOM_REGEX, s)
        if not m:
            raise ParseException(line, CannotParseAtom(s))

        return SAtom(s[: m.end()]), s[m.end() :], line


def parse(s: str, *, line: int = 1) -> SExp:
    s, line = _skip_whitespace(s, line)
    sexp, s, line = _parse_helper(s, line)
    s, line = _skip_whitespace(s, line)
    if s:
        raise ParseException(line, ExpectedEnd(s))

    return sexp


def parse_many(s: str, *, line: int = 1) -> list[SExp]:
    sexps = []
    while True:
        s, line = _skip_whitespace(s, line)
        if not s:
            break
        sexp, s, line = _parse_helper(s, line)
        sexps.append(sexp)
    return sexps


################################################################################
## Show exceptions


@dataclass
class BreakOutsideList:
    pass


SexpShowExceptionKind = BreakOutsideList


@dataclass
class SexpShowException(Exception):
    kind: SexpShowExceptionKind


################################################################################
## Showing


def _show_helper(
    sexp: SExp,
    indent_width: int,
    indent: int,
) -> str:
    match sexp:
        case SAtom(s):
            if s == BREAK:
                raise SexpShowException(BreakOutsideList())
            return s

        case SList(elems):
            s = "("
            sep = ""
            for e in elems:
                if e == SAtom(BREAK):
                    indent += 1
                    sep = "\n" + " " * indent_width * indent
                    continue

                es = _show_helper(e, indent_width, indent)
                s += sep + es

                if not sep:
                    sep = " "
            s += ")"
            return s


def show(sexp: SExp, *, indent_width: int = 2) -> str:
    return _show_helper(sexp, indent_width, 0)
