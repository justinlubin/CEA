from typing import Optional

from . import derivation as der
from . import framework as fw
from . import stdbiolib

FlexibleTerm = int | fw.Term


class Program:
    _trace: dict[fw.Metadata, fw.Event.D]
    _query: Optional[fw.Metadata]
    _library: fw.Library

    def __init__(self, *libraries: fw.Library) -> None:
        if stdbiolib.lib not in libraries:
            libraries += (stdbiolib.lib,)

        self._trace = {}
        self._library = fw.Library.merge(libraries)

    def Condition(self) -> stdbiolib.CondLit:
        return stdbiolib.CondLit()

    def do(
        self,
        E: type[fw.Event],
        at: dict[str, FlexibleTerm],
        where: dict[str, object],
    ):
        self._trace[E.M(**Program.wrap_all(at))] = E.D(**where)

    def query(
        self,
        A: type[fw.Analysis],
        at: dict[str, FlexibleTerm],
    ) -> None:
        dl_prog = fw.DatalogProgram(
            edbs=list(self._trace.keys()),
            idbs=self._library.rules(),
        )
        goal_atom = A.M(**Program.wrap_all(at))
        if dl_prog.run_query(query=fw.Query([goal_atom])):
            print(">>> Possible! <<<")
            der.Constructor(
                base_program=dl_prog,
                interactor=der.CLIInteractor(
                    goal_mode=der.CLIInteractor.Mode.AUTO,
                    rule_mode=der.CLIInteractor.Mode.FAST_FORWARD,
                ),
            ).construct(initial_goal=goal_atom)
            # print(*[str(t) for t in dt.postorder()], sep="\n")
        else:
            print(">>> Not possible! <<<")

    @staticmethod
    def wrap(x: FlexibleTerm) -> fw.Term:
        if isinstance(x, int):
            return stdbiolib.TimeLit(x)
        else:
            return x

    @staticmethod
    def wrap_all(xs: dict[str, FlexibleTerm]) -> dict[str, fw.Term]:
        return {k: Program.wrap(v) for k, v in xs.items()}
