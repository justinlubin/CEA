import tempfile
import subprocess
import os

# @dataclass
# class DatalogOutput:
#     facts: dict[str, dict[str, list[tuple[str, ...]]]]
#
#     def dl_repr(self) -> str:
#         def wrap(arg: str):
#             try:
#                 return str(int(arg))
#             except ValueError:
#                 return '"' + arg + '"'
#
#         ret = []
#         for rel_name, fn_facts in self.facts.items():
#             for fn_name, atoms in fn_facts.items():
#                 suffix = "" if fn_name == "#" else f"{rel_name}__{fn_name}"
#                 for args in atoms:
#                     ret.append(f"{rel_name}{suffix}({', '.join(map(wrap, args))}).")
#         return "\n".join(ret)


def run(program: str) -> dict[str, list[tuple[str, ...]]]:
    with tempfile.TemporaryDirectory() as tmp_dirname:
        program_filename = tmp_dirname + "/program.dl"
        with open(program_filename, "w") as f:
            f.write(program)
        subprocess.run(
            ["souffle", "-D", tmp_dirname, program_filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        facts: dict[str, list[tuple[str, ...]]] = {}
        for filename in os.listdir(tmp_dirname):
            if not filename.endswith(".csv"):
                continue
            rel_name = filename[:-4]
            with open(tmp_dirname + "/" + filename, "r") as f:
                facts[rel_name] = []
                for line in f.readlines():
                    stripped_line = line.strip()
                    if stripped_line == "()":
                        facts[rel_name].append(())
                    else:
                        facts[rel_name].append(tuple(stripped_line.split("\t")))
        return facts
