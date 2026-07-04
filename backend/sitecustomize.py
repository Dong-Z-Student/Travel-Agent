from __future__ import annotations

import site
from pathlib import Path


local_packages = Path(__file__).resolve().parent / ".python_packages"
if local_packages.exists():
    site.addsitedir(str(local_packages))

user_site = site.getusersitepackages()
if user_site:
    site.addsitedir(user_site)
