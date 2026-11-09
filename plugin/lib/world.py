"""The dashboard's world: real job state turned into places, scenes and a page.

`derive()` is the only place that decides where an agent stands, and it reads
nothing but the jobs' own state: an agent walks only when a job moved. The
scenes draw that state; the page wraps it in views. Everything is rendered
here, in Python, so the browser needs no build step and works without script.
"""

import json
import math
import re
import time
from collections import Counter
from html import escape
from pathlib import Path

import xp
from pixel import (bubble, box, chibi, cloud, cls, css_classes, css_tokens, nametag, rect,
                   sprite_at, status_marker, step_plate, text, tip, tip_rule)

PLUGIN = Path(__file__).resolve().parents[1]
THEMES = PLUGIN / "themes"
CSS_FILE = PLUGIN / "dashboard" / "festival.css"

# ---- The crew: one agent per role in the pipeline ---------------------------------

AGENTS = [
    ("intake", "Intake", "Decides what gets built", dict(hair="brown", top="green", style="short", acc="glasses", eyes="green")),
    ("spec", "Spec writer", "Turns an issue into a spec", dict(hair="lav", top="white", style="long", eyes="lav")),
    ("builder", "Builder", "Writes the code and opens the PR", dict(hair="black", top="coral", style="short", acc="hardhat", eyes="brown")),
    ("code", "Code reviewer", "Correctness and conventions", dict(hair="brown", top="navy", skin="skin2", style="short", acc="glasses", eyes="brown")),
    ("security", "Security reviewer", "Access, input, secrets", dict(hair="black", top="black", style="short", acc="headset", eyes="cyan")),
    ("ui", "UI reviewer", "Does it look like the app", dict(hair="pink", top="cyan", style="bob", eyes="pink")),
    ("ux", "UX reviewer", "Can people use it", dict(hair="yellow", top="green", skin="skin2", style="twin", eyes="green")),
    ("approver", "Approver", "Merge, or ask a person", dict(hair="silver", top="navy", style="spiky", eyes="cyan")),
]
AGENT = {k: (name, role, kw) for k, name, role, kw in AGENTS}
SHORT = {"intake": "Intake", "spec": "Spec writer", "builder": "Builder", "code": "Code",
         "security": "Security", "ui": "UI", "ux": "UX", "approver": "Approver"}

ZONES = {  # key: (x, y, w, h) on the 240x180 map
    "masterclass": (6, 8, 58, 62),
    "venue": (72, 8, 96, 62),
    "arena": (176, 8, 58, 62),
    "plaza": (72, 76, 72, 26),
    "tower": (150, 76, 22, 26),
    "pavilions": (6, 110, 58, 62),
    "beerfest": (72, 110, 84, 62),
    "suite": (164, 110, 70, 62),
}
SPOTS = {  # where characters stand in each zone (x, y of the 14x18 sprite)
    "masterclass": [(30, 35), (12, 35), (46, 35)],
    "venue": [(80, 36), (130, 36), (106, 50)],
    "arena": [(180, 30), (218, 30), (199, 46), (190, 46)],
    "plaza": [(128, 86), (112, 86), (96, 86), (80, 86)],  # from the right, clear of the sign first
    "tower": [(154, 80)],
    "pavilions": [(34, 132)],
    "beerfest": [(84, 135), (100, 150)],
    "suite": [(170, 121), (186, 121), (202, 121), (218, 121), (170, 141), (186, 141), (202, 141), (218, 141)],
}
WORKING = {"Working", "Testing", "Analysing", "Deciding"}
ROBE = {"top": "robe", "legs": "robe", "lanyard": "black"}  # idle agents relax in hotel robes, badges on
CROWD_SPOTS = [(10, 82), (24, 84), (38, 82), (52, 84), (180, 82), (194, 84), (208, 82), (222, 84)]  # the grass by the paths
STEPS = {  # the pipeline step each place stands for, shown on the map beside its sign
    "masterclass": "INTAKE",
    "pavilions": "SPEC",
    "venue": "BUILD",
    "arena": "GATE",
    "plaza": "REVIEW",
    "tower": "APPROVE",
    "beerfest": "YOUR CALL",
    "suite": "IDLE",
}
STAGE_LABEL = {"intake": "Intake", "needs-info": "Asked the author", "spec": "Spec", "build": "Build",
               "gate": "Gate", "review": "Review", "approve": "Approve", "merging": "Merging",
               "needs-human": "Your call", "awaiting-approval": "Awaiting approval",
               "merged": "Merged", "rejected": "Rejected"}


HANDLE = re.compile(r"^[A-Za-z0-9_-]{1,39}$")


def load_theme(name="cloudfest"):
    """A theme from the plugin's own themes/ folder, never from anywhere else."""
    if not re.fullmatch(r"[a-z0-9-]{1,40}", str(name)):
        raise ValueError(f"theme name {name!r}: use lowercase letters, digits and dashes")
    folder = (THEMES / name).resolve()
    if not folder.is_relative_to(THEMES.resolve()) or not (folder / "theme.json").is_file():
        raise ValueError(f"no theme {name!r} in {THEMES}")
    theme = json.loads((folder / "theme.json").read_text())
    logo_file = (folder / theme.get("logo", "logo.svg")).resolve()
    if not logo_file.is_relative_to(folder):
        raise ValueError(f"theme {name!r}: the logo must be inside the theme folder")
    theme["logo"] = logo_file.name
    theme["dir"] = folder
    sprites = ([p["sprite"] for p in theme.get("people", {}).values()] + list(theme.get("robes", {}).values())
               + theme.get("suite_friends", []) + theme.get("crowd", []))
    for sprite in sprites:
        if isinstance(sprite.get("acc"), list):
            sprite["acc"] = tuple(sprite["acc"])
    return theme


def clean_svg(raw):
    """Logos are inlined, so drop anything that could run: scripts, event handlers,
    foreignObject and javascript: links."""
    raw = re.sub(r"(?is)<script\b.*?</script\s*>", "", raw)
    raw = re.sub(r"(?is)<foreignObject\b.*?</foreignObject\s*>", "", raw)
    raw = re.sub(r"(?i)\s+on[a-z]+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", raw)
    return re.sub(r"(?i)(href\s*=\s*[\"'])\s*javascript:[^\"']*", r"\1#", raw)


def logo(theme, css_class):
    raw = clean_svg((theme["dir"] / theme["logo"]).read_text())
    raw = raw.split("?>", 1)[-1] if raw.lstrip().startswith("<?xml") else raw
    raw = raw.replace('fill="black"', 'fill="currentColor"')
    return raw.replace("<svg ", f'<svg class="{css_class}" role="img" aria-label="{escape(theme["name"])}" ', 1)


def place(theme, key):
    return theme.get("places", {}).get(key, key)


# ---- Real state -> who is where ------------------------------------------------------

def issue_ref(job):
    return f"#{job['issue']}"


def safe_url(url):
    """Only https links reach an href; anything else is shown as text."""
    return url if isinstance(url, str) and url.startswith("https://") else None


def ext_link(url, label):
    url = safe_url(url)
    if not url:
        return f"<span>{escape(label)}</span>"
    return f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a>'


def job_links(job):
    """The issue and the PR, each a link when its URL is known."""
    out = [ext_link(job.get("issue_url"), f"issue #{job['issue']}")]
    if job.get("pr"):
        out.append(ext_link(job.get("pr_url"), f"PR #{job['pr']}"))
    return "".join(out)


def open_job(job, inner):
    """A link that opens the job's status panel; the page's script does the opening."""
    jid = escape(job["id"])
    return f'<a class="job-open" href="#job={jid}" data-job="{jid}">{inner}</a>'


def model_of(job, agent):
    reviewers = (job.get("agents") or {}).get("reviewers") or {}
    return reviewers.get(agent) or ("opus" if agent in ("intake", "spec", "builder", "approver") else "")


def verdict_chips(job):
    """The current round as chips: the gate, then each routed reviewer."""
    if not job.get("round"):
        return ""

    def chip(label, v, title):
        v = v or "pending"
        tone = v if v in ("PASS", "CHANGES", "FAIL") else "pending"
        return f'<span class="chip chip-{tone.lower()}" title="{escape(title)}: {escape(v)}">{escape(label)}</span>'
    cells = [chip("gate", job.get("gate"), "gate")]
    if job.get("gate") == "PASS":
        short = {"security": "sec"}
        for r, v in (job.get("reviews") or {}).items():
            cells.append(chip(short.get(r, r), v, f"{r} review"))
    return f'<span class="chips"><span class="chip-round">R{job["round"]}</span>{"".join(cells)}</span>'


