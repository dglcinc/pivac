# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""CLAUDE.md loads in every session, so it has a size ceiling; the detail
lives in .claude/rules/ and docs/. Also checks that the three copies of the
pivac unit list agree, since a unit missing from the backup script's start
list stays dead after the monthly backup."""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CEILING = 30000


def test_claude_md_under_ceiling():
    n = len((REPO / "CLAUDE.md").read_text(encoding="utf-8"))
    assert n <= CEILING, (
        f"CLAUDE.md is {n} characters, over the {CEILING} ceiling: move the "
        "detail to .claude/rules/ or docs/ (see Keeping These Files Current)")


def test_rules_files_are_path_scoped_and_routed():
    core = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    rules = sorted((REPO / ".claude" / "rules").glob("*.md"))
    assert rules
    for f in rules:
        text = f.read_text(encoding="utf-8")
        assert text.startswith("---\npaths:\n"), f"{f.name} has no paths: frontmatter, so it would load every session"
        assert f".claude/rules/{f.name}" in core, f"{f.name} is missing from CLAUDE.md's routing table"


def _array(text, name):
    body = re.search(rf"^{name}=\((.*?)\)", text, re.S | re.M).group(1)
    return {s for s in body.split() if s.startswith("pivac-")}


def test_service_lists_agree():
    listed = subprocess.run(["bash", str(REPO / "scripts" / "pivac-services.sh"), "list"],
                            capture_output=True, text=True, check=True).stdout.split()
    backup = (REPO / "scripts" / "nas-image-backup.sh").read_text()
    assert set(listed) == _array(backup, "STOP_SVCS") == _array(backup, "START_SVCS")
    units = {p.stem for p in (REPO / "scripts" / "systemd").glob("pivac-*.service")}
    assert set(listed) <= units, f"no unit file for {set(listed) - units}"
