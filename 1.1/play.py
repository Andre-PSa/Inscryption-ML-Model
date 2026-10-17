"""Play a battle yourself.

    python play.py            encounter 1
    python play.py 3          encounter 3

The board is the viewer's; the buttons are whatever is legal right now.
"""

import sys
import tkinter as tk

import numpy as np

from Board.board import ACT_LENS_PICK, deckSortKey, result
from Board.encounters import ENCOUNTERS
from Env.environment import environment
from Model.replay import describeAction, describeCard, identity, snapshot
from viewer import (Viewer, enableDpiAwareness, BONE, BONE_DIM, BONE_FAINT,
                    CANDLE, GROUND, MOSS, BLOOD, PAD, WOOD, WOOD_RAISED)


class Play:
    def __init__(self, root, index=0, encounters=None):
        self.root = root
        self.index = index
        self.encounters = encounters if encounters is not None else ENCOUNTERS
        self.env = environment(encounters=self.encounters)
        self.env.reset(index=index)
        self.done = False
        self.ids = identity()

        replay = {"encounter": index + 1, "outcome": "playing",
                  "frames": [self.frame("your move")]}
        self.viewer = Viewer(root, replay, transport=False)

        self.bar = tk.Frame(root, bg=WOOD, height=40)
        self.bar.pack(fill="x", pady=(10, 0))
        self.bar.bind("<Configure>", self.flow)
        self.buttons = []

        self.status = tk.Label(root, bg=GROUND, fg=BONE_FAINT,
                               font=self.viewer.uiMono, pady=6)
        self.status.pack(fill="x")

        self.refresh("your move")

    def frame(self, label, reward=0.0):
        return snapshot(self.env.board, label, reward, 0.0, self.ids)

    def refresh(self, label, reward=0.0, animate=False):
        """Each move appends a frame, so the viewer has a previous state to animate from."""
        frames = self.viewer.replay["frames"]
        if animate:
            frames.append(self.frame(label, reward))
            self.viewer.goto(len(frames) - 1, animate=True)
        else:
            frames[:] = [self.frame(label, reward)]
            self.viewer.goto(0)

        for w in self.bar.winfo_children():
            w.destroy()
        self.buttons = []

        if self.done:
            self.endButtons()
            self.flow()
            return

        board = self.env.board
        for action in np.nonzero(board.legalActions())[0]:
            self.actionButton(describeAction(int(action), board), int(action),
                              self.deckCardFor(int(action)))
        self.flow()

        self.status.config(
            text=f"bones {board.bones}    scale {board.scales:+d}    "
                 f"turn {board.turn}    deck {len(board.playerDeck)}    "
                 f"squirrels {board.squirrelDeck}",
            fg=BONE_FAINT)

    def deckCardFor(self, action):
        """The deck card a pick-from-the-deck action would take, so it can be read before choosing."""
        if action < ACT_LENS_PICK:
            return None
        ordered = sorted(self.env.board.playerDeck, key=deckSortKey)
        return describeCard(ordered[action - ACT_LENS_PICK], identity())

    def actionButton(self, text, action, card=None):
        b = tk.Button(self.bar, text=text, font=self.viewer.uiMono,
                      command=lambda a=action: self.take(a),
                      bg=WOOD_RAISED, fg=BONE, activebackground=CANDLE,
                      activeforeground=GROUND, relief="flat", padx=10, pady=3,
                      highlightthickness=0, cursor="hand2")
        self.buttons.append(b)
        if card is not None:
            b.bind("<Enter>", lambda e: self.viewer.inspect(card))
            b.bind("<Leave>", lambda e: self.viewer.inspect(None))

    def flow(self, event=None):
        """Lay the buttons out left to right, wrapping onto a new row when one would run
        off the edge, so a long list of choices is never cut off."""
        width = self.bar.winfo_width() - PAD * 2
        if width <= 1:
            return
        x, y, rowHeight = 0, 8, 0
        for b in self.buttons:
            w, h = b.winfo_reqwidth(), b.winfo_reqheight()
            if x and x + w > width:
                x, y, rowHeight = 0, y + rowHeight + 4, 0
            b.place(x=PAD + x, y=y)
            x += w + 6
            rowHeight = max(rowHeight, h)
        self.bar.config(height=y + rowHeight + 8)

    def endButtons(self):
        self.buttons.append(tk.Button(
            self.bar, text="AGAIN", font=self.viewer.uiMono,
            command=self.restart, bg=CANDLE, fg=GROUND,
            activebackground=BONE, relief="flat", padx=12, pady=3,
            highlightthickness=0, cursor="hand2"))
        for i in range(len(self.encounters)):
            self.buttons.append(tk.Button(
                self.bar, text=f"#{i + 1}", font=self.viewer.uiMono,
                command=lambda n=i: self.restart(n),
                bg=WOOD_RAISED, fg=BONE, activebackground=CANDLE,
                activeforeground=GROUND, relief="flat", padx=9, pady=3,
                highlightthickness=0, cursor="hand2"))

    def take(self, action):
        board = self.env.board
        label = describeAction(action, board)
        _, reward, self.done = self.env.step(action)

        if self.done:
            outcome = {result.WIN: "won", result.LOSE: "lost"}.get(
                self.env.outcome, "out of turns")
            self.viewer.replay["outcome"] = outcome
            self.refresh(label, reward, animate=True)
            self.status.config(
                text=f"You {outcome}.  Scale ended at {self.env.board.scales:+d} "
                     f"after {self.env.board.turn} turns.",
                fg=MOSS if self.env.outcome is result.WIN else BLOOD)
        else:
            self.refresh(label, reward, animate=True)

    def restart(self, index=None):
        self.index = self.index if index is None else index
        self.env.reset(index=self.index)
        self.done = False
        self.ids = identity()
        self.viewer.replay["encounter"] = self.index + 1
        self.viewer.replay["outcome"] = "playing"
        self.refresh("your move")


def main(index=0, encounters=None):
    enableDpiAwareness()
    root = tk.Tk()
    Play(root, index, encounters)
    root.mainloop()


if __name__ == "__main__":
    main(int(sys.argv[1]) - 1 if len(sys.argv) > 1 else 0)
