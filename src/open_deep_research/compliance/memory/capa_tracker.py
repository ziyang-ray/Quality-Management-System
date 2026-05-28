"""CAPA (Corrective and Preventive Action) lifecycle tracker."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class CAPAStatus(str, Enum):
    """CAPA lifecycle status."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    OVERDUE = "OVERDUE"


class CAPAPriority(str, Enum):
    """CAPA priority level."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Finding:
    """A compliance finding that may require CAPA."""

    finding_id: str
    clause_id: str
    standard: str
    status: str  # 需澄清, 缺乏证据, 未提及
    rationale: str
    evidence_files: list[str] = field(default_factory=list)
    risk: str = ""
    recommendation: str = ""
    detected_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Finding:
        return cls(**data)


@dataclass
class EffectivenessCheck:
    """Effectiveness check record."""

    check_id: str
    check_date: str
    checker: str
    method: str
    result: str  # effective, ineffective, partially_effective
    evidence: str
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> EffectivenessCheck:
        return cls(**data)


@dataclass
class CAPA:
    """A CAPA record with full lifecycle tracking."""

    capa_id: str
    source_finding: Finding
    root_cause: str = ""
    corrective_action: str = ""
    preventive_action: str = ""
    responsible_person: str = ""
    due_date: str = ""
    status: CAPAStatus = CAPAStatus.OPEN
    priority: CAPAPriority = CAPAPriority.MEDIUM
    created_date: str = ""
    updated_date: str = ""
    effectiveness_check: Optional[EffectivenessCheck] = None
    closure_notes: str = ""
    closure_date: str = ""
    closure_approved_by: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> CAPA:
        data["status"] = CAPAStatus(data["status"])
        data["priority"] = CAPAPriority(data["priority"])
        if data.get("effectiveness_check"):
            data["effectiveness_check"] = EffectivenessCheck.from_dict(
                data["effectiveness_check"]
            )
        if data.get("source_finding"):
            data["source_finding"] = Finding.from_dict(data["source_finding"])
        return cls(**data)

    def is_overdue(self) -> bool:
        """Check if CAPA is overdue."""
        if self.status in (CAPAStatus.CLOSED, CAPAStatus.VERIFIED):
            return False
        if not self.due_date:
            return False
        return datetime.now() > datetime.fromisoformat(self.due_date)

    def get_age_days(self) -> int:
        """Get CAPA age in days."""
        if not self.created_date:
            return 0
        created = datetime.fromisoformat(self.created_date)
        return (datetime.now() - created).days

    def add_note(self, note: str):
        """Add a note to CAPA."""
        timestamp = datetime.now().isoformat()
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_date = timestamp


class CAPATracker:
    """CAPA lifecycle tracker."""

    def __init__(self, storage_path: str | Path = "data/memory/capa_tracker.json"):
        self.storage_path = Path(storage_path)
        self.capas: dict[str, CAPA] = {}
        self._next_id = 1
        self._load()

    def _load(self):
        """Load CAPAs from storage."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, encoding="utf-8") as f:
                data = json.load(f)

            self._next_id = data.get("next_id", 1)
            for capa_id, capa_data in data.get("capas", {}).items():
                self.capas[capa_id] = CAPA.from_dict(capa_data)

        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self):
        """Save CAPAs to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "next_id": self._next_id,
            "capas": {
                capa_id: capa.to_dict()
                for capa_id, capa in self.capas.items()
            },
        }

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_id(self) -> str:
        """Generate a new CAPA ID."""
        capa_id = f"CAPA-{self._next_id:04d}"
        self._next_id += 1
        return capa_id

    def create_capa(self, finding: Finding,
                   responsible_person: str = "",
                   priority: CAPAPriority = CAPAPriority.MEDIUM,
                   due_days: int = 30) -> CAPA:
        """Create a new CAPA from a finding."""
        capa_id = self._generate_id()
        now = datetime.now()

        capa = CAPA(
            capa_id=capa_id,
            source_finding=finding,
            responsible_person=responsible_person,
            due_date=(now + timedelta(days=due_days)).isoformat(),
            status=CAPAStatus.OPEN,
            priority=priority,
            created_date=now.isoformat(),
            updated_date=now.isoformat(),
        )

        self.capas[capa_id] = capa
        self._save()
        return capa

    def get_capa(self, capa_id: str) -> Optional[CAPA]:
        """Get a CAPA by ID."""
        return self.capas.get(capa_id)

    def update_status(self, capa_id: str, new_status: CAPAStatus,
                     notes: str = "") -> bool:
        """Update CAPA status."""
        capa = self.get_capa(capa_id)
        if not capa:
            return False

        old_status = capa.status
        capa.status = new_status
        capa.updated_date = datetime.now().isoformat()

        if notes:
            capa.add_note(f"Status changed: {old_status.value} -> {new_status.value}. {notes}")

        self._save()
        return True

    def update_root_cause(self, capa_id: str, root_cause: str) -> bool:
        """Update CAPA root cause."""
        capa = self.get_capa(capa_id)
        if not capa:
            return False

        capa.root_cause = root_cause
        capa.updated_date = datetime.now().isoformat()
        capa.add_note(f"Root cause updated: {root_cause[:100]}...")

        self._save()
        return True

    def update_actions(self, capa_id: str,
                      corrective_action: str = "",
                      preventive_action: str = "") -> bool:
        """Update CAPA actions."""
        capa = self.get_capa(capa_id)
        if not capa:
            return False

        if corrective_action:
            capa.corrective_action = corrective_action
        if preventive_action:
            capa.preventive_action = preventive_action

        capa.updated_date = datetime.now().isoformat()
        capa.add_note("Actions updated")

        self._save()
        return True

    def add_effectiveness_check(self, capa_id: str,
                               checker: str,
                               method: str,
                               result: str,
                               evidence: str,
                               notes: str = "") -> bool:
        """Add effectiveness check to CAPA."""
        capa = self.get_capa(capa_id)
        if not capa:
            return False

        check_id = f"EC-{capa_id}-{len(capa.notes) + 1:03d}"
        now = datetime.now()

        effectiveness_check = EffectivenessCheck(
            check_id=check_id,
            check_date=now.isoformat(),
            checker=checker,
            method=method,
            result=result,
            evidence=evidence,
            notes=notes,
        )

        capa.effectiveness_check = effectiveness_check
        capa.updated_date = now.isoformat()
        capa.add_note(f"Effectiveness check added: {result}")

        if result == "effective":
            self.update_status(capa_id, CAPAStatus.VERIFIED,
                             "Effectiveness verified")

        self._save()
        return True

    def close_capa(self, capa_id: str,
                  closure_notes: str,
                  approved_by: str) -> bool:
        """Close a CAPA."""
        capa = self.get_capa(capa_id)
        if not capa:
            return False

        now = datetime.now()
        capa.status = CAPAStatus.CLOSED
        capa.closure_notes = closure_notes
        capa.closure_date = now.isoformat()
        capa.closure_approved_by = approved_by
        capa.updated_date = now.isoformat()
        capa.add_note(f"CAPA closed by {approved_by}")

        self._save()
        return True

    def get_open_capas(self) -> list[CAPA]:
        """Get all open CAPAs."""
        return [
            capa for capa in self.capas.values()
            if capa.status in (CAPAStatus.OPEN, CAPAStatus.IN_PROGRESS)
        ]

    def get_overdue_capas(self) -> list[CAPA]:
        """Get overdue CAPAs."""
        return [
            capa for capa in self.capas.values()
            if capa.is_overdue()
        ]

    def get_capas_by_clause(self, clause_id: str) -> list[CAPA]:
        """Get CAPAs for a specific clause."""
        return [
            capa for capa in self.capas.values()
            if capa.source_finding.clause_id == clause_id
        ]

    def get_capas_by_status(self, status: CAPAStatus) -> list[CAPA]:
        """Get CAPAs by status."""
        return [
            capa for capa in self.capas.values()
            if capa.status == status
        ]

    def get_statistics(self) -> dict:
        """Get CAPA statistics."""
        total = len(self.capas)
        by_status = {}
        for status in CAPAStatus:
            by_status[status.value] = len(self.get_capas_by_status(status))

        overdue = len(self.get_overdue_capas())
        avg_age = 0
        if total > 0:
            avg_age = sum(c.get_age_days() for c in self.capas.values()) / total

        return {
            "total": total,
            "by_status": by_status,
            "overdue": overdue,
            "average_age_days": round(avg_age, 1),
        }

    def generate_report(self) -> str:
        """Generate CAPA tracking report."""
        stats = self.get_statistics()
        lines = ["# CAPA跟踪报告", ""]
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Statistics
        lines.append("## 统计概览")
        lines.append(f"- 总CAPA数：{stats['total']}")
        lines.append(f"- 超期CAPA数：{stats['overdue']}")
        lines.append(f"- 平均年龄：{stats['average_age_days']}天")
        lines.append("")

        lines.append("### 状态分布")
        for status, count in stats['by_status'].items():
            lines.append(f"- {status}: {count}")
        lines.append("")

        # Overdue CAPAs
        overdue = self.get_overdue_capas()
        if overdue:
            lines.append("## 超期CAPA")
            lines.append("| CAPA ID | 条款 | 负责人 | 到期日 | 年龄(天) |")
            lines.append("|---------|------|--------|--------|----------|")
            for capa in overdue:
                lines.append(
                    f"| {capa.capa_id} | {capa.source_finding.clause_id} | "
                    f"{capa.responsible_person} | {capa.due_date[:10]} | "
                    f"{capa.get_age_days()} |"
                )
            lines.append("")

        # Open CAPAs
        open_capas = self.get_open_capas()
        if open_capas:
            lines.append("## 进行中的CAPA")
            lines.append("| CAPA ID | 条款 | 状态 | 负责人 | 到期日 |")
            lines.append("|---------|------|------|--------|--------|")
            for capa in open_capas:
                lines.append(
                    f"| {capa.capa_id} | {capa.source_finding.clause_id} | "
                    f"{capa.status.value} | {capa.responsible_person} | "
                    f"{capa.due_date[:10]} |"
                )
            lines.append("")

        return "\n".join(lines)
