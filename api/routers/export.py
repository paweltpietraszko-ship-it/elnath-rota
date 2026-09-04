"""Thin wrap for ROTA-T021 Wydruk Grafiku (arch/T021_spec.md). Two
existing, unchanged sources: rota.persistence.site_repository (print
settings CRUD, T020) + the new thin application wrapper
durable_inputs.save_print_settings (T021 gap, save side only) for the
write; rota.application.schedule_export.generate_schedule_pdf (T020,
unchanged) for the export itself. Every ExportProblem.problem_code gets
its own Polish message here -- never a raw code, never a generic
catch-all (anglicism rule, arch/T021_spec.md)."""
from __future__ import annotations

import base64
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.durable_inputs import save_print_settings
from rota.application.schedule_export import ExportReady, generate_schedule_pdf
from rota.persistence.site_repository import SitePrintSettings, WorkCodeInterval, get_site_print_settings

router = APIRouter(prefix="/workspace", tags=["export"])

# Ground truth: every distinct code schedule_export.py can actually raise
# (grepped, not copied from the spec's own rough "~17" estimate -- 16
# confirmed, one -- PRINT_SETTINGS_INVALID -- constructed directly rather
# than via ExportProblemError, still exhaustive).
PROBLEM_MESSAGE_PL: dict[str, str] = {
    "PROVENANCE_INCOMPLETE": "Brak pełnej, jednoznacznej historii wersji grafiku dla tego miesiąca.",
    "PRINT_SETTINGS_MISSING": "Brak zapisanych ustawień wydruku dla tego obiektu. Skonfiguruj je poniżej.",
    "PRINT_SETTINGS_INVALID": "Zapisane ustawienia wydruku są niepoprawne. Popraw je i zapisz ponownie.",
    "NO_CURRENT_SCHEDULE": "Brak aktualnego grafiku dla tego miesiąca.",
    "REGIME_REPLAN_REQUIRED": "Zmieniono reżim planowania obiektu — przed wydrukiem zaplanuj ten miesiąc ponownie.",
    "UNSUPPORTED_TRAINEE_PRINT": "Grafik zawiera przypisania szkoleniowe, których ten wydruk jeszcze nie obsługuje.",
    "WORK_PROVENANCE_INCOMPLETE": "Co najmniej jedno przypisanie ma niespójne lub niepełne dane źródłowe.",
    "UNSUPPORTED_SHIFT_KIND": "Grafik zawiera rodzaj zmiany, którego ten wydruk nie obsługuje.",
    "MULTIPLE_WORK_ITEMS_PER_CELL": "Jeden dzień jednego pracownika ma więcej niż jedno niezależne zdarzenie — wydruk nie może ich rozdzielić.",
    "WORK_CODE_MAPPING_REQUIRED": "Co najmniej jedno przypisanie nie pasuje do żadnego skonfigurowanego kodu zmiany (D1–D5/N1–N5). Sprawdź ustawienia wydruku.",
    "ABSENCE_DECOMPOSITION_REQUIRED": "Nie udało się rozłożyć nieobecności pracownika na dostępne kody godzinowe.",
    "ABSENCE_REFERENCE_INCOMPLETE": "Brak pełnych danych źródłowych zapisanej nieobecności pracownika.",
    "ASSIGNMENT_ABSENCE_CONFLICT": "Pracownik ma realne przypisanie w dniu zgłoszonej nieobecności — dane są sprzeczne.",
    "ABSENCE_SITE_AMBIGUOUS": "Pracownik ma więcej niż jedno aktywne miejsce pracy — nie można jednoznacznie przypisać nieobecności.",
    "PRINT_FONT_UNAVAILABLE": "Brak w tym środowisku czcionki z pełnym zestawem polskich znaków.",
    "ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT": "Obsada lub nagłówek są zbyt duże, by zmieścić się na jednej stronie wydruku.",
}


class WorkCodeIntervalOut(BaseModel):
    start_time: str
    end_time: str
    end_next_day: bool


class SitePrintSettingsOut(BaseModel):
    site_id: str
    company_print_name: str
    site_print_name: str
    base_regime: Literal["12h", "24h"]
    work_code_intervals: dict[str, WorkCodeIntervalOut | None]
    reserve_hours: dict[str, int | None]
    # ROTA-T052: default S1 interval for MonthlyPlanning, not a WORK_CODE_KEYS entry.
    s1_default_interval: WorkCodeIntervalOut | None = None


