"""Group open items by team and draft a short follow-up note for each team.

Items without an owner go to the ISMS coordinator first, because someone has
to agree who is responsible before anyone can be chased.
"""

from collections import defaultdict

UNASSIGNED = "ISMS coordinator (owner to be agreed)"
GREETING = {UNASSIGNED: "ISMS coordinator"}


def group_by_team(issues):
    teams = defaultdict(list)
    for i in issues:
        teams[i.owner_team or UNASSIGNED].append(i)
    return dict(sorted(teams.items(), key=lambda kv: (kv[0] != UNASSIGNED, kv[0])))


def draft_note(team: str, items, audit_name: str = "the upcoming ISO/IEC 27001 surveillance audit") -> str:
    lines = [
        f"Hello {GREETING.get(team, team)} team,",
        "",
        f"to prepare for {audit_name}, these items are still open on your side:",
        "",
    ]
    for i in sorted(items, key=lambda x: (x.priority, x.ref)):
        lines.append(f"- [{i.control_id}] {i.detail}")
    lines += [
        "",
        "Could you let me know by Friday when each one will be done, or tell me if "
        "something is blocked or sits with another team? I am happy to go through "
        "it in a short call.",
        "",
        "Thank you!",
    ]
    return "\n".join(lines)
