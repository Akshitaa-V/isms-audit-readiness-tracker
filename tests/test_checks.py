import json
import random
from datetime import date
from pathlib import Path

import pytest

import generate_sample_data as gen
from audit_tracker import checks, readiness
from audit_tracker.followups import UNASSIGNED, draft_note, group_by_team
from audit_tracker.register import load
from audit_tracker.report import write_action_log, write_markdown

AS_OF = gen.AS_OF


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    folder = tmp_path_factory.mktemp("data")
    controls, requests, findings, injected = gen.build(random.Random(gen.SEED))
    gen.write_csv(folder / "controls.csv", controls)
    gen.write_csv(folder / "evidence_requests.csv", requests)
    gen.write_csv(folder / "findings.csv", findings)
    (folder / "injected_issues.json").write_text(json.dumps(injected))
    return folder


@pytest.fixture(scope="module")
def reg(data_dir):
    return load(data_dir)


@pytest.fixture(scope="module")
def injected(data_dir):
    return json.loads((data_dir / "injected_issues.json").read_text())


@pytest.fixture(scope="module")
def issues(reg):
    return checks.run_all(reg, AS_OF)


@pytest.mark.parametrize("kind", [
    "coverage_gap", "missing_owner", "overdue_request", "stale_evidence",
    "duplicate_request_id", "overdue_action", "high_finding_no_owner",
])
def test_every_planted_issue_is_found_and_nothing_else(issues, injected, kind):
    found = sorted(i.ref for i in issues if i.kind == kind)
    assert found == injected[kind]


def test_register_size(reg):
    assert len(reg.controls) == 32
    assert {c.theme for c in reg.controls} == {"Organizational", "People", "Physical", "Technological"}


def test_accepted_evidence_is_never_overdue(reg):
    overdue = {i.ref for i in checks.overdue_requests(reg, AS_OF)}
    assert not any(r.request_id in overdue and r.status == "accepted" for r in reg.requests)


def test_stale_boundary(reg):
    # Exactly 365 days old is still current; 366 days is stale.
    r = reg.requests[0]
    original = (r.status, r.last_reviewed)
    try:
        r.status = "accepted"
        r.last_reviewed = date(2025, 10, 1)
        assert not any(i.ref == r.request_id for i in checks.stale_evidence(reg, AS_OF))
        r.last_reviewed = date(2025, 9, 30)
        assert any(i.ref == r.request_id for i in checks.stale_evidence(reg, AS_OF))
    finally:
        r.status, r.last_reviewed = original


def test_priority_order(issues):
    assert [i.priority for i in issues] == sorted(i.priority for i in issues)


def test_readiness_is_consistent(reg):
    status = readiness.control_status(reg, AS_OF)
    rows = readiness.by_theme(reg, AS_OF)
    assert sum(t for _, _, t in rows) == 32
    assert sum(r for _, r, _ in rows) == sum(1 for s in status.values() if s == "ready")
    assert 0 <= readiness.overall(reg, AS_OF) <= 100


def test_gap_controls_are_not_ready(reg, injected):
    status = readiness.control_status(reg, AS_OF)
    for cid in injected["coverage_gap"]:
        assert status[cid] != "ready"


def test_unowned_items_go_to_coordinator_first(issues):
    teams = list(group_by_team(issues))
    assert teams[0] == UNASSIGNED


def test_follow_up_note_lists_every_item(issues):
    for team, items in group_by_team(issues).items():
        note = draft_note(team, items)
        assert note.startswith("Hello ") and note.splitlines()[0].endswith(" team,")
        assert sum(1 for line in note.splitlines() if line.startswith("- [")) == len(items)


def test_reports_are_written(reg, issues, tmp_path):
    write_markdown(reg, issues, AS_OF, tmp_path / "r.md")
    write_action_log(issues, tmp_path / "a.csv")
    assert "Overall readiness" in (tmp_path / "r.md").read_text()
    assert len((tmp_path / "a.csv").read_text().splitlines()) == len(issues) + 1


def test_generator_is_reproducible():
    a = gen.build(random.Random(gen.SEED))
    b = gen.build(random.Random(gen.SEED))
    assert a == b
