from dataclasses import dataclass

from Card.cardName import cardName
from Card.cardType import cardType
from Card.costType import costType
from Card.sigil import sigil


@dataclass(frozen=True)
class cardDef:
    name: cardName
    type: cardType
    hp: int
    attack: int
    cost: int
    currency: costType
    sigils: list[sigil]

# What a Fledgling card grows into at the end of its owner's turn.
GROWS_INTO = {
    cardName.WOLF_CUB: cardName.WOLF,
    cardName.RAVEN_EGG: cardName.RAVEN,
    cardName.ELK_FAWN: cardName.ELK,
    cardName.DIRE_WOLF_PUP: cardName.DIRE_WOLF,
    # Two stages: the pupa it becomes is itself a fledgling.
    cardName.STRANGE_LARVA: cardName.STRANGE_PUPA,
    cardName.STRANGE_PUPA: cardName.MOTHMAN,
}

CARDS = {
    cardName.SQUIRREL:      cardDef(cardName.SQUIRREL,      cardType.NORMAL,  1, 0, 0, costType.BLOOD, []),
    cardName.STOAT:         cardDef(cardName.STOAT,         cardType.NORMAL,  2, 1, 1, costType.BLOOD, []),
    cardName.BULLFROG:      cardDef(cardName.BULLFROG,      cardType.REPTILE, 2, 1, 1, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.ADDER:         cardDef(cardName.ADDER,         cardType.REPTILE, 2, 1, 2, costType.BLOOD, [sigil.TOUCH_OF_DEATH]),
    cardName.WOLF_CUB:      cardDef(cardName.WOLF_CUB,      cardType.CANINE,  1, 1, 2, costType.BLOOD, [sigil.FLEDGLING]),
    cardName.WOLF:          cardDef(cardName.WOLF,          cardType.CANINE,  2, 3, 2, costType.BLOOD, []),
    cardName.RIVER_SNAPPER: cardDef(cardName.RIVER_SNAPPER, cardType.REPTILE, 6, 1, 2, costType.BLOOD, []),
    cardName.COYOTE:        cardDef(cardName.COYOTE,        cardType.CANINE,  1, 2, 4, costType.BONES, []),
    cardName.BAT:           cardDef(cardName.BAT,           cardType.AVIAN,   1, 2, 6, costType.BONES, [sigil.AIRBORNE]),
    cardName.SPARROW:       cardDef(cardName.SPARROW,       cardType.AVIAN,   2, 1, 1, costType.BLOOD, [sigil.AIRBORNE]),
    cardName.RATTLER:       cardDef(cardName.RATTLER,       cardType.REPTILE, 1, 3, 6, costType.BONES, []),
    cardName.PORCUPINE:     cardDef(cardName.PORCUPINE,     cardType.NORMAL,  2, 1, 1, costType.BLOOD, [sigil.SHARP_QUILLS]),
    cardName.OPOSSUM:       cardDef(cardName.OPOSSUM,       cardType.NORMAL,  1, 1, 2, costType.BONES, []),
    cardName.RABBIT:        cardDef(cardName.RABBIT,        cardType.NORMAL,  1, 0, 0, costType.BLOOD, []),
    cardName.MOLE:          cardDef(cardName.MOLE,          cardType.NORMAL,  4, 0, 1, costType.BLOOD, [sigil.BURROWER]),
    cardName.MOLE_MAN:      cardDef(cardName.MOLE_MAN,      cardType.NORMAL,  6, 0, 1, costType.BLOOD, [sigil.MIGHTY_LEAP, sigil.BURROWER]),
    cardName.PACK_RAT:      cardDef(cardName.PACK_RAT,      cardType.NORMAL,  2, 2, 2, costType.BLOOD, [sigil.TRINKET_BEARER]),
    cardName.THE_WARREN:    cardDef(cardName.THE_WARREN,    cardType.NORMAL,  2, 0, 1, costType.BLOOD, [sigil.RABBIT_HOLE]),
    cardName.FIELD_MICE:    cardDef(cardName.FIELD_MICE,    cardType.NORMAL,  2, 2, 2, costType.BLOOD, [sigil.FECUNDITY]),
    cardName.WILD_BULL:     cardDef(cardName.WILD_BULL,     cardType.HOOVED,  2, 3, 2, costType.BLOOD, [sigil.RAMPAGER]),
    cardName.ELK_FAWN:      cardDef(cardName.ELK_FAWN,      cardType.HOOVED,  1, 1, 1, costType.BLOOD, [sigil.FLEDGLING, sigil.SPRINTER]),
    cardName.ELK:           cardDef(cardName.ELK,           cardType.HOOVED,  4, 2, 2, costType.BLOOD, [sigil.SPRINTER]),
    cardName.BLACK_GOAT:    cardDef(cardName.BLACK_GOAT,    cardType.HOOVED,  1, 0, 1, costType.BLOOD, [sigil.WORTHY_SACRIFICE]),
    cardName.MOOSE_BUCK:    cardDef(cardName.MOOSE_BUCK,    cardType.HOOVED,  7, 3, 3, costType.BLOOD, [sigil.HEFTY]),
    cardName.CORPSE_MAGGOTS: cardDef(cardName.CORPSE_MAGGOTS, cardType.INSECT, 2, 1, 5, costType.BONES, [sigil.CORPSE_EATER]),
    cardName.STRANGE_LARVA: cardDef(cardName.STRANGE_LARVA,  cardType.INSECT,  3, 0, 1, costType.BLOOD, [sigil.FLEDGLING]),
    cardName.STRANGE_PUPA:  cardDef(cardName.STRANGE_PUPA,   cardType.INSECT,  3, 0, 1, costType.BLOOD, [sigil.FLEDGLING]),
    cardName.MOTHMAN:       cardDef(cardName.MOTHMAN,        cardType.INSECT,  3, 7, 1, costType.BLOOD, [sigil.AIRBORNE]),
    cardName.ALPHA:         cardDef(cardName.ALPHA,         cardType.CANINE,  2, 1, 4, costType.BONES, [sigil.LEADER]),
    cardName.DIRE_WOLF_PUP: cardDef(cardName.DIRE_WOLF_PUP, cardType.CANINE,  1, 1, 2, costType.BLOOD, [sigil.FLEDGLING, sigil.BONE_DIGGER]),
    cardName.DIRE_WOLF:     cardDef(cardName.DIRE_WOLF,     cardType.CANINE,  5, 2, 3, costType.BLOOD, [sigil.DOUBLE_STRIKE]),
    cardName.RAVEN_EGG:     cardDef(cardName.RAVEN_EGG,     cardType.AVIAN,   2, 0, 1, costType.BLOOD, [sigil.FLEDGLING]),
    cardName.RAVEN:         cardDef(cardName.RAVEN,         cardType.AVIAN,   3, 2, 2, costType.BLOOD, [sigil.AIRBORNE]),
    cardName.CUCKOO:        cardDef(cardName.CUCKOO,        cardType.AVIAN,   1, 1, 1, costType.BLOOD, [sigil.AIRBORNE, sigil.BROOD_PARASITE]),
    cardName.TURKEY_VULTURE: cardDef(cardName.TURKEY_VULTURE, cardType.AVIAN, 3, 3, 8, costType.BONES, [sigil.AIRBORNE]),

    # Obstacles: no attack, immune to Touch of Death by virtue of being TERRAIN.
    cardName.STUMP:         cardDef(cardName.STUMP,         cardType.TERRAIN, 3, 0, 0, costType.BLOOD, []),
    cardName.BOULDER:       cardDef(cardName.BOULDER,       cardType.TERRAIN, 5, 0, 0, costType.BLOOD, []),
    cardName.GRAND_FIR:     cardDef(cardName.GRAND_FIR,     cardType.TERRAIN, 3, 0, 0, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.SNOWY_FIR:     cardDef(cardName.SNOWY_FIR,     cardType.TERRAIN, 4, 0, 0, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.SMOKE:         cardDef(cardName.SMOKE,         cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.FROZEN_OPOSSUM: cardDef(cardName.FROZEN_OPOSSUM, cardType.TERRAIN, 5, 0, 0, costType.BLOOD, [sigil.FROZEN_AWAY]),
    cardName.BROKEN_EGG:    cardDef(cardName.BROKEN_EGG,    cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.RABBIT_PELT:   cardDef(cardName.RABBIT_PELT,   cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
}
