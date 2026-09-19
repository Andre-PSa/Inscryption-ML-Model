"""Watch a recorded battle.

    python viewer.py                 # opens replay.json
    python viewer.py other.json

Space plays, arrow keys step, R restarts, Esc quits.
"""

import json
import math
import sys
import tkinter as tk
from tkinter import font as tkfont

# Candlelit cabin: dark wood, bone cardstock, one amber accent.
GROUND      = "#17120E"
WOOD        = "#241C15"
WOOD_RAISED = "#30251A"
GRAIN       = "#3D2F20"
BONE        = "#E8DCC4"
BONE_DIM    = "#9C8E74"
BONE_FAINT  = "#6A5E4A"
CANDLE      = "#E0A340"
BLOOD       = "#A2412F"
MOSS        = "#7C8B5A"

CARD_FACE   = "#DCCEAF"
CARD_QUIET  = "#B4A88C"
STONE_FACE  = "#4A4137"
CARD_EDGE   = "#8C7A55"
CARD_INK    = "#2B2218"
ATK_INK     = "#8E2F1F"
HP_INK      = "#3F5B2E"

CARD_W, CARD_H, GAP = 112, 142, 12
LANES = 4
PAD = 22
BOARD_W = LANES * CARD_W + (LANES - 1) * GAP
CANVAS_W = BOARD_W + PAD * 2

SCALE_Y = 66                 # centre of the balance beam
ROW_Y = (128, 296, 464)      # top of each card row
CANVAS_H = ROW_Y[2] + CARD_H + 10

# Rows in the order the frame stores them, with how their cards are drawn.
ROWS = (("LESHY'S NEXT CARDS", "leshyNext", "leshy", True),
        ("LESHY'S LINE", "leshyBattle", "leshy", False),
        ("YOUR LINE", "playerBattle", "player", False))

ANIM_MS = 420                # a whole slide, start to finish
ANIM_STEP = 16               # ~60fps


def laneX(lane):
    return PAD + lane * (CARD_W + GAP)


