"""
UK Admin — Canonical Schemas

Canonical data structures for UK government administrative tasks.
All UK Admin data flows through these schemas for consistency.

Usage:
    from datagarden.shared.uk_admin_schema import UKAdminTask, UKAdminService, UKAdminAction
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class UKAdminTask:
    """A UK government administrative task a citizen needs to complete."""
    task_id: str
    task_name: str
    category: str          # driving, tax, business, home, benefits, passport, vehicle
    subcategory: str       # licence, mot, self_assessment, etc
    authority: str         # DVLA, HMRC, DVSA, Home Office, etc
    jurisdiction: str      # GB, England, Scotland, Wales, NI
    url: str               # official GOV.UK URL
    cost_gbp: float = 0.0
    takes_time: str = ''   # e.g. '3 weeks', '24 hours'
    requires: List[str] = field(default_factory=list)
    agent_permissions: Dict[str, object] = field(default_factory=dict)
    failure_modes: List[str] = field(default_factory=list)
    official_source: str = ''
    last_verified: str = ''
    is_recurring: bool = False
    recurrence: str = ''
    related_tasks: List[str] = field(default_factory=list)
    commercial_needs: List[str] = field(default_factory=list)
    source: str = 'govuk'
    observed_at: str = ''

    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'category': self.category,
            'subcategory': self.subcategory,
            'authority': self.authority,
            'jurisdiction': self.jurisdiction,
            'url': self.url,
            'cost_gbp': self.cost_gbp,
            'takes_time': self.takes_time,
            'requires': self.requires,
            'agent_permissions': self.agent_permissions,
            'failure_modes': self.failure_modes,
            'official_source': self.official_source,
            'last_verified': self.last_verified,
            'is_recurring': self.is_recurring,
            'recurrence': self.recurrence,
            'related_tasks': self.related_tasks,
            'commercial_needs': self.commercial_needs,
            'source': self.source,
            'observed_at': self.observed_at,
        }


@dataclass
class UKAdminService:
    """A GOV.UK service (online transaction or guidance)."""
    service_id: str
    service_name: str
    organisation: str
    url: str
    transaction_url: str = ''
    done_url: str = ''
    cost_gbp: float = 0.0
    auth_required: bool = False
    one_login: bool = False
    agent_accessible: bool = False
    source: str = 'govuk'
    observed_at: str = ''

    def to_dict(self) -> dict:
        return {
            'service_id': self.service_id,
            'service_name': self.service_name,
            'organisation': self.organisation,
            'url': self.url,
            'transaction_url': self.transaction_url,
            'done_url': self.done_url,
            'cost_gbp': self.cost_gbp,
            'auth_required': self.auth_required,
            'one_login': self.one_login,
            'agent_accessible': self.agent_accessible,
            'source': self.source,
            'observed_at': self.observed_at,
        }


@dataclass
class UKAdminAction:
    """A single action within a UK Admin task (the steps an agent or human takes)."""
    action_id: str
    task_id: str
    action_type: str       # explain, gather, prefill, submit, payment, confirm
    agent_can: bool = False
    user_must: bool = False
    requires_auth: bool = False
    description: str = ''
    source: str = ''
    observed_at: str = ''

    def to_dict(self) -> dict:
        return {
            'action_id': self.action_id,
            'task_id': self.task_id,
            'action_type': self.action_type,
            'agent_can': self.agent_can,
            'user_must': self.user_must,
            'requires_auth': self.requires_auth,
            'description': self.description,
            'source': self.source,
            'observed_at': self.observed_at,
        }
