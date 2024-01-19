from typing import Optional

# from contextlib import contextmanager

from . import framework as fw
from . import library as lib
from . import derivation as der


class Program:
    _trace: list[fw.Atom]
    _query: Optional[fw.Atom]

    def __init__(self) -> None:
        self._trace = []

    def Condition(self) -> lib.CondLit:
        return lib.CondLit()

    def __getattr__(self, attr: str):
        selected_relation = None
        for rel in fw.Globals.defined_relations():
            if rel.name() == attr + "_M":
                selected_relation = rel
                break
        if not selected_relation:
            raise ValueError(f"Relation not found: {attr}")

        return lambda **kwargs: self._save_relation(selected_relation, kwargs)

    def query(self, run=True) -> None:
        self._query = self._trace.pop()

        if run:
            dl_prog = fw.DatalogProgram(
                edbs=self._trace,
                idbs=fw.Globals.defined_rules(),
            )
            if dl_prog.run_query(query=fw.Query([self._query])):
                print(">>> Possible! <<<")
                der.construct(
                    der.CLIDerivationTreeConstructor(base_program=dl_prog),
                    self._query,
                    dl_prog,
                )
            else:
                print(">>> Not possible! <<<")

    def _save_relation(
        self,
        relation: fw.Relation,
        args: dict[str, int | fw.Term],
    ) -> "Program":
        def wrap(a: int | fw.Term) -> fw.Term:
            if isinstance(a, int):
                return lib.TimeLit(a)
            else:
                return a

        self._trace.append(
            fw.DynamicAtom(
                relation=relation, args={k: wrap(v) for k, v in args.items()}
            )
        )

        return self
