"""Independent preimplementation boundary checks for draft 49285a7."""
from pathlib import Path

import pytest

import backend


def test_canonical_scope_may_be_followed_by_a_markdown_heading(tmp_path: Path):
    brief = tmp_path / "brief.md"
    brief.write_text(
        "# Brief\n\nTASK_SCOPE:\n- backend.py\n- view.tsx\n\n"
        "## Acceptance\n\nNormal narrative follows.\n",
        encoding="utf-8",
    )

    assert backend.read_task_scope(brief) == ["backend.py", "view.tsx"]


def test_non_utf8_brief_is_reported_as_an_unreadable_scope(tmp_path: Path):
    brief = tmp_path / "brief.md"
    brief.write_bytes(b"TASK_SCOPE:\n- source.ts\n\xff")

    with pytest.raises(ValueError, match="unable to read brief"):
        backend.read_task_scope(brief)