def blend(a, b, t):
    """Mix two #rrggbb colours; the canvas has no alpha, so fades are done in colour."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def ease(t):
    """Smoothstep, so cards pull away and settle instead of jerking."""
    return t * t * (3 - 2 * t)


def enableDpiAwareness():
    """Without this Windows bitmap-stretches the window and everything is
    blurry and oversized."""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


class Viewer:
    def __init__(self, root, replay, transport=True):
        self.root = root
        self.replay = replay
        self.i = 0
        self.playing = False
        self.transport = transport

        self.anim = None
        self.t = 1.0
        self.clearMotion()

        root.title("Leshy's Table")
        root.configure(bg=GROUND)
        root.minsize(420, 560)

        # Designed at CANVAS_W x CANVAS_H and scaled to fit the window.
        self.k = 1.0
        self.ox = self.oy = 0.0

        # Canvas fonts rescale; widget fonts must not, or resizing loops forever.
        self.fonts = {}
        for name, family, size, weight in (
                ("serif", "Georgia", 10, "normal"),
                ("monoBold", "Consolas", 12, "bold"),
                ("tiny", "Consolas", 7, "normal")):
            f = tkfont.Font(family=family, size=size, weight=weight)
            self.fonts[name] = (f, size)
            setattr(self, name, f)

        self.uiTitle = tkfont.Font(family="Georgia", size=15)
        self.uiMono = tkfont.Font(family="Consolas", size=9)
        self.uiTiny = tkfont.Font(family="Consolas", size=7)

        # ── header ──────────────────────────────────────────
        head = tk.Frame(root, bg=GROUND, padx=PAD, pady=10)
        head.pack(fill="x")
        tk.Label(head, text=f'Encounter {replay["encounter"]}', font=self.uiTitle,
                 bg=GROUND, fg=BONE).pack(side="left")
        outcome = replay["outcome"]
        tk.Label(head, text=outcome.upper(), font=self.uiMono, bg=GROUND,
                 fg={"won": MOSS, "lost": BLOOD}.get(outcome, BONE_FAINT)
                 ).pack(side="right")

        # ── board ───────────────────────────────────────────
        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H,
                                bg=GROUND, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.onResize)

        # ── readouts, as real widgets so they cannot collide ─
        info = tk.Frame(root, bg=GROUND, padx=PAD, pady=4)
        info.pack(fill="x")
        self.actionLabel = tk.Label(info, font=self.uiTitle, bg=GROUND, fg=CANDLE,
                                    anchor="w")
        self.actionLabel.pack(fill="x")
        self.statsLabel = tk.Label(info, font=self.uiMono, bg=GROUND, fg=BONE_FAINT,
                                   anchor="w")
        self.statsLabel.pack(fill="x")

        hand = tk.Frame(root, bg=GROUND, padx=PAD, pady=(0))
        hand.pack(fill="x")
        tk.Label(hand, text="HAND", font=self.uiTiny, bg=GROUND, fg=BONE_FAINT,
                 anchor="w").pack(fill="x")
        self.handLabel = tk.Label(hand, font=self.uiMono, bg=GROUND, fg=BONE_DIM,
                                  anchor="w", justify="left", wraplength=CANVAS_W - PAD * 2)
        self.handLabel.pack(fill="x")

        # ── transport ───────────────────────────────────────
        if transport:
            bar = tk.Frame(root, bg=WOOD, pady=8, padx=PAD)
            bar.pack(fill="x", pady=(10, 0))

            def button(text, cmd):
                b = tk.Button(bar, text=text, command=cmd, font=self.uiMono,
                              bg=WOOD_RAISED, fg=BONE, activebackground=CANDLE,
                              activeforeground=GROUND, relief="flat", padx=11, pady=3,
                              highlightthickness=0, cursor="hand2")
                b.pack(side="left", padx=(0, 7))
                return b

            button("< STEP", self.prev)
            self.playBtn = button("PLAY", self.togglePlay)
            button("STEP >", self.next)

            self.counter = tk.Label(bar, text="", font=self.uiMono, bg=WOOD, fg=BONE_DIM)
            self.counter.pack(side="right")

            self.slider = tk.Scale(bar, from_=0, to=len(replay["frames"]) - 1,
                                   orient="horizontal", showvalue=False,
                                   command=self.onSlide, bg=WOOD, fg=BONE,
                                   troughcolor=GROUND, activebackground=CANDLE,
                                   highlightthickness=0, relief="flat",
                                   sliderrelief="flat", width=12)
            self.slider.pack(side="left", padx=8, fill="x", expand=True)

            for key, fn in (("<Left>", self.prev), ("<Right>", self.next),
                            ("<space>", self.togglePlay), ("r", lambda: self.goto(0))):
                root.bind(key, lambda e, f=fn: f())

        for key, fn in (("<F11>", self.toggleFullscreen),
                        ("<Escape>", self.leaveFullscreen)):
            root.bind(key, lambda e, f=fn: f())

        self.render()

    # ── window ──────────────────────────────────────────────
    def toggleFullscreen(self):
        self.root.attributes("-fullscreen",
                             not self.root.attributes("-fullscreen"))

    def leaveFullscreen(self):
        if self.root.attributes("-fullscreen"):
            self.root.attributes("-fullscreen", False)
        else:
            self.root.destroy()

    # ── navigation ──────────────────────────────────────────
    def goto(self, i, animate=False):
        self.cancelAnim()
        i = max(0, min(len(self.replay["frames"]) - 1, i))
        moving = animate and i != self.i and \
            self.planMotion(self.replay["frames"][self.i], self.replay["frames"][i])
        self.i = i
        if self.transport:
            self.slider.set(self.i)
        if moving:
            self.animate()
        else:
            self.render()

    def prev(self):
        self.stop()
        self.goto(self.i - 1, animate=True)

    def next(self):
        self.stop()
        self.goto(self.i + 1, animate=True)

    def onSlide(self, value):
        if int(value) != self.i:
            self.stop()
            self.goto(int(value))

    def stop(self):
        self.playing = False
        self.playBtn.config(text="PLAY")

    def togglePlay(self):
        if self.playing:
            return self.stop()
        if self.i >= len(self.replay["frames"]) - 1:
            self.goto(0)
        self.playing = True
        self.playBtn.config(text="PAUSE")
        self.tick()

    def tick(self):
        if not self.playing:
            return
        if self.i >= len(self.replay["frames"]) - 1:
            return self.stop()
        self.goto(self.i + 1, animate=True)
        self.root.after(850, self.tick)

    # ── scaling ─────────────────────────────────────────────
    def onResize(self, event):
        """Fit the board to the window, keeping its proportions and centring
        the leftover space."""
        k = min(event.width / CANVAS_W, event.height / CANVAS_H)
        self.k = max(0.5, k)
        self.ox = (event.width - CANVAS_W * self.k) / 2
        self.oy = (event.height - CANVAS_H * self.k) / 2

        for font, base in self.fonts.values():
            font.configure(size=max(6, round(base * self.k)))
        self.render()

    def X(self, v):
        return self.ox + v * self.k

    def Y(self, v):
        return self.oy + v * self.k

    def S(self, v):
        return v * self.k

    # ── drawing ─────────────────────────────────────────────
    def text(self, x, y, s, font, fill, anchor="nw"):
        self.canvas.create_text(self.X(x), self.Y(y), text=s, font=font,
                                fill=fill, anchor=anchor)

    def rect(self, x1, y1, x2, y2, **kw):
        if "width" in kw:
            kw["width"] = max(1, round(self.S(kw["width"])))
        self.canvas.create_rectangle(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2), **kw)

    def line(self, x1, y1, x2, y2, **kw):
        if "width" in kw:
            kw["width"] = max(1, round(self.S(kw["width"])))
        self.canvas.create_line(self.X(x1), self.Y(y1), self.X(x2), self.Y(y2), **kw)

    def poly(self, points, **kw):
        if "width" in kw:
            kw["width"] = max(1, round(self.S(kw["width"])))
        flat = []
        for px, py in points:
            flat += [self.X(px), self.Y(py)]
        self.canvas.create_polygon(*flat, **kw)

    def oval(self, x, y, r, **kw):
        self.canvas.create_oval(self.X(x - r), self.Y(y - r),
                                self.X(x + r), self.Y(y + r), **kw)

    def drawCard(self, x, y, c, side, queued, fade=0.0, hit=0.0):
        if c is None:
            self.rect(x, y, x + CARD_W, y + CARD_H,
                      outline=GRAIN, dash=(3, 4), fill="#120E0A")
            return

        # A card entering or leaving shrinks about its own centre as it fades.
        if fade:
            w, h = CARD_W * (1 - 0.18 * fade), CARD_H * (1 - 0.18 * fade)
            x, y = x + (CARD_W - w) / 2, y + (CARD_H - h) / 2
        else:
            w, h = CARD_W, CARD_H

        def shade(colour):
            return blend(colour, GROUND, fade)

        terrain = c["type"] == "TERRAIN"
        if terrain:
            face, ink = STONE_FACE, BONE
        else:
            face = CARD_QUIET if queued else CARD_FACE
            ink = "#4A4034" if queued else CARD_INK
        edge = BONE_FAINT if terrain else (BLOOD if side == "leshy" else MOSS)
        if hit:
            face, edge = blend(face, BLOOD, hit), blend(edge, BONE, hit)

        self.rect(x, y, x + w, y + h, fill=shade(face), outline=shade(edge), width=2)
        self.text(x + 8, y + 7, c["name"].replace("_", " ").title(), self.serif, shade(ink))

        ty = y + 26
        for s in c["sigils"]:
            self.text(x + 8, ty, s.replace("_", " ").lower(), self.tiny,
                      shade(BONE_DIM if terrain else "#6B5C42"))
            ty += 11

        self.text(x + 8, y + h - 9, str(c["attack"]), self.monoBold,
                  shade(BONE_FAINT if terrain else ATK_INK), anchor="sw")
        hp = str(c["hp"]) if c["hp"] == c["maxHp"] else f'{c["hp"]}/{c["maxHp"]}'
        self.text(x + w - 8, y + h - 9, hp, self.monoBold,
                  shade(BONE_DIM if terrain else
                        (BLOOD if c["hp"] < c["maxHp"] else HP_INK)),
                  anchor="se")

    def drawScale(self, scales):
        cx, cy = CANVAS_W // 2, SCALE_Y
        angle = math.radians(max(-5, min(5, scales)) * 6)
        half = 74
        dx, dy = half * math.cos(angle), half * math.sin(angle)

        self.line(cx, cy, cx, cy + 30, fill=BONE_FAINT, width=3)
        self.poly([(cx - 18, cy + 30), (cx + 18, cy + 30),
                   (cx + 12, cy + 38), (cx - 12, cy + 38)],
                  fill="#4A3C2C", outline="")
        self.line(cx - dx, cy - dy, cx + dx, cy + dy, fill=CARD_EDGE, width=3)
        self.oval(cx, cy, 4, fill=CANDLE, outline="")

        for px, py, colour in ((cx - dx, cy - dy, BLOOD), (cx + dx, cy + dy, MOSS)):
            self.line(px, py, px, py + 17, fill=BONE_FAINT)
            self.poly([(px - 15, py + 17), (px + 15, py + 17),
                       (px + 10, py + 27), (px - 10, py + 27)],
                      fill="#2E2318", outline=colour, width=2)

        self.text(PAD, cy - 14, "LESHY", self.serif, BONE_DIM)
        self.text(PAD, cy + 2, str(abs(scales)) if scales < 0 else "0",
                  self.monoBold, BLOOD)
        self.text(CANVAS_W - PAD, cy - 14, "YOU", self.serif, BONE_DIM, anchor="ne")
        self.text(CANVAS_W - PAD, cy + 2, str(scales) if scales > 0 else "0",
                  self.monoBold, MOSS, anchor="ne")

    # ── animation ───────────────────────────────────────────
    def slotsOf(self, frame):
        """Every card in a frame keyed by its stable id, with where it sits."""
        out = {}
        for row, (_, key, _, _) in enumerate(ROWS):
            for lane, c in enumerate(frame[key]):
                if c is not None and c.get("id") is not None:
                    out[c["id"]] = (row, lane, c)
        return out

    def clearMotion(self):
        self.motion, self.leaving, self.entering, self.hurt = {}, [], set(), set()

    def planMotion(self, old, new):
        """Work out what slid, what arrived, what died and what took damage."""
        self.clearMotion()
        a, b = self.slotsOf(old), self.slotsOf(new)
        for cid, (row, lane, c) in b.items():
            if cid not in a:
                self.entering.add(cid)
                continue
            oldRow, oldLane, oldCard = a[cid]
            if (oldRow, oldLane) != (row, lane):
                self.motion[cid] = (oldRow, oldLane, row, lane, c)
            if c["hp"] < oldCard["hp"]:
                self.hurt.add(cid)
        for cid, (row, lane, c) in a.items():
            if cid not in b:
                self.leaving.append((row, lane, c))
        return self.motion or self.leaving or self.entering or self.hurt

    def animate(self):
        self.t = 0.0
        self.stepAnim()

    def stepAnim(self):
        self.t = min(1.0, self.t + ANIM_STEP / ANIM_MS)
        self.render()
        if self.t < 1.0:
            self.anim = self.root.after(ANIM_STEP, self.stepAnim)
        else:
            self.anim = None
            self.clearMotion()

    def cancelAnim(self):
        if self.anim is not None:
            self.root.after_cancel(self.anim)
            self.anim = None
        self.t = 1.0
        self.clearMotion()

    def render(self):
        cv = self.canvas
        cv.delete("all")
        f = self.replay["frames"][self.i]
        e = ease(self.t)

        self.drawScale(f["scales"])

        for row, (label, key, side, queued) in enumerate(ROWS):
            self.text(PAD, ROW_Y[row] - 12, label, self.tiny, BONE_FAINT)
            for lane, c in enumerate(f[key]):
                # A card still in flight leaves its destination looking empty.
                if c is not None and c.get("id") in self.motion:
                    c = None
                hit = math.sin(math.pi * self.t) if c is not None \
                    and c.get("id") in self.hurt else 0.0
                fade = 1 - e if c is not None and c.get("id") in self.entering else 0.0
                self.drawCard(laneX(lane), ROW_Y[row], c, side, queued, fade, hit)

        for row, lane, c in self.leaving:
            _, _, side, queued = ROWS[row]
            self.drawCard(laneX(lane), ROW_Y[row], c, side, queued, fade=e)

        for oldRow, oldLane, row, lane, c in self.motion.values():
            _, _, side, queued = ROWS[row]
            x = laneX(oldLane) + (laneX(lane) - laneX(oldLane)) * e
            y = ROW_Y[oldRow] + (ROW_Y[row] - ROW_Y[oldRow]) * e
            hit = math.sin(math.pi * self.t) if c["id"] in self.hurt else 0.0
            self.drawCard(x, y, c, side, queued, hit=hit)

        edge = ROW_Y[2] - 20
        self.line(PAD, edge, CANVAS_W - PAD, edge, fill=GRAIN)

        self.actionLabel.config(text=f["label"])
        self.statsLabel.config(
            text=f'turn {f["turn"]}    reward {f["reward"]:+.3f}    '
                 f'predicted {f["value"]:+.2f}    deck {f["deckLeft"]}    '
                 f'squirrels {f["squirrelsLeft"]}')

        hand = "   ".join(
            f'{c["name"].replace("_", " ").title()} '
            f'{c["cost"]}{"b" if c["currency"] == "BONES" else "*"}'
            for c in f["hand"]) or "empty"
        if f["holding"]:
            hand += f'      [holding {f["holding"]["name"].replace("_", " ").title()}]'
        self.handLabel.config(text=hand)

        if self.transport:
            self.counter.config(text=f'{self.i + 1} / {len(self.replay["frames"])}')


def watch(path="replay.json"):
    enableDpiAwareness()
    with open(path, encoding="utf-8") as fh:
        replay = json.load(fh)
    root = tk.Tk()
    Viewer(root, replay)
    root.mainloop()


if __name__ == "__main__":
    watch(sys.argv[1] if len(sys.argv) > 1 else "replay.json")
