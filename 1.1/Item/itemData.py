from Card.cardName import cardName
from Item.itemName import itemName

ITEM_INDEX = {i: n for n, i in enumerate(itemName)}

BOTTLED = {
    itemName.SQUIRREL_BOTTLE: cardName.SQUIRREL,
    itemName.BOULDER_BOTTLE: cardName.BOULDER,
    itemName.BLACK_GOAT_BOTTLE: cardName.BLACK_GOAT,
    itemName.FROZEN_OPOSSUM_BOTTLE: cardName.FROZEN_OPOSSUM,
}

TARGETS_LANE = frozenset({itemName.SCISSORS, itemName.SKINNING_KNIFE})

TARGETS_DECK = frozenset({itemName.LENS})

# Bleach strips your own sigils and nothing else, so it is almost never worth using.
# It is here so the item list matches the game, but the mask never offers it.
UNUSABLE = frozenset({itemName.BLEACH})

DISABLED = frozenset()

POSSIBLE_ITEMS = [i for i in itemName if i not in DISABLED]

PLIERS_SCALES = 1
HOGGY_BANK_BONES = 4
