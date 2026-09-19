"""Act 1 battles recorded from play.

Everything here is stored as cardName, never as card objects. Cards accumulate
damage and move sequences are consumed when played (getLaneCard pops), so an
encounter has to be rebuilt for every episode — names can't go stale.
"""

from dataclasses import dataclass, field

from Board.moves import move
from Board.totem import totem
from Card.card import card
from Card.cardData import CARDS
from Card.cardName import cardName
from Card.sigil import sigil

@dataclass(frozen=True)
class deckCard:
    """A copy that differs from its species — campfire buffs, granted sigils."""
    name: cardName
    sigils: list[sigil] = field(default_factory=list)
    attackMod: int = 0
    hpMod: int = 0


DeckEntry = cardName | deckCard

# One Leshy turn: four lanes, each a name or None.
Turn = list[cardName | None]


@dataclass(frozen=True)
class encounter:
    deck: list[DeckEntry]
    leshyBattle: list[cardName | None] = field(default_factory=lambda: [None] * 4)
    playerBattle: list[cardName | None] = field(default_factory=lambda: [None] * 4)
    moves: list[Turn] = field(default_factory=list)
    # One totem each; a side's totem only ever touches that side's cards.
    playerTotem: totem = None
    leshyTotem: totem = None

    def buildDeck(self) -> list[card]:
        return [buildCard(e) for e in self.deck]

    def buildLeshyBattle(self) -> list[card | None]:
        return [None if n is None else buildCard(n) for n in self.leshyBattle]

    def buildPlayerBattle(self) -> list[card | None]:
        return [None if n is None else buildCard(n) for n in self.playerBattle]

    def buildMoves(self) -> list[move]:
        return [buildMove(t) for t in self.moves]


def buildCard(entry: DeckEntry) -> card:
    """A fresh card from a name, or from a deckCard describing a modified copy."""
    if isinstance(entry, deckCard):
        return card(CARDS[entry.name], sigilMod=list(entry.sigils),
                    attackMod=entry.attackMod, hpMod=entry.hpMod)
    return card(CARDS[entry])


def buildMove(turn: Turn) -> move:
    """One turn's placements. Each lane holds at most one card."""
    return move(*[[] if n is None else [buildCard(n)] for n in turn])


N = None

# The plain starting deck, shared by the airborne drills:
# only the bullfrog blocks air.
VANILLA_DECK = [cardName.STOAT, cardName.STOAT, cardName.WOLF,
                cardName.BULLFROG, cardName.OPOSSUM]

# Encounter 9's deck: a goat worth three blood, a burrower, and maggots in reserve.
GOAT_DECK = [cardName.BLACK_GOAT, cardName.MOOSE_BUCK,
             deckCard(cardName.ELK_FAWN, hpMod=2),
             cardName.MOLE, cardName.CORPSE_MAGGOTS]

