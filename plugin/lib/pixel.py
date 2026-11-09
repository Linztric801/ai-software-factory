"""Pixel art for the factory's world: palette, primitives, anime chibi characters.

Everything is inline SVG with classes, so every colour stays a CSS token and the
art is crisp at any size. Shared by the dashboard scenes in world.py.
"""

from html import escape

PX = {
    "o": ["oklch(21% 0.03 275)"] * 3,                          # outline
    "skin": ["oklch(88% 0.05 65)", "oklch(80% 0.07 60)", "oklch(68% 0.08 50)"],
    "skin2": ["oklch(72% 0.07 55)", "oklch(62% 0.08 50)", "oklch(50% 0.07 45)"],
    "silver": ["oklch(93% 0.01 250)", "oklch(83% 0.015 250)", "oklch(68% 0.02 255)"],
    "pink": ["oklch(82% 0.1 355)", "oklch(72% 0.14 355)", "oklch(58% 0.14 355)"],
    "yellow": ["oklch(92% 0.13 95)", "oklch(85% 0.15 90)", "oklch(72% 0.14 80)"],
    "lav": ["oklch(84% 0.07 300)", "oklch(74% 0.1 300)", "oklch(60% 0.11 300)"],
    "brown": ["oklch(58% 0.07 55)", "oklch(48% 0.07 50)", "oklch(38% 0.06 45)"],
    "black": ["oklch(40% 0.02 270)", "oklch(30% 0.02 270)", "oklch(24% 0.02 270)"],
    "coral": ["oklch(72% 0.16 28)", "oklch(63% 0.19 26)", "oklch(52% 0.18 25)"],
    "cyan": ["oklch(88% 0.12 215)", "oklch(81% 0.14 220)", "oklch(66% 0.13 225)"],
    "navy": ["oklch(46% 0.08 260)", "oklch(37% 0.08 262)", "oklch(29% 0.07 265)"],
    "green": ["oklch(70% 0.14 150)", "oklch(60% 0.14 152)", "oklch(48% 0.12 155)"],
    "white": ["oklch(98% 0.005 240)", "oklch(92% 0.01 240)", "oklch(80% 0.015 245)"],
    "grey": ["oklch(72% 0.01 250)", "oklch(60% 0.01 250)", "oklch(48% 0.015 255)"],
    "robe": ["oklch(92% 0.03 85)", "oklch(85% 0.04 80)", "oklch(73% 0.05 75)"],
    "violet": ["oklch(68% 0.19 285)", "oklch(55% 0.25 285)", "oklch(43% 0.22 285)"],
    "pinkb": ["oklch(72% 0.15 5)", "oklch(62% 0.19 5)", "oklch(50% 0.17 5)"],
    "blond": ["oklch(86% 0.08 82)", "oklch(77% 0.09 76)", "oklch(64% 0.09 70)"],
    "led": ["oklch(72% 0.13 245)", "oklch(58% 0.17 255)", "oklch(44% 0.16 262)"],
    "blue": ["oklch(64% 0.14 250)", "oklch(54% 0.16 255)", "oklch(44% 0.15 258)"],
    "tan": ["oklch(80% 0.07 75)", "oklch(72% 0.08 70)", "oklch(60% 0.08 65)"],
    "amber": ["oklch(92% 0.11 85)", "oklch(84% 0.14 80)", "oklch(72% 0.14 70)"],
    "grass": ["oklch(36% 0.05 160)", "oklch(31% 0.05 160)", "oklch(27% 0.045 162)"],
    "path": ["oklch(66% 0.04 75)", "oklch(58% 0.045 72)", "oklch(49% 0.045 68)"],
    "wall": ["oklch(48% 0.03 260)", "oklch(40% 0.03 262)", "oklch(33% 0.03 265)"],
    "floor": ["oklch(56% 0.03 70)", "oklch(48% 0.035 65)", "oklch(40% 0.035 60)"],
    "sky": ["oklch(30% 0.06 268)", "oklch(25% 0.055 270)", "oklch(21% 0.05 272)"],
    "glass": ["oklch(78% 0.08 220)", "oklch(66% 0.08 225)", "oklch(52% 0.07 230)"],
    "beer": ["oklch(90% 0.13 90)", "oklch(82% 0.15 80)", "oklch(70% 0.15 70)"],
    "foam": ["oklch(99% 0.005 90)", "oklch(95% 0.01 90)", "oklch(86% 0.02 85)"],
    "wood": ["oklch(60% 0.08 60)", "oklch(51% 0.08 55)", "oklch(42% 0.07 50)"],
}
TONES = ("l", "", "d")


