from typing import Optional

from . import derivation as der
from . import framework as fw
from . import stdbiolib


class Program:
    _trace: list[fw.Atom]
    _query: Optional[fw.Atom]
    _library: fw.Library

    def __init__(self, *libraries: fw.Library) -> None:
        if stdbiolib.lib not in libraries:
            libraries += (stdbiolib.lib,)

        self._trace = []
        self._library = fw.Library.merge(libraries)

    def Condition(self) -> stdbiolib.CondLit:
        return stdbiolib.CondLit()

    def __getattr__(self, attr: str):
        selected_relation = None
        for rel in self._library.relations():
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
                idbs=self._library.rules(),
            )
            if dl_prog.run_query(query=fw.Query([self._query])):
                print(">>> Possible! <<<")
                der.Constructor(
                    base_program=dl_prog,
                    interactor=der.CLIInteractor(),
                ).construct(initial_goal=self._query)
            else:
                print(">>> Not possible! <<<")

    def _save_relation(
        self,
        relation: fw.Relation,
        args: dict[str, int | fw.Term],
    ) -> "Program":
        def wrap(a: int | fw.Term) -> fw.Term:
            if isinstance(a, int):
                return stdbiolib.TimeLit(a)
            else:
                return a

        self._trace.append(
            fw.DynamicAtom(
                relation=relation, args={k: wrap(v) for k, v in args.items()}
            )
        )

        return self
