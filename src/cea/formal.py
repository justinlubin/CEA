from typing import Callable, Self
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

Sort = str
Symbol = str


class Signature:
    sorts: set[Sort]
    funs: set[Symbol]
    rels: set[Symbol]
    ar: dict[Symbol, list[Sort]]

    def __init__(
        self,
        sorts: set[Sort],
        funs: set[Symbol],
        rels: set[Symbol],
        ar: dict[Symbol, list[Sort]],
    ):
        if funs & rels:
            raise ValueError("Overlapping function and relation symbols")

        if ar.keys() != (funs | rels):
            raise ValueError("Invalid arity domain")

        for a in ar:
            if not (set(ar[a]) <= sorts):
                raise ValueError(f"Invalid arity codomain for {a}")

        self.sorts = sorts
        self.funs = funs
        self.rels = rels
        self.ar = ar

    def compatible(self, other: "Signature") -> bool:
        return (
            self.sorts == other.sorts
            and not (self.funs & other.funs)
            and not (self.rels & other.rels)
        )

    def union(self, other: "Signature") -> "Signature":
        if not self.compatible(other):
            raise ValueError("Cannot union incompatible signatures")

        return Signature(
            self.sorts,
            self.funs | other.funs,
            self.rels | other.rels,
            self.ar | other.ar,
        )

    def relational(self) -> bool:
        return not self.funs

    def functional(self) -> bool:
        return not self.rels


value_types = Signature(
    sorts={"Time"},
    funs=set(),
    rels={"TimeEq", "TimeLt"},
    ar={"TimeEq": ["Time", "Time"], "TimeLt": ["Time", "Time"]},
)

event_types = Signature(
    sorts=value_types.sorts,
    funs=set(),
    rels={"Seq", "Transfect"},
    ar={"Seq": ["Time"], "Transfect": ["Time"]},
)

assert event_types.relational()
assert event_types.compatible(value_types)
