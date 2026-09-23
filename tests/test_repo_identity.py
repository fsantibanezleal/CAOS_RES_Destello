"""The version the repository advertises must be the same everywhere it is written."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_file_and_changelog_agree():
    display = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d\.\d{2}\.\d{3}", display), display
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    latest = re.search(r"^## \[(\d\.\d{2}\.\d{3})\]", changelog, re.MULTILINE)
    assert latest is not None, "CHANGELOG has no release heading"
    assert latest.group(1) == display
