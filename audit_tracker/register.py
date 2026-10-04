"""Load the audit register (controls, evidence requests, findings) from CSV."""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional


def _date(value: str) -> Optional[date]:
    value = (value or "").strip()
    return date.fromisoformat(value) if value else None


@dataclass
class Control:
    control_id: str
    theme: str
    description: str
    nist_csf_function: str
    owner_team: str


@dataclass
class EvidenceRequest:
    request_id: str
    control_id: str
    evidence: str
    owner_team: str
    requested_on: Optional[date]
    due: Optional[date]
    status: str
    last_reviewed: Optional[date]


@dataclass
class Finding:
    finding_id: str
    control_id: str
    severity: str
    raised_on: Optional[date]
    action: str
    action_owner: str
    due: Optional[date]
    status: str


@dataclass
class Register:
    controls: list
    requests: list
    findings: list


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load(folder) -> Register:
    folder = Path(folder)
    controls = [Control(**r) for r in _rows(folder / "controls.csv")]
    requests = [
        EvidenceRequest(
            request_id=r["request_id"].strip(),
            control_id=r["control_id"].strip(),
            evidence=r["evidence"],
            owner_team=r["owner_team"].strip(),
            requested_on=_date(r["requested_on"]),
            due=_date(r["due"]),
            status=r["status"].strip().lower(),
            last_reviewed=_date(r["last_reviewed"]),
        )
        for r in _rows(folder / "evidence_requests.csv")
    ]
    findings = [
        Finding(
            finding_id=r["finding_id"].strip(),
            control_id=r["control_id"].strip(),
            severity=r["severity"].strip().lower(),
            raised_on=_date(r["raised_on"]),
            action=r["action"],
            action_owner=r["action_owner"].strip(),
            due=_date(r["due"]),
            status=r["status"].strip().lower(),
        )
        for r in _rows(folder / "findings.csv")
    ]
    return Register(controls, requests, findings)
