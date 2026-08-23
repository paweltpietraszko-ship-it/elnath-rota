"""Wraps rota.application.bootstrap for Screen 1 (Workspace/Przedpokoj).
Marshalling only -- no business logic. The per-site enrichment loop
composes bootstrap/site_memory/site_repository reads exactly as
T021_spec.md describes ("one call per site for the filter chips"); it
does not reimplement any of those functions' own logic.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application import bootstrap
from rota.domain import CoordinatorSiteAssociation, Site, SitePlanningRegime, SiteProfile
from rota.persistence import site_memory
from rota.persistence.site_repository import get_site_print_settings

router = APIRouter(prefix="/workspace", tags=["workspace"])


class SiteSummary(BaseModel):
    site_id: str
    display_name: str
    planning_regime: str
    complete: bool
    missing: list[str]
    decision_required_months: list[str]
    print_settings_missing: bool


class CreateSiteRequest(BaseModel):
    display_name: str
    profile_display_name: str
    rolling_7d_decision_threshold_hours: int
    planning_regime: str  # "OCHRONA" | "ORDINARY"


class CreateSiteResponse(BaseModel):
    site_id: str
    profile_id: str


def _site_summary(conn, site) -> SiteSummary:
    completeness = bootstrap.coordinator_context_completeness(
        conn, coordinator_id=DEV_COORDINATOR_ID, site_id=site.site_id,
    )
    months = site_memory.current_decision_required_months_for_site(conn, site_id=site.site_id)
    print_settings = get_site_print_settings(conn, site.site_id)
    return SiteSummary(
        site_id=site.site_id,
        display_name=site.display_name,
        planning_regime=site.planning_regime.value,
        complete=completeness.complete,
        missing=list(completeness.missing),
        decision_required_months=[m.isoformat() for m in months],
        print_settings_missing=print_settings is None,
    )


@router.get("/sites", response_model=list[SiteSummary])
def list_sites(conn=Depends(get_conn)) -> list[SiteSummary]:
    sites = bootstrap.active_sites_for_coordinator(conn, coordinator_id=DEV_COORDINATOR_ID)
    return [_site_summary(conn, site) for site in sites]


@router.post("/sites", response_model=CreateSiteResponse, status_code=201)
def create_site(payload: CreateSiteRequest, conn=Depends(get_conn)) -> CreateSiteResponse:
    """brief.md section 4 Writes (round-2 A3 mapping): three UI inputs
    plus the chosen regime; every other field is generated or a fixed
    D2 constant. Same handler for both OCHRONA and ORDINARY entry
    points -- the frontend supplies which."""
    try:
        regime = SitePlanningRegime(payload.planning_regime)
    except ValueError as exc:
        raise to_http_exception(exc) from exc

    site_id = f"SITE-{uuid.uuid4().hex}"
    profile_id = f"PROF-{uuid.uuid4().hex}"

    site_profile = SiteProfile(
        profile_id=profile_id,
        display_name=payload.profile_display_name,
        active=True,
        standard_shifts=[],
        day_only_blocks_n=True,
        external_support_enabled=True,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=payload.rolling_7d_decision_threshold_hours,
    )
    site = Site(
        site_id=site_id, profile_id=profile_id, display_name=payload.display_name,
        active=True, planning_regime=regime,
    )
    association = CoordinatorSiteAssociation(
        coordinator_id=DEV_COORDINATOR_ID, site_id=site_id, active=True,
    )

    try:
        bootstrap.bootstrap_or_resume_coordinator_context(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id,
            coordinator=None, site_profile=site_profile, site=site, association=association,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc

    return CreateSiteResponse(site_id=site_id, profile_id=profile_id)
