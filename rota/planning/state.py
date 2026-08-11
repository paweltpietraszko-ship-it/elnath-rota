from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rota.domain import (
    Assignment,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    ExternalSupportWindow,
    Site,
    SiteMembership,
    SiteProfile,
    SiteRuleVersion,
    WorkBalance,
)


@dataclass
class PlanningState:
    # Tozsamosc kontekstu
    site: Site
    profile: SiteProfile
    month: date  # pierwszy dzien miesiaca

    # Kalendarz i granice
    calendar_days: list[CalendarDay]
    boundary_assignments: list[Assignment]
    # Assignments konczace sie w ostatnich dniach
    # poprzedniego miesiaca -- potrzebne dla REST-01
    # i LOAD-01 na granicy miesiaca

    # Pracownicy
    memberships: list[SiteMembership]
    employees: list[Employee]
    external_windows: list[ExternalSupportWindow]

    # Dostepnosc i reguly
    availability_records: list[AvailabilityRecord]
    site_rules: list[SiteRuleVersion]
    # tylko RESOLVED -- STATE-01

    # Kontekst planowania
    existing_assignments: list[Assignment]
    # biezaca ScheduleVersion -- PLANNED/REALIZED
    work_balances: list[WorkBalance]
    holiday_history: list[Assignment]
    # historyczne REALIZED Assignments w dni
    # CalendarDay(holiday=True) -- do holiday fairness

    # Metadane
    schedule_version_id: str


if __name__ == "__main__":
    state = PlanningState(
        site=Site(site_id="s1", profile_id="OCHRONA", display_name="Site 1", active=True),
        profile=SiteProfile(
            profile_id="OCHRONA",
            display_name="Ochrona",
            active=True,
            standard_shifts=[],
            day_only_blocks_n=True,
            external_support_enabled=False,
            training_s_enabled=True,
            training_s_weekdays_only=True,
            training_s_default_readiness_threshold=2,
            rolling_7d_decision_threshold_hours=60,
        ),
        month=date(2026, 10, 1),
        calendar_days=[],
        boundary_assignments=[],
        memberships=[],
        employees=[],
        external_windows=[],
        availability_records=[],
        site_rules=[],
        existing_assignments=[],
        work_balances=[],
        holiday_history=[],
        schedule_version_id="v1",
    )
    print(state)
