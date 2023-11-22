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

    @classmethod
    def dl_type(cls) -> str:
        return "number"


class TimeVar(Var, Time):
    pass


class TimeLit(Time):
    day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self.day = day

    def dl_repr(self) -> str:
        return str(self.day)


@dataclass
class TimeEq(Relation):
    lhs: Time
    rhs: Time

    @classmethod
    def dl_decl(cls) -> Optional[str]:
        return None

    def dl_repr(self) -> str:
        return f"{self.lhs.dl_repr()} = {self.rhs.dl_repr()}"


@dataclass
class TimeLt(Relation):
    lhs: Time
    rhs: Time

    @classmethod
    def dl_decl(cls) -> Optional[str]:
        return None

    def dl_repr(self) -> str:
        return f"{self.lhs.dl_repr()} < {self.rhs.dl_repr()}"


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

    @classmethod
    def dl_type(cls) -> str:
        return "symbol"


class CondVar(Var, Cond):
    pass


@dataclass
class CondLit(Cond):
    cond: str

    def dl_repr(self) -> str:
        return f'"{self.cond}"'


@dataclass
class CondEq(Relation):
    lhs: Cond
    rhs: Cond

    @classmethod
    def dl_decl(cls) -> Optional[str]:
        return None

    def dl_repr(self) -> str:
        return f"{self.lhs.dl_repr()} = {self.rhs.dl_repr()}"


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
