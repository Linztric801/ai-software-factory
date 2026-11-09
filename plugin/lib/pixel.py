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

def rect(x, y, w, h, c):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{c}"/>'


def box(x, y, w, h, name, outline=True):
    """A shaded block: outline, light top-left edge, dark bottom-right edge."""
    s = []
    if outline:
        s.append(rect(x - 1, y - 1, w + 2, h + 2, cls("o")))
    s.append(rect(x, y, w, h, cls(name)))
    s.append(rect(x, y, w, 1, cls(name, 0)))
    s.append(rect(x, y, 1, h, cls(name, 0)))
    s.append(rect(x, y + h - 1, w, 1, cls(name, 2)))
    s.append(rect(x + w - 1, y, 1, h, cls(name, 2)))
    return "".join(s)


def cloud(x, y):
    """A white cloud-shaped lamp, as hung over the Cloud Fair."""
    return (rect(x + 2, y - 1, 6, 1, cls("o")) + rect(x, y, 12, 4, cls("o")) + rect(x + 1, y - 2, 4, 2, cls("o"))
            + rect(x + 1, y + 1, 10, 2, cls("white")) + rect(x + 3, y, 4, 1, cls("white", 0))
            + rect(x + 2, y - 1, 2, 1, cls("white", 0)) + rect(x + 1, y + 3, 10, 1, cls("white", 2)))


def text(x, y, s, size=5, c="sign", anchor="start"):
    if any(ch.isdigit() for ch in s):
        c += " digits"
    size = round(size * (1 if "digits" in c else 1.25), 2)  # Jersey 10 runs small per point
    return (f'<text x="{x}" y="{y}" class="{c}" font-size="{size}" '
            f'text-anchor="{anchor}">{escape(s)}</text>')


# ---- Chibi characters: a 12x16 template, outlined and shaded in code ---------


BASE = [  # anime chibi, 12x16: big head, big eyes with a highlight, blush, small body
    "...HHHHHH...",
    ".HHHHHHHHHH.",
    "HHHHHHHHHHHH",
    "HHHHHHHHHHHH",
    "HHSSHSSHSSHH",
    "HSSSSSSSSSSH",
    "HSWISSSSWISH",
    "HSIISSSSIISH",
    "HSBSSSSSSBSH",
    ".SSSSSMMSSS.",
    "..SSSSSSSS..",
    "..TTTTTTTT..",
    ".STTTTTTTTS.",
    "..TTTTTTTT..",
    "...LL..LL...",
    "...OO..OO...",
]


