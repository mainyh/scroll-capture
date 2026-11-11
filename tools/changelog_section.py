"""Print the CHANGELOG.md section for a version (used as GitHub release notes).

    python tools/changelog_section.py 0.9.0
"""
import re
import sys
from pathlib import Path

version = sys.argv[1].lstrip("v")
text = Path(__file__).resolve().parent.parent.joinpath("CHANGELOG.md").read_text(encoding="utf-8")
m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]:|\Z)", text, re.S | re.M)
sys.stdout.reconfigure(encoding="utf-8")
print(m.group(1).strip() if m else f"ScrollCapture {version}")
