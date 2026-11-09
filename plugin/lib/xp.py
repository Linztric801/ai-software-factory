"""XP and levels, computed from the job records.

Agents earn XP only for verified outcomes: a job that was merged, which means
its checks passed, its reviews passed and the merge happened. Failed, rejected
or unfinished jobs earn nothing. The ledger is derived from the job files every
time, so it can always be explained and recomputed, every event has a unique
key (a job pays each agent at most once), and no agent can award itself XP.

Levels and titles are cosmetic: they never change what an agent may do.
"""

DEFAULT_RULES = {
    "intake": 10,               # accepted an issue that was merged
    "spec": 15,                 # wrote the spec of a merged job
    "builder_first_round": 40,  # built it, merged after one round
    "builder_more_rounds": 25,  # built it, merged after more rounds
    "review": 10,               # each reviewer on a merged job
    "approver": 10,             # decided on a merged job
}
DEFAULT_LEVELS = [
    [0, "New recruit"], [100, "Apprentice"], [250, "Specialist"],
    [500, "Senior specialist"], [900, "Expert"], [1500, "Master"],
]
REVIEWERS = {"code", "security", "ui", "ux"}


def ledger(jobs, settings=None):
    """Every XP event, oldest first: {key, agent, xp, job, issue, reason, at}."""
    rules = {**DEFAULT_RULES, **((settings or {}).get("xp", {}).get("rules", {}))}
    events, seen = [], set()

    def add(agent, xp, job, reason):
        key = f"{job['id']}:{agent}"
        if key in seen or xp <= 0:
            return
        seen.add(key)
        events.append({"key": key, "agent": agent, "xp": xp, "job": job["id"], "issue": job.get("issue"),
                       "reason": reason, "at": job.get("ended") or ""})

    for job in sorted((j for j in jobs if j.get("stage") == "merged"), key=lambda j: j.get("ended") or ""):
        ref = f"#{job.get('issue')}"
        pr = f"PR #{job['pr']}" if job.get("pr") else "the PR"
        add("intake", rules["intake"], job, f"accepted {ref}; {pr} merged")
        add("spec", rules["spec"], job, f"spec for {ref}; {pr} merged")
        first = job.get("round", 1) <= 1
        add("builder", rules["builder_first_round" if first else "builder_more_rounds"], job,
            f"built {ref}; {pr} merged after {job.get('round', 1)} round{'s' if not first else ''}")
        for r in ((job.get("agents") or {}).get("reviewers") or {}):
            if r in REVIEWERS:
                add(r, rules["review"], job, f"reviewed {ref}; {pr} merged")
        add("approver", rules["approver"], job,
            f"decided {ref}; {pr} merged" + (f", approved by @{job['approved_by']}" if job.get("approved_by") else ""))
    return events


def levels(settings=None):
    return (settings or {}).get("xp", {}).get("levels") or DEFAULT_LEVELS


def standing(events, settings=None):
    """Per agent: total XP, level number, title, and the next threshold (None at the top)."""
    table = sorted(levels(settings), key=lambda l: l[0])
    out = {}
    for agent in {e["agent"] for e in events} | {"intake", "spec", "builder", "code", "security", "ui", "ux", "approver"}:
        total = sum(e["xp"] for e in events if e["agent"] == agent)
        n = max(i for i, (floor, _) in enumerate(table) if total >= floor)
        nxt = table[n + 1] if n + 1 < len(table) else None
        out[agent] = {"xp": total, "level": n + 1, "title": table[n][1], "floor": table[n][0],
                      "next": nxt[0] if nxt else None, "next_title": nxt[1] if nxt else None}
    return out
