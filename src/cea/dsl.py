from typing import Optional

# from contextlib import contextmanager

from . import framework as fw
from . import library as lib


class Program:
    _trace: list[fw.Atom]
    _query: Optional[fw.Atom]

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
        self._query = self._trace.pop()

        if run:
            dl_prog = fw.DatalogProgram(edbs=self._trace)
            if dl_prog.run(query=fw.Query([self._query])):
                print(">>> Possible! <<<")
                fw.construct(
                    fw.CLIDerivationTreeConstructor(base_program=dl_prog),
                    self._query,
                )
            else:
                print(">>> Not possible! <<<")
