"""Act 1 battles recorded from play.

Everything here is stored as cardName, never as card objects. Cards accumulate
damage and move sequences are consumed as they are queued, so an encounter has
to be rebuilt for every episode — names can't go stale.
"""

from dataclasses import dataclass, field, replace

from Board.moves import move
from Board.totem import totem
from Card.card import card
from Card.cardData import CARDS
from Card.cardName import cardName
from Card.cardType import cardType
from Card.sigil import sigil
from Item.itemName import itemName

@dataclass(frozen=True)
class deckCard:
    """A copy that differs from its species — campfire buffs, granted sigils."""
    name: cardName
    sigils: list[sigil] = field(default_factory=list)
    attackMod: int = 0
    hpMod: int = 0


DeckEntry = cardName | deckCard

# One Leshy turn: the cards he plays, in the order he queues them.
Turn = list[cardName]


@dataclass(frozen=True)
class encounter:
    deck: list[DeckEntry]
    leshyBattle: list[cardName | None] = field(default_factory=lambda: [None] * 4)
    playerBattle: list[cardName | None] = field(default_factory=lambda: [None] * 4)
    moves: list[Turn] = field(default_factory=list)
    # One totem each; a side's totem only ever touches that side's cards.
    playerTotem: totem = None
    leshyTotem: totem = None
    playerItems: list[itemName] = field(default_factory=list)
    openingHand: list[DeckEntry] = field(default_factory=list)
    waterborneSquirrels: bool = False

    def buildItems(self) -> list[itemName]:
        return list(self.playerItems)

    def buildDeck(self) -> list[card]:
        return [buildCard(e) for e in self.deck]

    def pickOpening(self, built: list[card]) -> list[card]:
        """The cards of a freshly built deck that make up the opening hand, matched
        entry for entry so two copies of one card are not taken twice."""
        taken = []
        for entry in self.openingHand:
            i = next(i for i, e in enumerate(self.deck) if e == entry and i not in taken)
            taken.append(i)
        return [built[i] for i in taken]

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
    """One turn's cards. Leshy picks the lanes, so a blank in an old lane-by-lane
    turn is just skipped."""
    return move([buildCard(n) for n in turn if n is not None])


N = None

# The plain starting deck, shared by the airborne drills:
# only the bullfrog blocks air.
VANILLA_DECK = [cardName.STOAT, cardName.STOAT, cardName.WOLF,
                cardName.BULLFROG, cardName.OPOSSUM]

# Encounter 9's deck: a goat worth three blood, a burrower, and maggots in reserve.
GOAT_DECK = [cardName.BLACK_GOAT, cardName.MOOSE_BUCK,
             deckCard(cardName.ELK_FAWN, hpMod=2),
             cardName.MOLE, cardName.CORPSE_MAGGOTS]

DRILL_ITEMS = [
    [itemName.HOURGLASS, itemName.SCISSORS],
    [itemName.BOULDER_BOTTLE, itemName.PLIERS],
    [itemName.SKINNING_KNIFE, itemName.BLACK_GOAT_BOTTLE],
    [itemName.LENS, itemName.SQUIRREL_BOTTLE],
    [itemName.BOULDER_BOTTLE, itemName.SQUIRREL_BOTTLE],
    [itemName.SQUIRREL_BOTTLE, itemName.SQUIRREL_BOTTLE],
]

