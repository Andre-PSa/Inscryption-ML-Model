"""The RL view of a battle: reset, step, reward, done.

The board models Inscryption and knows nothing about training. Everything here
turns that into something an agent can learn from, which is why the reward
weights live on this side of the line.
"""

import random

from Board.board import (board, result, N_LANES, MAX_TURNS, ACT_RING_BELL,
                         ACT_SACRIFICE_SET, ACT_USE_ITEM, laneSet)
from Board.encounters import ENCOUNTERS
from Card.costType import costType

# Terminal values match the value head's tanh range; a larger one would saturate.
REWARD_WIN = 0.8
REWARD_LOSS = -1.0
REWARD_KILL = 0.024

# Indexed by blood cost. A dearer card is worth more than its cost says, so these climb.
REWARD_CARD_LOST = (-0.005, -0.015, -0.018, -0.022, -0.025)
REWARD_CARD_SACRIFICED = (-0.001, -0.015, -0.018, -0.022, -0.025)
REWARD_TURN = -0.005
REWARD_TURN_AFTER_5 = -0.025
REWARD_EXTRA_DAMAGE = 0.04

def gone(before, after):
    """Cards that were on the board and no longer are. A new arrival cannot cancel a death."""
    return [c for c in before if not any(c is d for d in after)]


def priced(cards, table):
    """Total from a per-blood-cost table. Bone cards have no blood cost, so they count as one."""
    return sum(table[c.cost if c.currency is costType.BLOOD else 1] for c in cards)

class environment:
    def __init__(self, encounters=None, rng=None):
        self.encounters = encounters if encounters is not None else ENCOUNTERS
        self.rng = rng if rng is not None else random.Random()
        self.board = None
        self.outcome = None

    def reset(self, index=None):
        """Start a battle and return the opening observation.

        Everything is rebuilt from card names, so the same encounter can be
        replayed forever without the previous episode's damage leaking in.
        """
        e = self.encounters[index] if index is not None \
            else self.rng.choice(self.encounters)

        self.outcome = None
        self.board = board()
        deck = e.buildDeck()
        self.board.populate_board(
            e.buildPlayerBattle(),
            e.buildLeshyBattle(),
            deck,
            [None] * N_LANES,
            e.buildMoves(),
            e.playerTotem,
            e.leshyTotem,
            e.buildItems(),
            e.pickOpening(deck),
            e.waterborneSquirrels,
        )
        return self.board.encode()

    def step(self, actionId):
        """Apply one action-head choice. Returns (observation, reward, done).

        Ringing the bell also runs Leshy's turn, so it is the only action that
        can end the battle. Sacrificing is the only other one that scores.
        """
        if actionId == ACT_RING_BELL:
            return self.resolveTurn()

        # The id names the lanes it spends, so the cards are known before they are gone.
        spent = priced([self.board.playerBattleCards[i]
                        for i in laneSet(actionId - ACT_SACRIFICE_SET)],
                       REWARD_CARD_SACRIFICED) \
            if ACT_SACRIFICE_SET <= actionId < ACT_USE_ITEM else 0.0
        self.board.applyAction(actionId)
        return self.board.encode(), spent, False

    def livingCards(self):
        # Leshy's queued row counts too — overkill can kill those.
        leshy = self.board.leshyBattleCards + self.board.leshyNextCards
        return ([c for c in leshy if c is not None and not c.isTerrain()],
                [c for c in self.board.playerBattleCards if c is not None and not c.isTerrain()])

    def resolveTurn(self):
        """Both halves of a round, scored by what died.

        Cards are diffed by identity around each half rather than counted, so a
        sigil that creates one — maggots, a thawed opossum, a parasite's egg —
        cannot cancel out a death that actually happened.
        """
        b = self.board
        leshyBefore, playerBefore = self.livingCards()

        self.outcome, scales = b.endPlayerTurn()
        if self.outcome is None:
            # Refused — a sacrifice is paid for and the card still needs placing.
            return b.encode(), 0.0, False

        leshyMid, playerMid = self.livingCards()
        reward = (len(gone(leshyBefore, leshyMid)) * REWARD_KILL
                  + priced(gone(playerBefore, playerMid), REWARD_CARD_LOST)
                  + REWARD_TURN)
        if b.turn > 5:
            reward += REWARD_TURN_AFTER_5

        if self.outcome is result.WIN:
            reward += (scales - 5) * REWARD_EXTRA_DAMAGE
            return b.encode(), reward + REWARD_WIN , True

        self.outcome = b.leshyTurn()
        leshyAfter, playerAfter = self.livingCards()
        reward += (len(gone(leshyMid, leshyAfter)) * REWARD_KILL
                   + priced(gone(playerMid, playerAfter), REWARD_CARD_LOST))
        b.refillLeshyQueue()

        if self.outcome is result.LOSE:
            return b.encode(), reward + REWARD_LOSS, True

        # Running the clock out is not a draw — Leshy keeps the board, so you lost.
        if b.turn >= MAX_TURNS:
            self.outcome = result.LOSE
            return b.encode(), reward + REWARD_LOSS, True

        return b.encode(), reward, False
