"""Wraps rota.application.bootstrap for Screen 1 (Workspace/Przedpokoj).
Marshalling only -- no business logic. The per-site enrichment loop
composes bootstrap/site_memory/site_repository reads exactly as
T021_spec.md describes ("one call per site for the filter chips"); it
does not reimplement any of those functions' own logic.
"""
from __future__ import annotations

import uuid
from dataclasses import replace

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.errors import to_http_exception
from rota.application import bootstrap
from rota.application.durable_inputs import update_site
from rota.domain import Coordinator, CoordinatorSiteAssociation, Site, SitePlanningRegime, SiteProfile
from rota.persistence import site_memory
from rota.persistence.site_repository import get_site, get_site_print_settings

router = APIRouter(prefix="/workspace", tags=["workspace"])


class SiteSummary(BaseModel):
    site_id: str
    display_name: str
    planning_regime: str
    complete: bool
    missing: list[str]
    decision_required_months: list[str]
    print_settings_missing: bool
    active: bool


class CreateSiteRequest(BaseModel):
    display_name: str
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
        active=site.active,
    )


@router.get("/sites", response_model=list[SiteSummary])
def list_sites(include_inactive: bool = False, conn=Depends(get_conn)) -> list[SiteSummary]:
    # 2026-08-26 owner decision: a coordinator can remove a Site from the
    # Workspace (Site.active=False, already-existing durable_inputs.update_site
    # semantics) without deleting anything -- schedule history, employees,
    # memberships stay fully intact and queryable, only this listing hides it
    # by default. include_inactive=True is the "show removed" view, needed to
    # find something again to reactivate.
    sites = (
        bootstrap.all_sites_for_coordinator(conn, coordinator_id=DEV_COORDINATOR_ID) if include_inactive
        else bootstrap.active_sites_for_coordinator(conn, coordinator_id=DEV_COORDINATOR_ID)
    )
    try:
        return [_site_summary(conn, site) for site in sites]
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/sites/{site_id}/deactivate", status_code=204)
def deactivate_site(site_id: str, conn=Depends(get_conn)) -> None:
    """Hide a Site from the Workspace -- Site.active=False via the existing
    update_site() write path. Never touches schedule/employee/membership
    history; see rota.application.durable_inputs.update_site's own docstring
    for why this is a plain upsert, not a versioned operation."""
    try:
        current = get_site(conn, site_id)
        update_site(conn, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id, site=replace(current, active=False))
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/sites/{site_id}/reactivate", status_code=204)
def reactivate_site(site_id: str, conn=Depends(get_conn)) -> None:
    """Bring a removed Site back into the Workspace. update_site() cannot do
    this itself -- its own require_active_coordinator_context guard demands
    the Site already be active (tasks/ROTA-T011-C/brief.md 2026-08-14
    RESOLUTION: "PEŁNA ODWRACALNOŚĆ DLA WSZYSTKICH TRZECH ENCJI"): the
    reversal path for exactly this lockout shape is
    bootstrap_or_resume_coordinator_context, which only requires the context
    NOT already be fully active."""
    try:
        current = get_site(conn, site_id)
        bootstrap.bootstrap_or_resume_coordinator_context(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id, site=replace(current, active=True),
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/sites", response_model=CreateSiteResponse, status_code=201)
def create_site(payload: CreateSiteRequest, conn=Depends(get_conn)) -> CreateSiteResponse:
    """ROTA-T049: two UI inputs plus the chosen regime -- SiteProfile.display_name
    is no longer a coordinator input (it has no reader anywhere in the product),
    it is derived from the Site's own display_name instead. Every other field
    is generated or a fixed constant. Same handler for both OCHRONA and
    ORDINARY entry points -- the frontend supplies which."""
    try:
        regime = SitePlanningRegime(payload.planning_regime)
    except ValueError as exc:
        raise to_http_exception(exc) from exc

    site_id = f"SITE-{uuid.uuid4().hex}"
    profile_id = f"PROF-{uuid.uuid4().hex}"

    site_profile = SiteProfile(
        profile_id=profile_id,
        display_name=payload.display_name,
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
    # ROTA-T028: the association below is FK-constrained to an existing
    # coordinators row, but nothing else in this app ever creates one --
    # a fresh/reset database has none. write_coordinator_in_open_transaction
    # is an idempotent UPSERT, so passing this on every call is safe.
    coordinator = Coordinator(coordinator_id=DEV_COORDINATOR_ID, display_name="Koordynator", active=True)

    try:
        bootstrap.bootstrap_or_resume_coordinator_context(
            conn, coordinator_id=DEV_COORDINATOR_ID, site_id=site_id,
            coordinator=coordinator, site_profile=site_profile, site=site, association=association,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc

    return CreateSiteResponse(site_id=site_id, profile_id=profile_id)
