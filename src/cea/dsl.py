from typing import Optional

from . import derivation as der
from . import framework as fw
from . import stdbiolib

FlexibleTerm = int | fw.Term


def construct_program(
    derivation_tree: der.Tree, trace: dict[fw.Metadata, fw.Event.D]
) -> str:
    initializations = []
    computations = []

    names: dict[fw.Atom, str] = {}

    for subtree, bc in derivation_tree.postorder():
        head = subtree.head()
        if head in names:
            continue

        names[head] = "_".join(bc)

        computation = subtree.computation()
        if computation:
            computations.append((head, computation, subtree.children()))
        else:
            assert isinstance(head, fw.Metadata) and head in trace
            initializations.append((head, trace[head]))

    blocks = []

    blocks.append("# %% Load data\n")

    for m1, d in initializations:
        blocks.append(
            f"{names[m1]} = {d._parent.__name__}(\n    d={d},\n    m={m1.unparse()},\n)\n"
        )

    blocks.append("# %% Compute\n")

    for m, c, children in computations:
        if names[m]:
            arg_prefix = names[m] + "_"
            lhs = names[m]
        else:
            arg_prefix = ""
            lhs = "\noutput"
        arg_string = ", ".join([f"{cc}={arg_prefix}{cc}" for cc in children])
        rhs = f"{c.__name__}({arg_string})"
        blocks.append(f"{lhs} = {rhs}")

    return "\n".join(blocks)


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

            dt = der.Constructor(
                base_program=dl_prog,
                interactor=der.CLIInteractor(
                    goal_mode=der.CLIInteractor.Mode.AUTO,
                    rule_mode=der.CLIInteractor.Mode.FAST_FORWARD,
                ),
            ).construct(initial_goal=goal_atom)

            output_program = construct_program(
                derivation_tree=dt,
                trace=self._trace,
            )

            print(f"\n## OUTPUT PROGRAM\n\n{output_program}")

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
