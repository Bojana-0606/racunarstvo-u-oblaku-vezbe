import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

app = Path(__file__).resolve().parent
csv = Path(os.environ["CSV_PATH"]).resolve()
target = os.environ["TARGET"]
k = int(os.environ["K"])
fold = int(os.environ["FOLD"])

if not 1 <= fold <= k:
    raise ValueError("FOLD mora biti između 1 i K")

with tempfile.TemporaryDirectory() as work:
    subprocess.run(
        [
            sys.executable, str(app / "folds.py"),
            "--csv", str(csv),
            "--target", target,
            "--k", str(k),
        ],
        cwd=work,
        check=True,
    )

    name = f"fold_{fold:04d}"
    subprocess.run(
        [
            sys.executable, str(app / "model.py"),
            "--train", f"{name}_train.csv",
            "--test", f"{name}_test.csv",
            "--target", target,
        ],
        cwd=work,
        check=True,
    )

    metrics = json.loads(
        (Path(work) / "metrics.json").read_text(encoding="utf-8")
    )
    metrics["fold"] = fold
    metrics["k"] = k
    print("RESULT_JSON=" + json.dumps(metrics), flush=True)