ENCOUNTERS = [
    # 1 — opens with stumps in Leshy's line and a boulder in yours.
    encounter(
        deck=[cardName.STOAT, cardName.ADDER, cardName.RIVER_SNAPPER,
              cardName.WOLF, cardName.WOLF],
        playerItems=[itemName.FROZEN_OPOSSUM_BOTTLE, itemName.LENS],
        leshyBattle=[cardName.STUMP, N, cardName.STUMP, N],
        playerBattle=[N, cardName.BOULDER, N, N],
        moves=[
            [cardName.WOLF_CUB],
            [cardName.BAT],
        ],
    ),

    # 2 — the stoat in this deck carries Touch of Death.
    encounter(
        deck=[deckCard(cardName.STOAT, [sigil.TOUCH_OF_DEATH]), cardName.SPARROW,
              cardName.RIVER_SNAPPER, cardName.WOLF, cardName.WOLF],
        playerItems=[itemName.LENS, itemName.SCISSORS],
        moves=[
            [cardName.COYOTE, cardName.BAT],
            [],
            [cardName.WOLF_CUB],
            [],
            [cardName.COYOTE],
        ],
    ),

    # 3
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.WOLF, cardName.BULLFROG],
        playerItems=[itemName.FAN, itemName.WISECLOCK],
        moves=[
            [cardName.RATTLER],
            [],
            [cardName.RATTLER],
        ],
    ),

    # 4 — same deck as 3.
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.WOLF, cardName.BULLFROG],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.SCISSORS],
        moves=[
            [cardName.COYOTE, cardName.PORCUPINE],
        ],
    ),

    # 5 — a frozen opossum blocking lane 2, and the deck runs a spiky opossum.
    encounter(
        deck=[cardName.BULLFROG, cardName.WOLF, cardName.STOAT,
              deckCard(cardName.OPOSSUM, [sigil.SHARP_QUILLS])],
        playerItems=[itemName.BOULDER_BOTTLE, itemName.HOGGY_BANK],
        leshyBattle=[N, cardName.FROZEN_OPOSSUM, N, N],
        moves=[
            [cardName.RAVEN_EGG],
            [cardName.CUCKOO],
        ],
    ),

    # 6 — a boulder on Leshy's side, a snowy fir clogging yours.
    encounter(
        deck=[cardName.BULLFROG, cardName.STOAT,
              deckCard(cardName.WOLF, hpMod=2),
              deckCard(cardName.OPOSSUM, [sigil.SHARP_QUILLS]),
              cardName.RABBIT_PELT],
        playerItems=[itemName.PLIERS, itemName.PLIERS],
        leshyBattle=[cardName.BOULDER, N, N, N],
        playerBattle=[N, N, cardName.SNOWY_FIR, N],
        moves=[
            [cardName.RABBIT, cardName.WILD_BULL],
            [cardName.RABBIT],
        ],
    ),

    # 7 — a burrowing mole wall, and fawns that sprint before they grow.
    encounter(
        deck=[cardName.BULLFROG, cardName.STOAT,
              deckCard(cardName.WOLF, hpMod=2),
              deckCard(cardName.OPOSSUM, [sigil.SHARP_QUILLS]),
              cardName.RABBIT_PELT, cardName.DIRE_WOLF],
        playerItems=[itemName.PLIERS, itemName.PLIERS],
        moves=[
            [cardName.MOLE, cardName.ELK_FAWN],
            [cardName.ELK_FAWN],
        ],
    ),

    # 8 — your own burrower at last, against four turns of steady pressure.
    encounter(
        deck=[cardName.BULLFROG, cardName.STOAT,
              deckCard(cardName.WOLF, hpMod=2),
              cardName.RABBIT_PELT, cardName.DIRE_WOLF,
              cardName.ELK_FAWN, cardName.PACK_RAT, cardName.MOLE_MAN],
        playerItems=[itemName.FAN, itemName.LENS],
        moves=[
            [cardName.BULLFROG],
            [cardName.ADDER, cardName.COYOTE],
            [cardName.RATTLER],
            [cardName.ADDER],
        ],
    ),

    # 9 — a goat worth three blood, and maggots that crawl in over your dead.
    encounter(
        deck=list(GOAT_DECK),
        playerItems=[itemName.FROZEN_OPOSSUM_BOTTLE, itemName.FAN],
        moves=[
            [cardName.SPARROW, cardName.SPARROW],
        ],
    ),

    # 10 — encounter 9's deck grown out, against three turns from every direction.
    encounter(
        deck=[cardName.BLACK_GOAT, cardName.MOOSE_BUCK,
              deckCard(cardName.ELK_FAWN, hpMod=4),
              cardName.MOLE, cardName.CORPSE_MAGGOTS,
              cardName.WILD_BULL, cardName.PACK_RAT, cardName.RABBIT_PELT],
        playerItems=[itemName.WISECLOCK, itemName.PLIERS],
        moves=[
            [cardName.WOLF_CUB],
            [cardName.PORCUPINE],
            [cardName.SPARROW, cardName.COYOTE],
        ],
    ),

    # 11 — a drill: nothing in this deck blocks air, so the bats have to be killed.
    encounter(
        deck=[cardName.STOAT] * 5,
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        moves=[
            [cardName.BAT],
            [],
            [cardName.BAT],
            [],
            [cardName.BAT],
            [],
            [cardName.BAT, cardName.BAT],
        ],
    ),

    # 12 — encounter 11 with no breathing room. Winnable, but only by perfect play.
    encounter(
        deck=[cardName.STOAT] * 5,
        playerItems=[itemName.HOURGLASS, itemName.PLIERS],
        moves=[
            [cardName.BAT],
            [cardName.BAT],
            [cardName.BAT],
            [],
            [cardName.BAT, cardName.BAT],
        ],
    ),

    # 13 — a burrowing mole beside a sprinting fawn, then a flier.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.HOGGY_BANK],
        moves=[
            [cardName.ELK_FAWN, cardName.MOLE],
            [cardName.SPARROW],
        ],
    ),

    # 14 — same deck plus a sprinting stoat, against two fawns at once.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE,
              deckCard(cardName.STOAT, [sigil.SPRINTER])],
        playerItems=[itemName.FROZEN_OPOSSUM_BOTTLE, itemName.WISECLOCK],
        moves=[
            [cardName.RABBIT, cardName.ELK_FAWN, cardName.ELK_FAWN],
        ],
    ),

    # 15 — a fir walling his line and a boulder clogging yours.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE,
              deckCard(cardName.STOAT, [sigil.SPRINTER])],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.SCISSORS],
        leshyBattle=[cardName.SNOWY_FIR, N, N, N],
        playerBattle=[N, N, cardName.BOULDER, N],
        moves=[
            [cardName.WILD_BULL, cardName.RABBIT],
            [cardName.RABBIT],
            [],
            [cardName.PORCUPINE],
        ],
    ),

    # 16 — four turns of canines and quills, answered by a ten card deck.
    encounter(
        deck=[cardName.STOAT, cardName.BULLFROG, cardName.OPOSSUM,
              cardName.WOLF, cardName.COYOTE,
              deckCard(cardName.STOAT, [sigil.SPRINTER]),
              cardName.PACK_RAT, cardName.PACK_RAT,
              cardName.MOLE_MAN, cardName.DIRE_WOLF_PUP],
        playerItems=[itemName.PLIERS, itemName.LENS],
        moves=[
            [cardName.OPOSSUM, cardName.WOLF_CUB],
            [cardName.WOLF],
            [cardName.OPOSSUM],
            [cardName.WOLF_CUB],
        ],
    ),

    # 17 — a frozen opossum clogging your line, a boulder clogging his.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS, cardName.THE_WARREN, cardName.BULLFROG,
              cardName.STOAT, cardName.WOLF],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.WISECLOCK],
        leshyBattle=[N, N, cardName.BOULDER, N],
        playerBattle=[cardName.FROZEN_OPOSSUM, N, N, N],
        moves=[
            [cardName.WILD_BULL, cardName.RABBIT],
            [cardName.RABBIT],
        ],
    ),

    # 18 — a warren sharpened at the campfire.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS, deckCard(cardName.THE_WARREN, attackMod=1),
              cardName.BULLFROG, cardName.STOAT, cardName.WOLF, cardName.WOLF_CUB],
        playerItems=[itemName.PLIERS, itemName.PLIERS],
        moves=[
            [cardName.MOLE, cardName.ELK_FAWN],
            [cardName.ELK_FAWN],
        ],
    ),

    # 19 — the warren's worthy sacrifice passes to every rabbit it digs up.
    encounter(
        deck=[cardName.CORPSE_MAGGOTS,
              deckCard(cardName.THE_WARREN, [sigil.WORTHY_SACRIFICE], attackMod=1),
              cardName.BULLFROG, cardName.STOAT, cardName.WOLF, cardName.WOLF_CUB],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        leshyBattle=[N, N, cardName.BOULDER, N],
        moves=[
            [cardName.RAVEN_EGG],
            [cardName.ALPHA],
            [cardName.RAVEN_EGG],
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
        playerItems=[itemName.HOGGY_BANK, itemName.LENS],
        moves=[
            [cardName.RABBIT, cardName.PORCUPINE, cardName.COYOTE],
            [cardName.COYOTE],
            [cardName.SPARROW],
            [cardName.COYOTE, cardName.COYOTE],
            [cardName.PORCUPINE],
        ],
    ),

    # 21-26 — airborne drills on one deck. The bullfrog is the only card in it
    # that blocks air; everything else has to kill the flier in its own lane.
    *[encounter(deck=list(VANILLA_DECK), playerItems=DRILL_ITEMS[n], moves=m)
      for n, m in enumerate((
        # 21 — one sparrow, and a turn to answer it.
        [[cardName.SPARROW],
         [],
         [cardName.SPARROW, cardName.SPARROW],
         [cardName.SPARROW],
         [cardName.SPARROW]],

        # 22 — two sparrows, far apart.
        [[cardName.SPARROW, cardName.SPARROW],
         [],
         [cardName.SPARROW, cardName.SPARROW],
         [cardName.SPARROW],
         [],
         [cardName.SPARROW, cardName.SPARROW, cardName.SPARROW]],

        # 23 — a bat hits twice as hard but dies to anything.
        [[cardName.BAT],
         [],
         [cardName.BAT]],

        # 24 — both at once, so one lane must be blocked and the other killed.
        [[cardName.SPARROW, cardName.BAT],
         [],
         [cardName.SPARROW]],

        # 25 — a vulture survives a stoat, so it wants the bullfrog or a wolf.
        [[cardName.TURKEY_VULTURE],
         [],
         [cardName.SPARROW]],

        # 26 — everything, with no spare turns.
        [[cardName.BAT, cardName.SPARROW],
         [],
         [],
         [cardName.TURKEY_VULTURE],
         [],
         [cardName.BAT]],
    ))],

    # 27 — two 2-damage threats at once. Both die to a single hit, but only one
    # can be answered per turn, so the other lane is conceded or chumped.
    encounter(
        deck=[cardName.STOAT, cardName.STOAT, cardName.WOLF, cardName.BULLFROG],
        playerItems=[itemName.BOULDER_BOTTLE, itemName.PLIERS],
        moves=[
            [cardName.COYOTE, cardName.COYOTE],
            [],
            [cardName.COYOTE],
        ],
    ),

    # 28 — a 3/2 wolf outranges every cheap card here, so squirrels have to buy
    # the turns it takes to afford the wolf that trades with it.
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.BULLFROG, cardName.SPARROW],
        playerItems=[itemName.WISECLOCK, itemName.PLIERS],
        moves=[
            [cardName.WOLF],
            [],
            [cardName.WOLF],
        ],
    ),

    # 29 — the cub dies to a stoat on sight and is a 3/2 wolf two turns later.
    # Answer it early, or commit two bodies to your own wolf once it has grown.
    encounter(
        deck=[cardName.STOAT, cardName.STOAT, cardName.WOLF, cardName.SPARROW],
        playerItems=[itemName.SCISSORS, itemName.FROZEN_OPOSSUM_BOTTLE],
        moves=[
            [cardName.WOLF_CUB],
            [],
            [cardName.COYOTE],
        ],
    ),

    # 30 — encounter 2's opening with room to breathe: the same coyote and bat,
    # but idle turns before the cub arrives.
    encounter(
        deck=[cardName.STOAT, cardName.WOLF, cardName.WOLF, cardName.SPARROW],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        moves=[
            [cardName.COYOTE, cardName.BAT],
            [],
            [],
            [cardName.WOLF_CUB],
        ],
    ),

    # 31-33 — the same three fights again, handed a deck with real tools: a goat
    # that pays three blood on its own, a burrower, and maggots waiting in hand.
    encounter(deck=list(GOAT_DECK), playerItems=[itemName.HOGGY_BANK, itemName.SQUIRREL_BOTTLE],
              moves=[          # encounter 2's sequence
        [cardName.COYOTE, cardName.BAT],
        [],
        [cardName.WOLF_CUB],
        [],
        [cardName.COYOTE],
    ]),

    encounter(deck=list(GOAT_DECK), playerItems=[itemName.SKINNING_KNIFE, itemName.SQUIRREL_BOTTLE],
              moves=[          # encounter 28's sequence
        [cardName.WOLF],
        [],
        [cardName.WOLF],
    ]),

    encounter(deck=list(GOAT_DECK), playerItems=[itemName.HOGGY_BANK, itemName.FROZEN_OPOSSUM_BOTTLE],
              moves=[          # encounter 30's sequence
        [cardName.COYOTE, cardName.BAT],
        [],
        [],
        [cardName.WOLF_CUB],
    ]),

    # 34
    encounter(
        deck=[cardName.RACCOON, cardName.DIRE_WOLF_PUP, cardName.COYOTE,
              cardName.PACK_RAT, cardName.CUCKOO, cardName.RING_WORM],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.SQUIRREL_BOTTLE],
        playerBattle=[N, N, cardName.GRAND_FIR, N],
        leshyTotem=totem(cardType.AVIAN, sigil.MIGHTY_LEAP),
        moves=[
            [cardName.KINGFISHER, cardName.RAVEN_EGG, cardName.KINGFISHER],
            [],
            [cardName.RIVER_OTTER],
            [],
            [],
            [],
            [cardName.BULLFROG],
        ],
    ),

    # 35
    encounter(
        deck=[cardName.RACCOON, cardName.DIRE_WOLF_PUP, cardName.COYOTE,
              cardName.PACK_RAT, cardName.CUCKOO,
              deckCard(cardName.RING_WORM, attackMod=2), cardName.GOLDEN_PELT],
        playerItems=[itemName.FAN, itemName.PLIERS],
        playerBattle=[N, cardName.STUMP, N, N],
        leshyTotem=totem(cardType.REPTILE, sigil.GUARDIAN),
        moves=[
            [cardName.SKINK],
            [cardName.BULLFROG, cardName.SKINK],
            [cardName.ADDER],
        ],
    ),

    # 36
    encounter(
        deck=[deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE, cardName.PACK_RAT, cardName.CUCKOO,
              deckCard(cardName.RING_WORM, attackMod=2), cardName.GOLDEN_PELT,
              cardName.MUD_TURTLE],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.HOGGY_BANK],
        leshyTotem=totem(cardType.INSECT, sigil.RAMPAGER),
        moves=[
            [cardName.FLYING_ANT],
            [cardName.FLYING_ANT],
            [cardName.FLYING_ANT],
            [cardName.FLYING_ANT],
            [cardName.FLYING_ANT, cardName.FLYING_ANT],
            [cardName.WORKER_ANT],
            [cardName.SKINK, cardName.WORKER_ANT],
        ],
    ),

    # 37
    encounter(
        deck=[deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE, cardName.PACK_RAT, cardName.PACK_RAT, cardName.CUCKOO,
              deckCard(cardName.RING_WORM, attackMod=2), cardName.GOLDEN_PELT,
              deckCard(cardName.MUD_TURTLE, sigils=[sigil.LOOSE_TAIL]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER]),
              cardName.THE_WARREN],
        playerItems=[itemName.SKINNING_KNIFE, itemName.SQUIRREL_BOTTLE],
        leshyBattle=[cardName.GRAND_FIR, N, N, N],
        playerBattle=[N, N, cardName.BOULDER, N],
        leshyTotem=totem(cardType.CANINE, sigil.RAMPAGER),
        moves=[
            [cardName.RABBIT, cardName.PORCUPINE, cardName.DIRE_WOLF_PUP],
            [],
            [cardName.WOLF],
            [],
            [cardName.WOLF],
        ],
    ),

    # 38
    encounter(
        deck=[deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE, cardName.PACK_RAT, cardName.PACK_RAT, cardName.PACK_RAT,
              cardName.CUCKOO, deckCard(cardName.RING_WORM, attackMod=2),
              cardName.GOLDEN_PELT,
              deckCard(cardName.MUD_TURTLE, sigils=[sigil.LOOSE_TAIL]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER]),
              cardName.THE_WARREN, cardName.ANT_QUEEN],
        playerItems=[itemName.SCISSORS, itemName.PLIERS],
        leshyTotem=totem(cardType.AVIAN, sigil.HEFTY),
        moves=[
            [cardName.SPARROW, cardName.RAVEN],
            [],
            [cardName.PORCUPINE, cardName.SPARROW, cardName.RAVEN],
            [cardName.STOAT, cardName.PORCUPINE, cardName.SPARROW],
        ],
    ),

    # 39
    encounter(
        deck=[deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE, cardName.PACK_RAT,
              deckCard(cardName.PACK_RAT, attackMod=2, hpMod=2),
              cardName.CUCKOO, deckCard(cardName.RING_WORM, attackMod=2),
              cardName.GOLDEN_PELT,
              deckCard(cardName.MUD_TURTLE, sigils=[sigil.LOOSE_TAIL]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER]),
              cardName.THE_WARREN, cardName.ANT_QUEEN, cardName.MEALWORM],
        playerItems=[itemName.PLIERS, itemName.FAN],
        leshyTotem=totem(cardType.CANINE, sigil.STINKY),
        moves=[
            [cardName.RABBIT, cardName.PORCUPINE, cardName.COYOTE],
            [cardName.PORCUPINE, cardName.COYOTE],
            [cardName.SPARROW],
            [cardName.PORCUPINE, cardName.ALPHA],
        ],
    ),

    # 40
    encounter(
        deck=[deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE, cardName.PACK_RAT,
              deckCard(cardName.PACK_RAT, attackMod=2, hpMod=2),
              cardName.CUCKOO, deckCard(cardName.RING_WORM, attackMod=4),
              cardName.GOLDEN_PELT,
              deckCard(cardName.MUD_TURTLE, sigils=[sigil.LOOSE_TAIL]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER]),
              cardName.THE_WARREN, deckCard(cardName.ANT_QUEEN, sigils=[sigil.MORSEL]),
              cardName.MAGPIE, cardName.MANTIS],
        playerItems=[itemName.HOURGLASS, itemName.FROZEN_OPOSSUM_BOTTLE],
        leshyTotem=totem(cardType.HOOVED, sigil.STINKY),
        moves=[
            [cardName.MOOSE_BUCK, cardName.MOLE_MAN],
            [cardName.ELK_FAWN, cardName.MOLE],
            [cardName.ELK],
            [cardName.ELK],
            [],
            [cardName.ALPHA],
        ],
    ),

    # 41
    encounter(
        deck=[deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE, cardName.PACK_RAT,
              deckCard(cardName.PACK_RAT, attackMod=2, hpMod=2),
              deckCard(cardName.CUCKOO, sigils=[sigil.BIFURCATED_STRIKE],
                       attackMod=1, hpMod=1),
              cardName.DIRE_WOLF, deckCard(cardName.RING_WORM, attackMod=4),
              cardName.GOLDEN_PELT,
              deckCard(cardName.MUD_TURTLE, sigils=[sigil.LOOSE_TAIL]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.HOARDER]),
              cardName.THE_WARREN, deckCard(cardName.ANT_QUEEN, sigils=[sigil.MORSEL]),
              cardName.MAGPIE],
        playerItems=[itemName.FROZEN_OPOSSUM_BOTTLE, itemName.BOULDER_BOTTLE],
        leshyTotem=totem(cardType.HOOVED, sigil.TOUCH_OF_DEATH),
        moves=[
            [cardName.MOOSE_BUCK, cardName.MOLE_MAN],
            [cardName.PRONGHORN, cardName.ELK_FAWN],
            [cardName.ELK_FAWN, cardName.ELK],
            [],
            [cardName.ELK],
            [cardName.SKINK],
        ],
    ),

    # 42
    encounter(
        deck=[cardName.ANT_QUEEN, cardName.FLYING_ANT, cardName.SKUNK,
              cardName.MAGPIE, cardName.MEALWORM],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        moves=[
            [cardName.SKINK],
            [cardName.ADDER],
            [cardName.ADDER],
        ],
    ),

    # 43
    encounter(
        deck=[cardName.ANT_QUEEN, cardName.FLYING_ANT,
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              cardName.MAGPIE, cardName.MEALWORM],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        playerBattle=[cardName.GRAND_FIR, N, N, N],
        leshyTotem=totem(cardType.AVIAN, sigil.MIGHTY_LEAP),
        moves=[
            [cardName.BEEHIVE, cardName.KINGFISHER, cardName.KINGFISHER],
            [cardName.RIVER_OTTER],
            [],
            [cardName.RIVER_OTTER],
            [cardName.KINGFISHER],
        ],
    ),

    # 44
    encounter(
        deck=[cardName.ANT_QUEEN, cardName.FLYING_ANT,
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER]),
              cardName.MEALWORM],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        leshyBattle=[N, N, N, cardName.STUMP],
        playerBattle=[N, cardName.STUMP, N, N],
        leshyTotem=totem(cardType.REPTILE, sigil.MIGHTY_LEAP),
        moves=[
            [cardName.BULLFROG],
            [cardName.ADDER, cardName.COYOTE],
            [cardName.BULLFROG],
            [cardName.ADDER],
        ],
    ),

    # 45
    encounter(
        deck=[deckCard(cardName.FLYING_ANT, sigils=[sigil.ANT_SPAWNER], hpMod=2),
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER]),
              deckCard(cardName.RABBIT_PELT, sigils=[sigil.MORSEL]),
              cardName.RATTLER, cardName.CORPSE_MAGGOTS],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        leshyTotem=totem(cardType.AVIAN, sigil.GUARDIAN),
        moves=[
            [cardName.RAVEN, cardName.MOLE],
            [cardName.RAVEN_EGG],
            [],
            [cardName.COYOTE, cardName.SPARROW],
        ],
    ),

    # 46
    encounter(
        deck=[deckCard(cardName.FLYING_ANT, sigils=[sigil.ANT_SPAWNER], hpMod=2),
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER], hpMod=2),
              deckCard(cardName.RABBIT_PELT, sigils=[sigil.MORSEL]),
              cardName.RATTLER, cardName.CORPSE_MAGGOTS,
              deckCard(cardName.GREAT_WHITE, sigils=[sigil.BROOD_PARASITE, sigil.ANT_SPAWNER])],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        leshyBattle=[N, N, N, cardName.BOULDER],
        playerBattle=[N, N, cardName.FROZEN_OPOSSUM, N],
        leshyTotem=totem(cardType.AVIAN, sigil.WATERBORNE),
        moves=[
            [cardName.PORCUPINE, cardName.WILD_BULL, cardName.RABBIT],
            [cardName.PORCUPINE],
            [cardName.PRONGHORN],
            [cardName.WILD_BULL, cardName.RABBIT],
        ],
    ),

    # 47 — the first with a totem of your own.
    encounter(
        deck=[deckCard(cardName.FLYING_ANT, sigils=[sigil.ANT_SPAWNER], hpMod=2),
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER], hpMod=2),
              deckCard(cardName.RABBIT_PELT, sigils=[sigil.MORSEL]),
              cardName.RATTLER, cardName.CORPSE_MAGGOTS,
              deckCard(cardName.GREAT_WHITE, sigils=[sigil.BROOD_PARASITE, sigil.ANT_SPAWNER]),
              cardName.LAMMERGEIER],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        playerTotem=totem(cardType.AVIAN, sigil.TRINKET_BEARER),
        leshyTotem=totem(cardType.HOOVED, sigil.SHARP_QUILLS),
        moves=[
            [cardName.ELK_FAWN, cardName.ELK_FAWN],
            [cardName.ELK],
            [cardName.ELK_FAWN, cardName.PRONGHORN],
        ],
    ),

    # 48
    encounter(
        deck=[deckCard(cardName.FLYING_ANT, sigils=[sigil.ANT_SPAWNER], hpMod=4),
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER], hpMod=2),
              cardName.RATTLER, cardName.RATTLER, cardName.CORPSE_MAGGOTS,
              deckCard(cardName.GREAT_WHITE, sigils=[sigil.BROOD_PARASITE, sigil.ANT_SPAWNER]),
              cardName.LAMMERGEIER, cardName.COYOTE],
        playerItems=[itemName.BLACK_GOAT_BOTTLE, itemName.FROZEN_OPOSSUM_BOTTLE],
        playerTotem=totem(cardType.INSECT, sigil.TRINKET_BEARER),
        leshyTotem=totem(cardType.AVIAN, sigil.LOOSE_TAIL),
        moves=[
            [cardName.RAVEN, cardName.SPARROW],
            [],
            [cardName.PORCUPINE, cardName.RAVEN, cardName.COYOTE],
        ],
    ),

    # 49
    encounter(
        deck=[deckCard(cardName.FLYING_ANT, sigils=[sigil.ANT_SPAWNER], hpMod=4),
              cardName.FLYING_ANT,
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER], hpMod=2),
              cardName.RATTLER, cardName.RATTLER, cardName.CORPSE_MAGGOTS,
              deckCard(cardName.GREAT_WHITE, sigils=[sigil.BROOD_PARASITE, sigil.ANT_SPAWNER]),
              cardName.LAMMERGEIER, cardName.COYOTE],
        playerItems=[itemName.PLIERS, itemName.FROZEN_OPOSSUM_BOTTLE],
        playerBattle=[cardName.STUMP, N, N, N],
        playerTotem=totem(cardType.INSECT, sigil.TRINKET_BEARER),
        leshyTotem=totem(cardType.HOOVED, sigil.DOUBLE_STRIKE),
        moves=[
            [cardName.PRONGHORN, cardName.MOLE],
            [cardName.PORCUPINE],
            [cardName.ELK_FAWN, cardName.PORCUPINE, cardName.PRONGHORN],
        ],
    ),

    # 50
    encounter(
        deck=[deckCard(cardName.FLYING_ANT, sigils=[sigil.ANT_SPAWNER], hpMod=4),
              cardName.FLYING_ANT,
              deckCard(cardName.SKUNK, sigils=[sigil.BEES_WITHIN]),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER], hpMod=2),
              deckCard(cardName.WORKER_ANT, sigils=[sigil.AIRBORNE, sigil.HOARDER]),
              cardName.RATTLER, cardName.RATTLER, cardName.CORPSE_MAGGOTS,
              deckCard(cardName.GREAT_WHITE, sigils=[sigil.BROOD_PARASITE, sigil.ANT_SPAWNER]),
              cardName.LAMMERGEIER, cardName.COYOTE, cardName.BLOODHOUND],
        playerItems=[itemName.SCISSORS, itemName.SQUIRREL_BOTTLE],
        leshyBattle=[cardName.BOULDER, N, N, N],
        playerBattle=[N, N, cardName.GRAND_FIR, N],
        playerTotem=totem(cardType.INSECT, sigil.TRINKET_BEARER),
        leshyTotem=totem(cardType.CANINE, sigil.DOUBLE_STRIKE),
        moves=[
            [cardName.PORCUPINE, cardName.PORCUPINE],
            [cardName.DIRE_WOLF],
            [cardName.WOLF_CUB, cardName.COYOTE],
            [cardName.WOLF],
            [cardName.BLOODHOUND, cardName.ALPHA],
        ],
    ),

    # 51
    encounter(
        deck=[cardName.RACCOON, cardName.DIRE_WOLF_PUP, cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL])],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        leshyTotem=totem(cardType.AVIAN, sigil.GUARDIAN),
        moves=[
            [cardName.MOLE, cardName.RAVEN_EGG],
            [],
            [],
            [cardName.RAVEN_EGG],
        ],
    ),

    # 52
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL])],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        leshyBattle=[N, N, N, cardName.BOULDER],
        leshyTotem=totem(cardType.AVIAN, sigil.SPRINTER),
        moves=[
            [cardName.RAVEN_EGG],
            [cardName.CUCKOO],
            [],
            [cardName.RAVEN_EGG],
        ],
    ),

    # 53
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1),
              cardName.RABBIT_PELT],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        leshyTotem=totem(cardType.HOOVED, sigil.WATERBORNE),
        moves=[
            [cardName.ELK, cardName.MOLE],
            [cardName.ELK_FAWN],
        ],
    ),

    # 54
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1, hpMod=2),
              cardName.RABBIT_PELT, cardName.PACK_RAT, cardName.FIELD_MICE],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        leshyTotem=totem(cardType.REPTILE, sigil.SPRINTER),
        moves=[
            [cardName.BULLFROG, cardName.BULLFROG],
            [cardName.ADDER],
            [],
            [cardName.ADDER, cardName.BULLFROG],
        ],
    ),

    # 55
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1, hpMod=2),
              cardName.RABBIT_PELT, cardName.PACK_RAT, cardName.DIRE_WOLF,
              deckCard(cardName.MEALWORM, sigils=[sigil.FECUNDITY])],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        playerBattle=[N, cardName.GRAND_FIR, N, N],
        leshyTotem=totem(cardType.AVIAN, sigil.GUARDIAN),
        moves=[
            [cardName.KINGFISHER, cardName.KINGFISHER, cardName.COYOTE],
            [cardName.SPARROW],
            [cardName.RAVEN],
            [cardName.BAT, cardName.CUCKOO],
            [cardName.RAVEN, cardName.TURKEY_VULTURE],
        ],
    ),

    # 56
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1, hpMod=2),
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], hpMod=2),
              cardName.RABBIT_PELT, cardName.PACK_RAT, cardName.DIRE_WOLF,
              deckCard(cardName.MEALWORM, sigils=[sigil.FECUNDITY]),
              cardName.BLOODHOUND],
        playerItems=[itemName.BLACK_GOAT_BOTTLE, itemName.PLIERS],
        leshyTotem=totem(cardType.INSECT, sigil.STINKY),
        moves=[
            [cardName.WORKER_ANT, cardName.WORKER_ANT, cardName.BEE],
            [cardName.MANTIS, cardName.MANTIS],
            [cardName.WORKER_ANT, cardName.FLYING_ANT],
            [],
            [cardName.WORKER_ANT, cardName.BEE],
        ],
    ),

    # 57
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1, hpMod=2),
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], hpMod=2),
              cardName.RABBIT_PELT, cardName.PACK_RAT, cardName.PACK_RAT, cardName.DIRE_WOLF,
              deckCard(cardName.MEALWORM, sigils=[sigil.FECUNDITY]),
              cardName.BLOODHOUND,
              deckCard(cardName.BULLFROG, sigils=[sigil.RABBIT_HOLE, sigil.TRINKET_BEARER]),
              cardName.GRIZZLY],
        playerItems=[itemName.BLACK_GOAT_BOTTLE, itemName.HOURGLASS],
        leshyTotem=totem(cardType.AVIAN, sigil.LOOSE_TAIL),
        moves=[
            [cardName.SPARROW, cardName.RAVEN],
            [],
            [cardName.COYOTE, cardName.PORCUPINE, cardName.RAVEN],
            [cardName.PORCUPINE, cardName.STOAT, cardName.COYOTE],
            [cardName.RAVEN],
        ],
    ),

    # 58 — the two pack rats merged at the mycologist.
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1, hpMod=2),
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], hpMod=2),
              cardName.RABBIT_PELT, deckCard(cardName.PACK_RAT, attackMod=2, hpMod=2),
              cardName.DIRE_WOLF,
              deckCard(cardName.MEALWORM, sigils=[sigil.FECUNDITY]),
              cardName.BLOODHOUND,
              deckCard(cardName.BULLFROG, sigils=[sigil.RABBIT_HOLE, sigil.TRINKET_BEARER]),
              cardName.GRIZZLY, cardName.GRIZZLY],
        playerItems=[itemName.SCISSORS, itemName.HOURGLASS],
        leshyTotem=totem(cardType.CANINE, sigil.BIFURCATED_STRIKE),
        moves=[
            [cardName.PORCUPINE, cardName.COYOTE, cardName.RABBIT],
            [cardName.WOLF, cardName.SPARROW, cardName.COYOTE],
            [cardName.SPARROW],
            [cardName.ALPHA, cardName.ALPHA],
            [cardName.COYOTE, cardName.PORCUPINE],
        ],
    ),

    # 59
    encounter(
        deck=[cardName.DIRE_WOLF_PUP,
              deckCard(cardName.DIRE_WOLF_PUP, sigils=[sigil.SCAVENGER]),
              cardName.COYOTE,
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], attackMod=1, hpMod=2),
              deckCard(cardName.THE_WARREN, sigils=[sigil.MORSEL], hpMod=2),
              cardName.RABBIT_PELT, deckCard(cardName.PACK_RAT, attackMod=2, hpMod=2),
              cardName.DIRE_WOLF,
              deckCard(cardName.MEALWORM, sigils=[sigil.FECUNDITY]),
              cardName.BLOODHOUND,
              deckCard(cardName.BULLFROG, sigils=[sigil.RABBIT_HOLE, sigil.TRINKET_BEARER]),
              cardName.GRIZZLY, cardName.GRIZZLY, cardName.RED_HART],
        playerItems=[itemName.FAN],
        playerBattle=[cardName.BOULDER, N, N, N],
        leshyTotem=totem(cardType.HOOVED, sigil.TOUCH_OF_DEATH),
        moves=[
            [cardName.MOLE, cardName.PRONGHORN],
            [cardName.ALPHA],
            [cardName.ELK_FAWN, cardName.PRONGHORN, cardName.ELK_FAWN],
            [cardName.ELK_FAWN],
        ],
    ),

    # 60 — squirrels are waterborne, and the geck feeds on what it kills.
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST]),
              cardName.TADPOLE, cardName.MAGPIE, cardName.RABBIT],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        waterborneSquirrels=True,
        leshyBattle=[cardName.BOULDER, N, N, N],
        playerBattle=[N, N, cardName.FROZEN_OPOSSUM, N],
        leshyTotem=totem(cardType.HOOVED, sigil.MIGHTY_LEAP),
        moves=[
            [cardName.WILD_BULL, cardName.RABBIT],
            [cardName.RABBIT],
        ],
    ),

    # 61
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST]),
              cardName.TADPOLE, cardName.MAGPIE, cardName.RABBIT,
              deckCard(cardName.RING_WORM, attackMod=2), cardName.MEALWORM],
        playerItems=[itemName.SQUIRREL_BOTTLE, itemName.PLIERS],
        waterborneSquirrels=True,
        leshyTotem=totem(cardType.AVIAN, sigil.GUARDIAN),
        moves=[
            [cardName.RAVEN, cardName.MOLE],
            [],
            [],
            [],
            [cardName.RAVEN_EGG],
            [cardName.RAVEN_EGG],
        ],
    ),

    # 62
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST]),
              cardName.TADPOLE, cardName.MAGPIE, cardName.RABBIT,
              deckCard(cardName.RING_WORM, attackMod=2), cardName.MEALWORM,
              deckCard(cardName.ANT_QUEEN, sigils=[sigil.WORTHY_SACRIFICE]),
              cardName.GREAT_WHITE],
        playerItems=[itemName.BLACK_GOAT_BOTTLE, itemName.SQUIRREL_BOTTLE],
        waterborneSquirrels=True,
        leshyBattle=[N, N, cardName.STUMP, N],
        leshyTotem=totem(cardType.INSECT, sigil.HEFTY),
        moves=[
            [cardName.TADPOLE, cardName.BEE],
            [cardName.CUCKOO],
            [cardName.MANTIS, cardName.BEE],
            [cardName.BEEHIVE],
            [cardName.BEE, cardName.CUCKOO],
        ],
    ),

    # 63
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST]),
              cardName.TADPOLE, cardName.MAGPIE,
              deckCard(cardName.RING_WORM, attackMod=2), cardName.MEALWORM,
              deckCard(cardName.ANT_QUEEN, sigils=[sigil.WORTHY_SACRIFICE]),
              cardName.GREAT_WHITE, cardName.RABBIT_PELT],
        playerItems=[itemName.BLACK_GOAT_BOTTLE, itemName.SQUIRREL_BOTTLE],
        waterborneSquirrels=True,
        leshyTotem=totem(cardType.REPTILE, sigil.BURROWER),
        moves=[
            [cardName.BEEHIVE, cardName.RATTLER],
            [cardName.ADDER, cardName.ALPHA],
            [cardName.RATTLER],
            [cardName.ADDER, cardName.BEEHIVE],
        ],
    ),

    # 64
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST]),
              cardName.TADPOLE, cardName.MAGPIE, cardName.MEALWORM,
              deckCard(cardName.ANT_QUEEN, sigils=[sigil.WORTHY_SACRIFICE]),
              cardName.GREAT_WHITE, cardName.RABBIT_PELT, cardName.CORPSE_MAGGOTS],
        playerItems=[itemName.BLACK_GOAT_BOTTLE, itemName.SQUIRREL_BOTTLE],
        waterborneSquirrels=True,
        leshyBattle=[N, N, cardName.STUMP, N],
        leshyTotem=totem(cardType.AVIAN, sigil.STINKY),
        moves=[
            [cardName.BULLFROG, cardName.SPARROW, cardName.KINGFISHER],
            [cardName.SPARROW],
            [cardName.RAVEN],
            [cardName.COYOTE],
            [cardName.RAVEN_EGG],
        ],
    ),

    # 65
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST]),
              cardName.MAGPIE,
              deckCard(cardName.MEALWORM, sigils=[sigil.WATERBORNE, sigil.FLEDGLING], hpMod=4),
              deckCard(cardName.ANT_QUEEN, sigils=[sigil.WORTHY_SACRIFICE]),
              cardName.GREAT_WHITE, cardName.CORPSE_MAGGOTS,
              cardName.TURKEY_VULTURE, cardName.WILD_BULL,
              deckCard(cardName.FLYING_ANT, sigils=[sigil.UNKILLABLE, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.TRINKET_BEARER, sigil.STINKY]),
              cardName.RABBIT_PELT],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        waterborneSquirrels=True,
        playerBattle=[cardName.GRAND_FIR, N, N, N],
        leshyTotem=totem(cardType.HOOVED, sigil.BLOOD_LUST),
        moves=[
            [cardName.PRONGHORN, cardName.MOLE],
            [cardName.PORCUPINE],
            [cardName.ALPHA, cardName.PRONGHORN, cardName.ELK_FAWN],
            [cardName.ELK_FAWN],
            [cardName.PORCUPINE],
        ],
    ),

    # 66
    encounter(
        deck=[deckCard(cardName.GECK, sigils=[sigil.BLOOD_LUST], hpMod=4),
              cardName.MAGPIE,
              deckCard(cardName.MEALWORM, sigils=[sigil.WATERBORNE, sigil.FLEDGLING], hpMod=4),
              deckCard(cardName.ANT_QUEEN, sigils=[sigil.WORTHY_SACRIFICE]),
              cardName.GREAT_WHITE, cardName.CORPSE_MAGGOTS,
              cardName.TURKEY_VULTURE, cardName.WILD_BULL,
              deckCard(cardName.FLYING_ANT, sigils=[sigil.UNKILLABLE, sigil.STINKY]),
              deckCard(cardName.FLYING_ANT, sigils=[sigil.TRINKET_BEARER, sigil.STINKY]),
              cardName.RABBIT_PELT, cardName.GRIZZLY],
        playerItems=[itemName.SQUIRREL_BOTTLE],
        waterborneSquirrels=True,
        leshyTotem=totem(cardType.AVIAN, sigil.DOUBLE_STRIKE),
        moves=[
            [cardName.RAVEN, cardName.COYOTE],
            [],
            [cardName.RAVEN, cardName.PORCUPINE, cardName.COYOTE],
            [cardName.STOAT, cardName.COYOTE, cardName.PORCUPINE],
            [cardName.RAVEN],
        ],
    ),
]


# One encounter from each group of encounters that share a deck or a Leshy script,
# drawn at random. Training never sees these; they measure how the agent does on
# battles it was not trained on.
TEST_ENCOUNTERS = [1, 3, 7, 12, 16, 19, 29, 32, 39, 45, 59, 61]

TRAIN_SET = [e for n, e in enumerate(ENCOUNTERS, 1) if n not in TEST_ENCOUNTERS]
TEST_SET = [ENCOUNTERS[n - 1] for n in TEST_ENCOUNTERS]
