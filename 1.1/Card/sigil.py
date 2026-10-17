from enum import Enum, auto

class sigil(Enum):
    # --- attacking: change what or how many targets a card strikes ---
    AIRBORNE = auto()
    BIFURCATED_STRIKE = auto()
    TRIFURCATED_STRIKE = auto()
    DOUBLE_STRIKE = auto()
    TOUCH_OF_DEATH = auto()

    # --- defending: change what happens when a card is struck ---
    MIGHTY_LEAP = auto()
    WATERBORNE = auto()
    SHARP_QUILLS = auto()
    LOOSE_TAIL = auto()
    BEES_WITHIN = auto()

    # --- on death ---
    MANY_LIVES = auto()
    BONE_KING = auto()
    CORPSE_EATER = auto()
    FROZEN_AWAY = auto()
    TRINKET_BEARER = auto()

    # --- end of turn ---
    FLEDGLING = auto()
    ANT_SPAWNER = auto()
    FECUNDITY = auto()
    DAM_BUILDER = auto()
    BURROWER = auto()
    BONE_DIGGER = auto()
    #eot movement
    SPRINTER = auto()
    HEFTY = auto()
    RAMPAGER = auto()

    # --- on play / deck manipulation ---
    HOARDER = auto()
    RABBIT_HOLE = auto()
    BROOD_PARASITE = auto()

    # --- passive: affect neighbouring or opposing cards ---
    LEADER = auto()
    STINKY = auto()
    ANNOYING = auto()
    WORTHY_SACRIFICE = auto()
    GUARDIAN = auto()
    SCAVENGER = auto()
    AMORPHOUS = auto()
    ARMORED = auto()
    BELLIST = auto()
    BLOOD_LUST = auto()
    BRITTLE = auto()
    FINICAL_HATCHLING = auto()
    KRAKEN_WATERBORNE = auto()
    MADE_OF_STONE = auto()
    MORSEL = auto()
    OMNI_STRIKE = auto()
    REPULSIVE = auto()
    TIDAL_LOCK = auto()
    UNKILLABLE = auto()
    STEEL_TRAP = auto()

MOVEMENT = frozenset({sigil.SPRINTER, sigil.HEFTY, sigil.RAMPAGER})

