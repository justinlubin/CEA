from dataclasses import dataclass
from typing import Optional

# from contextlib import contextmanager

from . import framework as fw
from . import library as lib


@dataclass
class Goal(fw.Atom):
    pass


class Program:
    _trace: list[fw.Atom]
    # _relations: list[fw.Relation]
    # _rules: list[fw.Rule]
    _qoi: Optional[fw.Atom]

    def __init__(
        self,
        # relations: list[fw.Relation],
        # rules: list[fw.Rule],
    ) -> None:
        self._trace = []
        # self._relations = relations
        # self._rules = rules

    def _save_relation(self, Rel: fw.Relation, args: list[fw.Term]) -> "Program":
        def wrap(a):
            if isinstance(a, int):
                return lib.TimeLit(a)
            else:
                return a

        self._trace.append(Rel(*map(wrap, args)))
        return self

    def Condition(self) -> lib.CondLit:
        return lib.CondLit()

    def __getattr__(self, attr):
        selected_rel = None
        for Rel in fw.Globals.defined_relations():
            if attr + ".M" == Rel.__qualname__:
                selected_rel = Rel
                break
        if not selected_rel:
            raise ValueError(f"Relation not found: {attr}")

        return lambda *args: self._save_relation(selected_rel, args)

    def qoi(self) -> None:
        self._qoi = self._trace.pop()

    def dl_repr(self) -> str:
        if not self._qoi:
            raise ValueError("QOI not set")

        blocks = []

        for rel in fw.Globals.defined_relations():
            rel_decl = rel.dl_decl()
            if rel_decl:
                blocks.append(rel_decl)

        blocks.append("")

        for rule in fw.Globals.defined_rules():
            blocks.append(rule.dl_repr())

        blocks.append("")

        for fact in self._trace:
            blocks.append(fact.dl_repr() + ".")

        blocks.append("")

        goal = Goal()
        blocks.append(fw.Rule("goal", goal, [self._qoi]).dl_repr())
        blocks.append("")
        blocks.append(f".output {goal.name()}")

        return "\n".join(blocks)

        # def condition(self) -> lib.CondLit:
        #     return lib.CondLit()

        # def transfect(self, day: int, condition: lib.Cond) -> None:
        #     self._trace.append(lib.Transfect.M(lib.TimeLit(day), condition))

        # def seq(self, day: int, condition: lib.Cond) -> None:
        #     self._trace.append(lib.Transfect.M(lib.TimeLit(day), condition))

        # algo
