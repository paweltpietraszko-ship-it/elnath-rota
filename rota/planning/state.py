from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rota.domain import (
    Assignment,
    AvailabilityRecord,
    CalendarDay,
    Deviation,
    Employee,
    ExternalSupportWindow,
    ShiftDemand,
    Site,
    SiteMembership,
    SiteProfile,
    SiteRuleVersion,
    WorkBalance,
)


@dataclass(frozen=True)
class PlanningState:
    # Tozsamosc kontekstu
    site: Site
    profile: SiteProfile
    month: date  # pierwszy dzien miesiaca

    # Kalendarz i granice
    calendar_days: tuple[CalendarDay, ...]
    boundary_assignments: tuple[Assignment, ...]
    # Assignments z konca poprzedniego miesiaca
    # potrzebne dla REST-01 i LOAD-01

    # Pracownicy
    memberships: tuple[SiteMembership, ...]
    employees: tuple[Employee, ...]
    external_windows: tuple[ExternalSupportWindow, ...]

    # Dostepnosc
    availability_records: tuple[AvailabilityRecord, ...]

    # Reguly -- STATE-01: dwa osobne zbiory
    site_rules: tuple[SiteRuleVersion, ...]
    # tylko RESOLVED -- executable przez PlanningEngine
    unresolved_site_rules: tuple[SiteRuleVersion, ...]
    # tylko NEEDS_RESOLUTION -- display only, nie executable

    # Kontekst biezacej ScheduleVersion
    shift_demands: tuple[ShiftDemand, ...]
    existing_assignments: tuple[Assignment, ...]
    deviations: tuple[Deviation, ...]

    # Bilans i historia
    work_balances: tuple[WorkBalance, ...]
    holiday_history: tuple[Assignment, ...]
    # historyczne REALIZED w CalendarDay(holiday=True)

    # Kontekst cross-site (REST-01 / LOAD-01)
    other_site_assignments: tuple[Assignment, ...]
    # Assignments tych samych Employee na innych Site
    # gdy dane dostepne; Assignment.schedule_version_id
    # nalezy do innego Site

    # Metadane
    schedule_version_id: str


if __name__ == "__main__":
    state = PlanningState(
        site=Site(site_id="s1", profile_id="OCHRONA", display_name="Site 1", active=True),
        profile=SiteProfile(
            profile_id="OCHRONA",
            display_name="Ochrona",
            active=True,
            standard_shifts=(),
            day_only_blocks_n=True,
            external_support_enabled=False,
            training_s_enabled=True,
            training_s_weekdays_only=True,
            training_s_default_readiness_threshold=2,
            rolling_7d_decision_threshold_hours=60,
        ),
        month=date(2026, 10, 1),
        calendar_days=(),
        boundary_assignments=(),
        memberships=(),
        employees=(),
        external_windows=(),
        availability_records=(),
        site_rules=(),
        unresolved_site_rules=(),
        shift_demands=(),
        existing_assignments=(),
        deviations=(),
        work_balances=(),
        holiday_history=(),
        other_site_assignments=(),
        schedule_version_id="v1",
    )
    print(state)
