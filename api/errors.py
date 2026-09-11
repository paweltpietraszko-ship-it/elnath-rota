"""Shared exception -> HTTP status mapping (brief.md section 3.2: one
shared helper, never per-router ad-hoc handling).

ROTA-T060 (ARCHITECT_RULING R2, brief 2.1): this module is the ONLY owner
of the public-error contract. A controlled, coordinator-safe error always
keeps its correct HTTP status, gets a Polish operational message with no
technical identifier, and carries the `X-Elnath-Public-Error: 1` header --
the one marker `client.ts` trusts before rendering a `detail` string.
`str(exc)` (or any per-instance interpolation of it) never reaches the
public message: every entry below is a fixed, generic sentence for its
exception class, since the exception's own text is exactly where a raw
id/site_id/version_id lives.
"""
from __future__ import annotations

from fastapi import HTTPException

from rota.application.errors import (
    CandidateRejected,
    CoordinatorContextAlreadyActive,
    HistoricalServiceMutationRejected,
    InvalidCoordinatorContext,
    NoCurrentScheduleVersion,
    NotWorkedRequiresPlannedPrimary,
    ReplanNotAvailableAfterAcceptance,
    ScheduleVersionNotWorking,
)
from rota.persistence.employee_repository import EmployeeNotFound
from rota.persistence.schedule_errors import (
    CannotDeleteLiveScheduleVersion,
    CannotRestoreLiveScheduleVersion,
    NonEditableScheduleVersion,
    ScheduleVersionNotFound,
)
from rota.persistence.site_memory import CoordinatorActionNotFound
from rota.persistence.site_profile_repository import SiteProfileNotFound
from rota.persistence.site_repository import (
    InvalidSitePrintSettings,
    SiteNotFound,
    SiteRegimeChangeRejected,
    UnknownSiteProfile,
)
from rota.planning.shift_catalog import InvalidStandardShift

PUBLIC_ERROR_HEADER_NAME = "X-Elnath-Public-Error"
_PUBLIC_ERROR_HEADERS = {PUBLIC_ERROR_HEADER_NAME: "1"}

_UNEXPECTED_ERROR_DETAIL = "Wystąpił nieoczekiwany błąd. Spróbuj ponownie."

_STATUS_AND_DETAIL_BY_EXCEPTION: tuple[tuple[type[Exception], int, str], ...] = (
    (SiteNotFound, 404, "Nie znaleziono wskazanego obiektu."),
    (UnknownSiteProfile, 404, "Nie znaleziono profilu zmianowego dla tego obiektu."),
    (SiteProfileNotFound, 404, "Nie znaleziono profilu zmianowego."),
    (EmployeeNotFound, 404, "Nie znaleziono wskazanego pracownika."),
    (CoordinatorActionNotFound, 404, "Nie znaleziono wskazanej akcji koordynatora."),
    (NoCurrentScheduleVersion, 404, "Brak aktualnego grafiku dla tego miesiąca."),
    (ScheduleVersionNotFound, 404, "Nie znaleziono wskazanej wersji grafiku."),
    (NotWorkedRequiresPlannedPrimary, 400, "Tę operację można wykonać tylko dla zaplanowanej służby podstawowej."),
    (InvalidCoordinatorContext, 403, "Koordynator lub obiekt nie są aktywni w tym kontekście."),
    (CoordinatorContextAlreadyActive, 409, "Ten kontekst koordynatora jest już aktywny."),
    (SiteRegimeChangeRejected, 409, "Nie można teraz zmienić reżimu planowania tego obiektu."),
    (ScheduleVersionNotWorking, 409, "Ta wersja grafiku nie jest już wersją roboczą."),
    (ReplanNotAvailableAfterAcceptance, 409, "Ten miesiąc ma już zaakceptowany grafik — użyj „Przelicz Plan” zamiast REPLAN."),
    (NonEditableScheduleVersion, 409, "Tej wersji grafiku nie można już edytować."),
    (CannotDeleteLiveScheduleVersion, 409, "Nie można usunąć wersji grafiku, która już obowiązuje."),
    (CannotRestoreLiveScheduleVersion, 409, "Nie można przywrócić wersji grafiku, która już obowiązuje."),
    (InvalidSitePrintSettings, 422, "Nieprawidłowe ustawienia wydruku dla tego obiektu."),
    (InvalidStandardShift, 400, "Nieprawidłowa definicja zmiany w katalogu zmian."),
    (CandidateRejected, 400, "Wybrany kandydat narusza twardą regułę planowania i nie może zostać zaakceptowany."),
    (
        HistoricalServiceMutationRejected, 409,
        "Ta służba już się rozpoczęła — jej danych nie można już zmienić. Można jedynie zapisać, "
        "kto faktycznie ją wykonał, podając powód.",
    ),
    (ValueError, 400, "Nieprawidłowe dane wejściowe."),
)


def public_http_exception(status_code: int, detail: str) -> HTTPException:
    """ROTA-T060: the ONLY function allowed to attach the public-error
    marker. `detail` must already be a fixed, coordinator-safe Polish
    sentence with no technical identifier -- never pass a raw exception's
    `str()`/`repr()` or any f-string built from one here."""
    return HTTPException(status_code=status_code, detail=detail, headers=dict(_PUBLIC_ERROR_HEADERS))


def to_http_exception(exc: Exception) -> HTTPException:
    for exc_type, status_code, detail in _STATUS_AND_DETAIL_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return public_http_exception(status_code, detail)
    # ARCHITECT_RULING R2 (brief 2.1.5): an unknown 500 may only ever carry
    # the public marker once its content has been replaced by this fixed,
    # safe, neutral text -- the raw exception is never forwarded.
    return public_http_exception(500, _UNEXPECTED_ERROR_DETAIL)
