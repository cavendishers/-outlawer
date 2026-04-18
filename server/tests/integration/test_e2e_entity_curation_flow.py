import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_entity_curation_e2e_flow_script() -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    subprocess.run(
        [sys.executable, "scripts/e2e_entity_curation_flow.py"],
        cwd=ROOT,
        env=env,
        check=True,
    )
