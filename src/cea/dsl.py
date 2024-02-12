from . import derivation as der
from . import framework as fw
from . import stdbiolib

FlexibleTerm = int | fw.Term


class Program:
    _trace: dict[fw.Metadata, object]
    _library: fw.Library

    def __init__(self, *libraries: fw.Library) -> None:
        if stdbiolib.lib not in libraries:
            libraries += (stdbiolib.lib,)

        self._trace = {}
        self._library = fw.Library.merge(libraries)

    def do(self, m: fw.Metadata, d: object) -> None:
        assert m._parent == d._parent  # type: ignore
        self._trace[m] = d

    def query(self, m: fw.Metadata) -> None:
        dl_prog = fw.DatalogProgram(
            edbs=list(self._trace.keys()),
            idbs=self._library.rules(),
        )
        if dl_prog.run_query(query=fw.Query([m])):
            print(">>> Possible! <<<")

            dt = der.Constructor(
                base_program=dl_prog,
                interactor=der.CLIInteractor(
                    goal_mode=der.CLIInteractor.Mode.AUTO,
                    rule_mode=der.CLIInteractor.Mode.FAST_FORWARD,
                ),
            ).construct(initial_goal=m)

            output_program = self._construct_output_program(derivation_tree=dt)

            print(f"\n## OUTPUT PROGRAM\n\n{output_program}")

        else:
            print(">>> Not possible! <<<")

    def _construct_output_program(self, derivation_tree: der.Tree) -> str:
        initializations = []
        computations = []

        names: dict[fw.Atom, str] = {}

        for subtree, bc in derivation_tree.postorder():
            head = subtree.head()
            assert isinstance(head, fw.Metadata)
            if head in names:
                continue

            names[head] = "_".join(bc)

            computation = subtree.computation()
            if computation:
                computations.append((head, computation, subtree.children()))
            else:
                assert head in self._trace
                initializations.append((head, self._trace[head]))

        blocks = []

        blocks.append("from cea.stdbiolib import *\n")

        blocks.append("# %% Load data\n")

        for m1, d in initializations:
            parent = d._parent  # type: ignore
            blocks.append(
                f"{names[m1]} = {parent.__name__}(\n    d={d},\n    m={m1.unparse()},\n)\n"
            )

        blocks.append("\n# %% Compute\n")

        for m, c, children in computations:
            parent = m._parent  # type: ignore
            lhs = names[m] if names[m] else "output"
            arg_string = ", ".join(
                [
                    f"{child_param}={names[child.head()]}"
                    for child_param, child in children.items()
                ]
            )
            blocks.append(
                f"{lhs} = {parent.__name__}(\n    d={c.__name__}({arg_string}),\n    m={m.unparse()},\n)\n"
            )

        return "\n".join(blocks)
