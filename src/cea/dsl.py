from dataclasses import dataclass
from typing import Optional

# from contextlib import contextmanager

from . import framework as fw
from . import library as lib
from . import souffle


@dataclass
class Goal:
    @dataclass
    class M(fw.Atom):
        pass

    @dataclass
    class D:
        pass


def goal_fn() -> Goal.D:
    return Goal.D()


class Program:
    _trace: list[fw.Atom]
    _qoi: Optional[fw.Atom]

    def __init__(self) -> None:
        self._trace = []

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

        return lambda *args, **kwargs: self._save_relation(selected_rel, args)

    def query(self, run=True) -> None:
        self._qoi = self._trace.pop()

        if run:
            program = self.dl_repr()
            output = souffle.run(program)
            if True or output.facts[Goal.M.name()]:
                print(output)
            else:
                print("Not possible!")

    def dl_repr(self) -> str:
        if not self._qoi:
            raise ValueError("QOI not set")

        blocks = []

        for rel in fw.Globals.defined_relations():
            rel_decl = rel.dl_decl()
            if rel_decl:
                blocks.append(rel_decl)
                blocks.append(f".output {rel.name()}")
                blocks.append("")

        blocks.append("")

        for rule in fw.Globals.defined_rules():
            blocks.append(rule.dl_repr())
            blocks.append("")

        blocks.append("")

        for fact in self._trace:
            blocks.append(fact.dl_repr() + ".")

        blocks.append("")

        blocks.append(
            fw.Rule(
                fn=goal_fn,
                head=Goal.M(),
                dependencies=[],
                checks=[self._qoi],
            ).dl_repr()
        )

        return "\n".join(blocks)
