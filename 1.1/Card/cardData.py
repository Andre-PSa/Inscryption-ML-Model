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
SPAWNS_ON_DEATH = {
    cardName.BAIT_BUCKET: cardName.GREAT_WHITE,
    cardName.STRANGE_FROG: cardName.LEAPING_TRAP,
}

GROWS_INTO = {
    cardName.WOLF_CUB: cardName.WOLF,
    cardName.RAVEN_EGG: cardName.RAVEN,
    cardName.ELK_FAWN: cardName.ELK,
    cardName.DIRE_WOLF_PUP: cardName.DIRE_WOLF,
    cardName.TADPOLE: cardName.BULLFROG,
    # Two stages: the pupa it becomes is itself a fledgling.
    cardName.STRANGE_LARVA: cardName.STRANGE_PUPA,
    cardName.STRANGE_PUPA: cardName.MOTHMAN,
}

CARDS = {
    cardName.SQUIRREL:      cardDef(cardName.SQUIRREL,      cardType.SQUIRREL, 1, 0, 0, costType.BLOOD, []),
    cardName.STOAT:         cardDef(cardName.STOAT,         cardType.NORMAL,  2, 1, 1, costType.BLOOD, []),
    cardName.BULLFROG:      cardDef(cardName.BULLFROG,      cardType.REPTILE, 2, 1, 1, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.SKINK:         cardDef(cardName.SKINK,         cardType.REPTILE, 2, 1, 1, costType.BLOOD, [sigil.LOOSE_TAIL]),
    cardName.ADDER:         cardDef(cardName.ADDER,         cardType.REPTILE, 1, 1, 2, costType.BLOOD, [sigil.TOUCH_OF_DEATH]),
    cardName.WOLF_CUB:      cardDef(cardName.WOLF_CUB,      cardType.CANINE,  1, 1, 1, costType.BLOOD, [sigil.FLEDGLING]),
    cardName.WOLF:          cardDef(cardName.WOLF,          cardType.CANINE,  2, 3, 2, costType.BLOOD, []),
    cardName.RIVER_SNAPPER: cardDef(cardName.RIVER_SNAPPER, cardType.REPTILE, 6, 1, 2, costType.BLOOD, []),
    cardName.COYOTE:        cardDef(cardName.COYOTE,        cardType.CANINE,  1, 2, 4, costType.BONES, []),
    cardName.BAT:           cardDef(cardName.BAT,           cardType.AVIAN,   1, 2, 4, costType.BONES, [sigil.AIRBORNE]),
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
    cardName.RACCOON:       cardDef(cardName.RACCOON,       cardType.NORMAL,  1, 1, 1, costType.BLOOD, [sigil.SCAVENGER]),
    cardName.RING_WORM:     cardDef(cardName.RING_WORM,     cardType.INSECT,  1, 0, 1, costType.BLOOD, []),
    cardName.RIVER_OTTER:   cardDef(cardName.RIVER_OTTER,   cardType.NORMAL,  1, 1, 1, costType.BLOOD, [sigil.WATERBORNE]),
    cardName.TAIL:          cardDef(cardName.TAIL,          cardType.NORMAL,  2, 0, 0, costType.BLOOD, []),
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
    cardName.KINGFISHER:    cardDef(cardName.KINGFISHER,    cardType.AVIAN,   1, 1, 1, costType.BLOOD, [sigil.WATERBORNE]),

    # Obstacles: no attack, immune to Touch of Death by virtue of being TERRAIN.
    cardName.STUMP:         cardDef(cardName.STUMP,         cardType.TERRAIN, 3, 0, 0, costType.BLOOD, []),
    cardName.BOULDER:       cardDef(cardName.BOULDER,       cardType.TERRAIN, 5, 0, 0, costType.BLOOD, [sigil.MADE_OF_STONE]),
    cardName.GRAND_FIR:     cardDef(cardName.GRAND_FIR,     cardType.TERRAIN, 3, 0, 0, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.SNOWY_FIR:     cardDef(cardName.SNOWY_FIR,     cardType.TERRAIN, 4, 0, 0, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.SMOKE:         cardDef(cardName.SMOKE,         cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.FROZEN_OPOSSUM: cardDef(cardName.FROZEN_OPOSSUM, cardType.TERRAIN, 5, 0, 0, costType.BLOOD, [sigil.FROZEN_AWAY]),
    cardName.BROKEN_EGG:    cardDef(cardName.BROKEN_EGG,    cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.RABBIT_PELT:   cardDef(cardName.RABBIT_PELT,   cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.GOLDEN_PELT:   cardDef(cardName.GOLDEN_PELT,   cardType.TERRAIN, 3, 0, 0, costType.BLOOD, []),
    cardName.MAGPIE: cardDef(cardName.MAGPIE, cardType.AVIAN, 1, 1, 2, costType.BLOOD, [sigil.AIRBORNE, sigil.HOARDER]),
    cardName.BLOODHOUND: cardDef(cardName.BLOODHOUND, cardType.CANINE, 3, 2, 2, costType.BLOOD, [sigil.GUARDIAN]),
    cardName.CAGED_WOLF: cardDef(cardName.CAGED_WOLF, cardType.CANINE, 6, 0, 2, costType.BLOOD, []),
    cardName.CHILD_13: cardDef(cardName.CHILD_13, cardType.HOOVED, 1, 0, 1, costType.BLOOD, [sigil.MANY_LIVES]),
    cardName.LONG_ELK: cardDef(cardName.LONG_ELK, cardType.HOOVED, 2, 1, 4, costType.BONES, [sigil.SPRINTER, sigil.TOUCH_OF_DEATH]),
    cardName.PACK_MULE: cardDef(cardName.PACK_MULE, cardType.HOOVED, 5, 0, 0, costType.BLOOD, [sigil.SPRINTER]),
    cardName.PRONGHORN: cardDef(cardName.PRONGHORN, cardType.HOOVED, 3, 1, 2, costType.BLOOD, [sigil.SPRINTER, sigil.BIFURCATED_STRIKE]),
    cardName.BEE: cardDef(cardName.BEE, cardType.INSECT, 1, 1, 0, costType.BLOOD, [sigil.AIRBORNE]),
    cardName.BEEHIVE: cardDef(cardName.BEEHIVE, cardType.INSECT, 2, 0, 1, costType.BLOOD, [sigil.BEES_WITHIN]),
    cardName.COCKROACH: cardDef(cardName.COCKROACH, cardType.INSECT, 1, 1, 4, costType.BONES, [sigil.UNKILLABLE]),
    cardName.MANTIS: cardDef(cardName.MANTIS, cardType.INSECT, 1, 1, 1, costType.BLOOD, [sigil.BIFURCATED_STRIKE]),
    cardName.MANTIS_GOD: cardDef(cardName.MANTIS_GOD, cardType.INSECT, 1, 1, 1, costType.BLOOD, [sigil.TRIFURCATED_STRIKE]),
    cardName.MEALWORM: cardDef(cardName.MEALWORM, cardType.INSECT, 2, 0, 2, costType.BONES, [sigil.MORSEL]),
    cardName.PELT_LICE: cardDef(cardName.PELT_LICE, cardType.INSECT, 1, 1, 4, costType.BLOOD, [sigil.DOUBLE_STRIKE]),
    cardName.AMALGAM: cardDef(cardName.AMALGAM, cardType.NORMAL, 3, 3, 2, costType.BLOOD, []),
    cardName.AMOEBA: cardDef(cardName.AMOEBA, cardType.NORMAL, 2, 1, 2, costType.BONES, [sigil.AMORPHOUS]),
    cardName.AQUASQUIRREL: cardDef(cardName.AQUASQUIRREL, cardType.NORMAL, 1, 0, 0, costType.BLOOD, []),
    cardName.BEAVER: cardDef(cardName.BEAVER, cardType.NORMAL, 4, 1, 2, costType.BLOOD, [sigil.DAM_BUILDER]),
    cardName.CAT: cardDef(cardName.CAT, cardType.NORMAL, 1, 0, 1, costType.BLOOD, [sigil.MANY_LIVES]),
    cardName.FURRY_TAIL: cardDef(cardName.FURRY_TAIL, cardType.NORMAL, 2, 0, 0, costType.BLOOD, []),
    cardName.GREAT_KRAKEN: cardDef(cardName.GREAT_KRAKEN, cardType.NORMAL, 1, 1, 1, costType.BLOOD, [sigil.KRAKEN_WATERBORNE]),
    cardName.GREAT_WHITE: cardDef(cardName.GREAT_WHITE, cardType.NORMAL, 2, 4, 3, costType.BLOOD, [sigil.WATERBORNE]),
    cardName.GRIZZLY: cardDef(cardName.GRIZZLY, cardType.NORMAL, 6, 4, 3, costType.BLOOD, []),
    cardName.HODAG: cardDef(cardName.HODAG, cardType.NORMAL, 5, 1, 2, costType.BLOOD, [sigil.BLOOD_LUST]),
    cardName.IJIRAQ: cardDef(cardName.IJIRAQ, cardType.NORMAL, 1, 4, 0, costType.BLOOD, [sigil.REPULSIVE]),
    cardName.MOLE_SEAMAN: cardDef(cardName.MOLE_SEAMAN, cardType.NORMAL, 8, 1, 1, costType.BLOOD, [sigil.BURROWER, sigil.MIGHTY_LEAP]),
    cardName.RAT_KING: cardDef(cardName.RAT_KING, cardType.NORMAL, 1, 2, 2, costType.BLOOD, [sigil.BONE_KING]),
    cardName.SKELETON_CREW: cardDef(cardName.SKELETON_CREW, cardType.NORMAL, 1, 2, 2, costType.BONES, [sigil.BRITTLE]),
    cardName.SKUNK: cardDef(cardName.SKUNK, cardType.NORMAL, 3, 0, 1, costType.BLOOD, [sigil.STINKY]),
    cardName.STATIC_CARD: cardDef(cardName.STATIC_CARD, cardType.NORMAL, 1, 0, 0, costType.BLOOD, []),
    cardName.STINKBUG: cardDef(cardName.STINKBUG, cardType.NORMAL, 2, 1, 2, costType.BONES, [sigil.STINKY]),
    cardName.TAIL_FEATHERS: cardDef(cardName.TAIL_FEATHERS, cardType.NORMAL, 2, 0, 0, costType.BLOOD, []),
    cardName.THE_DAUS: cardDef(cardName.THE_DAUS, cardType.NORMAL, 2, 2, 2, costType.BLOOD, [sigil.BELLIST]),
    cardName.THE_LIMONCELLO: cardDef(cardName.THE_LIMONCELLO, cardType.NORMAL, 80, 2, 0, costType.BLOOD, [sigil.MIGHTY_LEAP, sigil.OMNI_STRIKE, sigil.MADE_OF_STONE]),
    cardName.THE_MOON: cardDef(cardName.THE_MOON, cardType.NORMAL, 40, 1, 0, costType.BLOOD, [sigil.MADE_OF_STONE, sigil.MIGHTY_LEAP, sigil.OMNI_STRIKE, sigil.TIDAL_LOCK]),
    cardName.UNDEAD_CAT: cardDef(cardName.UNDEAD_CAT, cardType.NORMAL, 6, 3, 1, costType.BLOOD, []),
    cardName.URAYULI: cardDef(cardName.URAYULI, cardType.NORMAL, 7, 7, 4, costType.BLOOD, []),
    cardName.WOLVERINE: cardDef(cardName.WOLVERINE, cardType.NORMAL, 3, 1, 5, costType.BONES, [sigil.BLOOD_LUST]),
    cardName.WRIGGLING_LEG: cardDef(cardName.WRIGGLING_LEG, cardType.NORMAL, 2, 0, 0, costType.BLOOD, []),
    cardName.GECK: cardDef(cardName.GECK, cardType.REPTILE, 1, 1, 0, costType.BLOOD, []),
    cardName.MUD_TURTLE: cardDef(cardName.MUD_TURTLE, cardType.REPTILE, 2, 2, 2, costType.BLOOD, [sigil.ARMORED]),
    cardName.OUROBOROS: cardDef(cardName.OUROBOROS, cardType.REPTILE, 1, 1, 2, costType.BLOOD, [sigil.UNKILLABLE]),
    cardName.TADPOLE: cardDef(cardName.TADPOLE, cardType.REPTILE, 1, 0, 0, costType.BLOOD, [sigil.WATERBORNE, sigil.FLEDGLING]),
    cardName.WRIGGLING_TAIL: cardDef(cardName.WRIGGLING_TAIL, cardType.REPTILE, 2, 0, 0, costType.BLOOD, []),
    cardName.WOLF_PELT: cardDef(cardName.WOLF_PELT, cardType.TERRAIN, 2, 0, 0, costType.BLOOD, []),
    cardName.CURIOUS_EGG: cardDef(cardName.CURIOUS_EGG, cardType.NORMAL, 1, 0, 1, costType.BONES, [sigil.FINICAL_HATCHLING]),
    cardName.ZOMBIE_PARROT: cardDef(cardName.ZOMBIE_PARROT, cardType.NORMAL, 3, 2, 0, costType.BLOOD, [sigil.AIRBORNE, sigil.BRITTLE]),
    cardName.CHIME: cardDef(cardName.CHIME, cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.DAM: cardDef(cardName.DAM, cardType.TERRAIN, 2, 0, 0, costType.BLOOD, []),
    cardName.BAIT_BUCKET: cardDef(cardName.BAIT_BUCKET, cardType.TERRAIN, 1, 0, 0, costType.BLOOD, []),
    cardName.LEAPING_TRAP: cardDef(cardName.LEAPING_TRAP, cardType.TERRAIN, 1, 0, 0, costType.BLOOD, [sigil.MIGHTY_LEAP, sigil.STEEL_TRAP]),
    cardName.STRANGE_FROG: cardDef(cardName.STRANGE_FROG, cardType.TERRAIN, 2, 1, 0, costType.BLOOD, [sigil.MIGHTY_LEAP]),
    cardName.GOLD_NUGGET: cardDef(cardName.GOLD_NUGGET, cardType.TERRAIN, 2, 0, 0, costType.BLOOD, []),
    cardName.ANT_QUEEN: cardDef(cardName.ANT_QUEEN, cardType.INSECT, 3, 0, 2, costType.BLOOD, [sigil.ANT_SPAWNER]),
    cardName.WORKER_ANT: cardDef(cardName.WORKER_ANT, cardType.INSECT, 2, 0, 1, costType.BLOOD, []),
    cardName.FLYING_ANT: cardDef(cardName.FLYING_ANT, cardType.INSECT, 1, 0, 1, costType.BLOOD, [sigil.AIRBORNE]),
    cardName.RED_HART: cardDef(cardName.RED_HART, cardType.HOOVED, 2, 0, 2, costType.BLOOD, [sigil.SPRINTER]),
    cardName.LAMMERGEIER: cardDef(cardName.LAMMERGEIER, cardType.AVIAN, 4, 0, 3, costType.BLOOD, [sigil.AIRBORNE]),
    cardName.BELL_TENTACLE: cardDef(cardName.BELL_TENTACLE, cardType.NORMAL, 3, 0, 2, costType.BLOOD, []),
    cardName.HAND_TENTACLE: cardDef(cardName.HAND_TENTACLE, cardType.NORMAL, 1, 0, 1, costType.BLOOD, []),
    cardName.MIRROR_TENTACLE: cardDef(cardName.MIRROR_TENTACLE, cardType.NORMAL, 3, 0, 1, costType.BLOOD, []),
}
