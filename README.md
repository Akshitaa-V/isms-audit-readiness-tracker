# ISMS Audit Readiness Tracker

A small Python tool that answers the question every ISMS coordinator gets a few weeks before an ISO/IEC 27001 audit: *which controls are we actually ready to show, and who still owes us what?*

It reads an audit register (controls, evidence requests and audit findings) from three CSV files, runs seven readiness checks, scores readiness per Annex A theme, and writes:

- `reports/readiness_report.md` – readiness by theme, open issues by type, priority 1 items, and a short follow-up note per team
- `reports/action_log.csv` – every open item with priority, owner and status, ready to paste into a tracker

## What it checks

| Check | Why it matters in an audit |
|---|---|
| Control without any evidence request | Nothing to show the auditor for that control |
| Evidence request without an owner | Nobody will deliver it unless responsibility is agreed |
| Evidence request past its due date | The audit date does not move |
| Accepted evidence older than 12 months | Auditors expect evidence from the current audit period |
| Duplicate request IDs | Breaks traceability between request and evidence |
| Corrective action past its due date | Open findings from the last audit get followed up first |
| Open high-severity finding without action owner | Highest risk, and nobody is on it |

A control counts as **ready** when it has accepted evidence reviewed within the last 12 months and no open high-severity finding.

## Run it

```bash
python generate_sample_data.py              # writes data/*.csv
python -m audit_tracker --as-of 2026-10-01  # writes reports/
python -m pytest -q                         # 17 tests
```

Python 3.10+ with the standard library only; `pytest` for the tests.

## Results on the sample register

The sample register has 32 Annex A controls across all four themes, 62 evidence requests and 12 findings. Twenty-five problems are planted on purpose (listed in `data/injected_issues.json`).

- All 25 planted problems are found, with no false alarms on the clean rows (checked by the tests).
- Overall readiness: 56.2% (18 of 32 controls). The People theme is at 0 of 3, which would be the first thing to raise with HR.
- Items without an owner are routed to the ISMS coordinator first, because responsibility has to be agreed before anyone can be chased.

## Notes and limits

- The data is synthetic. Control descriptions are short summaries in my own words, not the wording of the standard.
- The NIST CSF 2.0 function next to each control is an indicative mapping for orientation, not an official crosswalk. The same register structure would work for SOC 2, C5 or TISAX by swapping `controls.csv`.
- The tool tracks and flags; it does not decide whether evidence is sufficient. That judgement stays with the control owner and the auditor.

## Layout

```
audit_tracker/
  register.py    load the CSV register
  checks.py      the seven readiness checks
  readiness.py   ready / not ready per control and per theme
  followups.py   group open items by team, draft follow-up notes
  report.py      Markdown report and CSV action log
generate_sample_data.py
tests/
```
