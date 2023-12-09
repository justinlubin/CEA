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


class Infect:
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
        path: str


@dataclass
class PhenotypeScore:
    @dataclass
    class M(Atom):
        ti: Time
        tf: Time
        c: Cond

    @dataclass
    class D:
        fold_change: list[float]
        sig: list[float]


###############################################################################
# API


def pc(
    infection: Infect.M,
    seq1: Seq.M,
    seq2: Seq.M,
    ret: PhenotypeScore.M,
) -> list[Atom]:
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
    infection: Infect.D,
    seq1: Seq.D,
    seq2: Seq.D,
) -> PhenotypeScore.D:
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
    return PhenotypeScore.D(fold_change, sig)


@precondition(pc)
def mageck_enrichment(
    infection: Infect.D,
    seq1: Seq.D,
    seq2: Seq.D,
) -> PhenotypeScore.D:
    mageck_output = subprocess.check_output(["mageck", ...])  # type: ignore
    fold_change, sig = parse_mageck_output(mageck_output)  # type: ignore
    return PhenotypeScore.D(fold_change, sig)
