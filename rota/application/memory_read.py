"""Operation 11 (tasks/ROTA-T009/brief.md): simple application reads over
the SiteMemory already stored by T005 -- not a new audit subsystem.
"""
from __future__ import annotations

from datetime import date

from rota.persistence.site_memory import decision_for_rule_version, rule_history, rule_provenance
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.persistence.site_rule_repository import list_rule_ids_for_site


def effective_rules_for_month(conn, *, site_id: str, month: date):
    """Returns (resolved, unresolved, applicability) exactly as
    assembled for a PlanningState -- the same source of truth."""
    return assemble_monthly_site_rules(conn, site_id, month)


def rules_history_for_site(conn, *, site_id: str):
    return {rule_id: rule_history(conn, site_id, rule_id) for rule_id in list_rule_ids_for_site(conn, site_id)}


def decision_chain_for_rule_family(conn, *, site_id: str, rule_id: str):
    return rule_history(conn, site_id, rule_id)


def provenance_for_rule_version(conn, *, rule_version_id: str):
    return rule_provenance(conn, rule_version_id)


def decision_for_rule(conn, *, rule_version_id: str):
    return decision_for_rule_version(conn, rule_version_id)
