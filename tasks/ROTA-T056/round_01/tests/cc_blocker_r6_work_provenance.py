"""ROTA-T056 -- CC blocker found during implementation (round 6, before any
product code was written for the manual-correction/export path). Not a
Codex test, not part of TASK_SCOPE -- a minimal reproducer proving
_validate_item's existing WORK_PROVENANCE_INCOMPLETE gate rejects exactly
the flow brief.md section 8 describes: a manual correction that keeps the
Assignment's original covers_demand_id but changes its real
start_datetime/end_datetime to a custom (e.g. 17h) duration.

Run: .venv/Scripts/python.exe tasks/ROTA-T056/round_01/tests/cc_blocker_r6_work_provenance.py
"""
import sys
from dataclasses import replace
from datetime import datetime

sys.path.insert(0, ".")

from rota.application import schedule_export as SE
from rota.domain import ShiftKind
from rota.persistence.db import connect
from rota.persistence.site_repository import save_site_print_settings
import tests.test_t020 as T020

conn = connect(":memory:")
T020._seed(conn)
save_site_print_settings(conn, T020._settings())

demand, assignment = T020._work_item(1, 6, 18, kind=ShiftKind.D)  # normal 12h D, 06:00-18:00
# Brief section 8: "wybor kodu buduje nowy realny przedzial na dacie
# jednoznacznie pokrywanego ShiftDemandu; pozostale pola Assignmentu
# zachowuje" -- same covers_demand_id, only start/end change.
custom = replace(assignment, end_datetime=datetime(2026, 8, 1, 23, 0))  # 17h total
T020._create_version(conn, [demand], [custom])

result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=T020.MONTH, period_label="sierpien 2026")
print(type(result).__name__, getattr(result, "problem_code", None), getattr(result, "message", None))
assert type(result).__name__ == "ExportProblem" and result.problem_code == "WORK_PROVENANCE_INCOMPLETE", (
    "expected WORK_PROVENANCE_INCOMPLETE -- if this assertion fails, the blocker no longer reproduces, re-check schedule_export.py::_validate_item"
)
print("BLOCKER CONFIRMED: schedule_export.py::_validate_item rejects a same-covers_demand_id, "
      "changed-duration Assignment before _map_work_code is ever reached.")
