"""Readiness checks on the audit register.

Each check returns Issue objects. A check only looks at one kind of problem,
so a single row can raise more than one issue (for example, an overdue request
that also has no owner).
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

STALE_AFTER_DAYS = 365
OPEN_STATES = {"open", "in progress"}


@dataclass(frozen=True)
class Issue:
    kind: str
    ref: str          # request id, finding id or control id
    control_id: str
    owner_team: str
    detail: str
    priority: int     # 1 = fix first


def coverage_gaps(reg):
    covered = {r.control_id for r in reg.requests}
    return [
        Issue("coverage_gap", c.control_id, c.control_id, c.owner_team,
              f"No evidence requested for control {c.control_id} ({c.description})", 1)
        for c in reg.controls if c.control_id not in covered
    ]


def missing_owner(reg):
    return [
        Issue("missing_owner", r.request_id, r.control_id, "",
              f"{r.request_id} has no responsible team", 2)
        for r in reg.requests if not r.owner_team
    ]


def overdue_requests(reg, as_of: date):
    out = []
    for r in reg.requests:
        if r.status != "accepted" and r.due and r.due < as_of:
            days = (as_of - r.due).days
            out.append(Issue("overdue_request", r.request_id, r.control_id, r.owner_team,
                             f"{r.request_id} ({r.evidence}) is {days} days past due, status '{r.status}'",
                             1 if days > 30 else 2))
    return out


def stale_evidence(reg, as_of: date):
    limit = as_of - timedelta(days=STALE_AFTER_DAYS)
    return [
        Issue("stale_evidence", r.request_id, r.control_id, r.owner_team,
              f"{r.request_id} was last reviewed on {r.last_reviewed}, more than 12 months ago", 2)
        for r in reg.requests
        if r.status == "accepted" and r.last_reviewed and r.last_reviewed < limit
    ]


def duplicate_ids(reg):
    counts = Counter(r.request_id for r in reg.requests)
    seen = set()
    out = []
    for r in reg.requests:
        if counts[r.request_id] > 1 and r.request_id not in seen:
            seen.add(r.request_id)
            out.append(Issue("duplicate_request_id", r.request_id, r.control_id, r.owner_team,
                             f"{r.request_id} appears {counts[r.request_id]} times in the register", 3))
    return out


def overdue_actions(reg, as_of: date):
    return [
        Issue("overdue_action", f.finding_id, f.control_id, f.action_owner,
              f"Corrective action for {f.finding_id} ({f.severity}) was due on {f.due}", 1)
        for f in reg.findings
        if f.status in OPEN_STATES and f.due and f.due < as_of
    ]


def high_findings_without_owner(reg):
    return [
        Issue("high_finding_no_owner", f.finding_id, f.control_id, "",
              f"High-severity finding {f.finding_id} has no action owner", 1)
        for f in reg.findings
        if f.severity == "high" and f.status in OPEN_STATES and not f.action_owner
    ]


def run_all(reg, as_of: date):
    issues = (coverage_gaps(reg) + missing_owner(reg) + overdue_requests(reg, as_of)
              + stale_evidence(reg, as_of) + duplicate_ids(reg)
              + overdue_actions(reg, as_of) + high_findings_without_owner(reg))
    return sorted(issues, key=lambda i: (i.priority, i.kind, i.ref))
