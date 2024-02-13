import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import subprocess as sp

from dataclasses import dataclass
from typing import ClassVar, Optional

from .framework import *
from .util import override

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
        return Day(int(s))

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

    def days(self) -> int:
        raise ValueError("Cannot compute days")

    def __eq__(self, other) -> "TimeEq":  # type: ignore[override]
        return TimeEq(lhs=self, rhs=other)

    def __lt__(self, other) -> "TimeLt":  # type: ignore[override]
        return TimeLt(lhs=self, rhs=other)


class Day(Time):
    _day: int

    def __init__(self, day: int):
        if day < 0:
            raise ValueError("Negative day")
        self._day = day

    @override
    def dl_repr(self) -> str:
        return str(self._day)

    @override
    def unparse(self) -> str:
        return f"Day({self._day})"

    @override
    def days(self) -> int:
        return self._day


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


class PopulationSort(Sort):
    @override
    def dl_repr(self) -> str:
        return "symbol"

    @override
    def parse(self, s: str) -> Term:
        return Pop(s)

    @override
    def var(cls, name: str) -> Var:
        class V(Var, Population):
            pass

        return V(name)


class Population(Term):
    _sort: ClassVar[Sort] = PopulationSort()

    @override
    @classmethod
    def sort(cls) -> Sort:
        return cls._sort

    def __eq__(self, other) -> "PopulationEq":  # type: ignore[override]
        return PopulationEq(lhs=self, rhs=other)

    def name(self) -> str:
        raise ValueError("Cannot compute name")


class Pop(Population):
    _counter: ClassVar[int] = 0

    symbol: str

    def __init__(self, symbol: Optional[str] = None) -> None:
        if symbol:
            self.symbol = symbol
        else:
            self.symbol = f"p{Pop._counter}"
            Pop._counter += 1

    @override
    def dl_repr(self) -> str:
        return f'"{self.symbol}"'

    @override
    def unparse(self) -> str:
        return f'Pop("{self.symbol}")'

    @override
    def name(self) -> str:
        return self.symbol


class PopulationEq(Metadata):
    lhs: Population
    rhs: Population

    @override
    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return "="


# Infection


class InfectionSort(Sort):
    @override
    def dl_repr(self) -> str:
        return "symbol"

    @override
    def parse(self, s: str) -> Term:
        library, negative_controls = s.split(";")
        return Inf(library=library, negative_controls=negative_controls)

    @override
    def var(cls, name: str) -> Var:
        class V(Var, Infection):
            pass

        return V(name)


class Infection(Term):
    _sort: ClassVar[Sort] = InfectionSort()

    @override
    @classmethod
    def sort(cls) -> Sort:
        return cls._sort

    def __eq__(self, other) -> "InfectionEq":  # type: ignore[override]
        return InfectionEq(lhs=self, rhs=other)

    def library(self) -> str:
        raise ValueError("Cannot compute path")

    def negative_controls(self) -> str:
        raise ValueError("Cannot compute negative controls")


class Inf(Infection):
    _library: str
    _negative_controls: str

    def __init__(self, library: str, negative_controls: str) -> None:
        self._library = library
        self._negative_controls = negative_controls

    @override
    def dl_repr(self) -> str:
        return f'"{self._library};{self._negative_controls}"'

    @override
    def unparse(self) -> str:
        return f'Inf(library="{self._library}", negative_controls="{self._negative_controls}")'

    @override
    def library(self) -> str:
        return self._library

    @override
    def negative_controls(self) -> str:
        return self._negative_controls


class InfectionEq(Metadata):
    lhs: Infection
    rhs: Infection

    @override
    @classmethod
    def infix_symbol(cls) -> Optional[str]:
        return "="


###############################################################################
# MDs


class Infect(MD):
    class M(Metadata):
        t: Time
        pop: Population
        inf: Infection

    @dataclass
    class D:
        pass

    m: M
    d: D


class Infected(MD):
    class M(Metadata):
        t: Time
        pop: Population
        inf: Infection

    @dataclass
    class D:
        pass

    m: M
    d: D


class CellSort(MD):
    class M(Metadata):
        t: Time
        pop_in: Population
        pop_no: Population
        pop_yes: Population

    @dataclass
    class D:
        pass

    m: M
    d: D


class Seq(MD):
    class M(Metadata):
        t: Time
        pop: Population

    @dataclass
    class D:
        path: str

    m: M
    d: D


class ReadCountMatrix(MD):
    class M(Metadata):
        t1: Time
        t2: Time
        pop1: Population
        pop2: Population

    @dataclass
    class D:
        path: str
        inf: Infection

    m: M
    d: D


class PhenotypeScore(MD):
    class M(Metadata):
        t1: Time
        t2: Time
        pop1: Population
        pop2: Population

    @dataclass
    class D:
        path: str

    m: M
    d: D


class VolcanoPlot(MD):
    class M(Metadata):
        t1: Time
        t2: Time
        pop1: Population
        pop2: Population

    @dataclass
    class D:
        pass

    m: M
    d: D


###############################################################################
# API

# Infections


