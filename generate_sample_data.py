"""Generate a synthetic ISMS audit register for demos and tests.

The register covers 32 ISO/IEC 27001:2022 Annex A controls. Control names are
short descriptions in my own words, not the text of the standard. The NIST CSF
2.0 function next to each control is an indicative mapping for orientation,
not an official crosswalk.

Known problems are planted on purpose and listed in data/injected_issues.json,
so the tests can check that every planted problem is found and that clean rows
are left alone.
"""

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

AS_OF = date(2026, 10, 1)
SEED = 27001
DATA = Path(__file__).parent / "data"

# (control id, theme, short description, indicative NIST CSF 2.0 function, owner team)
CONTROLS = [
    ("5.1", "Organizational", "Security policy set approved and published", "Govern", "Security"),
    ("5.2", "Organizational", "Security roles and responsibilities defined", "Govern", "Security"),
    ("5.9", "Organizational", "Asset inventory kept up to date", "Identify", "IT Operations"),
    ("5.12", "Organizational", "Information classified by sensitivity", "Identify", "Security"),
    ("5.15", "Organizational", "Access control rules defined", "Protect", "IT Operations"),
    ("5.17", "Organizational", "Authentication secrets managed", "Protect", "IT Operations"),
    ("5.18", "Organizational", "Access rights granted, reviewed and removed", "Protect", "IT Operations"),
    ("5.19", "Organizational", "Supplier security requirements agreed", "Govern", "Legal and Privacy"),
    ("5.23", "Organizational", "Cloud service use secured", "Protect", "Platform Engineering"),
    ("5.24", "Organizational", "Incident handling planned and prepared", "Respond", "Security"),
    ("5.26", "Organizational", "Incidents responded to as planned", "Respond", "Security"),
    ("5.29", "Organizational", "Security kept during disruption", "Recover", "IT Operations"),
    ("5.30", "Organizational", "ICT ready for business continuity", "Recover", "Platform Engineering"),
    ("5.31", "Organizational", "Legal and contractual requirements tracked", "Govern", "Legal and Privacy"),
    ("5.34", "Organizational", "Personal data protected (GDPR)", "Protect", "Legal and Privacy"),
    ("5.35", "Organizational", "Independent review of the ISMS", "Govern", "Security"),
    ("6.1", "People", "Background screening before hiring", "Protect", "People"),
    ("6.3", "People", "Security awareness training delivered", "Protect", "People"),
    ("6.7", "People", "Remote working secured", "Protect", "IT Operations"),
    ("7.1", "Physical", "Office perimeter secured", "Protect", "Facilities"),
    ("7.4", "Physical", "Premises monitored", "Detect", "Facilities"),
    ("8.2", "Technological", "Privileged access restricted", "Protect", "IT Operations"),
    ("8.5", "Technological", "Secure authentication (MFA)", "Protect", "IT Operations"),
    ("8.7", "Technological", "Malware protection in place", "Protect", "IT Operations"),
    ("8.8", "Technological", "Technical vulnerabilities managed", "Identify", "Platform Engineering"),
    ("8.9", "Technological", "Configurations baselined", "Protect", "Platform Engineering"),
    ("8.13", "Technological", "Backups taken and restore-tested", "Recover", "Platform Engineering"),
    ("8.15", "Technological", "Security logs produced and kept", "Detect", "Platform Engineering"),
    ("8.16", "Technological", "Monitoring for anomalies", "Detect", "Security"),
    ("8.24", "Technological", "Cryptography used as defined", "Protect", "Platform Engineering"),
    ("8.25", "Technological", "Secure development life cycle", "Protect", "Platform Engineering"),
    ("8.32", "Technological", "Changes controlled and approved", "Protect", "Platform Engineering"),
]

EVIDENCE_TYPES = [
    "policy document", "screenshot of configuration", "system export",
    "meeting minutes", "training completion report", "ticket sample",
    "access review sign-off", "test protocol",
]


def _d(offset_days: int) -> str:
    return (AS_OF + timedelta(days=offset_days)).isoformat()


