"""Write the readiness report (Markdown) and the action log (CSV)."""

import csv
from collections import Counter
from pathlib import Path

from . import readiness
from .followups import draft_note, group_by_team

KIND_LABELS = {
    "coverage_gap": "Control without evidence request",
    "missing_owner": "Evidence request without owner",
    "overdue_request": "Evidence request overdue",
    "stale_evidence": "Evidence older than 12 months",
    "duplicate_request_id": "Duplicate request ID",
    "overdue_action": "Corrective action overdue",
    "high_finding_no_owner": "High finding without action owner",
}


def write_action_log(issues, path: Path):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["priority", "type", "reference", "control", "owner_team", "detail", "status"])
        for i in issues:
            w.writerow([i.priority, KIND_LABELS[i.kind], i.ref, i.control_id,
                        i.owner_team or "to be agreed", i.detail, "open"])


def write_markdown(reg, issues, as_of, path: Path):
    themes = readiness.by_theme(reg, as_of)
    counts = Counter(i.kind for i in issues)
    out = [
        f"# ISMS audit readiness report ({as_of.isoformat()})",
        "",
        f"Register: {len(reg.controls)} Annex A controls, {len(reg.requests)} evidence requests, "
        f"{len(reg.findings)} audit findings.",
        "",
        f"**Overall readiness: {readiness.overall(reg, as_of)}% of controls ready.**",
        "",
        "## Readiness by theme",
        "",
        "| Theme | Ready | Total | Share |",
        "|---|---|---|---|",
    ]
    for theme, ready, total in themes:
        out.append(f"| {theme} | {ready} | {total} | {round(100 * ready / total)}% |")
    out += ["", "## Open issues", "", "| Type | Count |", "|---|---|"]
    for kind, label in KIND_LABELS.items():
        out.append(f"| {label} | {counts.get(kind, 0)} |")
    out += ["", "## Priority 1 items", ""]
    for i in issues:
        if i.priority == 1:
            out.append(f"- [{i.control_id}] {i.detail} (owner: {i.owner_team or 'to be agreed'})")
    out += ["", "## Follow-up notes by team", ""]
    for team, items in group_by_team(issues).items():
        out += [f"### {team} ({len(items)} items)", "", "```text", draft_note(team, items), "```", ""]
    path.write_text("\n".join(out), encoding="utf-8")