def infect_infected_pc(inf: Infect.M, ret: Infected.M) -> list[Metadata]:
    return [ret.t == inf.t, ret.pop == inf.pop, ret.inf == inf.inf]


@precondition(lib, infect_infected_pc)
def infect_infected(inf: Infect) -> Infected.D:
    return Infected.D()


def commute_infected_sort_yes_pc(
    inf: Infected.M,
    cs: CellSort.M,
    ret: Infected.M,
) -> list[Metadata]:
    return [
        inf.pop == cs.pop_in,
        inf.t < cs.t,
        ret.t == inf.t,
        ret.pop == cs.pop_yes,
        ret.inf == inf.inf,
    ]


def commute_infected_sort_no_pc(
    inf: Infected.M,
    cs: CellSort.M,
    ret: Infected.M,
) -> list[Metadata]:
    return [
        inf.pop == cs.pop_in,
        inf.t < cs.t,
        ret.t == inf.t,
        ret.pop == cs.pop_no,
        ret.inf == inf.inf,
    ]


@precondition(lib, commute_infected_sort_yes_pc)
def commute_infected_sort_yes(inf: Infected, cs: CellSort) -> Infected.D:
    return inf.d


@precondition(lib, commute_infected_sort_no_pc)
def commute_infected_sort_no(inf: Infected, cs: CellSort) -> Infected.D:
    return inf.d


# Read Counts


def quantify_pc(
    inf1: Infected.M,
    inf2: Infected.M,
    seq1: Seq.M,
    seq2: Seq.M,
    ret: ReadCountMatrix.M,
) -> list[Metadata]:
    return [
        inf1.t == inf2.t,
        inf1.inf == inf2.inf,
        inf1.pop == seq1.pop,
        inf2.pop == seq2.pop,
        inf1.t < seq1.t,
        inf2.t < seq2.t,
        ret.t1 == seq1.t,
        ret.pop1 == seq1.pop,
        ret.t2 == seq2.t,
        ret.pop2 == seq2.pop,
    ]


@precondition(lib, quantify_pc)
def quantify(inf1: Infected, inf2: Infected, seq1: Seq, seq2: Seq) -> ReadCountMatrix.D:
    inf = inf1.m.inf
    name1 = seq1.m.pop.name()
    name2 = seq2.m.pop.name()
    fullname = f"{name1}-{name2}"
    sp.run(
        [
            "mageck",
            "count",
            "-l",
            inf.library(),
            "-n",
            fullname,
            "--sample-label",
            f"{name1},{name2}",
            "--fastq",
            seq1.d.path,
            seq2.d.path,
        ]
    )
    return ReadCountMatrix.D(path=f"{fullname}.count.txt", inf=inf)


# MAGeCK


def mageck_sequential_pc(
    rcm: ReadCountMatrix.M,
    ret: PhenotypeScore.M,
) -> list[Metadata]:
    return [
        rcm.t1 < rcm.t2,
        rcm.pop1 == rcm.pop2,
        ret.t1 == rcm.t1,
        ret.t2 == rcm.t2,
        ret.pop1 == rcm.pop1,
        ret.pop2 == rcm.pop2,
    ]


def mageck_parallel_pc(
    rcm: ReadCountMatrix.M,
    ret: PhenotypeScore.M,
) -> list[Metadata]:
    return [
        rcm.t1 == rcm.t2,
        ret.t1 == rcm.t1,
        ret.t2 == rcm.t2,
        ret.pop1 == rcm.pop1,
        ret.pop2 == rcm.pop2,
    ]


@precondition(lib, mageck_sequential_pc)
def mageck_sequential(
    rcm: ReadCountMatrix,
) -> PhenotypeScore.D:
    return ...  # type: ignore


@precondition(lib, mageck_parallel_pc)
def mageck_parallel(
    rcm: ReadCountMatrix,
) -> PhenotypeScore.D:
    name1 = rcm.m.pop1.name()
    name2 = rcm.m.pop2.name()
    fullname = f"{name1}-{name2}"
    sp.run(
        [
            "mageck",
            "test",
            "-k",
            f"{fullname}.count.txt",
            "-t",
            name2,
            "-c",
            name1,
            "-n",
            fullname,
            "--control-sgrna",
            rcm.d.inf.negative_controls(),
        ]
    )
    return PhenotypeScore.D(path=f"{fullname}.gene_summary.txt")


def volcano_plot_pc(ps: PhenotypeScore.M, ret: VolcanoPlot.M) -> list[Metadata]:
    return [
        ret.t1 == ps.t1,
        ret.t2 == ps.t2,
        ret.pop1 == ps.pop1,
        ret.pop2 == ps.pop2,
    ]


@precondition(lib, volcano_plot_pc)
def volcano_plot(ps: PhenotypeScore) -> VolcanoPlot.D:
    df = pd.read_csv(ps.d.path, sep="\t")
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    ax.scatter(df["pos|lfc"], -np.log10(df["pos|fdr"]))
    ax.set_xlabel("LFC")
    ax.set_ylabel("FDR")
    fig.savefig(f"Volcano-{ps.d.path}.pdf")
    return VolcanoPlot.D()
