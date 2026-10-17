from dataclasses import dataclass, field, replace

from Card.cardName import cardName

ANTS = frozenset({cardName.WORKER_ANT, cardName.FLYING_ANT, cardName.ANT_QUEEN,
                  cardName.AMALGAM})

LANES_FROM_BELL = 4


@dataclass(frozen=True)
class powerContext:
    ownBattleCards: tuple = ()
    sacrifices: int = 0
    bones: int = 0
    handSize: int = 0
    opposite: object = None
    lane: int = 0


def antsOut(c, ctx):
    return sum(1 for x in ctx.ownBattleCards if x is not None and x.name in ANTS)


def sacrificesMade(c, ctx):
    return ctx.sacrifices


def halfTheBones(c, ctx):
    return ctx.bones // 2


def nearerTheBell(c, ctx):
    return LANES_FROM_BELL - ctx.lane


def cardsInHand(c, ctx):
    return ctx.handSize


def mirrorsOpposite(c, ctx):
    o = ctx.opposite
    if o is None or o.name is cardName.MIRROR_TENTACLE:
        return 0
    return o.attack(replace(ctx, opposite=None))


POWER = {
    cardName.WORKER_ANT: antsOut,
    cardName.FLYING_ANT: antsOut,
    cardName.ANT_QUEEN: antsOut,
    cardName.RED_HART: sacrificesMade,
    cardName.LAMMERGEIER: halfTheBones,
    cardName.BELL_TENTACLE: nearerTheBell,
    cardName.HAND_TENTACLE: cardsInHand,
    cardName.MIRROR_TENTACLE: mirrorsOpposite,
}
