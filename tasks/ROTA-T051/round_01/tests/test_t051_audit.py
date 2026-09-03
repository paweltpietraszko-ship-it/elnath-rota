from __future__ import annotations

import re

import pymupdf

from rota.application import schedule_export as export
from rota.domain import ShiftKind
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
from tests.test_t020 import MONTH, _create_version, _seed, _settings, _work_item


def test_t051_real_pdf_human_header_and_internal_revision_are_separated() -> None:
    conn = connect(":memory:")
    _seed(conn)
    save_site_print_settings(
        conn,
        _settings(company_print_name="Firma Testowa", site_print_name="Obiekt Alfa"),
    )
    demand, assignment = _work_item(3, 6, 18, kind=ShiftKind.D)
    _create_version(
        conn,
        [demand],
        [assignment],
        version_id="SV-01234567-89ab-cdef-0123-456789abcdef",
    )

    result = export.generate_schedule_pdf(
        conn,
        site_id="SITE-1",
        month=MONTH,
        period_label="Sierpień 2026",
    )

    assert isinstance(result, export.ExportReady)
    with pymupdf.open(stream=result.pdf_bytes, filetype="pdf") as document:
        visible_text = "\n".join(page.get_text() for page in document)

    assert "Firma Testowa — Obiekt Alfa" in visible_text
    assert "Sierpień 2026" in visible_text
    assert "2026-08-01" in visible_text
    assert "2026-08-31" in visible_text
    assert "Kod weryfikacyjny grafiku:" in visible_text
    assert "Rewizja treści:" in visible_text
    assert "Schedule provenance" not in visible_text
    assert "Revision:" not in visible_text
    assert "SV-" not in visible_text
    assert re.search(r"\b[0-9a-f]{64}\b", visible_text) is None

    assert len(result.document_revision) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", result.document_revision)
    # brief.md:46-51 freezes full technical values in the API and limits
    # truncation to visible PDF/UI presentation.
    assert result.schedule_provenance.startswith(
        "Schedule provenance: SV-01234567-89ab-cdef-0123-456789abcdef / lineage-sha256:"
    )
    assert re.search(r"\b[0-9a-f]{64}\b", result.schedule_provenance)
