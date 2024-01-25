from dataclasses import dataclass

from .framework import *

lib = Library()

###############################################################################
# Values

# Time


class TimeSort(Sort):
    @override
    def dl_repr(self) -> str:
        return "number"

    @override
    def parse(self, s: str) -> Term:
        return TimeLit(int(s))

    @override
    def var(self, s: str) -> Var:
        class V(Var, Time):
            pass

        return V(s)


class Time(Term):
    _sort: ClassVar[Sort] = TimeSort()

    @override
    @classmethod
    def sort(cls) -> Sort:
        return cls._sort

    def __eq__(self, other) -> "TimeEq":  # type: ignore[override]
        return TimeEq(lhs=self, rhs=other)

    def __lt__(self, other) -> "TimeLt":  # type: ignore[override]
        return TimeLt(lhs=self, rhs=other)


class TimeLit(Time):
    day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self.day = day

    @override
    def dl_repr(self) -> str:
        return str(self.day)


class TimeEq(Metadata):
    lhs: Time
    rhs: Time

    @override
    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return "="


class TimeLt(Metadata):
    lhs: Time
    rhs: Time

    @override
    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return "<"


# Condition


class CondSort(Sort):
    @override
    def dl_repr(self) -> str:
        return "symbol"

    @override
    def parse(self, s: str) -> Term:
        return CondLit(s)

    @override
    def var(cls, name: str) -> Var:
        class V(Var, Cond):
            pass

        return V(name)


class Cond(Term):
    _sort: ClassVar[Sort] = CondSort()

    @override
    @classmethod
    def sort(cls) -> Sort:
        return cls._sort

    def __eq__(self, other) -> "CondEq":  # type: ignore[override]
        return CondEq(lhs=self, rhs=other)


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


class CondEq(Metadata):
    lhs: Cond
    rhs: Cond

    @override
    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return "="


###############################################################################
# Events


class Infect(Event):
    @dataclass
    class D:
        library: str

    class M(Metadata):
        t: Time
        c: Cond


class Seq(Event):
    @dataclass
    class D:
        path: str

    class M(Metadata):
        t: Time
        c: Cond


###############################################################################
# Analysis types


class Distribution(Analysis):
    @dataclass
    class D:
        histogram: list[float]

    class M(Metadata):
        t: Time
        c: Cond


class PhenotypeScore(Analysis):
    @dataclass
    class D:
        fold_change: list[float]
        sig: list[float]

    class M(Metadata):
        ti: Time
        tf: Time
        c: Cond


###############################################################################
# API

# MAGeCK


def mageck_pc(
    infection: Infect.M,
    seq1: Seq.M,
    seq2: Seq.M,
    ret: PhenotypeScore.M,
) -> list[Metadata]:
    return [
        infection.t < seq1.t,
        seq1.t < seq2.t,
        ret.ti == seq1.t,
        ret.tf == seq2.t,
        infection.c == seq1.c,
        infection.c == seq2.c,
        infection.c == ret.c,
    ]


@precondition(lib, mageck_pc)
def mageck_enrichment(
    infection: Infect,
    seq1: Seq,
    seq2: Seq,
) -> PhenotypeScore.D:
    mageck_output = subprocess.check_output(["mageck", ...])  # type: ignore
    fold_change, sig = parse_mageck_output(mageck_output)  # type: ignore
    return PhenotypeScore.D(fold_change=fold_change, sig=sig)


# quantify


def quantify_pc(
    infection: Infect.M,
    seq: Seq.M,
    ret: Distribution.M,
):
    return [
        infection.c == seq.c,
        infection.t < seq.t,
        ret.t == seq.t,
        ret.c == seq.c,
    ]


@precondition(lib, quantify_pc)
def quantify(
    infection: Infect,
    seq: Seq,
) -> Distribution.D:
    return ...  # type: ignore


# t-test


def ttest_pc(
    d1: Distribution.M,
    d2: Distribution.M,
    ret: PhenotypeScore.M,
):
    return [
        d1.c == d2.c,
        d1.t < d2.t,
        ret.c == d1.c,
        ret.ti == d1.t,
        ret.tf == d2.t,
    ]


@precondition(lib, ttest_pc)
def ttest_enrichment(
    d1: Distribution,
    d2: Distribution,
) -> PhenotypeScore.D:
    return ...  # type: ignore


# wrong


def pc_wrong(
    infection: Infect.M,
    seq1: Seq.M,
    seq2: Seq.M,
    ret: PhenotypeScore.M,
) -> list[Metadata]:
    return [
        infection.t > seq1.t,
        seq1.t < seq2.t,
        ret.ti == seq1.t,
        ret.tf == seq2.t,
        infection.c == seq1.c,
        infection.c == seq2.c,
        infection.c == ret.c,
    ]


@precondition(lib, pc_wrong)
def wrong_fn(
    infection: Infect,
    seq1: Seq,
    seq2: Seq,
) -> PhenotypeScore.D:
    return ...  # type: ignore
