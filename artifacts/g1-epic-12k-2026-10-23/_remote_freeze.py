import subprocess
import pathlib

out = subprocess.check_output(
    ["bash", "-lc", "source /content/epic-venv/bin/activate && pip freeze"],
    text=True,
)
path = pathlib.Path("/content/ContextWeave/g1_epic_12k_pip_freeze.txt")
path.write_text(out)
print("wrote", path, "lines", len(out.splitlines()))
