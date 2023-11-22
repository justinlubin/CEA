import tempfile
import subprocess
import os


def run(program: str) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp_dirname:
        program_filename = tmp_dirname + "/program.dl"
        with open(program_filename, "w") as f:
            f.write(program)
        subprocess.run(
            ["souffle", "-D", tmp_dirname, program_filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ret = {}
        for filename in os.listdir(tmp_dirname):
            if filename.startswith(".") or filename == "program.dl":
                continue
            with open(tmp_dirname + "/" + filename, "r") as f:
                ret[filename] = f.read()
        return ret
