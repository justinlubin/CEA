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
class TimeEq(Atom):
    lhs: Time
    rhs: Time

    @classmethod
    def dl_decl(cls) -> Optional[str]:
        return None

    def dl_repr(self) -> str:
        return f"{self.lhs.dl_repr()} = {self.rhs.dl_repr()}"


@dataclass
class TimeLt(Atom):
    lhs: Time
    rhs: Time

    @classmethod
    def dl_decl(cls) -> Optional[str]:
        return None

    def dl_repr(self) -> str:
        return f"{self.lhs.dl_repr()} < {self.rhs.dl_repr()}"


@dataclass
class TimeUnique(Atom):
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


class CondLit(Cond):
    _counter: ClassVar[int] = 0

    symbol: str

    def __init__(self, symbol: Optional[str] = None) -> None:
        if symbol:
            self.symbol = symbol
        else:
            self.symbol = f"c{CondLit._counter}"
            CondLit._counter += 1

    def dl_repr(self) -> str:
        return f'"{self.symbol}"'


@dataclass
class CondEq(Atom):
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
class TCAtom(Atom):
    t: Time
    c: Cond


###############################################################################
# Data


class Transfect:
    class M(TCAtom):
        pass

    @dataclass
    class D:
        library: str


class Seq:
    class M(TCAtom):
        pass

    @dataclass
    class D:
        results: str


@dataclass
class SGRE:
    @dataclass
    class M(Atom):
        ti: Time
        tf: Time
        c: Cond

    @dataclass
    class D:
        fold_change: float
        sig: float


###############################################################################
# API


def pc(tr: Transfect.M, s1: Seq.M, s2: Seq.M, ret: SGRE.M) -> list[Atom]:
    return [
        tr.t < s1.t,
        s1.t < s2.t,
        # tr.t.uniq(),
        ret.ti == s1.t,
        ret.tf == s2.t,
        tr.c == s1.c,
        tr.c == s2.c,
        tr.c == ret.c,
    ]


# @precondition(
#     lambda tr, s1, s2, ret: [
#         tr.t < s1.t,
#         s1.t < s2.t,
#         # tr.t.uniq(),
#         ret.ti == s1.t,
#         ret.tf == s2.t,
#         tr.c == s1.c,
#         tr.c == s2.c,
#         tr.c == ret.c,
#     ]
# )


@precondition(pc)
def sgre(tr: Transfect.D, s1: Seq.D, s2: Seq.D) -> SGRE.D:
    return SGRE.D(2, 0.03)