ENCOUNTERS = [
    # 1 — opens with stumps in Leshy's line and a boulder in yours.
    encounter(
        deck=[cardName.STOAT, cardName.ADDER, cardName.RIVER_SNAPPER,
              cardName.WOLF, cardName.WOLF],
        leshyBattle=[cardName.STUMP, N, cardName.STUMP, N],
        playerBattle=[N, cardName.BOULDER, N, N],
        moves=[
            [N, cardName.WOLF_CUB, N, N],
            [N, N, N, cardName.BAT],
        ],
    ),

    # 2 — the stoat in this deck carries Touch of Death.
    encounter(
        deck=[deckCard(cardName.STOAT, [sigil.TOUCH_OF_DEATH]), cardName.SPARROW,
              cardName.RIVER_SNAPPER, cardName.WOLF, cardName.WOLF],
        moves=[
            [N, cardName.COYOTE, cardName.BAT, N],
            [N, N, N, N],
            [N, N, N, cardName.WOLF_CUB],
            [N, N, N, N],
            [N, N, N, cardName.COYOTE],
        ],
    ),

    # 3
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.WOLF, cardName.BULLFROG],
        moves=[
            [N, N, N, cardName.RATTLER],
            [N, N, N, N],
            [N, N, N, cardName.RATTLER],
        ],
    ),

    # 4 — same deck as 3.
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.WOLF, cardName.BULLFROG],
        moves=[
            [N, cardName.COYOTE, cardName.PORCUPINE, N],
        ],
    ),

    # 5 — a frozen opossum blocking lane 2, and the deck runs a spiky opossum.
    encounter(
        deck=[cardName.BULLFROG, cardName.WOLF, cardName.STOAT,
              deckCard(cardName.OPOSSUM, [sigil.SHARP_QUILLS])],
        leshyBattle=[N, cardName.FROZEN_OPOSSUM, N, N],
        moves=[
            [cardName.RAVEN_EGG, N, N, N],
            [N, N, cardName.CUCKOO, N],
        ],
    ),

    # 6 — a boulder on Leshy's side, a snowy fir clogging yours.
    encounter(
        deck=[cardName.BULLFROG, cardName.STOAT,
              deckCard(cardName.WOLF, hpMod=2),
              deckCard(cardName.OPOSSUM, [sigil.SHARP_QUILLS]),
              cardName.RABBIT_PELT],
        leshyBattle=[cardName.BOULDER, N, N, N],
        playerBattle=[N, N, cardName.SNOWY_FIR, N],
        moves=[
            [N, cardName.RABBIT, N, cardName.WILD_BULL],
            [N, N, cardName.RABBIT, N],
        ],
    ),

    # 7 — a burrowing mole wall, and fawns that sprint before they grow.
    encounter(
        deck=[cardName.BULLFROG, cardName.STOAT,
              deckCard(cardName.WOLF, hpMod=2),
              deckCard(cardName.OPOSSUM, [sigil.SHARP_QUILLS]),
              cardName.RABBIT_PELT, cardName.DIRE_WOLF],
        moves=[
            [cardName.MOLE, cardName.ELK_FAWN, N, N],
            [N, N, N, cardName.ELK_FAWN],
        ],
    ),

    # 8 — your own burrower at last, against four turns of steady pressure.
    encounter(
        deck=[cardName.BULLFROG, cardName.STOAT,
              deckCard(cardName.WOLF, hpMod=2),
              cardName.RABBIT_PELT, cardName.DIRE_WOLF,
              cardName.ELK_FAWN, cardName.PACK_RAT, cardName.MOLE_MAN],
        moves=[
            [cardName.BULLFROG, N, N, N],
            [N, cardName.ADDER, cardName.COYOTE, N],
            [N, N, cardName.RATTLER, N],
            [N, N, N, cardName.ADDER],
        ],
    ),

    # 9 — a goat worth three blood, and maggots that crawl in over your dead.
    encounter(
        deck=list(GOAT_DECK),
        moves=[
            [cardName.SPARROW, cardName.SPARROW, N, N],
        ],
    ),

    # 10 — encounter 9's deck grown out, against three turns from every direction.
    encounter(
        deck=[cardName.BLACK_GOAT, cardName.MOOSE_BUCK,
              deckCard(cardName.ELK_FAWN, hpMod=4),
              cardName.MOLE, cardName.CORPSE_MAGGOTS,
              cardName.WILD_BULL, cardName.PACK_RAT, cardName.RABBIT_PELT],
        moves=[
            [N, N, N, cardName.WOLF_CUB],
            [N, cardName.PORCUPINE, N, N],
            [cardName.SPARROW, N, N, cardName.COYOTE],
        ],
    ),

    # 11 — a drill: nothing in this deck blocks air, so the bats have to be killed.
    encounter(
        deck=[cardName.STOAT] * 5,
        moves=[
            [cardName.BAT, N, N, N],
            [N, N, N, N],
            [N, N, cardName.BAT, N],
            [N, N, N, N],
            [N, cardName.BAT, N, N],
            [N, N, N, N],
            [cardName.BAT, N, N, cardName.BAT],
        ],
    ),

    # 12 — encounter 11 with no breathing room. Winnable, but only by perfect play.
    encounter(
        deck=[cardName.STOAT] * 5,
        moves=[
            [cardName.BAT, N, N, N],
            [N, N, cardName.BAT, N],
            [N, cardName.BAT, N, N],
            [N, N, N, N],
            [cardName.BAT, N, N, cardName.BAT],
        ],
    ),

    # 13 — a burrowing mole beside a sprinting fawn, then a flier.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE],
        moves=[
            [N, cardName.ELK_FAWN, N, cardName.MOLE],
            [cardName.SPARROW, N, N, N],
        ],
    ),

    # 14 — same deck plus a sprinting stoat, against two fawns at once.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE,
              deckCard(cardName.STOAT, [sigil.SPRINTER])],
        moves=[
            [cardName.RABBIT, cardName.ELK_FAWN, cardName.ELK_FAWN, N],
        ],
    ),

    # 15 — a fir walling his line and a boulder clogging yours.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE,
              deckCard(cardName.STOAT, [sigil.SPRINTER])],
        leshyBattle=[cardName.SNOWY_FIR, N, N, N],
        playerBattle=[N, N, cardName.BOULDER, N],
        moves=[
            [N, cardName.WILD_BULL, cardName.RABBIT, N],
            [N, N, N, cardName.RABBIT],
            [N, N, N, N],
            [N, N, N, cardName.PORCUPINE],
        ],
    ),

    # 16 — four turns of canines and quills, answered by a ten card deck.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE,
              deckCard(cardName.STOAT, [sigil.SPRINTER]),
              cardName.PACK_RAT, cardName.PACK_RAT,
              cardName.MOLE_MAN, cardName.DIRE_WOLF_PUP],
        moves=[
            [cardName.OPOSSUM, N, N, cardName.WOLF_CUB],
            [N, cardName.WOLF, N, N],
            [N, N, cardName.OPOSSUM, N],
            [cardName.WOLF_CUB, N, N, N],
        ],
    ),

    # 17 — a frozen opossum clogging your line, a boulder clogging his.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS, cardName.THE_WARREN, cardName.BULLFROG,
              cardName.STOAT, cardName.WOLF],
        leshyBattle=[N, N, cardName.BOULDER, N],
        playerBattle=[cardName.FROZEN_OPOSSUM, N, N, N],
        moves=[
            [cardName.WILD_BULL, cardName.RABBIT, N, N],
            [N, N, N, cardName.RABBIT],
        ],
    ),

    # 18 — a warren sharpened at the campfire.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS, deckCard(cardName.THE_WARREN, attackMod=1),
              cardName.BULLFROG, cardName.STOAT, cardName.WOLF, cardName.WOLF_CUB],
        moves=[
            [cardName.MOLE, cardName.ELK_FAWN, N, N],
            [N, N, N, cardName.ELK_FAWN],
        ],
    ),

    # 19 — the warren's worthy sacrifice passes to every rabbit it digs up.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS,
              deckCard(cardName.THE_WARREN, [sigil.WORTHY_SACRIFICE], attackMod=1),
              cardName.BULLFROG, cardName.STOAT, cardName.WOLF, cardName.WOLF_CUB],
        leshyBattle=[N, N, cardName.BOULDER, N],
        moves=[
            [cardName.RAVEN_EGG, N, N, N],
            [N, cardName.ALPHA, N, N],
            [cardName.RAVEN_EGG, N, N, N],
        ],
    ),

    # 20 — five turns of pressure, answered by two warrens and a larva.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS,
              deckCard(cardName.THE_WARREN, [sigil.WORTHY_SACRIFICE], attackMod=1),
              deckCard(cardName.THE_WARREN, [sigil.WORTHY_SACRIFICE],
                       attackMod=2, hpMod=1),
              deckCard(cardName.STOAT, attackMod=2),
              cardName.WOLF, cardName.WOLF_CUB, cardName.RIVER_SNAPPER,
              cardName.FIELD_MICE, cardName.STRANGE_LARVA],
        moves=[
            [N, cardName.RABBIT, cardName.PORCUPINE, cardName.COYOTE],
            [cardName.COYOTE, N, N, N],
            [N, N, N, cardName.SPARROW],
            [cardName.COYOTE, N, cardName.COYOTE, N],
            [N, cardName.PORCUPINE, N, N],
        ],
    ),

    # 21-26 — airborne drills on one deck. The bullfrog is the only card in it
    # that blocks air; everything else has to kill the flier in its own lane.
    *[encounter(deck=list(VANILLA_DECK), moves=m) for m in (
        # 21 — one sparrow, and a turn to answer it.
        [[N, cardName.SPARROW, N, N],
         [N, N, N, N],
         [N, cardName.SPARROW, cardName.SPARROW, N],
         [cardName.SPARROW, N, N, N],
         [N,N,N,cardName.SPARROW]],

        # 22 — two sparrows, far apart.
        [[cardName.SPARROW, N, N, cardName.SPARROW],
         [N, N, N, N],
         [cardName.SPARROW, N, cardName.SPARROW, N],
         [N, cardName.SPARROW, N, N],
         [N,N,N,N],
         [cardName.SPARROW, cardName.SPARROW, cardName.SPARROW, N]],

        # 23 — a bat hits twice as hard but dies to anything.
        [[N, N, cardName.BAT, N],
         [N, N, N, N],
         [N, cardName.BAT, N, N]],

        # 24 — both at once, so one lane must be blocked and the other killed.
        [[cardName.SPARROW, N, cardName.BAT, N],
         [N, N, N, N],
         [N, N, N, cardName.SPARROW]],

        # 25 — a vulture survives a stoat, so it wants the bullfrog or a wolf.
        [[N, cardName.TURKEY_VULTURE, N, N],
         [N, N, N, N],
         [cardName.SPARROW, N, N, N]],

        # 26 — everything, with no spare turns.
        [[cardName.BAT, N, cardName.SPARROW, N],
         [N, N, N, N],
         [N,N,N,N],
         [N, cardName.TURKEY_VULTURE, N, N],
         [N,N,N,N],
         [N, N, N, cardName.BAT]],
    )],

    # 27 — two 2-damage threats at once. Both die to a single hit, but only one
    # can be answered per turn, so the other lane is conceded or chumped.
    encounter(
        deck=[cardName.STOAT, cardName.STOAT, cardName.WOLF, cardName.BULLFROG],
        moves=[
            [N, cardName.COYOTE, cardName.COYOTE, N],
            [N, N, N, N],
            [cardName.COYOTE, N, N, N],
        ],
    ),

    # 28 — a 3/2 wolf outranges every cheap card here, so squirrels have to buy
    # the turns it takes to afford the wolf that trades with it.
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.BULLFROG, cardName.SPARROW],
        moves=[
            [cardName.WOLF, N, N, N],
            [N, N, N, N],
            [N, N, cardName.WOLF, N],
        ],
    ),

    # 29 — the cub dies to a stoat on sight and is a 3/2 wolf two turns later.
    # Answer it early, or commit two bodies to your own wolf once it has grown.
    encounter(
        deck=[cardName.STOAT, cardName.STOAT, cardName.WOLF, cardName.SPARROW],
        moves=[
            [N, N, cardName.WOLF_CUB, N],
            [N, N, N, N],
            [N, cardName.COYOTE, N, N],
        ],
    ),

    # 30 — encounter 2's opening with room to breathe: the same coyote and bat,
    # but idle turns before the cub arrives.
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.WOLF, cardName.SPARROW],
        moves=[
            [N, cardName.COYOTE, cardName.BAT, N],
            [N, N, N, N],
            [N, N, N, N],
            [N, N, N, cardName.WOLF_CUB],
        ],
    ),

    # 31-33 — the same three fights again, handed a deck with real tools: a goat
    # that pays three blood on its own, a burrower, and maggots waiting in hand.
    encounter(deck=list(GOAT_DECK), moves=[          # encounter 2's sequence
        [N, cardName.COYOTE, cardName.BAT, N],
        [N, N, N, N],
        [N, N, N, cardName.WOLF_CUB],
        [N, N, N, N],
        [N, N, N, cardName.COYOTE],
    ]),

    encounter(deck=list(GOAT_DECK), moves=[          # encounter 28's sequence
        [cardName.WOLF, N, N, N],
        [N, N, N, N],
        [N, N, cardName.WOLF, N],
    ]),

    encounter(deck=list(GOAT_DECK), moves=[          # encounter 30's sequence
        [N, cardName.COYOTE, cardName.BAT, N],
        [N, N, N, N],
        [N, N, N, N],
        [N, N, N, cardName.WOLF_CUB],
    ]),
]