def build(rng: random.Random):
    controls = [dict(zip(["control_id", "theme", "description", "nist_csf_function", "owner_team"], c))
                for c in CONTROLS]

    # Controls left without any evidence request (coverage gap)
    gap_controls = rng.sample([c["control_id"] for c in controls], 3)

    requests = []
    n = 0
    for c in controls:
        if c["control_id"] in gap_controls:
            continue
        for _ in range(rng.randint(1, 3)):
            n += 1
            status = rng.choices(["accepted", "submitted", "requested"], weights=[6, 2, 2])[0]
            if status == "accepted":
                due = _d(-rng.randint(20, 200))
                reviewed = _d(-rng.randint(10, 300))
            else:
                due = _d(rng.randint(5, 60))   # still in time
                reviewed = ""
            requests.append({
                "request_id": f"EV-{n:03d}",
                "control_id": c["control_id"],
                "evidence": rng.choice(EVIDENCE_TYPES),
                "owner_team": c["owner_team"],
                "requested_on": _d(-rng.randint(30, 240)),
                "due": due,
                "status": status,
                "last_reviewed": reviewed,
            })

    injected = {"coverage_gap": sorted(gap_controls, key=lambda x: [int(p) for p in x.split(".")])}

    pool = list(range(len(requests)))
    rng.shuffle(pool)

    def take(k):
        return [pool.pop() for _ in range(k)]

    # Missing owner
    injected["missing_owner"] = []
    for i in take(4):
        requests[i]["owner_team"] = ""
        injected["missing_owner"].append(requests[i]["request_id"])

    # Overdue: not accepted and due date passed
    injected["overdue_request"] = []
    for i in take(6):
        requests[i]["status"] = rng.choice(["requested", "submitted"])
        requests[i]["due"] = _d(-rng.randint(3, 45))
        requests[i]["last_reviewed"] = ""
        injected["overdue_request"].append(requests[i]["request_id"])

    # Stale: accepted, but last review older than 12 months
    injected["stale_evidence"] = []
    for i in take(5):
        requests[i]["status"] = "accepted"
        requests[i]["due"] = _d(-rng.randint(400, 500))
        requests[i]["last_reviewed"] = _d(-rng.randint(380, 520))
        injected["stale_evidence"].append(requests[i]["request_id"])

    # Duplicate request IDs (copy-paste error in the register)
    injected["duplicate_request_id"] = []
    for i in take(2):
        dup = dict(requests[i])
        dup["evidence"] = "duplicate entry"
        requests.append(dup)
        injected["duplicate_request_id"].append(dup["request_id"])

    # Findings from the last internal audit
    covered = sorted({r["control_id"] for r in requests})
    findings = []
    for k in range(1, 13):
        findings.append({
            "finding_id": f"F-{k:02d}",
            "control_id": rng.choice(covered),
            "severity": rng.choices(["low", "medium", "high"], weights=[4, 4, 2])[0],
            "raised_on": _d(-rng.randint(60, 150)),
            "action": "Corrective action agreed with control owner",
            "action_owner": "",
            "due": _d(rng.randint(10, 90)),
            "status": rng.choice(["open", "in progress", "closed"]),
        })
    for f in findings:
        f["action_owner"] = next(c["owner_team"] for c in controls if c["control_id"] == f["control_id"])

    fpool = list(range(len(findings)))
    rng.shuffle(fpool)
    injected["overdue_action"] = []
    for i in fpool[:3]:
        findings[i]["status"] = "open"
        findings[i]["due"] = _d(-rng.randint(5, 40))
        injected["overdue_action"].append(findings[i]["finding_id"])
    injected["high_finding_no_owner"] = []
    for i in fpool[3:5]:
        findings[i]["severity"] = "high"
        findings[i]["status"] = "open"
        findings[i]["action_owner"] = ""
        injected["high_finding_no_owner"].append(findings[i]["finding_id"])

    for v in injected.values():
        v.sort()
    return controls, requests, findings, injected


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    DATA.mkdir(exist_ok=True)
    controls, requests, findings, injected = build(random.Random(SEED))
    write_csv(DATA / "controls.csv", controls)
    write_csv(DATA / "evidence_requests.csv", requests)
    write_csv(DATA / "findings.csv", findings)
    (DATA / "injected_issues.json").write_text(json.dumps(injected, indent=2) + "\n", encoding="utf-8")
    print(f"{len(controls)} controls, {len(requests)} evidence requests, {len(findings)} findings")
    print("planted issues:", {k: len(v) for k, v in injected.items()})


if __name__ == "__main__":
    main()