def people_for(names, theme):
    """Display names for the people an approval names (theme people, or the raw handle)."""
    people = theme.get("people", {})
    return [people.get(n, {}).get("name", n) for n in names]


def derive(jobs, settings, theme):
    """Where every agent is and why, from the jobs alone."""
    work = {k: [] for k in AGENT}

    def add(agent, zone, state, why, job, say=None):
        work[agent].append((zone, state, why, job, say or why[:1].upper() + why[1:]))

    # Approver handles come from the project's settings: keep only plain names.
    approvers = [a for a in settings.get("approvers", []) if isinstance(a, str) and HANDLE.match(a)]
    named = people_for(approvers, theme)
    for job in sorted(jobs, key=lambda j: j.get("started") or ""):
        st, ref = job["stage"], issue_ref(job)
        if st == "intake":
            add("intake", "masterclass", "Analysing", f"reading {ref}", job)
        elif st == "needs-info":
            add("intake", "masterclass", "Waiting for the author", f"a question on {ref}", job, f"Question on {ref}")
        elif st == "spec":
            add("spec", "pavilions", "Analysing", f"spec for {ref}", job)
        elif st == "build":
            add("builder", "venue", "Working", f"building {ref}", job)
        elif st == "gate":
            add("builder", "arena", "Testing", f"checks for {ref}", job)
        elif st == "review":
            for r, verdict in (job.get("reviews") or {}).items():
                if verdict == "pending" and r in AGENT:
                    add(r, "plaza", "Testing", f"reviewing {ref}", job)
        elif st == "approve":
            add("approver", "tower", "Deciding", f"deciding {ref}", job)
        elif st == "merging":
            add("approver", "tower", "Working", f"merging {ref}", job)
        elif st == "awaiting-approval":
            who = " and ".join(named) if named else "a person"
            say = f"Waiting for {named[0]}" if len(named) == 1 else (f"Waiting for {len(named)} people" if named else "Waiting for a person")
            add("approver", "beerfest", "Waiting for approval", f"{ref} approved, needs {who} to merge", job, say)
        elif st == "needs-human":
            who = " and ".join(named) if named else "a person"
            say = f"Waiting for {named[0]}" if len(named) == 1 else (f"Waiting for {len(named)} people" if named else "Waiting for a person")
            add("approver", "beerfest", "Waiting for approval", f"{ref} needs {who}", job, say)
    agents = {}
    for k in AGENT:
        items = work[k]
        if not items:
            agents[k] = {"zone": "suite", "state": "Idle", "why": "free for a quest", "jobs": [], "say": "",
                         "places": [{"zone": "suite", "state": "Idle", "why": "free for a quest", "jobs": [], "say": ""}]}
            continue
        # One figure per place the agent has work in, so a job that is building and one at
        # the gate show the builder in both places, as the old office's clones did.
        by_zone = {}
        for item in sorted(items, key=lambda i: 0 if i[1].startswith("Waiting") else 1):
            by_zone.setdefault(item[0], []).append(item)
        places = []
        for zone, group in by_zone.items():
            _, pstate, pwhy, _, psay = group[0]
            more = len(group) - 1
            places.append({"zone": zone, "state": pstate, "why": f"{pwhy} and {more} more" if more else pwhy,
                           "jobs": [i[3] for i in group], "say": f"{psay} +{more}" if more else psay})
        # A waiting job outranks running ones: it needs a person.
        items.sort(key=lambda i: 0 if i[1].startswith("Waiting") else 1)
        zone, state, why, _, say = items[0]
        if len(items) > 1:
            why = f"{why} and {len(items) - 1} more"
            waiting_items = [i for i in items if i[1].startswith("Waiting for approval")]
            if state.startswith("Waiting for approval") and len(waiting_items) > 1:
                say = say.replace("Waiting for", f"{len(waiting_items)} PRs wait for", 1)
            else:
                say = f"{say} +{len(items) - 1}"
        agents[k] = {"zone": zone, "state": state, "why": why, "jobs": [i[3] for i in items], "say": say,
                     "places": places}
    stages = Counter(j["stage"] for j in jobs)
    running = sum(n for s, n in stages.items() if s in {"intake", "spec", "build", "gate", "review", "approve", "merging"})
    waiting = [j for j in jobs if j["stage"] in ("needs-human", "awaiting-approval")]
    merged = sorted((j for j in jobs if j["stage"] == "merged"), key=lambda j: j.get("ended") or "")
    return {
        "agents": agents,
        "stats": {"merged": stages["merged"], "rejected": stages["rejected"], "running": running,
                  "waiting": len(waiting) + stages["needs-info"], "jobs": len(jobs),
                  "cost": sum(j.get("cost_usd") or 0 for j in jobs)},
        "waiting": waiting,
        "questions": [j for j in jobs if j["stage"] == "needs-info"],
        "approvers": approvers,
        "latest": merged[-1] if merged else None,
    }


# ---- Scenes ---------------------------------------------------------------------------

