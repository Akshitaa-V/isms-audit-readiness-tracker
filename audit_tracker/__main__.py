"""Command line entry point.

    python -m audit_tracker --data data --out reports --as-of 2026-10-01
"""

import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from . import readiness
from .checks import run_all
from .register import load
from .report import write_action_log, write_markdown


def main(argv=None):
    p = argparse.ArgumentParser(description="ISMS audit readiness check")
    p.add_argument("--data", default="data")
    p.add_argument("--out", default="reports")
    p.add_argument("--as-of", default=date.today().isoformat())
    args = p.parse_args(argv)

    as_of = date.fromisoformat(args.as_of)
    reg = load(args.data)
    issues = run_all(reg, as_of)
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    write_markdown(reg, issues, as_of, out / "readiness_report.md")
    write_action_log(issues, out / "action_log.csv")

    print(f"Overall readiness: {readiness.overall(reg, as_of)}%")
    for theme, ready, total in readiness.by_theme(reg, as_of):
        print(f"  {theme:<15} {ready}/{total}")
    print(f"Open issues: {len(issues)}  {dict(Counter(i.kind for i in issues))}")
    print(f"Wrote {out / 'readiness_report.md'} and {out / 'action_log.csv'}")


if __name__ == "__main__":
    main()
