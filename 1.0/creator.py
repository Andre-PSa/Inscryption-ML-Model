"""Design an encounter, then play it or watch the model play it.

    python creator.py

Pick a card, give it any modifiers you want, then click a slot to place it.
PLAY opens it as a game, VIEW records the model playing it, and COPY prints it
as Python ready to paste into encounters.py.
"""

import tkinter as tk
from tkinter import ttk

from Board.encounters import VANILLA_DECK, ENCOUNTERS, GOAT_DECK, deckCard, encounter
from Card.cardData import CARDS
from Card.cardName import cardName
from Card.costType import costType
from Card.sigil import sigil
from viewer import (BLOOD, BONE, BONE_DIM, BONE_FAINT, CANDLE, GRAIN, GROUND,
                    MOSS, PAD, WOOD, WOOD_RAISED, Viewer, enableDpiAwareness)

ERASE = "— empty —"
N_LANES = 4


def pretty(name):
    return name.replace("_", " ").title()


def nameOf(entry):
    return entry.name if isinstance(entry, deckCard) else entry


def statsOf(entry):
    """Attack, hp and the full sigil list, with any modifiers applied."""
    c = CARDS[nameOf(entry)]
    mod = entry if isinstance(entry, deckCard) else None
    return (c.attack + (mod.attackMod if mod else 0),
            c.hp + (mod.hpMod if mod else 0),
            list(c.sigils) + (list(mod.sigils) if mod else []))


def describe(entry):
    """Everything about a card, for the palette readout."""
    if entry is None:
        return ""
    c = CARDS[nameOf(entry)]
    attack, hp, sigils = statsOf(entry)
    cost = f"{c.cost} {'bones' if c.currency is costType.BONES else 'blood'}"
    names = ", ".join(pretty(s.name) for s in sigils) or "no sigils"
    return f"{attack}/{hp}   {pretty(c.type.name)}   {cost}   {names}"


def label(entry):
    """Short form for a board slot or deck row."""
    if entry is None:
        return "·"
    text = pretty(nameOf(entry).name)
    if isinstance(entry, deckCard):
        bits = []
        if entry.attackMod:
            bits.append(f"{entry.attackMod:+d}a")
        if entry.hpMod:
            bits.append(f"{entry.hpMod:+d}h")
        if entry.sigils:
            bits.append(f"+{len(entry.sigils)}s")
        text += "  " + " ".join(bits)
    return text