def css_tokens():
    lines = []
    for name, tones in PX.items():
        for suffix, value in zip(TONES, tones):
            lines.append(f"--px-{name}{'-' + suffix if suffix else ''}: {value};")
    return "\n  ".join(lines)


def css_classes():
    out = []
    for name in PX:
        for suffix in TONES:
            key = f"{name}{'-' + suffix if suffix else ''}"
            out.append(f".k-{key}{{fill:var(--px-{key})}}")
    return "".join(out)


def cls(name, tone=1):
    return f"k-{name}{'' if tone == 1 else '-' + TONES[tone]}"


# ---- Drawing primitives (SVG user units = pixels) --------------------------

def rect(x, y, w, h, c, r=0):
    rx = f' rx="{r}"' if r else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}"{rx} class="{c}"/>'


def box(x, y, w, h, name, outline=True):
    """A flat rounded block with a soft drop shadow and a lighter top band."""
    r = round(min(1.6, w / 4, h / 4), 2)
    s = []
    if outline:
        s.append(f'<rect x="{x}" y="{y + 0.7}" width="{w}" height="{h}" rx="{r}" class="{cls("o")}" opacity=".22"/>')
    s.append(rect(x, y, w, h, cls(name), r))
    if h >= 4:
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{round(min(2, h * .3), 2)}" rx="{r}" class="{cls(name, 0)}" opacity=".55"/>')
    return "".join(s)


def cloud(x, y):
    """A white cloud-shaped lamp, as hung over the Cloud Fair."""
    return (f'<g class="{cls("white")}"><circle cx="{x + 3.5}" cy="{y + 1.6}" r="2.2"/><circle cx="{x + 6.5}" cy="{y + .8}" r="2.8"/>'
            f'<circle cx="{x + 9.3}" cy="{y + 1.9}" r="2"/><rect x="{x + 1.3}" y="{y + 1.6}" width="10" height="2.4" rx="1.2"/></g>')


