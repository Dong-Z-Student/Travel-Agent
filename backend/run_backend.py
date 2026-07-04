from __future__ import annotations

import runpy
import sys
from pathlib import Path


backend_root = Path(__file__).resolve().parent
local_packages = backend_root / ".python_packages"
if local_packages.exists():
    sys.path.insert(0, str(local_packages))

if len(sys.argv) == 1:
    sys.argv = ["uvicorn", "app.main:app", "--reload"]
else:
    sys.argv = ["uvicorn", *sys.argv[1:]]

runpy.run_module("uvicorn", run_name="__main__")