def ambient(theme, salt):
    lines = theme.get("lines", {}).get("ambient") or ["Free for a quest!"]
    return lines[(int(time.time() // 30) + salt) % len(lines)]


def booth_name(project):
    name = project.split("-", 1)[-1] if "-" in project else project
    return name if len(name) <= 11 else name[:10] + "…"


def world_map(world, theme, project="project"):
    s = ['<svg class="px world" viewBox="0 0 240 180" role="img" aria-labelledby="map-title map-desc">',
         '<title id="map-title">Festival map</title>',
         '<desc id="map-desc">The factory as a festival ground. The list beside the map says who is where.</desc>',
         '<defs><pattern id="grass" width="240" height="180" patternUnits="userSpaceOnUse">',
         rect(0, 0, 240, 180, cls("grass")),
         '</pattern><pattern id="tiles" width="4" height="4" patternUnits="userSpaceOnUse">',
         rect(0, 0, 4, 4, cls("path")),
         '</pattern></defs>',
         '<rect width="240" height="180" fill="url(#grass)"/>',
         '<rect x="0" y="104" width="240" height="6" fill="url(#tiles)"/>',
         '<rect x="64" y="0" width="6" height="180" fill="url(#tiles)"/>',
         '<rect x="170" y="0" width="6" height="104" fill="url(#tiles)"/>',
         '<rect x="158" y="104" width="6" height="76" fill="url(#tiles)"/>',
         '<rect x="70" y="70" width="100" height="6" fill="url(#tiles)"/>']
    for key, (x, y, w, h) in ZONES.items():
        label = place(theme, key)
        s.append(box(x, y, w, h, "violet" if key in ("venue", "pavilions") else "floor"))
        s.append(zone_art(key, x, y, w, h, theme, booth_name(project)))
        sy = y + 2 if h < 40 else y + h - 9
        s.append(box(x + 2, sy, round(len(label) * 3 * 0.85) + 6, 7, "wood"))
        s.append(text(x + 5, sy + 5, label, 4.2))
        if key in STEPS:
            s.append(step_plate(x + 2, y - 6, STEPS[key]))  # a tab on the path above the place
    used, tips, tags, bubbles, rules = Counter(), [], [], [], []
    said = set()  # one bubble per place and line: four reviewers on one job share it
    figures = [(k, n, a) for k in AGENT for n, a in enumerate(world["agents"][k].get("places") or [world["agents"][k]])]
    for k, n, a in figures:
        name, _, kw = AGENT[k]
        mid = f"map-{k}" if n == 0 else f"map-{k}-{n}"
        spots = SPOTS[a["zone"]]
        sx, sy = spots[used[a["zone"]] % len(spots)]
        used[a["zone"]] += 1
        anim = "idle" if a["state"] == "Idle" else ("work" if a["state"] in WORKING else None)
        job = a["jobs"][0] if a["jobs"] else None
        look = {**kw, **ROBE} if a["state"] == "Idle" else kw
        s.append(sprite_at(sx, sy, chibi(**look), f"{name}: {a['state']}, {a['why']}", anim, id_=mid,
                           job=job["id"] if job else None))
        s.append(status_marker(sx, sy, "Working" if a["state"] in WORKING else a["state"]))
        if job:
            model = model_of(job, k)
            title = job["title"] if len(job["title"]) <= 40 else job["title"][:39] + "…"
            pr = f", PR #{job['pr']}" if job.get("pr") else ""
            lines = [f"{name}{' · ' + model if model else ''}",
                     f"{STAGE_LABEL.get(job['stage'], job['stage'])}, round {job.get('round') or 0}",
                     f"#{job['issue']}{pr}", title, "Click for status and PR"]
        else:
            lines = [name, a["state"]]
        tips.append(tip(mid, sx + 7, sy - 7, lines))
        rules.append(tip_rule(mid, k))
        if a["zone"] != "suite":  # the suite is a crowd; hover tells who is who
            tags.append(nametag(sx + 7, sy + 19, SHORT[k]))
        if a["state"] != "Idle" and (a["zone"], a["say"]) not in said:
            said.add((a["zone"], a["say"]))
            bubbles.append(bubble(sx + 7, sy - 7, a["say"][:24], "task", shift=-6 if a["zone"] == "plaza" else 0))
        elif used["suite"] == 1 and sum(1 for x in world["agents"].values() if x["state"] == "Idle") <= 2:
            bubbles.append(bubble(sx + 7, sy - 2, ambient(theme, 0), "ambient"))
    people = theme.get("people", {})
    for key, sprite in theme.get("robes", {}).items():
        if key not in people or used["suite"] >= len(SPOTS["suite"]):
            continue
        sx, sy = SPOTS["suite"][used["suite"]]
        used["suite"] += 1
        who = people[key]
        s.append(sprite_at(sx, sy, chibi(**sprite), f"{who['name']}, {who['role']}, in a robe (cameo)", "idle", id_=f"map-robe-{key}"))
        tips.append(tip(f"map-robe-{key}", sx + 7, sy - 7, [who["name"], "In a robe at the after party"]))
        rules.append(tip_rule(f"map-robe-{key}"))
    for i, ((cx, cy), sprite) in enumerate(zip(CROWD_SPOTS, theme.get("crowd", []))):
        s.append(sprite_at(cx, cy, chibi(**sprite), "A festival friend (cameo)", "idle", id_=f"map-crowd-{i}"))
        tips.append(tip(f"map-crowd-{i}", cx + 7, cy - 1, ["Festival friend", "At the festival"]))
        rules.append(tip_rule(f"map-crowd-{i}"))
    host = theme.get("people", {}).get(theme.get("host", ""))
    if host:
        s.append(sprite_at(140, 128, chibi(**host["sprite"]), f"{host['name']}, {host['role']} (cameo)", id_="map-host"))
        tips.append(tip("map-host", 147, 121, [host["name"], host["role"].split(",")[0]]))
        rules.append(tip_rule("map-host"))
        tags.append(nametag(147, 147, host.get("short", host["name"])))
    s.extend(bubbles)
    s.extend(tags)
    s.extend(tips)
    s.append(f"<style>{''.join(rules)}</style></svg>")
    return "".join(s)


def zone_art(key, x, y, w, h, theme, booth="project"):
    s = []
    if key == "venue":
        s.append(box(x + 4, y + 2, w - 8, 30, "sky"))
        s.append(rect(x + 6, y + 4, w - 12, 1, cls("grey", 2)))
        for i in range(x + 10, x + w - 8, 10):
            s.append(box(i, y + 5, 3, 2, "grey", outline=False))
            s.append(rect(i + 1, y + 7, 1, 1, cls("cyan", 0)))
        s.append(box(x + 8, y + 10, 18, 16, "led"))
        s.append(box(x + w - 26, y + 10, 18, 16, "led"))
        s.append(box(x + 30, y + 9, w - 60, 18, "led"))
        s.append(f'<g transform="translate({x + 31.5} {y + 12.5}) scale(0.16)">{logo(theme, "map-logo")}</g>')
        s.append(text(x + w / 2, y + 24, "main stage", 3.4, "sign", "middle"))
        s.append(box(x + 6, y + 28, w - 12, 3, "black"))
        for i in range(x + 8, x + w - 8, 6):
            s.append(rect(i, y + 29, 2, 1, cls("cyan")))
        s.append(cloud(x + 42, y + 36))
        s.append(box(x + 8, y + 40, 30, 14, "white"))
        s.append(text(x + 23, y + 49, booth, 3.4, "sign-dark", "middle"))
    elif key == "masterclass":
        for i in range(2):
            s.append(box(x + 4 + i * 27, y + 4, 23, 20, "wall"))
            s.append(box(x + 7 + i * 27, y + 7, 17, 10, "white"))
            s.append(rect(x + 9 + i * 27, y + 10, 10, 1, cls("navy")))
            s.append(rect(x + 9 + i * 27, y + 13, 7, 1, cls("navy")))
    elif key == "arena":
        s.append(box(x + 4, y + 4, w - 8, 30, "sky"))
        s.append(box(x + 8, y + 8, w - 16, 22, "green", outline=False))
        s.append(box(x + 16, y + 12, 26, 9, "black"))
        s.append(text(x + 29, y + 18.5, "gate", 3.6, "sign-cyan", "middle"))
    elif key == "plaza":
        s.append(box(x + 4, y + 11, 18, 13, "wood"))
        for i in range(3):
            s.append(box(x + 6 + i * 5, y + 13, 4, 4, ["white", "amber", "cyan"][i], outline=False))
    elif key == "tower":
        s.append(box(x + 6, y + 11, 10, 13, "wall"))
        s.append(box(x + 4, y + 11, 14, 4, "glass"))
    elif key == "pavilions":
        s.append(cloud(x + 22, y + 4))
        px = x + 4
        s.append(box(px, y + 14, 23, 20, "white"))
        for j in range(0, 23, 4):
            s.append(rect(px + j, y + 8, 2, 6, cls("coral")))
        s.append(rect(px, y + 8, 23, 1, cls("o")))
        s.append(text(px + 11.5, y + 26, booth, 3.2, "sign-dark", "middle"))
    elif key == "beerfest":
        s.append(box(x + 6, y + 4, w - 12, 30, "wood"))
        s.append(box(x + 46, y + 4, w - 52, 7, "blue"))
        s.append(text(x + 46 + (w - 52) / 2, y + 9.4, place(theme, "beerfest_sign"), 4.6, "sign", "middle"))
        s.append(box(x + 30, y + 22, 6, 9, "beer"))
        s.append(box(x + 30, y + 20, 6, 3, "foam"))
        s.append(rect(x + 36, y + 24, 2, 4, cls("o")))
        for i in range(4):
            s.append(box(x + 8 + i * 18, y + 40, 12, 4, "wood"))
    elif key == "suite":
        s.append(box(x + 4, y + 8, 46, 40, "wall"))
        s.append(box(x + 4, y + 2, 46, 6, "coral"))
        s.append(text(x + 27, y + 6.6, place(theme, "suite_sign"), 3.4, "sign", "middle"))
        s.append(box(x + 7, y + 11, 40, 11, "amber"))
        for i in range(1, 4):
            s.append(rect(x + 7 + i * 10, y + 11, 1, 11, cls("o")))
        s.append(rect(x + 4, y + 24, 46, 1, cls("o")))
        s.append(box(x + 7, y + 27, 40, 12, "amber"))
        for i in range(1, 4):
            s.append(rect(x + 7 + i * 10, y + 27, 1, 12, cls("o")))
        s.append(box(x + 50, y + 30, 16, 16, "wood"))
    return "".join(s)


def person_sprite(theme, key):
    person = theme.get("people", {}).get(key)
    if person:
        return person["name"], person["role"], person["sprite"]
    return key, "Approver", dict(hair="brown", top="grey", style="short", eyes="brown")


def bierfest_scene(world, theme):
    W = 160
    host = theme.get("people", {}).get(theme.get("host", ""))
    s = [f'<svg class="px scene" viewBox="0 0 {W} 100" role="img" aria-label="{escape(place(theme, "beerfest_long"))}">',
         rect(0, 0, W, 100, cls("white", 2)), rect(0, 70, W, 30, cls("wood", 2))]
    for i in range(0, W, 10):
        s.append(rect(i, 0, 1, 30, cls("white")))
    s.append(rect(0, 30, W, 2, cls("wood")))
    for i in range(0, W, 6):
        s.append(rect(i, 32, 5, 2, cls("blue" if (i // 6) % 2 else "white", 0)))
    s.append(rect(46, 2, 1, 7, cls("o")))
    s.append(rect(96, 2, 1, 7, cls("o")))
    s.append(box(34, 9, 74, 5, "wood"))
    for i in range(38, 104, 8):
        s.append(box(i, 10, 3, 3, ["coral", "white", "blue"][(i // 8) % 3], outline=False))
    for bx, by in ((10, 6), (120, 4), (140, 12)):
        s.append(box(bx, by + 4, 10, 12, "yellow"))
        s.append(box(bx, by, 10, 5, "foam"))
        s.append(rect(bx + 10, by + 7, 3, 6, cls("o")))
    s.append(box(64, 38, 70, 10, "blue"))
    s.append(text(99, 45.5, place(theme, "beerfest_long"), 4.6, "sign", "middle"))
    s.append(box(8, 58, 144, 12, "wood"))
    tips, rules = [], []
    names = [person_sprite(theme, p)[0] for p in world["approvers"]]
    if host:
        s.append(sprite_at(40, 40, chibi(**host["sprite"]), f"{host['name']}, host (cameo)", id_="bf-host"))
        s.append(rect(58, 44, 1, 14, cls("o")))
        s.append(box(57, 41, 3, 3, "grey"))
        tips.append(tip("bf-host", 47, 40, [host["name"], host["role"].split(",")[0]], width=W))
        rules.append(tip_rule("bf-host"))
        if world["waiting"]:
            who = ", ".join(n.split()[0] for n in names) or "Folks"
            s.append(bubble(46, 39, [f"{who}!", *wrap(theme.get('lines', {}).get('invite', 'A review is waiting!'), 22)], "ambient", shift=6))
    if world["waiting"]:
        s.append(sprite_at(84, 74, chibi(**AGENT["approver"][2]), "Approver, waiting", id_="bf-approver"))
        s.append(status_marker(84, 74, "Waiting for approval"))
        tips.append(tip("bf-approver", 91, 67, ["Approver", f"Waiting on {len(world['waiting'])}"], width=W))
        rules.append(tip_rule("bf-approver"))
        for i, p in enumerate(world["approvers"][:3]):
            name, role, kw = person_sprite(theme, p)
            x = 108 + i * 18
            s.append(sprite_at(x, 74, chibi(**kw), f"{name}, named approver", id_=f"bf-p{i}"))
            s.append(nametag(x + 7, 93, name.split()[0], 3))
            tips.append(tip(f"bf-p{i}", x + 7, 74, [name, "Named approver"], width=W))
            rules.append(tip_rule(f"bf-p{i}"))
    for i, a in enumerate(("builder", "code", "ui")):
        s.append(sprite_at(20 + i * 16, 78, chibi(**AGENT[a][2], pose="back"), f"{AGENT[a][0]}, at the table"))
    s.extend(tips)
    s.append(f"<style>{''.join(rules)}</style></svg>")
    return "".join(s)


def wrap(line, width):
    out, cur = [], ""
    for word in line.split():
        if cur and len(cur) + 1 + len(word) > width:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return out + ([cur] if cur else [])


def popup_scene(world, theme):
    W = 120
    host = theme.get("people", {}).get(theme.get("host", ""))
    s = [f'<svg class="px popup-scene" viewBox="0 0 {W} 64" role="img" aria-label="The host and the named approvers raise a stein at the BierFest">',
         rect(0, 0, W, 64, cls("sky")), rect(0, 50, W, 14, cls("wood", 2))]
    for i in range(0, W, 8):
        s.append(rect(i + 3, 3 + (i // 8) % 2, 2, 2, cls(["amber", "coral", "cyan"][(i // 8) % 3])))
    s.append(box(14, 46, 92, 5, "wood"))
    cast = ([("host", host["name"], host["sprite"])] if host else []) + \
           [(f"p{i}", *(lambda n, r, k: (n, k))(*person_sprite(theme, p))) for i, p in enumerate(world["approvers"][:2])]
    xs = [18, 53, 86][:len(cast)]
    tips, rules = [], []
    for (key, name, kw), x in zip(cast, xs):
        s.append(sprite_at(x, 28, chibi(**kw), name, id_=f"pop-{key}"))
        s.append(nametag(x + 7, 47, name.split()[0], 3))
        tips.append(tip(f"pop-{key}", x + 7, 28, [name, "Host" if key == "host" else "Named approver"], width=W))
        rules.append(tip_rule(f"pop-{key}"))
    for gx in (36, 47, 71, 80)[:2 * max(1, len(cast) - 1)]:
        s.append(box(gx, 34, 5, 8, "beer"))
        s.append(box(gx, 32, 5, 3, "foam"))
    names = [person_sprite(theme, p)[0].split()[0] for p in world["approvers"][:2]]
    if host:
        first = f"{', '.join(names)}!" if names else "Hey!"
        s.append(bubble(25, 26, [first, *wrap(theme.get("lines", {}).get("invite", "A review is waiting!"), 24)], "ambient", shift=22, size=4.2))
    s.extend(tips)
    s.append(f"<style>{''.join(rules)}</style></svg>")
    return "".join(s)


def stage_scene(world, theme):
    W = 220
    st = world["stats"]
    host = theme.get("people", {}).get(theme.get("host", ""))
    s = [f'<svg class="px scene" viewBox="0 0 {W} 130" role="img" aria-label="The main stage: the factory’s numbers on the LED wall">',
         rect(0, 0, W, 130, cls("sky", 2)), rect(0, 4, W, 2, cls("grey", 2)), rect(0, 9, W, 1, cls("grey", 2))]
    for i in range(0, W, 6):
        s.append(rect(i, 6, 1, 3, cls("grey", 2)))
    for n, lx in enumerate(range(10, W - 4, 22)):
        s.append(box(lx, 10, 6, 5, "grey"))
        drift = (-1, 1)[n % 2]
        for k in range(1, 34, 2):
            s.append(rect(lx + 2 + drift * (k // 3), 16 + k, 2, 1, cls("led", 0)))
    s.append(box(10, 20, 40, 40, "led"))
    s.append(box(W - 50, 20, 40, 40, "led"))
    s.append(f'<g transform="translate(14 23) scale(0.155)">{logo(theme, "wall-logo")}</g>')
    s.append(text(30, 37, "AI Software", 4, "sign", "middle"))
    s.append(text(30, 42.5, "Factory", 4, "sign", "middle"))
    latest = world["latest"]
    s.append(text(W - 30, 30, "Just in", 4.2, "sign", "middle"))
    if latest and latest.get("pr"):
        s.append(text(W - 30, 41, f"PR #{latest['pr']}", 5, "sign", "middle"))
        s.append(text(W - 30, 48, "merged", 3.8, "sign", "middle"))
    else:
        s.append(text(W - 30, 44, "nothing yet", 3.6, "sign", "middle"))
    s.append(box(56, 18, W - 112, 44, "navy"))
    s.append(text(W / 2, 27, "Factory today", 6, "sign", "middle"))
    for i, (num, label) in enumerate(((st["merged"], "merged"), (st["rejected"], "rejected"),
                                      (st["running"], "running"), (st["jobs"], "jobs"))):
        bx = 62 + i * 25
        s.append(box(bx, 33, 21, 22, "led"))
        s.append(text(bx + 10.5, 45, str(num), 9, "sign", "middle"))
        s.append(text(bx + 10.5, 51.5, label, 3.2, "sign", "middle"))
    s.append(box(30, 78, W - 60, 8, "black"))
    for i in range(32, W - 30, 7):
        s.append(rect(i, 80, 3, 1, cls("cyan")))
    rules, tips = [], []
    if host:
        s.append(sprite_at(70, 60, chibi(**host["sprite"]), f"{host['name']}, hosting", id_="ms-host"))
        s.append(bubble(74, 61, wrap(theme.get("lines", {}).get("stage_welcome", "Welcome!"), 16), "ambient", shift=-40))
        tips.append(tip("ms-host", 77, 60, [host["name"], host["role"].split(",")[0]], width=W))
        rules.append(tip_rule("ms-host"))
    a = world["agents"]["approver"]
    s.append(sprite_at(136, 60, chibi(**AGENT["approver"][2]), f"Approver: {a['state']}", id_="ms-approver"))
    tips.append(tip("ms-approver", 143, 60, ["Approver", a["state"]], width=W))
    rules.append(tip_rule("ms-approver"))
    for row, cy in enumerate((92, 104, 116)):
        for cx in range(4 + (row % 2) * 7, W, 14):
            s.append(rect(cx, cy, 8, 7, cls("navy", 2)) + rect(cx + 1, cy - 2, 6, 2, cls("navy", 2)) + rect(cx - 1, cy + 7, 10, 8, cls("navy", 2)))
    for i, k in enumerate(("intake", "spec", "builder", "code", "security", "ui", "ux")):
        if world["agents"][k]["state"] == "Idle":
            s.append(sprite_at(22 + i * 26, 96 + (i % 2) * 4, chibi(**AGENT[k][2], pose="back"), f"{AGENT[k][0]}, in the audience"))
    s.extend(tips)
    s.append(f"<style>{''.join(rules)}</style></svg>")
    return "".join(s)


def suite_scene(world, theme):
    W, H = 220, 132
    s = [f'<svg class="px scene" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(place(theme, "suite_long"))}: idle agents relax">',
         rect(0, 0, W, H, cls("sky"))]
    for sx, sy in ((168, 6), (190, 14), (210, 4), (176, 22), (204, 30), (186, 2)):
        s.append(rect(sx, sy, 1, 1, cls("white")))
    for a in range(16):
        s.append(rect(round(196 + 12 * math.cos(a / 16 * 6.28)), round(34 + 12 * math.sin(a / 16 * 6.28)), 1, 1, cls("amber")))
    for i in range(0, 52, 2):
        s.append(rect(166 + i, 56 - abs((i % 26) - 13), 2, 1, cls("cyan", 2)))
    s.append(box(4, 6, 158, 122, "wall"))
    s.append(box(8, 10, 150, 18, "sky"))
    for i in range(1, 6):
        s.append(rect(8 + i * 25, 10, 1, 18, cls("o")))
    s.append(box(96, 50, 34, 5, "navy"))
    s.append(box(96, 46, 34, 4, "navy"))
    s.append(rect(8, 56, 150, 3, cls("wood", 2)))
    for i in range(52, 158, 5):
        s.append(rect(i, 50, 1, 6, cls("o")))
    s.append(rect(52, 50, 106, 1, cls("o")))
    for i in range(9):
        s.append(box(10 + i * 4, 59 + i * 7, 10, 2, "wood"))
    s.append(box(8, 62, 150, 62, "floor"))
    for i in range(10):
        s.append(rect(54 + i * 10, 63, 3, 2, cls(["coral", "cyan", "amber"][i % 3])))
    s.append(box(50, 68, 70, 9, "violet"))
    s.append(text(85, 74.6, place(theme, "suite_banner"), 4.4, "sign", "middle"))
    s.append(box(56, 104, 40, 8, "navy"))
    s.append(box(56, 98, 40, 6, "navy"))
    s.append(box(100, 100, 14, 12, "black"))
    s.append(rect(102, 98, 10, 2, cls("cyan")))
    s.append(box(124, 92, 32, 22, "wood"))
    s.append(rect(136, 84, 2, 8, cls("grey", 0)))
    s.append(rect(132, 84, 10, 2, cls("grey")))
    s.append(box(166, 92, 50, 6, "wood"))
    s.append(rect(166, 84, 50, 1, cls("o")))
    spots = [(60, 84), (74, 84), (88, 86), (100, 30), (116, 30), (172, 74), (200, 74), (140, 70)]
    idle = [k for k in AGENT if world["agents"][k]["state"] == "Idle"]
    tips, rules = [], []
    for (x, y), k in zip(spots, idle):
        name, role, kw = AGENT[k]
        s.append(sprite_at(x, y, chibi(**{**kw, **ROBE}), f"{name}, idle", "idle", id_=f"suite-{k}"))
        tips.append(tip(f"suite-{k}", x + 7, y, [name, "Idle, relaxing"], width=W))
        rules.append(tip_rule(f"suite-{k}"))
    # The robe crew: the two hosts and three festival friends, badges on, always at the party.
    people = theme.get("people", {})
    crew = [(people[k]["name"], "In a robe", sp) for k, sp in theme.get("robes", {}).items() if k in people]
    crew += [("Festival friend", "In a robe", sp) for sp in theme.get("suite_friends", [])]
    for i, ((x, y), (who, line, sprite)) in enumerate(zip([(12, 104), (26, 106), (40, 104), (186, 74), (140, 98)], crew)):
        s.append(sprite_at(x, y, chibi(**sprite), f"{who}, in a robe (cameo)", "idle", id_=f"suite-crew-{i}"))
        tips.append(tip(f"suite-crew-{i}", x + 7, y, [who, line], width=W))
        rules.append(tip_rule(f"suite-crew-{i}"))
    if idle:
        s.append(bubble(123, 29, wrap(ambient(theme, 1), 16), "ambient"))
    s.extend(tips)
    s.append(f"<style>{''.join(rules)}</style></svg>")
    return "".join(s)


def avatar(kw, label):
    return (f'<svg class="px avatar avatar-s" viewBox="0 0 14 18" role="img" aria-label="{escape(label)}">'
            f'{chibi(**kw)}</svg>')


# ---- Regions: the parts of the page the browser refreshes ------------------------------------

def regions(jobs, settings, theme, project, demo=False):
    world = derive(jobs, settings, theme)
    st = world["stats"]
    who = "".join(
        f'<li data-agent="{k}"><span class="who-avatar">{avatar(kw, name)}</span><span><strong>{escape(name)}</strong>'
        f'<span class="state state-{escape(world["agents"][k]["state"].split()[0].lower())}">{escape(world["agents"][k]["state"])}</span>'
        f'<span class="where">{escape(place(theme, world["agents"][k]["zone"]))}, '
        + (open_job(world["agents"][k]["jobs"][0], escape(world["agents"][k]["why"])) if world["agents"][k]["jobs"]
           else escape(world["agents"][k]["why"]))
        + '</span></span></li>'
        for k, (name, role, kw) in AGENT.items())
    waiting = world["waiting"]
    names = [person_sprite(theme, p)[0] for p in world["approvers"]]
    host = theme.get("people", {}).get(theme.get("host", ""), {})
    host_first = host.get("name", "The host").split()[0]
    alert = (f'<a class="mini-alert" href="#beerfest"><strong>{escape(host_first)} needs you</strong>'
             f'<span>{len(waiting)} review{"s" if len(waiting) != 1 else ""} and a beer wait at the {escape(place(theme, "beerfest_sign"))}</span></a>'
             if waiting else "")
    side = (f'{alert}<h2 id="who-h">Who is where</h2><ol class="who">{who}</ol>'
            f'<h2 class="side-h2">Factory health</h2><dl class="health">'
            f'<div><dt>Merged</dt><dd class="num">{st["merged"]}</dd></div>'
            f'<div><dt>Rejected at intake</dt><dd class="num">{st["rejected"]}</dd></div>'
            f'<div><dt>Running</dt><dd class="num">{st["running"]}</dd></div>'
            f'<div><dt>Spent, API rates</dt><dd class="num">${st["cost"]:,.0f}</dd></div></dl>'
            f'<p class="note">{escape(project)}: {st["jobs"]} jobs{". Demo data, not a real project" if demo else ""}.</p>')

    def job_line(j):
        title = open_job(j, f'<strong>{escape(j["title"])}</strong>')
        return f'<li>{title} <span class="links">{job_links(j)}</span></li>'

    who_text = " and ".join(names) if names else "A person"
    bierfest = (
        f'<div class="alert-scene">{bierfest_scene(world, theme)}</div><div class="alert-body">'
        + (f'<h2 id="bf-h">{escape(host_first)} needs you: {len(waiting)} review{"s are" if len(waiting) != 1 else " is"} waiting at the {escape(place(theme, "beerfest_sign"))}</h2>'
           f'<p>{escape(who_text)}: these PRs wait for a person.</p><ul class="approvals">{"".join(job_line(j) for j in waiting)}</ul>'
           f'<p class="note">{escape(host.get("name", "The host"))}’s line is invented flavour text. The approver’s reasons are in each PR’s decision comment.</p>'
           if waiting else
           f'<h2 id="bf-h">Nobody needs you right now</h2><p>When the approver escalates a PR, it shows up here, and {escape(host_first)} calls the people who decide.</p>')
        + "</div>")
    popup = ""
    if waiting:
        ids = ",".join(j["id"] for j in waiting)
        popup = (f'<dialog class="popup" open aria-labelledby="pop-h" data-jobs="{escape(ids)}">{popup_scene(world, theme)}'
                 f'<div class="popup-body"><h2 id="pop-h">{escape(host_first)} needs you at the {escape(place(theme, "beerfest_sign"))}</h2>'
                 f'<p>{escape(theme.get("lines", {}).get("invite", ""))} {escape(who_text)}: {len(waiting)} PR{"s" if len(waiting) != 1 else ""} wait for a person.</p>'
                 f'<div class="actions"><a class="button primary" href="#beerfest">Come to the {escape(place(theme, "beerfest_sign"))}</a>'
                 f'<form method="dialog"><button class="button" type="submit">Later</button></form></div>'
                 f'<p class="hint">Later only closes this; nothing is approved or rejected. The host’s line is invented flavour.</p></div></dialog>')

    columns = [("Queued", ["intake", "needs-info"]), ("Spec and build", ["spec", "build"]),
               ("Checks and review", ["gate", "review", "approve", "merging"]),
               ("Waiting for a person", ["needs-human", "awaiting-approval"]), ("Done", ["merged"]), ("Rejected", ["rejected"])]
    def card(j):
        tone = " tone-human" if j["stage"] in ("needs-human", "awaiting-approval") else ""
        num = escape(j["id"].split("-")[0])
        risk = (j.get("intake") or {}).get("risk")
        meta = [num, escape(STAGE_LABEL.get(j["stage"], j["stage"]))]
        if j.get("round"):
            meta.append(f'round {j["round"]}')
        if risk:
            meta.append(f"{escape(str(risk))} risk")
        hint = ""
        if j["stage"] == "needs-human":
            first = f'Merge PR #{j["pr"]} to approve, or give' if j.get("pr") else "Give"
            hint = f'<span class="quest-hint">{first} feedback with /cloudfest:after-party</span>'
        elif j["stage"] == "awaiting-approval":
            hint = f'<span class="quest-hint">A person approves: party-job approve {num}, or merge the PR</span>'
        title = open_job(j, f'<span class="quest-title">{escape(j["title"])}</span>')
        return (f'<li class="quest{tone}">{title}<span class="quest-meta">{" · ".join(meta)}</span>'
                f'<span class="links">{job_links(j)}</span>{verdict_chips(j)}{hint}</li>')
    board = "".join(
        f'<section class="column" aria-label="{name}"><div class="column-head"><h3>{name}</h3>'
        f'<span class="count num">{sum(1 for j in jobs if j["stage"] in stages)}</span></div>'
        + (f'<ol>{"".join(card(j) for j in sorted((j for j in jobs if j["stage"] in stages), key=lambda j: j.get("ended") or j.get("started") or "", reverse=True)[:6])}</ol>'
           if any(j["stage"] in stages for j in jobs) else '<p class="empty">Nothing here.</p>')
        + "</section>" for name, stages in columns)
    quests = board if jobs else '<p class="empty">No quests yet. Label an issue <code>factory</code> and run <code>/cloudfest:after-party run</code>.</p>'

    events = xp.ledger(jobs, settings)
    standing = xp.standing(events, settings)

    def level_bar(k):
        st = standing[k]
        if st["next"]:
            fill = (st["xp"] - st["floor"]) / (st["next"] - st["floor"])
            label = f'{st["xp"]} XP, {st["next"] - st["xp"]} to {st["next_title"]}'
        else:
            fill, label = 1, f'{st["xp"]} XP, top level'
        return (f'<span class="crew-level">Level {st["level"]}, {escape(st["title"])}</span>'
                f'<span class="xp" role="meter" aria-valuemin="{st["floor"]}" aria-valuemax="{st["next"] or st["xp"]}" '
                f'aria-valuenow="{st["xp"]}" aria-label="{escape(label)}"><span style="--fill: {fill:.2f}"></span></span>'
                f'<span class="crew-xp num">{escape(label)}</span>')
    crew = "".join(
        f'<li class="crew-card"><svg class="px crew-svg" viewBox="0 0 14 18" role="img" aria-label="{escape(name)}">{chibi(**kw)}</svg>'
        f'<span class="crew-name">{escape(name)}</span><span class="crew-role">{escape(world["agents"][k]["state"])}</span>'
        f'{level_bar(k)}</li>'
        for k, (name, role, kw) in AGENT.items())
    ledger_rows = "".join(
        f'<tr><td>{escape((e["at"] or "")[:10])}</td><td>{escape(AGENT[e["agent"]][0])}</td><td>{escape(e["reason"])}</td>'
        f'<td class="num">+{e["xp"]}</td></tr>' for e in reversed(events[-8:]))
    ledger = (f'<table class="ledger"><caption>Latest XP, each from a merged job. Levels are cosmetic and grant no rights.</caption>'
              f'<thead><tr><th scope="col">Date</th><th scope="col">Agent</th><th scope="col">Verified event</th>'
              f'<th scope="col" class="num">XP</th></tr></thead><tbody>{ledger_rows}</tbody></table>' if events else
              '<p class="empty">No XP yet: agents earn it when a job they worked on is merged.</p>')
    people = "".join(
        f'<li class="crew-card host-card"><svg class="px crew-svg" viewBox="0 0 14 18" role="img" aria-label="{escape(p["name"])}">{chibi(**p["sprite"])}</svg>'
        f'<span class="crew-name">{escape(p["name"])}</span><span class="crew-role">{escape(p["role"])}</span></li>'
        for p in theme.get("people", {}).values())

    rows = "".join(
        f'<tr><td>{open_job(j, escape(j["id"]))}</td><td>{escape(j["title"])}</td>'
        f'<td>{escape(STAGE_LABEL.get(j["stage"], j["stage"]))}</td><td class="num">{j["round"]}</td>'
        f'<td class="num">{ext_link(j.get("pr_url"), "#" + str(j["pr"])) if j.get("pr") else "none"}</td>'
        f'<td class="num">{ext_link(j.get("issue_url"), "#" + str(j["issue"]))}</td>'
        f'<td class="num">${(j.get("cost_usd") or 0):.2f}</td></tr>'
        for j in sorted(jobs, key=lambda j: j["id"], reverse=True)[:12])
    ops = (f'<table class="ops"><thead><tr><th scope="col">Job</th><th scope="col">Title</th><th scope="col">Stage</th>'
           f'<th scope="col" class="num">Round</th><th scope="col" class="num">PR</th><th scope="col" class="num">Issue</th><th scope="col" class="num">Cost</th></tr></thead>'
           f'<tbody>{rows}</tbody></table>' if jobs else '<p class="empty">No jobs yet.</p>')
    return {
        "r-world": world_map(world, theme, project),
        "r-side": side,
        "r-stage": stage_scene(world, theme),
        "r-bierfest": bierfest,
        "r-quests": quests,
        "r-crew": (f'<ul class="crew">{crew}</ul>'
                   + (f'<h3 class="hosts-h">The people</h3><ul class="crew hosts">{people}</ul>' if people else "")
                   + ledger),
        "r-suite": suite_scene(world, theme),
        "r-ops": ops,
        "r-popup": popup,
        "r-count": str(len(waiting)) if waiting else "",
    }


# ---- The job panel: one job's status, links and files ---------------------------------

DRAWER_HTML = """<dialog class="drawer" id="job-drawer" aria-labelledby="d-title">
  <div class="d-head">
    <p class="d-num" id="d-num"></p>
    <h2 id="d-title"></h2>
    <p class="links" id="d-links"></p>
    <form method="dialog"><button class="d-close" type="submit" aria-label="Close">×</button></form>
  </div>
  <div class="d-body">
    <nav class="d-files" id="d-files" aria-label="The job's files"></nav>
    <article class="d-doc"><div class="md" id="d-doc"></div></article>
  </div>
</dialog>"""

# Reads the same /jobs/ files the factory writes: job.json for the header, the folder
# listing for the files, each file's first line for its verdict colour. Agent-written
# markdown is escaped before anything is rendered; links keep only https and relative URLs.
DRAWER_JS = r"""
const drawer = document.getElementById('job-drawer')
const $d = id => document.getElementById(id)
const escH = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
const STAGE = { intake: 'Intake', 'needs-info': 'Asked the author', spec: 'Spec', build: 'Build', gate: 'Gate', review: 'Review', approve: 'Approve', merging: 'Merging', 'needs-human': 'Your call', 'awaiting-approval': 'Awaiting approval', merged: 'Merged', rejected: 'Rejected' }
let openId = null, openPath = null, openText
const firstLines = new Map()
const getText = async url => { const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.text() }
const safe = u => /^https:\/\//.test(u || '') ? u : null
const ext = (u, label) => safe(u) ? `<a href="${escH(u)}" target="_blank" rel="noopener noreferrer">${escH(label)}</a>` : `<span>${escH(label)}</span>`
async function listFiles(dir) {
  const doc = new DOMParser().parseFromString(await getText(dir), 'text/html')
  const out = []
  for (const a of doc.querySelectorAll('a')) {
    const h = decodeURIComponent(a.getAttribute('href'))
    if (h.endsWith('/')) out.push(...(await listFiles(dir + h)).map(f => h + f))
    else if (h.endsWith('.md')) out.push(h)
  }
  return out
}
const ORDER = ['issue.md', 'intake.md', 'spec.md', 'build.md', 'decision.md', 'rejection.md']
const ROUND_ORDER = ['checks', 'review-code', 'review-security', 'review-ux', 'review-ui', 'merge-checks']
function rank(f) {
  if (ORDER.includes(f)) return [0, ORDER.indexOf(f), f]
  const m = f.match(/^round-(\d+)\/(.+)\.md$/)
  if (m) return [2, Number(m[1]) * 10 + ROUND_ORDER.indexOf(m[2]), f]
  return [1, 0, f]
}
const sortFiles = fs => fs.sort((a, b) => { const [x, y] = [rank(a), rank(b)]; return x[0] - y[0] || x[1] - y[1] || x[2].localeCompare(y[2]) })
function tone(first) {
  if (/^(VERDICT:\s*PASS|GATE:\s*PASS|APPROVE|STATUS:\s*READY|DECISION:\s*ACCEPT)$/.test(first)) return 'good'
  if (/^(VERDICT:\s*CHANGES|DECISION:\s*NEEDS-INFO)$/.test(first)) return 'warn'
  if (/^(ESCALATE|REJECTED|STATUS:\s*BLOCKED|GATE:\s*FAIL|DECISION:\s*REJECT)$/.test(first)) return 'stop'
  return ''
}
function inline(s) {
  const codes = []
  s = escH(s).replace(/`([^`]+)`/g, (_, c) => `\u0000${codes.push(c) - 1}\u0000`)
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\(((?:https:\/\/|\.{0,2}\/|#)[^)\s]*)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[i]}</code>`)
}
function splitSummary(lines) {
  const start = lines.findIndex(l => /^##\s+Summary\s*$/.test(l))
  if (start === -1) return { lines, summary: null }
  let end = start + 1
  while (end < lines.length && !/^#{1,2}\s/.test(lines[end])) end++
  return { lines: [...lines.slice(0, start), ...lines.slice(end)], summary: lines.slice(start + 1, end).join('\n') }
}
function markdown(src) {
  const split = splitSummary(src.replace(/\r/g, '').split('\n'))
  const lines = split.lines
  let i = 0, html = ''
  const first = (lines[0] || '').trim(), t = tone(first)
  if (t) {
    html += `<div class="verdict ${t}">${escH(first)}</div>`
    i = 1
    const extra = []
    while (i < lines.length && /^[A-Z-]+:\s/.test(lines[i])) extra.push(lines[i++])
    if (extra.length) html += `<pre class="head">${escH(extra.join('\n'))}</pre>`
  }
  if (split.summary !== null) html += `<section class="summary"><h3>Summary</h3>${markdown(split.summary)}</section>`
  const isList = l => /^\s*([-*+]|\d+\.)\s+/.test(l)
  const isBlock = l => /^(#{1,6}\s|```|\s*>|\|)/.test(l) || isList(l)
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (line.startsWith('```')) {
      const body = []; i++
      while (i < lines.length && !lines[i].startsWith('```')) body.push(lines[i++])
      i++; html += `<pre><code>${escH(body.join('\n'))}</code></pre>`; continue
    }
    const h = line.match(/^(#{1,6})\s+(.*)$/)
    if (h) { const n = Math.min(h[1].length + 1, 5); html += `<h${n}>${inline(h[2])}</h${n}>`; i++; continue }
    if (/^\s*>/.test(line)) {
      const body = []
      while (i < lines.length && /^\s*>/.test(lines[i])) body.push(lines[i++].replace(/^\s*>\s?/, ''))
      html += `<blockquote>${markdown(body.join('\n'))}</blockquote>`; continue
    }
    if (line.startsWith('|')) {
      const rows = []
      while (i < lines.length && lines[i].startsWith('|')) rows.push(lines[i++])
      const cells = r => r.replace(/^\||\|$/g, '').split('|').map(c => inline(c.trim()))
      const body = rows.filter(r => !/^\|[\s:|-]+\|$/.test(r))
      html += '<table>' + body.map((r, n) => `<tr>${cells(r).map(c => n ? `<td>${c}</td>` : `<th>${c}</th>`).join('')}</tr>`).join('') + '</table>'
      continue
    }
    if (isList(line)) {
      const ordered = /^\s*\d+\./.test(line), items = []
      while (i < lines.length && (isList(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && items.length))) {
        const l = lines[i++]
        if (isList(l)) items.push({ indent: l.match(/^\s*/)[0].length, text: l.replace(/^\s*([-*+]|\d+\.)\s+/, '') })
        else items[items.length - 1].text += ' ' + l.trim()
      }
      const lis = items.map(({ indent, text }) => `<li${indent ? ` style="margin-left:${indent * 0.6}em"` : ''}>${inline(text)}</li>`).join('')
      html += ordered ? `<ol>${lis}</ol>` : `<ul>${lis}</ul>`; continue
    }
    const para = []
    while (i < lines.length && lines[i].trim() && !isBlock(lines[i])) para.push(lines[i++])
    html += `<p>${inline(para.join(' '))}</p>`
  }
  return html
}
async function refreshDrawer() {
  if (!openId) return
  const base = `jobs/${encodeURIComponent(openId)}/`
  let job
  try { job = JSON.parse(await getText(base + 'job.json')) } catch (e) {
    $d('d-num').textContent = openId; $d('d-title').textContent = 'No job files here'
    $d('d-links').innerHTML = ''; $d('d-files').innerHTML = ''
    $d('d-doc').innerHTML = '<p class="note">This view has no job files (demo mode, or the job was removed).</p>'
    return
  }
  const cost = Number(job.cost_usd || 0).toFixed(2)
  $d('d-num').textContent = `${job.id} · ${STAGE[job.stage] || job.stage}${job.round ? ` · round ${job.round}` : ''} · $${cost}`
  $d('d-title').textContent = job.title
  $d('d-links').innerHTML = ext(job.issue_url, `issue #${job.issue}`) + (job.pr ? ext(job.pr_url, `PR #${job.pr}`) : '')
  const files = sortFiles(await listFiles(base))
  if (!openPath || !files.includes(openPath)) openPath = files.includes('decision.md') ? 'decision.md' : files.includes('build.md') ? 'build.md' : files[0] || null
  let text = null
  if (openPath) { text = await getText(base + openPath); firstLines.set(base + openPath, text.split('\n')[0].trim()) }
  await Promise.all(files.filter(f => !firstLines.has(base + f)).map(async f => firstLines.set(base + f, (await getText(base + f)).split('\n')[0].trim())))
  let group = null
  $d('d-files').innerHTML = files.map(f => {
    const g = f.includes('/') ? f.split('/')[0].replace('round-', 'Round ') : 'Job'
    const head = g !== group ? `<p class="group">${escH(g)}</p>` : ''
    group = g
    const name = f.includes('/') ? f.split('/')[1].replace(/^review-|\.md$/g, '') : f.replace(/\.md$/, '')
    return `${head}<button type="button" class="file${f === openPath ? ' on' : ''}" data-file="${escH(f)}"><span class="v ${tone(firstLines.get(base + f) || '')}"></span>${escH(name)}</button>`
  }).join('') || '<p class="note">No files yet.</p>'
  if (text !== openText) { openText = text; $d('d-doc').innerHTML = text === null ? '<p class="note">Intake hasn’t written anything yet.</p>' : markdown(text) }
}
async function openDrawer(id) {
  openId = id; openPath = null; openText = undefined
  if (!drawer.open) drawer.showModal()
  try { await refreshDrawer() } catch (e) { $d('d-doc').innerHTML = `<p class="note">${escH(e.message)}</p>` }
}
drawer.addEventListener('close', () => { openId = null; if (/^#job=/.test(location.hash)) history.replaceState(null, '', location.pathname) })
drawer.addEventListener('click', e => { if (e.target === drawer) drawer.close() })
document.addEventListener('click', e => {
  const file = e.target.closest('[data-file]')
  if (file) { openPath = file.dataset.file; openText = undefined; $d('d-doc').parentElement.scrollTop = 0; refreshDrawer(); return }
  const link = e.target.closest('[data-job]')
  if (link) { e.preventDefault(); openDrawer(link.dataset.job) }
})
const fromHash = () => {
  const m = location.hash.match(/^#job=(.+)$/)
  if (m) openDrawer(decodeURIComponent(m[1]))
  else if (drawer.open) drawer.close()  // switching views closes the job
}
addEventListener('hashchange', fromHash); fromHash()
setInterval(() => { if (openId) refreshDrawer().catch(() => {}) }, 4000)
"""


def page(jobs, settings, theme, project, demo=False, refresh_ms=3000):
    r = regions(jobs, settings, theme, project, demo)
    css = CSS_FILE.read_text().replace("/*PX_TOKENS*/", css_tokens())
    product = escape(theme.get("product", "AI Software Factory"))
    flag = '<p class="mock-flag">Demo</p>' if demo else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{product}</title>
<link rel="icon" href="data:,">
<meta name="description" content="The factory's agents on a festival map, placed by the real state of their jobs.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Jersey+10&display=swap" rel="stylesheet">
<style>
{css}
{css_classes()}
</style>
</head>
<body>
<header class="bar">
  <div class="container bar-inner">
    <a class="brand" href="#world">{logo(theme, "brand-logo")}<span class="brand-name">AI Software Factory</span></a>
    <nav aria-label="Views">
      <a href="#world" aria-current="page">Festival</a>
      <a href="#stage">Main stage</a>
      <a href="#beerfest">{escape(place(theme, "beerfest_sign"))} <span class="tab-count num" id="r-count">{r["r-count"]}</span></a>
      <a href="#quests">Quests</a>
      <a href="#crew">Crew</a>
      <a href="#suite">Suite</a>
      <a href="#ops">Operations</a>
    </nav>
    {flag}
  </div>
</header>
<main>
<section id="world" class="view world-band" aria-labelledby="world-h">
  <div class="container world-grid">
    <div class="map-col">
      <div class="map-head">
        <div>
          <h1 id="world-h">{product}</h1>
          <p class="lede">{escape(project)}. Every agent stands where its job really is.</p>
        </div>
        <label class="toggle"><input type="checkbox" id="bubbles" checked> Speech bubbles</label>
      </div>
      <div id="r-world">{r["r-world"]}</div>
      <p class="legend"><span class="key key-task" aria-hidden="true"></span>White bubbles report real state <span class="key key-ambient" aria-hidden="true"></span>Tinted ones are ambient flavour <span class="stale" id="stale" hidden>Can’t reach the factory’s state; showing the last view.</span></p>
    </div>
    <aside class="side" id="r-side" aria-labelledby="who-h">{r["r-side"]}</aside>
  </div>
</section>
<section id="stage" class="view stage-band" aria-labelledby="st-h"><div class="container stage-view">
  <div class="stage-copy"><h2 id="st-h">Main stage</h2><p>The factory’s own numbers, and its latest merge.</p></div>
  <div id="r-stage">{r["r-stage"]}</div>
</div></section>
<section id="beerfest" class="view alert-band" aria-labelledby="bf-h"><div class="container alert" id="r-bierfest">{r["r-bierfest"]}</div></section>
<section id="quests" class="view" aria-labelledby="q-h"><div class="container block">
  <div class="block-head"><h2 id="q-h">Quests</h2><p>Every job in the factory, by stage. Done means the checks, reviews and merge happened.</p></div>
  <div class="board" id="r-quests">{r["r-quests"]}</div>
</div></section>
<section id="crew" class="view" aria-labelledby="c-h"><div class="container block">
  <div class="block-head"><h2 id="c-h">The crew</h2><p>One agent per job in the pipeline, and the people around them.</p></div>
  <div id="r-crew">{r["r-crew"]}</div>
</div></section>
<section id="suite" class="view" aria-labelledby="s-h"><div class="container block">
  <div class="suite-card"><div class="suite-copy"><h2 id="s-h">{escape(place(theme, "suite_long"))}</h2>
  <p>Only agents with nothing to do come up here. Busy, blocked or waiting agents never do.</p></div>
  <div id="r-suite">{r["r-suite"]}</div></div>
</div></section>
<section id="ops" class="view" aria-labelledby="o-h"><div class="container block">
  <div class="block-head"><h2 id="o-h">Operations</h2><p>The same factory without the festival: the latest jobs.</p></div>
  <div class="table-wrap" id="r-ops">{r["r-ops"]}</div>
</div></section>
</main>
<div id="r-popup">{r["r-popup"]}</div>
{DRAWER_HTML}
<script>{DRAWER_JS}
  const tabs = document.querySelectorAll('.bar nav a')
  const mark = () => tabs.forEach(a => a.toggleAttribute('aria-current', a.hash === (location.hash || '#world')))
  addEventListener('hashchange', mark); mark()
  const seen = key => {{ try {{ return localStorage.getItem('party-dismissed') === key }} catch {{ return false }} }}
  const wirePopup = () => {{
    const d = document.querySelector('#r-popup dialog')
    if (!d) return
    if (seen(d.dataset.jobs)) d.close()
    d.addEventListener('close', () => {{ try {{ localStorage.setItem('party-dismissed', d.dataset.jobs) }} catch {{}} }})
  }}
  wirePopup()
  const refresh = async () => {{
    try {{
      const res = await fetch('live', {{ cache: 'no-store' }})
      if (!res.ok) throw new Error(res.status)
      const data = await res.json()
      for (const [id, html] of Object.entries(data)) {{
        const el = document.getElementById(id)
        if (el && el.innerHTML !== html) {{ el.innerHTML = html; if (id === 'r-popup') wirePopup() }}
      }}
      document.getElementById('stale').hidden = true
    }} catch {{ document.getElementById('stale').hidden = false }}
  }}
  setInterval(refresh, {refresh_ms})
</script>
</body>
</html>
"""


# ---- Demo mode: clearly labelled sample data ----------------------------------------------------

def demo_jobs():
    def j(i, issue, title, stage, rnd=1, pr=None, reviews=None, cost=0.0):
        return {"id": f"{i:03d}-demo", "issue": issue, "title": title, "stage": stage, "round": rnd,
                "pr": pr, "pr_url": f"https://example.com/pr/{pr}" if pr else None,
                "reviews": reviews or {}, "cost_usd": cost, "started": f"2026-11-0{1 + i % 8}T10:00:00Z",
                "ended": f"2026-11-0{1 + i % 8}T12:00:00Z" if stage in ("merged", "rejected") else None}
    done = [j(i, 100 + i, f"Demo feature {i}", "merged", pr=200 + i, cost=4.2) for i in range(1, 13)]
    return done + [
        j(13, 113, "Demo: add a dark mode switch", "rejected"),
        j(14, 114, "Demo: show the logo on print pages", "spec", cost=0.4),
        j(15, 115, "Demo: bookings day list", "build", cost=1.8),
        j(16, 116, "Demo: group bookings", "review", pr=216, reviews={"code": "PASS", "ui": "pending", "ux": "pending"}, cost=3.1),
        j(17, 117, "Demo: a new public booking email", "needs-human", pr=217, cost=5.0),
        j(18, 118, "Demo: change plan limits", "needs-human", pr=218, cost=4.4),
        j(19, 119, "Demo: which page did you mean?", "needs-info"),
    ]
