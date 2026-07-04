from __future__ import annotations

import site
import sys
from pathlib import Path


user_site = site.getusersitepackages()
candidate_sites = [
    str(Path(__file__).resolve().parents[1] / ".python_packages"),
    user_site,
    str(Path.home() / "AppData" / "Roaming" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "site-packages"),
]

for candidate_site in candidate_sites:
    if candidate_site:
        try:
            site.addsitedir(candidate_site)
        except OSError:
            pass