def text(x, y, s, size=5, c="sign", anchor="start"):
    if any(ch.isdigit() for ch in s):
        c += " digits"
    size = round(size * 0.92, 2)
    return (f'<text x="{x}" y="{y}" class="{c}" font-size="{size}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


# ---- Figures: flat vector people in a 14x18 box, shaded with tones, no outlines -----


def fill(name, tone=1):
    return f'class="{cls(name, tone)}"'


def stroke(name, width, tone=1):
    var = f"--px-{name}{'' if tone == 1 else '-' + TONES[tone]}"
    return f'fill="none" style="stroke:var({var})" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"'


def acc_colour(acc):
    return {"cap": "blue", "cowboy": "tan", "hardhat": "yellow", "headset": "black", "headband": "black"}.get(acc, "grey")


HAIR_TOP = "M3.65 5.9C3.1 1.2 10.9 1.2 10.35 5.9C10.1 4.6 9.6 3.8 9.1 3.55C8.2 4.05 6.2 4.1 5.1 3.45C4.5 3.8 3.95 4.6 3.65 5.9Z"


def chibi(hair, top, legs="navy", skin="skin", style="short", acc=None, pose="front", eyes="navy", shirt=False, beard=False,
          lanyard=None):
    """One person, drawn as smooth flat shapes: same name and box as the old pixel sprite,
    so every scene and the avatars use it unchanged."""
    accs = set(acc if isinstance(acc, tuple) else (acc,))
    bald = hair == "skin"
    robe = top == "robe"
    back = pose == "back"
    s = ['<g class="fig">', f'<ellipse cx="7" cy="17.55" rx="3.9" ry="0.55" {fill("o")} opacity=".22"/>']

    # Hair that falls behind the head and shoulders
    if not bald and style in ("long", "bob", "twin"):
        low = {"long": 11.4, "bob": 8.2, "twin": 9.6}[style]
        s.append(f'<path d="M3.5 4.6C3.5 1.6 10.5 1.6 10.5 4.6V{low}Q10.5 {low + .5} 10 {low + .5}H4Q3.5 {low + .5} 3.5 {low}Z" {fill(hair, 2)}/>')
        if style == "twin":
            s.append(f'<ellipse cx="2.6" cy="7.8" rx="1.1" ry="2.2" {fill(hair, 2)}/><ellipse cx="11.4" cy="7.8" rx="1.1" ry="2.2" {fill(hair, 2)}/>')

    # Legs and shoes
    s.append(f'<rect x="4.9" y="12.4" width="1.9" height="4.9" rx=".8" {fill(legs, 2 if robe else 1)}/>')
    s.append(f'<rect x="7.2" y="12.4" width="1.9" height="4.9" rx=".8" {fill(legs)}/>')
    if robe:  # bare shins under the robe
        s.append(f'<rect x="5.15" y="15" width="1.45" height="1.9" rx=".6" {fill(skin)}/><rect x="7.4" y="15" width="1.45" height="1.9" rx=".6" {fill(skin)}/>')
    s.append(f'<ellipse cx="5.7" cy="17.25" rx="1.2" ry=".5" {fill("black", 2)}/><ellipse cx="8.3" cy="17.25" rx="1.2" ry=".5" {fill("black", 2)}/>')

    # Arms (a raised one for a wave or a peace sign), then the torso over them
    left_up, right_up = "wave" in accs, "peace" in accs
    sleeve = top
    if left_up:
        s.append(f'<path d="M3.6 9.4L1.9 5.6" {stroke(sleeve, 1.45)}/><circle cx="1.75" cy="5.1" r=".72" {fill(skin)}/>')
    else:
        s.append(f'<path d="M3.7 9.3L3.1 12.6" {stroke(sleeve, 1.5)}/><circle cx="3.05" cy="13.15" r=".68" {fill(skin)}/>')
    if right_up:
        s.append(f'<path d="M10.4 9.4L12.1 5.9" {stroke(sleeve, 1.45)}/><circle cx="12.25" cy="5.4" r=".72" {fill(skin)}/>'
                 f'<path d="M12 4.8L11.85 3.9M12.55 4.8L12.75 3.95" {stroke(skin, .35)}/>')
    else:
        s.append(f'<path d="M10.3 9.3L10.9 12.6" {stroke(sleeve, 1.5)}/><circle cx="10.95" cy="13.15" r=".68" {fill(skin)}/>')
    hem = 15.2 if robe else 13.1
    s.append(f'<path d="M4.6 8.55Q7 7.95 9.4 8.55Q10.6 8.9 10.5 10.2L10.1 {hem}H3.9L3.5 10.2Q3.4 8.9 4.6 8.55Z" {fill(top)}/>')
    s.append(f'<path d="M7 8.3V{hem}" {stroke(top, .25, 2)} opacity=".5"/>' if not robe else "")
    if robe:  # waffle robe: lapels over a tee, a tied belt, texture dots
        under = shirt if isinstance(shirt, str) else "black"
        s.append(f'<path d="M5.7 8.35L7 11L8.3 8.35Z" {fill(under)}/>')
        s.append(f'<path d="M5.5 8.4L7 11.3L6.4 12.2L4.7 8.8Z" {fill(top, 0)}/><path d="M8.5 8.4L7 11.3L7.6 12.2L9.3 8.8Z" {fill(top, 0)}/>')
        s.append(f'<rect x="3.75" y="12.1" width="6.5" height=".55" rx=".25" {fill(top, 2)}/>')
        dots = "".join(f'<circle cx="{x}" cy="{y}" r=".12"/>' for y in (13.2, 14.2) for x in (4.6, 5.8, 8.2, 9.4))
        s.append(f'<g {fill(top, 2)} opacity=".55">{dots}</g>')
    elif shirt and not back:  # a shirt or tee showing in the opening
        colour = shirt if isinstance(shirt, str) else "white"
        s.append(f'<path d="M6 8.35L7 10.3L8 8.35Z" {fill(colour)}/>')
    if lanyard and not back:  # lanyard and the red-topped festival badge
        s.append(f'<path d="M5.95 8.5L6.55 11.2M8.05 8.5L7.45 11.2" {stroke(lanyard, .32)}/>')
        s.append(f'<rect x="5.95" y="11" width="2.1" height="2.25" rx=".3" {fill("white")}/>'
                 f'<rect x="5.95" y="11" width="2.1" height=".7" rx=".3" {fill("pinkb")}/>'
                 f'<rect x="6.35" y="12.1" width="1.3" height=".22" {fill("grey")}/>')

    # Neck and head
    s.append(f'<rect x="6.25" y="7.2" width="1.5" height="1.5" rx=".5" {fill(skin, 2)}/>')
    s.append(f'<ellipse cx="3.85" cy="5.3" rx=".55" ry=".75" {fill(skin, 2)}/><ellipse cx="10.15" cy="5.3" rx=".55" ry=".75" {fill(skin, 2)}/>')
    s.append(f'<ellipse cx="7" cy="4.9" rx="3.15" ry="3.25" {fill(skin)}/>')
    if back:
        s.append(f'<ellipse cx="7" cy="4.7" rx="3.25" ry="3.25" {fill(hair if not bald else skin)}/>')
    else:
        if beard:
            s.append(f'<path d="M3.9 5.1C3.9 8.9 10.1 8.9 10.1 5.1C9.6 6.7 8.4 7.2 7 7.2C5.6 7.2 4.4 6.7 3.9 5.1Z" {fill(hair, 2)}/>')
        side = -0.7 if pose == "side" else 0
        for ex in ((5.75 + side,) if pose == "side" else (5.75, 8.25)):
            s.append(f'<ellipse cx="{ex}" cy="5.25" rx=".42" ry=".52" {fill(eyes, 2)}/><circle cx="{ex + .14}" cy="5.07" r=".14" {fill("white", 0)}/>')
        brow = hair if not bald else "brown"
        s.append(f'<path d="M5.15 4.25Q5.75 3.95 6.35 4.2M7.65 4.2Q8.25 3.95 8.85 4.25" {stroke(brow, .28, 2)}/>')
        s.append(f'<ellipse cx="4.85" cy="6.2" rx=".55" ry=".3" {fill("pink")} opacity=".45"/><ellipse cx="9.15" cy="6.2" rx=".55" ry=".3" {fill("pink")} opacity=".45"/>')
        s.append(f'<path d="M6.25 6.55Q7 7.15 7.75 6.55" {stroke("coral", .3, 2)}/>')

    # Hair on top
    if not bald and not back:
        if style == "spiky":
            s.append(f'<path d="M3.7 5.2C3.3 2.4 4.2 1.9 4.6 1.2L5.4 2.1L6.2 0.9L7.1 2L8 0.9L8.8 2.1L9.6 1.2C10 1.9 10.7 2.4 10.3 5.2C9.6 3.6 8.4 3.2 7 3.2C5.6 3.2 4.4 3.6 3.7 5.2Z" {fill(hair)}/>')
        elif style == "curly":
            bumps = "".join(f'<circle cx="{x}" cy="{y}" r="1.05"/>' for x, y in ((4.3, 3.6), (5.4, 2.3), (7, 1.85), (8.6, 2.3), (9.7, 3.6), (3.9, 5), (10.1, 5)))
            s.append(f'<g {fill(hair)}>{bumps}</g>')
        else:
            s.append(f'<path d="{HAIR_TOP}" {fill(hair)}/>')
        s.append(f'<path d="M5.2 2.4Q7 1.7 8.8 2.4" {stroke(hair, .35, 0)} opacity=".6"/>')
    elif bald and not back:
        s.append(f'<ellipse cx="6" cy="2.6" rx="1.2" ry=".5" {fill(skin, 0)} opacity=".8"/>')

    # Headwear and eyewear
    a = acc_colour(next((x for x in accs if x in ("cap", "cowboy", "hardhat", "headset", "headband")), None))
    if "headband" in accs:
        s.append(f'<rect x="3.75" y="3.35" width="6.5" height=".85" rx=".4" {fill(a, 2)}/>')
    if "headshades" in accs or "goggles" in accs:
        c = "cyan" if "goggles" in accs else "black"
        s.append(f'<rect x="4.4" y="2.05" width="2.2" height="1.1" rx=".5" {fill(c, 2)}/><rect x="7.4" y="2.05" width="2.2" height="1.1" rx=".5" {fill(c, 2)}/>'
                 f'<path d="M6.6 2.5H7.4" {stroke("black", .3, 2)}/>')
    if "cap" in accs:
        s.append(f'<path d="M3.6 4.1C3.6 0.9 10.4 0.9 10.4 4.1Z" {fill(a)}/><path d="M3.4 4.15H1.2Q1.6 3.35 3.6 3.55Z" {fill(a, 2)}/>'
                 f'<rect x="3.5" y="3.75" width="7" height=".55" rx=".25" {fill(a, 2)}/><circle cx="7" cy="1.25" r=".35" {fill(a, 2)}/>')
    if "hardhat" in accs:
        s.append(f'<path d="M3.8 3.9C3.8 0.8 10.2 0.8 10.2 3.9Z" {fill(a)}/><rect x="2.9" y="3.6" width="8.2" height=".7" rx=".35" {fill(a, 2)}/>'
                 f'<rect x="6.6" y="1.1" width=".8" height="2.6" rx=".3" {fill(a, 0)}/>')
    if "cowboy" in accs:
        s.append(f'<ellipse cx="7" cy="3.6" rx="5.2" ry=".85" {fill(a, 2)}/><path d="M4.6 3.6C4.6 .6 9.4 .6 9.4 3.6Z" {fill(a)}/>')
    if "headset" in accs:
        s.append(f'<path d="M3.7 5C3.7 .9 10.3 .9 10.3 5" {stroke(a, .45)}/><rect x="3.15" y="4.4" width="1.1" height="1.9" rx=".5" {fill(a, 2)}/>'
                 f'<rect x="9.75" y="4.4" width="1.1" height="1.9" rx=".5" {fill(a, 2)}/><path d="M4 6.2Q4.6 7.5 6.1 7.2" {stroke(a, .3)}/>')
    if not back and "shades" in accs:
        s.append(f'<rect x="4.65" y="4.75" width="2.1" height="1.15" rx=".45" {fill("black", 2)}/><rect x="7.25" y="4.75" width="2.1" height="1.15" rx=".45" {fill("black", 2)}/>'
                 f'<path d="M6.75 5.1H7.25" {stroke("black", .3, 2)}/>')
    elif not back and "glasses" in accs:
        s.append(f'<rect x="4.75" y="4.55" width="2" height="1.45" rx=".45" {stroke("black", .32, 2)}/>'
                 f'<rect x="7.25" y="4.55" width="2" height="1.45" rx=".45" {stroke("black", .32, 2)}/><path d="M6.75 5.05H7.25" {stroke("black", .3, 2)}/>')
    s.append("</g>")
    return "".join(s)


# ---- The cast: eight agents by role, two cameo hosts --------------------------


def sprite_at(x, y, svg, label, anim=None, id_=None, job=None):
    """A character; with a job id it is a link that opens that job's status."""
    a = f' class="bob {anim}"' if anim else ""
    inner = f'<g transform="translate({x} {y})"><g{a}><title>{escape(label)}</title>{svg}</g></g>'
    if id_ and job:
        return (f'<a id="{escape(id_)}" class="actor" href="#job={escape(job)}" data-job="{escape(job)}" '
                f'aria-label="{escape(label)}">{inner}</a>')
    tag = f' id="{escape(id_)}" class="actor" tabindex="0" aria-label="{escape(label)}"' if id_ else ""
    return f'<g transform="translate({x} {y})"{tag}><g{a}><title>{escape(label)}</title>{svg}</g></g>'


def step_plate(x, y, label, size=3.2):
    """The pipeline step a place stands for, on a small plate beside its sign."""
    w = round(len(label) * size * 0.62 + 5)
    return rect(x, y, w, 5, cls("black", 2), 2.5) + text(x + 2.5, y + 3.7, label, size, "sign-cyan")


def nametag(cx, y, label, size=3.3):
    """A small, always-visible name plate under a character's feet."""
    w = round(len(label) * size * 0.62 + 4)
    x = round(cx - w / 2)
    return rect(x, y, w, 5, cls("black", 2), 2.5) + text(cx, y + 3.7, label, size, "sign", "middle")


def tip_rule(id_, list_key=None):
    """CSS that shows a name card while its character is hovered or focused, and
    while its row in the who-is-where list is hovered."""
    rule = f"#{id_}:is(:hover,:focus-visible)~#tip-{id_}{{display:inline}}"
    if list_key:
        rule += f'body:has(.who li[data-agent="{list_key}"]:hover) #tip-{id_}{{display:inline}}'
    return rule


def tip(id_, cx, top, lines, width=240):
    """A name card for one character; it shows through tip_rule(id_)."""
    size = 4
    w = round(max(len(l) for l in lines) * size * 0.6 + 8)
    h = round(len(lines) * (size + 1.6) + 4)
    x = max(1, min(round(cx - w / 2), width - w - 1))
    y = max(1, top - h - 3)
    out = [f'<g class="tip" id="tip-{id_}" aria-hidden="true">',
           f'<rect x="{x}" y="{y + .8}" width="{w}" height="{h}" rx="2" class="{cls("o")}" opacity=".3"/>',
           rect(x, y, w, h, cls("black", 2), 2), rect(x + 2, y, w - 4, .6, cls("cyan"), .3)]
    for i, line in enumerate(lines):
        out.append(text(x + 4, y + 2 + (i + 1) * (size + 1.6) - 1.4, line, size, "sign" if i else "sign-cyan"))
    out.append("</g>")
    return "".join(out)


def status_marker(x, y, state):
    """A small pixel badge above a head; the text list carries the same state."""
    if state == "Working" or state == "Testing" or state == "Analysing":
        return f'<circle cx="{x + 7}" cy="{y - 4}" r="1.6" class="{cls("cyan")}"/><circle cx="{x + 7}" cy="{y - 4}" r=".7" class="{cls("white", 0)}"/>'
    if state.startswith("Waiting") or state == "Blocked":
        mark = "?" if state.startswith("Waiting") else "!"
        return (f'<circle cx="{x + 7}" cy="{y - 4.5}" r="2.3" class="{cls("coral")}"/>'
                + text(x + 7, y - 3.2, mark, 3.6, "sign", "middle"))
    return ""


def bubble(tip_x, tip_y, lines, kind="task", shift=0, size=3.6):
    """A pixel speech bubble whose tail points at (tip_x, tip_y).
    kind "task" reports real state; "ambient" is flavour text and looks lighter."""
    lines = [lines] if isinstance(lines, str) else lines
    w = round(max(len(l) for l in lines) * size * 0.62 + 6)
    h = round(len(lines) * (size + 1.4) + 3)
    x = round(tip_x - w / 2 + shift)
    y = tip_y - 3 - h
    fill = "white" if kind == "task" else "cyan"
    tone = 1 if kind == "task" else 0
    s = [f'<g class="bubble-g bubble-{kind}">',
         f'<rect x="{x}" y="{y + .7}" width="{w}" height="{h}" rx="2" class="{cls("o")}" opacity=".25"/>',
         rect(x, y, w, h, cls(fill, tone), 2),
         f'<path d="M{tip_x - 1.6} {y + h - .2}L{tip_x + .5} {y + h + 2.4}L{tip_x + 1.6} {y + h - .2}Z" class="{cls(fill, tone)}"/>']
    for i, line in enumerate(lines):
        s.append(text(x + 3, y + 2 + (i + 1) * (size + 1.4) - 1.2, line, size, "sign-dark"))
    s.append("</g>")
    return "".join(s)


