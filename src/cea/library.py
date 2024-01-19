from dataclasses import dataclass
from .framework import *

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
        return TimeEq(self, other)

    def __lt__(self, other) -> "TimeLt":  # type: ignore[override]
        return TimeLt(self, other)


class TimeLit(Time):
    day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self.day = day

    @override
    def dl_repr(self) -> str:
        return str(self.day)


@dataclass
class TimeEq(Predicate):
    lhs: Time
    rhs: Time


@dataclass
class TimeLt(Predicate):
    lhs: Time
    rhs: Time


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
        return CondEq(self, other)


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
class CondEq(Predicate):
    lhs: Cond
    rhs: Cond


###############################################################################
# Data


@event
@dataclass
class Infect:
    library: str

    class M(Metadata):
        t: Time
        c: Cond


@event
@dataclass
class Seq:
    path: str

    class M(Metadata):
        t: Time
        c: Cond


@analysis
@dataclass
class PhenotypeScore:
    fold_change: list[float]
    sig: list[float]

    class M(Metadata):
        ti: Time
        tf: Time
        c: Cond


###############################################################################
# API


def pc(
    infection: Infect.M,
    seq1: Seq.M,
    seq2: Seq.M,
    ret: PhenotypeScore.M,
) -> list[Predicate]:
    return [
        infection.t < seq1.t,
        seq1.t < seq2.t,
        ret.ti == seq1.t,
        ret.tf == seq2.t,
        infection.c == seq1.c,
        infection.c == seq2.c,
        infection.c == ret.c,
    ]


@precondition(pc)
def ttest_enrichment(
    infection: Infect,
    seq1: Seq,
    seq2: Seq,
) -> PhenotypeScore:
    with open(infection.library, "r") as lib_file:
        lib = lib_file.read()

    with open(seq1.path, "r") as seq1_file:
        fasta1 = seq1_file.read()

    with open(seq2.path, "r") as seq2_file:
        fasta2 = seq2_file.read()

    count_matrix = make_count_matrix(lib, fasta1, fasta2)  # type: ignore
    fold_change = []
    sig = []
    for gene, before_count, after_count in count_matrix:
        tvalue, pvalue = scipy.stats.ttest_ind(...)  # type: ignore
        fold_change.append(tvalue)
        sig.append(pvalue)
    return PhenotypeScore(fold_change, sig)


@precondition(pc)
def mageck_enrichment(
    infection: Infect,
    seq1: Seq,
    seq2: Seq,
) -> PhenotypeScore:
    mageck_output = subprocess.check_output(["mageck", ...])  # type: ignore
    fold_change, sig = parse_mageck_output(mageck_output)  # type: ignore
    return PhenotypeScore(fold_change, sig)


def pc_wrong(
    infection: Infect.M,
    seq1: Seq.M,
    seq2: Seq.M,
    ret: PhenotypeScore.M,
) -> list[Predicate]:
    return [
        infection.t > seq1.t,
        seq1.t < seq2.t,
        ret.ti == seq1.t,
        ret.tf == seq2.t,
        infection.c == seq1.c,
        infection.c == seq2.c,
        infection.c == ret.c,
    ]


@precondition(pc_wrong)
def wrong_fn(
    infection: Infect,
    seq1: Seq,
    seq2: Seq,
) -> PhenotypeScore:
    return ...  # type: ignore
