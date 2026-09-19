from enum import Enum, auto


class damageType(Enum):
    """What a card's damage does when it lands"""
    NORMAL = auto()
    DEATH = auto()