class Creator:
    def __init__(self, root):
        self.root = root
        self.deck = list(VANILLA_DECK)
        self.leshyBattle = [None] * N_LANES
        self.playerBattle = [None] * N_LANES
        self.moves = [[None] * N_LANES]
        self.card = None
        self.attackMod = 0
        self.hpMod = 0

        root.title("Encounter Creator")
        root.configure(bg=GROUND)
        root.minsize(1150, 700)

        self.mono = ("Consolas", 9)
        self.tiny = ("Consolas", 7)

        self.palette()
        body = tk.Frame(root, bg=GROUND, padx=PAD)
        body.pack(fill="both", expand=True)
        self.modPanel(body)
        self.deckPanel(body)
        self.boardPanel(body)
        self.actions()
        self.status = tk.Label(root, bg=GROUND, fg=BONE_FAINT, font=self.mono,
                               anchor="w", padx=PAD, pady=4)
        self.status.pack(fill="x")
        self.refresh()

    # ── palette ─────────────────────────────────────────────
    def palette(self):
        bar = tk.Frame(self.root, bg=WOOD, padx=PAD, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="CARD", font=self.tiny, bg=WOOD, fg=BONE_FAINT).pack(side="left")

        self.picker = ttk.Combobox(bar, values=[ERASE] + [pretty(n.name) for n in cardName],
                                   state="readonly", width=22, font=self.mono)
        self.picker.current(0)
        self.picker.pack(side="left", padx=8)
        self.picker.bind("<<ComboboxSelected>>", lambda e: self.pick())

        self.readout = tk.Label(bar, text="", font=self.mono, bg=WOOD, fg=CANDLE, anchor="w")
        self.readout.pack(side="left", padx=10, fill="x", expand=True)
        tk.Label(bar, text="click a slot to place  ·  right-click to clear",
                 font=self.tiny, bg=WOOD, fg=BONE_FAINT).pack(side="right")

    def pick(self):
        i = self.picker.current()
        self.card = None if i == 0 else list(cardName)[i - 1]
        self.clampMods()
        self.refresh()

    def brush(self):
        """The card as configured: a plain name, or a deckCard if modified."""
        if self.card is None:
            return None
        chosen = self.chosenSigils()
        if not chosen and not self.attackMod and not self.hpMod:
            return self.card
        return deckCard(self.card, chosen, self.attackMod, self.hpMod)

    # ── modifiers ───────────────────────────────────────────
    def modPanel(self, parent):
        panel = tk.Frame(parent, bg=GROUND, pady=10)
        panel.pack(side="left", fill="y", padx=(0, PAD))
        tk.Label(panel, text="MODIFIERS", font=self.tiny, bg=GROUND, fg=BONE_FAINT,
                 anchor="w").pack(fill="x")

        self.attackLabel = self.stepper(panel, "attack", self.bumpAttack)
        self.hpLabel = self.stepper(panel, "health", self.bumpHp)

        tk.Label(panel, text="GRANTED SIGILS", font=self.tiny, bg=GROUND,
                 fg=BONE_FAINT, anchor="w").pack(fill="x", pady=(10, 2))
        self.sigilList = tk.Listbox(panel, selectmode="multiple", width=24, height=14,
                                    font=self.tiny, bg=WOOD, fg=BONE,
                                    selectbackground=CANDLE, selectforeground=GROUND,
                                    highlightthickness=0, borderwidth=0,
                                    activestyle="none", exportselection=False)
        for s in sigil:
            self.sigilList.insert("end", f" {pretty(s.name)}")
        self.sigilList.pack()
        self.sigilList.bind("<<ListboxSelect>>", lambda e: self.refresh())

        self.button(panel, "CLEAR MODIFIERS", self.clearMods).pack(fill="x", pady=8)

    def stepper(self, parent, name, bump):
        row = tk.Frame(parent, bg=GROUND)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=name, font=self.tiny, bg=GROUND, fg=BONE_DIM,
                 width=7, anchor="w").pack(side="left")
        self.button(row, "−", lambda: bump(-1)).pack(side="left")
        shown = tk.Label(row, text="+0", font=self.mono, bg=GROUND, fg=BONE, width=4)
        shown.pack(side="left", padx=2)
        self.button(row, "+", lambda: bump(+1)).pack(side="left")
        return shown

    def bumpAttack(self, d):
        self.attackMod += d
        self.clampMods()
        self.refresh()

    def bumpHp(self, d):
        self.hpMod += d
        self.clampMods()
        self.refresh()

    def clampMods(self):
        """Attack may fall to 0, health may not fall below 1 — a 0-hp card is already dead."""
        if self.card is None:
            return
        c = CARDS[self.card]
        self.attackMod = max(self.attackMod, -c.attack)
        self.hpMod = max(self.hpMod, 1 - c.hp)

    def chosenSigils(self):
        return [list(sigil)[i] for i in self.sigilList.curselection()]

    def clearMods(self):
        self.attackMod = self.hpMod = 0
        self.sigilList.selection_clear(0, "end")
        self.refresh()

    # ── deck ────────────────────────────────────────────────
    def deckPanel(self, parent):
        panel = tk.Frame(parent, bg=GROUND, pady=10)
        panel.pack(side="left", fill="y", padx=(0, PAD))
        tk.Label(panel, text="DECK", font=self.tiny, bg=GROUND, fg=BONE_FAINT,
                 anchor="w").pack(fill="x")

        self.deckList = tk.Listbox(panel, width=32, height=17, font=self.mono,
                                   bg=WOOD, fg=BONE, selectbackground=CANDLE,
                                   selectforeground=GROUND, highlightthickness=0,
                                   borderwidth=0, activestyle="none")
        self.deckList.pack(pady=4)

        row = tk.Frame(panel, bg=GROUND)
        row.pack(fill="x", pady=(2, 8))
        self.button(row, "ADD", self.addCard).pack(side="left")
        self.button(row, "REMOVE", self.removeCard).pack(side="left", padx=6)

        tk.Label(panel, text="LOAD A SAVED ENCOUNTER", font=self.tiny, bg=GROUND,
                 fg=BONE_FAINT, anchor="w").pack(fill="x", pady=(10, 2))
        row = tk.Frame(panel, bg=GROUND)
        row.pack(fill="x")
        self.encounterPicker = ttk.Combobox(
            row, values=[f"Encounter {i + 1}" for i in range(len(ENCOUNTERS))],
            state="readonly", width=16, font=self.mono)
        self.encounterPicker.current(0)
        self.encounterPicker.pack(side="left")
        self.button(row, "LOAD", self.loadEncounter).pack(side="left", padx=6)

        tk.Label(panel, text="DECK PRESETS", font=self.tiny, bg=GROUND, fg=BONE_FAINT,
                 anchor="w").pack(fill="x", pady=(10, 2))
        for name, cards in (("Vanilla deck", VANILLA_DECK), ("Goat deck", GOAT_DECK),
                            ("Empty", [])):
            self.button(panel, name, lambda c=cards: self.setDeck(c)).pack(fill="x", pady=2)

    def setDeck(self, cards):
        self.deck = list(cards)
        self.refresh()

    def loadEncounter(self):
        """Pull a saved encounter onto the board so it can be played or edited."""
        i = self.encounterPicker.current()
        e = ENCOUNTERS[i]
        self.deck = list(e.deck)
        # In place: the lane buttons captured these lists when they were built.
        self.leshyBattle[:] = list(e.leshyBattle)
        self.playerBattle[:] = list(e.playerBattle)
        self.moves = [list(t) for t in e.moves] or [[None] * N_LANES]
        self.refresh()
        self.say(f"loaded encounter {i + 1}.", MOSS)

    def addCard(self):
        if self.card:
            self.deck.append(self.brush())
            self.refresh()

    def removeCard(self):
        sel = self.deckList.curselection()
        if sel:
            self.deck.pop(sel[0])
            self.refresh()

    # ── board ───────────────────────────────────────────────
    def boardPanel(self, parent):
        self.board = tk.Frame(parent, bg=GROUND, pady=10)
        self.board.pack(side="left", fill="both", expand=True)

        self.leshyButtons = self.laneRow(self.board, "LESHY'S LINE",
                                         self.leshyBattle, BLOOD)
        self.playerButtons = self.laneRow(self.board, "YOUR LINE",
                                          self.playerBattle, MOSS)

        tk.Frame(self.board, bg=GRAIN, height=1).pack(fill="x", pady=10)
        head = tk.Frame(self.board, bg=GROUND)
        head.pack(fill="x")
        tk.Label(head, text="LESHY'S MOVES", font=self.tiny, bg=GROUND,
                 fg=BONE_FAINT).pack(side="left")
        self.button(head, "+ TURN", self.addTurn).pack(side="right")
        self.button(head, "− TURN", self.removeTurn).pack(side="right", padx=6)

        self.movesFrame = tk.Frame(self.board, bg=GROUND)
        self.movesFrame.pack(fill="x", pady=4)
        self.moveButtons = []

    def laneRow(self, parent, title, target, edge):
        tk.Label(parent, text=title, font=self.tiny, bg=GROUND, fg=BONE_FAINT,
                 anchor="w").pack(fill="x", pady=(8, 2))
        row = tk.Frame(parent, bg=GROUND)
        row.pack(fill="x")
        buttons = []
        for lane in range(N_LANES):
            b = tk.Button(row, text="·", font=self.mono, width=16, height=2,
                          bg=WOOD_RAISED, fg=BONE, activebackground=CANDLE,
                          activeforeground=GROUND, relief="flat",
                          highlightbackground=edge, highlightthickness=1,
                          cursor="hand2")
            b.configure(command=lambda t=target, i=lane: self.place(t, i))
            b.bind("<Button-3>", lambda e, t=target, i=lane: self.place(t, i, True))
            b.pack(side="left", padx=3)
            buttons.append(b)
        return buttons

    def place(self, target, lane, clear=False):
        target[lane] = None if clear else self.brush()
        self.refresh()

    def addTurn(self):
        self.moves.append([None] * N_LANES)
        self.refresh()

    def removeTurn(self):
        if len(self.moves) > 1:
            self.moves.pop()
            self.refresh()

    def buildMoveRows(self):
        for w in self.movesFrame.winfo_children():
            w.destroy()
        self.moveButtons = []
        for t, turn in enumerate(self.moves):
            row = tk.Frame(self.movesFrame, bg=GROUND)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"t{t + 1}", font=self.tiny, bg=GROUND,
                     fg=BONE_FAINT, width=3).pack(side="left")
            buttons = []
            for lane in range(N_LANES):
                b = tk.Button(row, text="·", font=self.mono, width=16,
                              bg=WOOD, fg=BONE_DIM, activebackground=CANDLE,
                              activeforeground=GROUND, relief="flat",
                              highlightthickness=0, cursor="hand2")
                b.configure(command=lambda t=turn, i=lane: self.place(t, i))
                b.bind("<Button-3>", lambda e, t=turn, i=lane: self.place(t, i, True))
                b.pack(side="left", padx=3)
                buttons.append(b)
            self.moveButtons.append(buttons)

    # ── actions ─────────────────────────────────────────────
    def actions(self):
        bar = tk.Frame(self.root, bg=WOOD, padx=PAD, pady=8)
        bar.pack(fill="x")
        self.button(bar, "PLAY", self.play, CANDLE, GROUND).pack(side="left")
        self.button(bar, "VIEW", self.view).pack(side="left", padx=8)
        self.button(bar, "COPY", self.copy).pack(side="left")

    def button(self, parent, text, cmd, bg=WOOD_RAISED, fg=BONE):
        return tk.Button(parent, text=text, command=cmd, font=self.mono, bg=bg,
                         fg=fg, activebackground=CANDLE, activeforeground=GROUND,
                         relief="flat", padx=9, pady=2, highlightthickness=0,
                         cursor="hand2")

    def usedMoves(self):
        """Every turn up to the last Leshy plays into. An empty turn in the middle
        is a turn he does nothing, which changes the encounter, so it is kept."""
        played = [i for i, t in enumerate(self.moves) if any(x is not None for x in t)]
        return [list(t) for t in self.moves[:played[-1] + 1]] if played else []

    def encounter(self):
        return encounter(deck=list(self.deck),
                         leshyBattle=list(self.leshyBattle),
                         playerBattle=list(self.playerBattle),
                         moves=self.usedMoves())

    def play(self):
        if not self.deck:
            return self.say("A deck needs at least one card.", BLOOD)
        from play import Play
        Play(tk.Toplevel(self.root), 0, encounters=[self.encounter()])

    def view(self):
        if not self.deck:
            return self.say("A deck needs at least one card.", BLOOD)
        self.say("loading the model…", CANDLE)
        self.root.update()
        import main
        from Model.replay import recordEpisode
        replay = recordEpisode(main.loadModel(), 0, encounters=[self.encounter()])
        Viewer(tk.Toplevel(self.root), replay)
        self.say(f"model {replay['outcome']} in {replay['steps']} steps.", MOSS)

    def copy(self):
        src = self.source()
        self.root.clipboard_clear()
        self.root.clipboard_append(src)
        # tkinter owns the clipboard until it flushes, so it must not wait for idle.
        self.root.update()
        self.say(f"copied {len(src.splitlines())} lines to the clipboard.", MOSS)

    def source(self):
        def entry(e):
            if e is None:
                return "N"
            if not isinstance(e, deckCard):
                return f"cardName.{e.name}"
            args = [f"cardName.{e.name.name}"]
            if e.sigils:
                args.append("[" + ", ".join(f"sigil.{s.name}" for s in e.sigils) + "]")
            if e.attackMod:
                args.append(f"attackMod={e.attackMod}")
            if e.hpMod:
                args.append(f"hpMod={e.hpMod}")
            return f"deckCard({', '.join(args)})"

        lines = ["encounter(",
                 "    deck=[" + ", ".join(entry(c) for c in self.deck) + "],"]
        for field, row in (("leshyBattle", self.leshyBattle),
                           ("playerBattle", self.playerBattle)):
            if any(x is not None for x in row):
                lines.append(f"    {field}=[" + ", ".join(entry(c) for c in row) + "],")
        turns = self.usedMoves()
        if turns:
            lines.append("    moves=[")
            for t in turns:
                lines.append("        [" + ", ".join(entry(c) for c in t) + "],")
            lines.append("    ],")
        lines.append("),")
        return "\n".join(lines)

    # ── redraw ──────────────────────────────────────────────
    def say(self, text, colour=BONE_FAINT):
        self.status.config(text=text, fg=colour)

    def refresh(self):
        self.attackLabel.config(text=f"{self.attackMod:+d}")
        self.hpLabel.config(text=f"{self.hpMod:+d}")
        self.readout.config(text=describe(self.brush()))

        self.deckList.delete(0, "end")
        for c in self.deck:
            attack, hp, _ = statsOf(c)
            self.deckList.insert("end", f" {label(c):<24}{attack}/{hp}")

        for buttons, target in ((self.leshyButtons, self.leshyBattle),
                                (self.playerButtons, self.playerBattle)):
            for b, c in zip(buttons, target):
                b.config(text=label(c), fg=BONE if c else BONE_FAINT)

        self.buildMoveRows()
        for buttons, turn in zip(self.moveButtons, self.moves):
            for b, c in zip(buttons, turn):
                b.config(text=label(c), fg=BONE if c else BONE_FAINT)

        turns = sum(1 for t in self.moves if any(x is not None for x in t))
        played = sum(1 for t in self.moves for c in t if c is not None)
        self.say(f"{len(self.deck)} cards in deck   ·   {turns} turns, "
                 f"{played} cards from Leshy")


def main():
    enableDpiAwareness()
    root = tk.Tk()
    Creator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
