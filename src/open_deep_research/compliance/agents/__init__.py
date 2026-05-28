"""Multi-agent system for compliance audit simulation."""

from open_deep_research.compliance.agents.roles import (
    AuditRole,
    AgentProfile,
    AUDIT_PROFILES,
)
from open_deep_research.compliance.agents.lead_auditor import LeadAuditorAgent
from open_deep_research.compliance.agents.department_rep import DepartmentRepAgent
from open_deep_research.compliance.agents.orchestrator import AuditOrchestrator

__all__ = [
    "AuditRole",
    "AgentProfile",
    "AUDIT_PROFILES",
    "LeadAuditorAgent",
    "DepartmentRepAgent",
    "AuditOrchestrator",
]
