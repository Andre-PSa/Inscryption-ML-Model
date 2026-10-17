"""Record a battle as JSON so it can be watched rather than read.

The model plays, every step is snapshotted, and the result is a flat list of
frames a viewer can step through.
"""

import json

import numpy as np

from Board.board import (ACT_SELECT_HAND, ACT_PLACE_LANE, ACT_DRAW_DECK,
                         ACT_DRAW_SQUIRREL, ACT_RING_BELL, ACT_SACRIFICE_SET,
                         ACT_USE_ITEM, ACT_ITEM_LANE, ACT_LENS_PICK,
                         N_ACTIONS, N_LANES, deckSortKey, laneSet, result)
from Env.environment import environment
from Model.train import predict, softmax, MASKED


class identity:
    """Stable per-card ids for the viewer's animations."""

    def __init__(self):
        self.ids = {}
        # Every card is kept alive, or CPython could hand its address to a new one.
        self.seen = []

    def of(self, c):
        if id(c) not in self.ids:
            self.ids[id(c)] = len(self.seen)
            self.seen.append(c)
        return self.ids[id(c)]


def describeCard(c, ids):
    if c is None:
        return None
    return {
        "id": ids.of(c),
        "name": c.name.name,
        "attack": c.attack(),
        "hp": c.hp,
        "maxHp": c.definition.hp + c.hpMod,
        "cost": c.cost,
        "currency": c.currency.name,
        "type": c.type.name,
        "sigils": [s.name for s in c.sigils],
    }


def itemLabel(item):
    return "item" if item is None else item.name.replace("_", " ").lower()


def describeAction(actionId, board):
    if actionId is None:
        return "—"
    if actionId < ACT_PLACE_LANE:
        slot = actionId - ACT_SELECT_HAND
        held = board.playerHand[slot] if slot < len(board.playerHand) else None
        return f"select {held.name.name}" if held else f"select slot {slot}"
    if actionId < ACT_DRAW_DECK:
        return f"place in lane {actionId - ACT_PLACE_LANE + 1}"
    if actionId == ACT_DRAW_DECK:
        return "draw from deck"
    if actionId == ACT_DRAW_SQUIRREL:
        return "draw a squirrel"
    if actionId == ACT_RING_BELL:
        return "ring the bell"
    if actionId < ACT_USE_ITEM:
        lanes = laneSet(actionId - ACT_SACRIFICE_SET)
        if not lanes:
            return "sacrifice nothing"
        return "sacrifice lane " + ", ".join(str(i + 1) for i in lanes)
    if actionId < ACT_ITEM_LANE:
        slot = actionId - ACT_USE_ITEM
        if slot < len(board.playerItems):
            return f"use {itemLabel(board.playerItems[slot])}"
        return f"use item slot {slot}"
    if actionId < ACT_LENS_PICK:
        lane = actionId - ACT_ITEM_LANE + 1
        return f"{itemLabel(board.itemToUse)} on lane {lane}"
    slot = actionId - ACT_LENS_PICK
    ordered = sorted(board.playerDeck, key=deckSortKey)
    if slot < len(ordered):
        return f"take {ordered[slot].name.name} from deck"
    return f"take deck slot {slot}"


def snapshot(board, label, reward, value, ids):
    return {
        "label": label,
        "turn": board.turn,
        "scales": board.scales,
        "reward": round(float(reward), 4),
        "value": round(float(value), 4),
        "leshyNext": [describeCard(c, ids) for c in board.leshyNextCards],
        "leshyBattle": [describeCard(c, ids) for c in board.leshyBattleCards],
        "playerBattle": [describeCard(c, ids) for c in board.playerBattleCards],
        "hand": [describeCard(c, ids) for c in board.playerHand],
        "holding": describeCard(board.cardToPlay, ids),
        "items": [i.name for i in board.playerItems],
        "aiming": None if board.itemToUse is None else board.itemToUse.name,
        "hoarding": board.hoarding,
        "deckLeft": len(board.playerDeck),
        "squirrelsLeft": board.squirrelDeck,
    }


def recordEpisode(model, encounterIndex=0, greedy=True, seed=0, maxSteps=400,
                  encounters=None):
    """Play one battle and return every frame of it."""
    rng = np.random.default_rng(seed)
    env = environment(encounters=encounters)
    env.reset(index=encounterIndex)
    ids = identity()

    frames = []
    obs = env.board.encode()
    _, value = predict(model, obs)
    frames.append(snapshot(env.board, "battle begins", 0.0, value, ids))

    done, steps, total = False, 0, 0.0
    while not done and steps < maxSteps:
        b = env.board
        actScores, value = predict(model, obs)

        mask = b.legalActions()
        if not mask.any():
            break
        probs = softmax(np.where(mask, actScores, MASKED))
        action = int(np.argmax(probs)) if greedy \
            else int(rng.choice(N_ACTIONS, p=probs))
        label = describeAction(action, b)
        obs, reward, done = env.step(action)

        total += reward
        steps += 1
        frames.append(snapshot(env.board, label, reward, value, ids))

    outcome = {result.WIN: "won", result.LOSE: "lost"}.get(env.outcome, "stalled")
    return {
        "encounter": encounterIndex + 1,
        "outcome": outcome,
        "totalReward": round(float(total), 4),
        "steps": steps,
        "lanes": N_LANES,
        "frames": frames,
    }


def writeReplay(model, path="replay.json", **kwargs):
    data = recordEpisode(model, **kwargs)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"{path}: encounter {data['encounter']}, "
          f"{data['outcome']} in {data['steps']} steps")
    return data