class SitePrintSettingsIn(BaseModel):
    # ROTA-T021 UI audit gate (finding #10): extra="forbid" makes a stray
    # field (e.g. a caller echoing SitePrintSettingsOut.site_id back into
    # this request body) a real validation error instead of a silently
    # dropped field.
    model_config = ConfigDict(extra="forbid")
    company_print_name: str
    site_print_name: str
    base_regime: Literal["12h", "24h"]
    work_code_intervals: dict[str, WorkCodeIntervalOut | None]
    reserve_hours: dict[str, int | None]
    s1_default_interval: WorkCodeIntervalOut | None = None


class ExportRequest(BaseModel):
    period_label: str


class ExportResultOut(BaseModel):
    ok: bool
    pdf_base64: str | None = None
    document_revision: str | None = None
    schedule_provenance: str | None = None
    problem_code: str | None = None
    message: str | None = None


def _settings_out(s: SitePrintSettings) -> SitePrintSettingsOut:
    return SitePrintSettingsOut(
        site_id=s.site_id, company_print_name=s.company_print_name, site_print_name=s.site_print_name,
        base_regime=s.base_regime,
        work_code_intervals={
            k: WorkCodeIntervalOut(start_time=v.start_time, end_time=v.end_time, end_next_day=v.end_next_day) if v else None
            for k, v in s.work_code_intervals.items()
        },
        reserve_hours=dict(s.reserve_hours),
        s1_default_interval=(
            WorkCodeIntervalOut(
                start_time=s.s1_default_interval.start_time,
                end_time=s.s1_default_interval.end_time,
                end_next_day=s.s1_default_interval.end_next_day,
            )
            if s.s1_default_interval
            else None
        ),
    )


@router.get("/sites/{site_id}/print-settings", response_model=SitePrintSettingsOut | None)
def get_print_settings(site_id: str, conn=Depends(get_conn)) -> SitePrintSettingsOut | None:
    settings = get_site_print_settings(conn, site_id)
    return _settings_out(settings) if settings else None


@router.put("/sites/{site_id}/print-settings", status_code=204)
def put_print_settings(site_id: str, payload: SitePrintSettingsIn, conn=Depends(get_conn)) -> None:
    settings = SitePrintSettings(
        site_id=site_id, company_print_name=payload.company_print_name, site_print_name=payload.site_print_name,
        base_regime=payload.base_regime,
        work_code_intervals={
            k: WorkCodeInterval(start_time=v.start_time, end_time=v.end_time, end_next_day=v.end_next_day) if v else None
            for k, v in payload.work_code_intervals.items()
        },
        reserve_hours=dict(payload.reserve_hours),
        s1_default_interval=(
            WorkCodeInterval(
                start_time=payload.s1_default_interval.start_time,
                end_time=payload.s1_default_interval.end_time,
                end_next_day=payload.s1_default_interval.end_next_day,
            )
            if payload.s1_default_interval
            else None
        ),
    )
    try:
        save_print_settings(conn, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id, settings=settings)
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/sites/{site_id}/schedule/{month}/export", response_model=ExportResultOut)
def post_export(site_id: str, month: date, payload: ExportRequest, conn=Depends(get_conn)) -> ExportResultOut:
    try:
        result = generate_schedule_pdf(conn, site_id=site_id, month=month, period_label=payload.period_label)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    if isinstance(result, ExportReady):
        return ExportResultOut(
            ok=True, pdf_base64=base64.b64encode(result.pdf_bytes).decode("ascii"),
            document_revision=result.document_revision, schedule_provenance=result.schedule_provenance,
        )
    # Every code schedule_export.py can raise today is covered above
    # (grepped exhaustively) -- this fallback only guards against a future
    # code added there without this map being updated, so it stays
    # explicit that the codebase moved rather than showing English text.
    message = PROBLEM_MESSAGE_PL.get(result.problem_code, f"Nieprzetłumaczony kod błędu wydruku: {result.problem_code}.")
    return ExportResultOut(ok=False, problem_code=result.problem_code, message=message)


if __name__ == "__main__":
    print("api.routers.export module OK")