def chibi(hair, top, legs="navy", skin="skin", style="short", acc=None, pose="front", eyes="navy", shirt=False, beard=False,
          lanyard=None):
    accs = acc if isinstance(acc, tuple) else (acc,)
    g = [list("." + row + ".") for row in BASE]
    g.insert(0, list("." * 14))
    g.append(list("." * 14))
    W, H = 14, 18

    def put(r, c, v):
        if 0 <= r < H and 0 <= c < W:
            g[r][c] = v

    if style == "spiky":
        for c in (2, 5, 8, 11):
            put(0, c, "H")
            put(1, c - 1, "H")
    if style == "bob":
        for r in range(9, 12):
            put(r, 1, "H")
            put(r, 12, "H")
    if style == "long":
        for r in range(9, 15):
            put(r, 1, "H")
            put(r, 12, "H")
    if style == "curly":   # a bumpy top and fuller sides
        for c in (2, 3, 10, 11):
            put(1, c, "H")
        for c in (4, 6, 8):
            put(0, c, "H")
        for r in range(5, 9):
            put(r, 1, "H")
            put(r, 12, "H")
    if style == "twin":
        for r in range(4, 13):
            put(r, 0, "H")
            put(r, 13, "H")
    if "cap" in accs:       # blue cap, brim to the left
        for c in range(2, 13):
            put(1, c, "A")
            put(2, c, "A")
        for c in range(0, 5):
            put(3, c, "A")
    if "cowboy" in accs:    # tan hat with a wide brim
        for c in range(3, 11):
            put(0, c, "A")
            put(1, c, "A")
        for c in range(0, 14):
            put(2, c, "A")
    if "hardhat" in accs:
        for c in range(3, 11):
            put(1, c, "A")
        for c in range(1, 13):
            put(2, c, "A")
    if "headband" in accs:  # a dark band across the forehead
        for c in range(1, 13):
            put(4, c, "A")
    if "headshades" in accs:  # sunglasses pushed up on the head
        for c in (3, 4, 5, 8, 9, 10):
            put(2, c, "E")
        put(2, 6, "E")
        put(2, 7, "E")
    if "goggles" in accs:   # coloured glasses pushed up on the head
        for c in (3, 4, 5, 8, 9, 10):
            put(2, c, "C")
        put(2, 6, "E")
        put(2, 7, "E")
    if "shades" in accs:    # sunglasses over both eyes
        for r in (7, 8):
            for c in (2, 3, 4, 9, 10, 11):
                put(r, c, "E")
        put(7, 5, "E")
        put(7, 8, "E")
        put(7, 6, "E")
        put(7, 7, "E")
    if "glasses" in accs:   # frames beside both eyes and a bridge
        for r in (7, 8):
            for c in (2, 5, 8, 11):
                put(r, c, "E")
        put(7, 6, "E")
        put(7, 7, "E")
    if "headset" in accs:
        for r in range(3, 10):
            put(r, 0, "A")
            put(r, 13, "A")
        put(10, 2, "A")
    if "wave" in accs:     # left hand up, waving
        for r in range(6, 13):
            put(r, 0, "S")
        put(5, 0, "S")
    if "peace" in accs:     # right hand up with two fingers
        for r in range(9, 14):
            put(r, 13, "S")
    if shirt and pose != "back":   # white shirt showing between the lapels
        for r in range(12, 15):
            put(r, 6, "K")
            put(r, 7, "K")
    if lanyard and pose != "back":  # a lanyard from the neck and the red-topped festival badge
        for r in (12, 13):
            put(r, 5, "N")
            put(r, 8, "N")
        put(14, 6, "Q")
        put(14, 7, "Q")
        put(15, 6, "G")
        put(15, 7, "G")
    if beard and pose != "back":   # short beard along the jaw and chin
        for c in range(3, 11):
            if g[10][c] == "S":
                g[10][c] = "D"
        for c in (2, 11):
            if g[9][c] == "S":
                g[9][c] = "D"
        for c in range(4, 10):
            if g[11][c] == "S":
                g[11][c] = "D"
    if pose == "back":
        for r in range(5, 11):
            for c in range(W):
                if g[r][c] in "SWIBM":
                    g[r][c] = "H"
    if pose == "side":     # facing left: one eye, a nose, hair over the far half
        for r in range(5, 11):
            for c in range(8, 13):
                if g[r][c] in "SWIBM":
                    g[r][c] = "H"
        put(8, 1, "S")

    palette = {"H": hair, "S": skin, "T": top, "L": legs, "A": acc_colour(next((a for a in accs if a not in ("glasses", "peace", "wave", "shades", "headshades", "goggles")), None)), "E": "o", "O": "o",
               "W": "white", "I": eyes, "B": "pink", "M": "coral", "K": shirt if isinstance(shirt, str) else "white", "D": hair,
               "C": "cyan", "N": lanyard or "black", "Q": "pinkb", "G": "white"}
    fixed = {"W": 0, "I": 2, "B": 0, "M": 2, "K": 1, "D": 2, "C": 1, "N": 2, "Q": 1, "G": 0}
    filled = {(r, c) for r in range(H) for c in range(W) if g[r][c] != "."}
    out = []
    for r in range(H):
        for c in range(W):
            if (r, c) in filled:
                continue
            if any((r + dr, c + dc) in filled for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.append((r, c, cls("o")))
    for r, c in filled:
        k = g[r][c]
        name = palette[k]
        if k in "EO":
            out.append((r, c, cls("o")))
            continue
        if k in fixed:
            out.append((r, c, cls(name, fixed[k])))
            continue
        same = lambda rr, cc: 0 <= rr < H and 0 <= cc < W and g[rr][cc] == k
        tone = 1
        if not same(r, c + 1) or not same(r + 1, c):
            tone = 2
        elif not same(r - 1, c) or not same(r, c - 1):
            tone = 0
        if k == "S" and tone == 0:
            tone = 1
        out.append((r, c, cls(name, tone)))
    return runs(out)


def acc_colour(acc):
    return {"cap": "blue", "cowboy": "tan", "hardhat": "yellow", "headset": "black", "headband": "black"}.get(acc, "grey")


def runs(cells):
    """Merge horizontal runs of one class into single rects."""
    by_row = {}
    for r, c, k in cells:
        by_row.setdefault(r, []).append((c, k))
    s = []
    for r, row in sorted(by_row.items()):
        row.sort()
        start, prev, kind = row[0][0], row[0][0], row[0][1]
        for c, k in row[1:] + [(None, None)]:
            if c is not None and c == prev + 1 and k == kind:
                prev = c
                continue
            s.append(rect(start, r, prev - start + 1, 1, kind))
            if c is not None:
                start, prev, kind = c, c, k
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
    return (rect(x - 1, y - 1, w + 2, 7, cls("o")) + rect(x, y, w, 5, cls("black", 2))
            + text(x + 2.5, y + 4, label, size, "sign-cyan"))


def nametag(cx, y, label, size=3.3):
    """A small, always-visible name plate under a character's feet."""
    w = round(len(label) * size * 0.62 + 4)
    x = round(cx - w / 2)
    return (rect(x - 1, y - 1, w + 2, 7, cls("o")) + rect(x, y, w, 5, cls("black", 2))
            + text(cx, y + 4, label, size, "sign", "middle"))


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
    out = [f'<g class="tip" id="tip-{id_}" aria-hidden="true">', rect(x - 1, y - 1, w + 2, h + 2, cls("o")),
           rect(x, y, w, h, cls("black", 2)), rect(x, y, w, 1, cls("cyan"))]
    for i, line in enumerate(lines):
        out.append(text(x + 4, y + 2 + (i + 1) * (size + 1.6) - 1.4, line, size, "sign" if i else "sign-cyan"))
    out.append("</g>")
    return "".join(out)


def status_marker(x, y, state):
    """A small pixel badge above a head; the text list carries the same state."""
    if state == "Working" or state == "Testing" or state == "Analysing":
        return box(x + 5, y - 6, 4, 4, "cyan")
    if state.startswith("Waiting"):
        return box(x + 4, y - 7, 6, 5, "coral") + rect(x + 6, y - 6, 2, 1, cls("white")) + rect(x + 7, y - 5, 1, 1, cls("white")) + rect(x + 7, y - 3, 1, 1, cls("white"))
    if state == "Blocked":
        return box(x + 5, y - 7, 4, 5, "coral") + rect(x + 6, y - 6, 2, 2, cls("white")) + rect(x + 6, y - 3, 2, 1, cls("white"))
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
         rect(x - 1, y - 1, w + 2, h + 2, cls("o")),
         rect(x, y, w, h, cls(fill, tone)),
         rect(tip_x - 2, y + h, 5, 1, cls("o")), rect(tip_x - 1, y + h, 3, 1, cls(fill, tone)),
         rect(tip_x - 1, y + h + 1, 3, 1, cls("o")), rect(tip_x, y + h + 1, 1, 1, cls(fill, tone)),
         rect(tip_x, y + h + 2, 1, 1, cls("o"))]
    for i, line in enumerate(lines):
        s.append(text(x + 3, y + 2 + (i + 1) * (size + 1.4) - 1.2, line, size, "sign-dark"))
    s.append("</g>")
    return "".join(s)


