import sys

import src.cea.souffle as souffle
import src.cea.dsl as dsl

from typing import Any

if len(sys.argv) != 2:
    print(f"usage: {sys.argv[0]} <file.py>")
    sys.exit(1)


vals: dict[str, Any] = {}
with open(sys.argv[1], "r") as f:
    exec(f.read(), vals)

prog = None
for val in vals.values():
    if isinstance(val, dsl.Program):
        if prog:
            raise ValueError("Multiple defined programs")
        else:
            prog = val
if not prog:
    raise ValueError("No defined program")

output = souffle.run(prog.dl_repr())

if output["Goal.csv"]:
    print("Possible!")
else:
    print("Not possible!")
