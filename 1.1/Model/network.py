import keras
from keras import layers

from Card.card import CARD_FEATURES
from Item.itemName import itemName
from Board.board import (
    board,
    N_ROWS,
    N_LANES,
    MAX_HAND,
    MAX_DECK,
    MAX_ITEMS,
    HAND_FEATURES,
    N_ACTIONS,
)

# Read off the encoder so the two can never disagree about the width.
GLOBAL_FEATURES = len(board().encodeGlobals())

TRUNK_UNITS = 256
LANE_UNITS = 64
HAND_UNITS = 16
# Lower than the hand's: there are MAX_DECK slots and every one widens the trunk.
DECK_UNITS = 8
ITEM_UNITS = 8


def buildNetwork():
    """Two heads on one shared trunk.

    action (N_ACTIONS,)  scores for the numbered action list, sacrifices included
    value  (1,)          -1..+1 estimate of how this game ends
    """
    laneIn = layers.Input(shape=(N_ROWS, N_LANES, CARD_FEATURES), name="lanes")
    handIn = layers.Input(shape=(MAX_HAND, HAND_FEATURES), name="hand")
    deckIn = layers.Input(shape=(MAX_DECK, CARD_FEATURES), name="deck")
    itemsIn = layers.Input(shape=(MAX_ITEMS, len(itemName)), name="items")
    globalIn = layers.Input(shape=(GLOBAL_FEATURES,), name="globals")

    # Lane-major, so one shared Dense learns a matchup once for all four lanes.
    x = layers.Permute((2, 1, 3))(laneIn)
    x = layers.Reshape((N_LANES, N_ROWS * CARD_FEATURES))(x)
    x = layers.Dense(LANE_UNITS, activation="relu")(x)
    laneOut = layers.Flatten()(x)

    y = layers.Dense(HAND_UNITS, activation="relu")(handIn)
    handOut = layers.Flatten()(y)

    # Same treatment as the hand; the encoder sorts the deck so no slot means "next".
    z = layers.Dense(DECK_UNITS, activation="relu")(deckIn)
    deckOut = layers.Flatten()(z)

    w = layers.Dense(ITEM_UNITS, activation="relu")(itemsIn)
    itemsOut = layers.Flatten()(w)

    trunk = layers.Concatenate()([laneOut, handOut, deckOut, itemsOut, globalIn])
    trunk = layers.Dense(TRUNK_UNITS, activation="relu")(trunk)
    trunk = layers.Dense(TRUNK_UNITS, activation="relu")(trunk)

    actionHead = layers.Dense(N_ACTIONS, name="action")(trunk)
    valueHead = layers.Dense(1, activation="tanh", name="value")(trunk)

    return keras.Model(
        inputs=[laneIn, handIn, deckIn, itemsIn, globalIn],
        outputs=[actionHead, valueHead],
    )
