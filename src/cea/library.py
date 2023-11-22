from dataclasses import dataclass
from .framework import *

###############################################################################
# Values

# Time


class Time(Term):
    def __eq__(self, other) -> "TimeEq":  # type: ignore[override]
        return TimeEq(self, other)

    def __lt__(self, other) -> "TimeLt":  # type: ignore[override]
        return TimeLt(self, other)

    def uniq(self) -> "TimeUnique":
        return TimeUnique(self)

    @classmethod
    def var(cls, name: str) -> Var:
        return TimeVar(name)


class TimeVar(Time, Var):
    name: str

    def __init__(self, name: str):
        self.name = name


class TimeLit(Time):
    day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self.day = day


@dataclass
class TimeEq(Relation):
    lhs: Time
    rhs: Time


@dataclass
class TimeLt(Relation):
    lhs: Time
    rhs: Time


@dataclass
class TimeUnique(Relation):
    t: Time


# Condition


class Cond(Term, metaclass=ABCMeta):
    def __eq__(self, other) -> "CondEq":  # type: ignore[override]
        return CondEq(self, other)

    @classmethod
    def var(cls, name: str) -> Var:
        return CondVar(name)


class CondVar(Cond, Var):
    name: str

    def __init__(self, name: str) -> None:
        self.name = name


class CondLit(Cond):
    cond: str

    def __init__(self, cond: str) -> None:
        self.cond = cond


@dataclass
class CondEq(Relation):
    lhs: Cond
    rhs: Cond


###############################################################################
# Helper relations


@dataclass
class TCRelation(Relation):
    t: Time
    c: Cond


###############################################################################
# Data


@dataclass
class Transfect(Data):
    library: str

    class R(TCRelation):
        pass


@dataclass
class Seq(Data):
    results: str

    class R(TCRelation):
        pass


@dataclass
class SGRE(Data):
    fold_change: float
    sig: float

    @dataclass
    class R(Relation):
        ti: Time
        tf: Time
        c: Cond


###############################################################################
# API


def pc(tr: Transfect.R, s1: Seq.R, s2: Seq.R, ret: SGRE.R) -> list[Relation]:
    return [
        tr.t < s1.t,
        s1.t < s2.t,
        tr.t.uniq(),
        ret.ti == s1.t,
        ret.tf == s2.t,
        tr.c == s1.c,
        tr.c == s2.c,
        tr.c == ret.c,
    ]


@precondition(pc)
def sgre(tr: Transfect, s1: Seq, s2: Seq) -> SGRE:
    return SGRE(2, 0.03)
