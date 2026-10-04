"""Audit readiness per Annex A theme.

A control counts as ready when it has at least one accepted piece of evidence
reviewed within the last 12 months and no open high-severity finding.
"""

from collections import defaultdict
from datetime import date, timedelta

from .checks import OPEN_STATES, STALE_AFTER_DAYS


def control_status(reg, as_of: date):
    limit = as_of - timedelta(days=STALE_AFTER_DAYS)
    current = {
        r.control_id for r in reg.requests
        if r.status == "accepted" and r.last_reviewed and r.last_reviewed >= limit
    }
    blocked = {
        f.control_id for f in reg.findings
        if f.severity == "high" and f.status in OPEN_STATES
    }
    status = {}
    for c in reg.controls:
        if c.control_id in blocked:
            status[c.control_id] = "blocked by open high finding"
        elif c.control_id in current:
            status[c.control_id] = "ready"
        else:
            status[c.control_id] = "evidence missing or outdated"
    return status


def by_theme(reg, as_of: date):
    status = control_status(reg, as_of)
    totals = defaultdict(lambda: [0, 0])  # theme -> [ready, total]
    for c in reg.controls:
        totals[c.theme][1] += 1
        if status[c.control_id] == "ready":
            totals[c.theme][0] += 1
    order = ["Organizational", "People", "Physical", "Technological"]
    return [(t, *totals[t]) for t in order if t in totals]


def overall(reg, as_of: date) -> float:
    rows = by_theme(reg, as_of)
    ready = sum(r for _, r, _ in rows)
    total = sum(t for _, _, t in rows)
    return round(100 * ready / total, 1) if total else 0.0
