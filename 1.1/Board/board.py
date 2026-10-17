from dataclasses import dataclass
from enum import Enum, auto
from Card.card import card, CARD_FEATURES, STAT_CAP, SIGIL_INDEX
from Card.cardData import CARDS, cardDef, SPAWNS_ON_DEATH
from Card.cardName import cardName
from Card.cardType import cardType
from Card.costType import costType
from Card.power import powerContext
from Card.attackType import attackType
from Card.sigil import sigil
from Board.totem import totem
from Board.moves import move
from Item.itemName import itemName
from Item.itemData import (ITEM_INDEX, BOTTLED, TARGETS_LANE, TARGETS_DECK,
                           UNUSABLE, POSSIBLE_ITEMS, PLIERS_SCALES, HOGGY_BANK_BONES)
from bisect import insort
import random
import numpy as np

SQUIRREL_COUNT = 10
INITIAL_DRAW = 3
N_LANES = 4
N_ROWS = 3
MAX_HAND = 30
MAX_DECK = 99

# Action ids are fixed for the life of a trained model; renumbering invalidates it.
ACT_SELECT_HAND = 0                          # 0..29  select hand position i
ACT_PLACE_LANE = ACT_SELECT_HAND + MAX_HAND  # 30..33 place cardToPlay in lane i
ACT_DRAW_DECK = ACT_PLACE_LANE + N_LANES     # 34
ACT_DRAW_SQUIRREL = ACT_DRAW_DECK + 1        # 35
ACT_RING_BELL = ACT_DRAW_SQUIRREL + 1        # 36
# One id per lane set, as a bitmask: bit i means lane i is spent. 0b0011 is lanes 0 and 1.
ACT_SACRIFICE_SET = ACT_RING_BELL + 1        # 37..52
N_SACRIFICE_SETS = 1 << N_LANES              # 16

# A run normally carries three items. One of the challenge modifiers caps it at
# a single item, so this is the number to change when that is modelled.
MAX_ITEMS = 2

ACT_USE_ITEM = ACT_SACRIFICE_SET + N_SACRIFICE_SETS   # 53..54  use item in slot i
ACT_ITEM_LANE = ACT_USE_ITEM + MAX_ITEMS              # 55..58  aim it at leshy's lane i
ACT_LENS_PICK = ACT_ITEM_LANE + N_LANES               # 59..157 take deck slot i
N_ACTIONS = ACT_LENS_PICK + MAX_DECK                  # 158


def laneSet(mask: int):
    """The lanes a sacrifice-set bitmask names."""
    return [i for i in range(N_LANES) if mask >> i & 1]

# Neither side is obliged to act, so a stalled battle still has to end.
MAX_TURNS = 50

# The encoder clips here; past this many bones, more changes no decision.
BONE_CAP = 20.0

# Brood Parasite lays a broken egg most of the time, a raven egg occasionally.
BROOD_RAVEN_CHANCE = 0.10

SPAWNERS = frozenset({sigil.FECUNDITY, sigil.RABBIT_HOLE, sigil.ANT_SPAWNER})

# Two extra numbers board cards don't need: the cost, and whether it is bones.
HAND_FEATURES = CARD_FEATURES + 2

# Reused for every empty slot, so it must never be written to.
EMPTY_SLOT = np.zeros(CARD_FEATURES, dtype=np.float32)

NAME_INDEX = {n: i for i, n in enumerate(cardName)}


def handSortKey(c: card):
    """Hand order means nothing in game, so the hand is kept in one canonical
    order. The encoder's hand slots and the select-hand action ids both index
    straight into it, so this is the single definition both rely on."""
    return (c.name.value, c.attack(), c.hp)


def deckSortKey(c: card):
    """The hand's key plus sigils. Two cards that tie here encode identically, so
    no ordering of the shuffled deck can survive into the observation."""
    return (c.name.value, c.attack(), c.hp,
            tuple(sorted(SIGIL_INDEX[s] for s in c.sigils)))

class result(Enum):
    WIN = auto()
    NOT_FINISHED = auto()
    LOSE = auto()


@dataclass
class board:
    scales: int = 0
    squirrelDeck: int = SQUIRREL_COUNT
    leshyNextCards: list[card | None] = None
    leshyBattleCards: list[card | None] = None
    leshyMoveSequence: list[move] = None
    playerBattleCards: list[card | None] = None
    playerHand: list[card] = None
    playerDeck: list[card] = None
    cardToPlay: card = None
    hasSacrificed: bool = False
    hasDrawnCard: bool = True
    turn: int = 0
    bones: int = 0
    playerTotem: totem = None
    leshyTotem: totem = None
    playerItems: list[itemName] = None
    itemToUse: itemName = None
    leshySkipped: bool = False
    sacrificesThisTurn: int = 0
    hoarding: bool = False
    waterborneSquirrels: bool = False

    def __post_init__(self):
        if self.leshyNextCards is None:
            self.leshyNextCards = [None] * 4
        if self.leshyBattleCards is None:
            self.leshyBattleCards = [None] * 4
        if self.playerBattleCards is None:
            self.playerBattleCards = [None] * 4
        if self.leshyMoveSequence is None:
            self.leshyMoveSequence = []
        if self.playerHand is None:
            self.playerHand = []
        if self.playerDeck is None:
            self.playerDeck = []
        if self.playerItems is None:
            self.playerItems = []

    def populate_board(self, playerCards: list[card | None], leshyCards: list[card | None],
                       playerDeck: list[card | None], leshyNextCards: list[card | None], leshyMoves: list[move],
                       playerTotem: totem = None, leshyTotem: totem = None,
                       playerItems: list[itemName] = None,
                       openingHand: list[card] = None,
                       waterborneSquirrels: bool = False):
        self.waterborneSquirrels = waterborneSquirrels
        self.playerTotem = playerTotem
        self.leshyTotem = leshyTotem
        self.playerItems = list(playerItems) if playerItems else []
        self.playerBattleCards = [self.applyTotem(c, playerTotem) for c in playerCards]
        self.leshyBattleCards = [self.applyTotem(c, leshyTotem) for c in leshyCards]
        self.leshyNextCards = [self.applyTotem(c, leshyTotem) for c in leshyNextCards]
        self.playerDeck = [self.applyTotem(c, playerTotem) for c in playerDeck]
        self.leshyMoveSequence = leshyMoves
        if openingHand:
            self.playerDeck = [c for c in self.playerDeck
                               if not any(c is h for h in openingHand)]
        random.shuffle(self.playerDeck)

        if openingHand:
            for c in openingHand:
                self.addToHand(c)
        else:
            #fair hand
            for i in range(len(self.playerDeck)):
                if self.playerDeck[i].cost <=1 and not self.playerDeck[i].isTerrain():
                    self.addToHand(self.playerDeck.pop(i))
                    break
                #If no cards with 0 or 1 cost, just take one normally
                if i == len(self.playerDeck):
                    self.addToHand(self.playerDeck.pop())

            #-1 for fair hand
            for i in range(INITIAL_DRAW - 1):
                self.addToHand(self.playerDeck.pop())
        self.addToHand(self.makeSquirrel())
        self.squirrelDeck-= 1

        self.refillLeshyQueue()
        self.hasDrawnCard = True

    def applyTotem(self, c: card | None, t: totem):
        """Grant a totem's sigil. Called once per card created, never on transfer."""
        if c is None or t is None:
            return c
        if c.type is t.affectedType or c.name is cardName.AMALGAM:
            c.addSigil(t.imposedSigil)
        return c

    def queueLane(self):
        """Where Leshy queues his next card: against a player card that can hurt him
        first, then where you have nothing, then any lane he holds nothing in, and
        only then wherever a queue spot is left. Several lanes fitting the same
        rule are chosen between at random. None when every spot is taken."""
        def rank(lane):
            held = self.leshyBattleCards[lane] is not None
            yours = self.playerBattleCards[lane]
            if held:
                return 3
            if yours is not None and yours.attack(self.powerContextFor(
                    self.playerBattleCards, lane, self.leshyBattleCards)) >= 1:
                return 0
            return 1 if yours is None else 2

        ranks = {lane: rank(lane) for lane in range(N_LANES)
                 if self.leshyNextCards[lane] is None}
        if not ranks:
            return None
        best = min(ranks.values())
        return random.choice([lane for lane, r in ranks.items() if r == best])

    def refillLeshyQueue(self):
        """Queue the next turn's cards. A card with no queue spot left is lost, not
        carried to the following turn."""
        if not self.leshyMoveSequence:
            return
        for c in self.leshyMoveSequence.pop(0).cards:
            lane = self.queueLane()
            if lane is None:
                break
            self.leshyNextCards[lane] = self.applyTotem(c, self.leshyTotem)


    def makeSquirrel(self):
        """A fresh squirrel from the pile, waterborne when the battle says so."""
        c = card(CARDS[cardName.SQUIRREL])
        if self.waterborneSquirrels:
            c.addSigil(sigil.WATERBORNE)
        return c

    def addToHand(self, c: card):
        """The only way a card enters the hand, so the hand is always sorted."""
        insort(self.playerHand, c, key=handSortKey)

    def selectCardToPlay(self, handIdx):
        """Selects Card to play, returns sacrifice cost necessary.

        A chosen card cannot be swapped for another, since the board has not
        changed and a swap could only reach a card that was already selectable.
        Ringing the bell does put it back, so a selection is never a trap.
        """
        if handIdx not in range(len(self.playerHand)) or\
            self.cardToPlay is not None or\
            not self.canAfford(self.playerHand[handIdx]) or\
            self.hasSacrificed or\
            not self.hasDrawnCard:
            return None
        self.cardToPlay = self.playerHand.pop(handIdx)
        return self.cardToPlay.cost

    def paysFor(self, lanes, cost):
        """A set must cover the cost with none of it spare — the game stops you once it is paid."""
        blood = [self.playerBattleCards[i].bloodValue() for i in lanes]
        return sum(blood) >= cost and all(sum(blood) - b < cost for b in blood)

    def sacrificeCards(self, cardIdxToSacrifice):
        """Sacrifices cards to play cardToPlay"""
        if  self.hasSacrificed or\
            self.cardToPlay is None or\
            any(i not in range(N_LANES) for i in cardIdxToSacrifice) or\
            any(self.playerBattleCards[i] is None or self.playerBattleCards[i].isTerrain() for i in cardIdxToSacrifice) or\
            len(set(cardIdxToSacrifice)) != len(cardIdxToSacrifice) or\
            not self.paysFor(cardIdxToSacrifice, self.cardToPlay.cost):
            return None

        morsels = [(self.playerBattleCards[i].attack(self.powerContextFor(
                        self.playerBattleCards, i, self.leshyBattleCards)),
                    self.playerBattleCards[i].hp)
                   for i in cardIdxToSacrifice if self.playerBattleCards[i].isMorsel()]

        self.hasSacrificed = True
        self.sacrificesThisTurn += len(cardIdxToSacrifice)
        for cardIdx in cardIdxToSacrifice:
            self.playerBattleCards[cardIdx].kill()
            self.cardDied(self.playerBattleCards[cardIdx], cardIdx, self.playerBattleCards)

        self.cardToPlay.attackMod += sum(a for a, _ in morsels)
        self.cardToPlay.hpMod += sum(h for _, h in morsels)

    def playCard(self, lane):
        """Plays cardToPlay on lane if lane is unobstructed"""
        if self.cardToPlay is None or\
            self.needsSacrifice() or\
            lane not in range(N_LANES) or\
            self.playerBattleCards[lane] is not None:
            return None

        if self.cardToPlay.currency is costType.BONES:
            self.bones -= self.cardToPlay.cost

        self.playerBattleCards[lane] = self.cardToPlay
        self.cardPlaced(self.cardToPlay, lane, self.leshyBattleCards)
        self.cardToPlay = None
        self.hasSacrificed = False

    def canAfford(self, c: card):
        """Whether c could be selected, paid for, and placed right now."""
        onBoard = sum(1 for x in self.playerBattleCards if x is not None)

        if c.currency is costType.BONES:
            return c.cost <= self.bones and onBoard < N_LANES

        sacrificeable = sum(x.bloodValue() for x in self.playerBattleCards
                            if x is not None and not x.isTerrain())
        if c.cost > sacrificeable:
            return False

        #For inserting 0 cost cards, which need one empty field
        return c.cost > 0 or onBoard < N_LANES

    def needsSacrifice(self):
        """True when a card is selected and its cost is still unpaid, so the
        only actions on offer are the sacrifice sets. Bone cards never pay
        this way — their cost comes off the counter when they are placed."""
        return self.cardToPlay is not None and\
            self.cardToPlay.currency is costType.BLOOD and\
            not self.cardToPlay.cost == 0 and\
            not self.hasSacrificed

    def legalActions(self):
        """Boolean mask over the action ids. The phase is derived from
        cardToPlay and hasSacrificed rather than stored separately."""
        mask = np.zeros(N_ACTIONS, dtype=bool)

        if self.hoarding or self.itemToUse in TARGETS_DECK:
            for slot in range(min(len(self.playerDeck), MAX_DECK)):
                mask[ACT_LENS_PICK + slot] = True
            return mask

        if self.itemToUse in TARGETS_LANE:
            for lane in range(N_LANES):
                if self.leshyBattleCards[lane] is not None:
                    mask[ACT_ITEM_LANE + lane] = True
            mask[ACT_RING_BELL] = True
            return mask

        if self.needsSacrifice():
            # Sets of exactly the right size, using only spendable lanes.
            cost = self.cardToPlay.cost
            spendable = self.spendableLanes()
            for m in range(N_SACRIFICE_SETS):
                lanes = laneSet(m)
                if all(i in spendable for i in lanes) and self.paysFor(lanes, cost):
                    mask[ACT_SACRIFICE_SET + m] = True
            # Putting the card back down beats being forced to spend your own line.
            mask[ACT_RING_BELL] = True
            return mask

        if not self.hasDrawnCard:
            if self.playerDeck:
                mask[ACT_DRAW_DECK] = True
            if self.squirrelDeck > 0:
                mask[ACT_DRAW_SQUIRREL] = True

        else:
            if self.cardToPlay is None:
                for slot, c in enumerate(self.playerHand[:MAX_HAND]):
                    if self.canAfford(c):
                        mask[ACT_SELECT_HAND + slot] = True
                for slot, i in enumerate(self.playerItems):
                    if self.canUseItem(i):
                        mask[ACT_USE_ITEM + slot] = True
                mask[ACT_RING_BELL] = True

            if self.canPlayCard():
                for lane in range(N_LANES):
                    if self.playerBattleCards[lane] is None:
                        mask[ACT_PLACE_LANE + lane] = True

        return mask

    def canPlayCard(self):
        """Held and paid for — free, bones, or blood already sacrificed."""
        return self.cardToPlay is not None and not self.needsSacrifice()

    def spendableLanes(self):
        """Lanes holding a card that can be sacrificed. Terrain occupies a
        lane but cannot be spent."""
        return [i for i, c in enumerate(self.playerBattleCards)
                if c is not None and not c.isTerrain()]

    def applyAction(self, actionId):
        """Run whatever action an id names."""
        if actionId < ACT_PLACE_LANE:
            return self.selectCardToPlay(actionId - ACT_SELECT_HAND)
        if actionId < ACT_DRAW_DECK:
            return self.playCard(actionId - ACT_PLACE_LANE)
        if actionId == ACT_DRAW_DECK:
            return self.drawCard()
        if actionId == ACT_DRAW_SQUIRREL:
            return self.drawSquirrel()
        if actionId == ACT_RING_BELL:
            return self.endPlayerTurn()
        if actionId < ACT_USE_ITEM:
            return self.sacrificeCards(laneSet(actionId - ACT_SACRIFICE_SET))
        if actionId < ACT_ITEM_LANE:
            return self.selectItem(actionId - ACT_USE_ITEM)
        if actionId < ACT_LENS_PICK:
            return self.aimItem(actionId - ACT_ITEM_LANE)
        return self.lensPick(actionId - ACT_LENS_PICK)

    def endPlayerTurn(self):
        """Ring the bell: every player card strikes the lane opposite it."""
        if self.hasSacrificed or self.hoarding:
            return None, 0

        if self.cardToPlay is not None:
            self.addToHand(self.cardToPlay)
            self.cardToPlay = None

        if self.itemToUse is not None:
            self.gainItem(self.itemToUse)
            self.itemToUse = None


        for lane, attacker in enumerate(self.playerBattleCards):
            if attacker is None:
                continue
            ctx = self.powerContextFor(self.playerBattleCards, lane,
                                       self.leshyBattleCards)
            if attacker.attack(ctx) == 0:
                continue

            self.strikeLane(lane, attacker, self.playerBattleCards,
                            self.leshyBattleCards, 1, self.leshyNextCards)

        if (self.squirrelDeck > 0 or self.playerDeck):
            self.hasDrawnCard = False
        self.turn += 1
        self.sacrificesThisTurn = 0

        self.applyEndOfOwnTurn(self.playerBattleCards)
        if not self.leshySkipped:
            self.applyEndOfOpponentTurn(self.leshyBattleCards)

        if self.scales >= 5:
            return result.WIN, self.scales
        return result.NOT_FINISHED, 0


    def powerContextFor(self, attackers: list[card | None], lane: int,
                        defenders: list[card | None]):
        return powerContext(tuple(attackers), self.sacrificesThisTurn, self.bones,
                            len(self.playerHand), defenders[lane], lane)

    def releaseBees(self, *cards: card | None):
        """A card with bees within owes one for every time it took damage. They
        always go to you, whichever side the card is on."""
        for c in cards:
            while c is not None and c.bees:
                c.bees -= 1
                self.addToHand(self.applyTotem(card(CARDS[cardName.BEE]), self.playerTotem))

    def reacts(self, row: list[card | None]):
        """Whether a row's cards answer what is done to them. An hourglass stops
        Leshy's whole side until his turn, so nothing of his reacts in between."""
        return row is self.playerBattleCards or not self.leshySkipped

    def strike(self, lane: int, attacker: card, defenders: list[card|None],
               sign: int, queued: list[card|None] = None,
               attackers: list[card|None] = None, home: int = None):
        """One attack into a lane, carrying overkill through to whatever is queued behind it.
        home is the lane the attacker stands in, when it is not the one being struck."""
        defender = defenders[lane]
        overkill_target = queued[lane] if queued is not None else None
        ctx = self.powerContextFor(attackers if attackers is not None else (),
                                   lane if home is None else home, defenders)
        reacts = self.reacts(defenders)
        if defender is None and reacts:
            defender = self.burrow(lane, defenders, attacker)

        if defender is None or defender.isWaterborne():
            self.scales += sign * attacker.attack(ctx)
            return

        if defender.shedsTail() and reacts:
            defender = self.shedTail(lane, defender, defenders)

        self.scales += sign * attacker.battle(defender, ctx, reacts)
        if reacts:
            self.ringChime(defender, attacker, defenders)

        if defender.hp <= 0:
            self.cardDied(defender, lane, defenders)
            self.corpseEater(lane, defenders)
            if attacker.hasBloodLust():
                attacker.attackMod += 1
            if overkill_target is not None:
                overkill_target.hurt(-defender.hp, attacker, reacts=reacts)
                if overkill_target.hp <= 0:
                    self.cardDied(overkill_target, lane, queued)
                    if attacker.hasBloodLust():
                        attacker.attackMod += 1

        self.releaseBees(attacker, defender, overkill_target)

    def strikeLane(self, lane: int, attacker: card, attackers: list[card|None],
                   defenders: list[card|None], sign: int, queued: list[card|None] = None):
        """Every strike one attacker gets, stopping early if something kills it back."""
        targets = [lane + o for o in attacker.strikeOffsets() if lane + o in range(N_LANES)]
        for target in targets:
            self.strike(target, attacker, defenders, sign, queued, attackers, lane)
            # Quills or a steel trap can kill the attacker on the way in.
            if attacker.hp <= 0:
                if attackers[lane] is attacker:
                    self.cardDied(attacker, lane, attackers)
                self.corpseEater(lane, attackers)
                return

    def leshyTurn(self):
        # An hourglass stops him placing, attacking and moving, but your own cards
        # still finish their round, so your fledglings grow and his do not.
        if self.leshySkipped:
            self.leshySkipped = False
            self.applyEndOfOpponentTurn(self.playerBattleCards)
            return result.NOT_FINISHED

        for lane, next_card in enumerate(self.leshyNextCards):
            if next_card is None:
                continue
            if self.leshyBattleCards[lane] is None:
                self.leshyBattleCards[lane] = next_card
                self.leshyNextCards[lane] = None
                self.cardPlaced(next_card, lane, self.playerBattleCards)

        for lane, attacker in enumerate(self.leshyBattleCards):
            if attacker is None:
                continue
            ctx = self.powerContextFor(self.leshyBattleCards, lane,
                                       self.playerBattleCards)
            if attacker.attack(ctx) == 0:
                continue

            self.strikeLane(lane, attacker, self.leshyBattleCards,
                            self.playerBattleCards, -1)

        self.applyEndOfOwnTurn(self.leshyBattleCards)
        self.applyEndOfOpponentTurn(self.playerBattleCards)

        if self.scales <= -5:
            return result.LOSE
        return result.NOT_FINISHED

    def moveCard(self, c: card, lane: int, targetLane:int, movementType:sigil, battleCards: list[card|None]):
        match(movementType):
            case sigil.SPRINTER:
                if targetLane not in range(N_LANES) or battleCards[targetLane] is not None:
                    targetLane = lane - c.direction
                    if targetLane not in range(N_LANES) or battleCards[targetLane] is not None:
                        return
                    c.direction*=-1
                battleCards[targetLane] = c
                battleCards[lane] = None
                    
            case sigil.RAMPAGER:
                if targetLane not in range(N_LANES):
                    targetLane = lane - c.direction
                    c.direction*=-1
                temp = battleCards[targetLane]
                battleCards[targetLane] = c
                battleCards[lane] = temp

            case sigil.HEFTY:
                if sum(1 for x in battleCards if x is not None) == N_LANES:
                    return
                if not self.push(c, lane, battleCards):
                    c.direction*=-1
                    self.push(c, lane, battleCards)

    def push(self, c: card, lane: int, battleCards: list[card|None]):
        """Shove c and every card ahead of it one lane along, unless the far end of the chain is a wall."""
        end = lane + c.direction
        while end in range(N_LANES) and battleCards[end] is not None:
            end += c.direction
        if end not in range(N_LANES):
            return False
        while end != lane:
            battleCards[end] = battleCards[end - c.direction]
            end -= c.direction
        battleCards[lane] = None
        return True

    def burrow(self, lane: int, battleCards: list[card|None], attacker: card):
        """The leftmost burrower slides into an empty lane about to be attacked."""
        for i in range(N_LANES):
            c = battleCards[i]
            if c is None or not c.isBurrower():
                continue
            if attacker.attType is attackType.AIR and not c.blocksAir():
                continue
            battleCards[lane] = c
            battleCards[i] = None
            self.refreshAlphas(battleCards)
            return c
        return None

    def gainItem(self, i: itemName):
        if len(self.playerItems) < MAX_ITEMS:
            self.playerItems.append(i)

    def selectItem(self, slot: int):
        """Picks an item up. One that needs aiming is held until it is aimed."""
        if slot not in range(len(self.playerItems)) or\
            self.itemToUse is not None or\
            self.cardToPlay is not None or\
            self.hasSacrificed or\
            not self.canUseItem(self.playerItems[slot]):
            return None

        i = self.playerItems[slot]
        if i in TARGETS_LANE or i in TARGETS_DECK:
            self.itemToUse = self.playerItems.pop(slot)
            return self.itemToUse

        self.playerItems.pop(slot)
        return self.useItem(i)

    def canUseItem(self, i: itemName):
        """Whether an item could do anything if picked up right now."""
        if i in UNUSABLE:
            return False
        if i in TARGETS_DECK:
            return bool(self.playerDeck)
        if i is itemName.HOURGLASS:
            return not self.leshySkipped
        if i is itemName.FAN:
            return any(c is not None for c in self.playerBattleCards)
        return True

    def useItem(self, i: itemName):
        """Everything an item does the moment it is spent, aiming aside."""
        if i is itemName.SQUIRREL_BOTTLE:
            self.addToHand(card(CARDS[cardName.SQUIRREL]))
        elif i in BOTTLED:
            self.addToHand(self.applyTotem(card(CARDS[BOTTLED[i]]), self.playerTotem))
        elif i is itemName.PLIERS:
            self.scales += PLIERS_SCALES
        elif i is itemName.HOGGY_BANK:
            self.bones += HOGGY_BANK_BONES
        elif i is itemName.HOURGLASS:
            self.leshySkipped = True
        elif i is itemName.FAN:
            for c in self.playerBattleCards:
                if c is not None:
                    c.fanned = True
        elif i is itemName.WISECLOCK:
            self.wiseclock()
        return i

    def aimItem(self, lane: int):
        """Spend a held item on one of Leshy's lanes."""
        if self.itemToUse not in TARGETS_LANE or\
            lane not in range(N_LANES) or\
            self.leshyBattleCards[lane] is None:
            return None

        victim = self.leshyBattleCards[lane]
        victim.kill()
        self.cardDied(victim, lane, self.leshyBattleCards)
        if self.itemToUse is itemName.SKINNING_KNIFE:
            self.addToHand(self.applyTotem(card(CARDS[cardName.RABBIT_PELT]),
                                           self.playerTotem))
        spent, self.itemToUse = self.itemToUse, None
        return spent

    def lensPick(self, slot: int):
        """Take a named card straight out of the deck, by its slot in the sorted order."""
        if not (self.hoarding or self.itemToUse in TARGETS_DECK) or\
            slot not in range(len(self.playerDeck)):
            return None
        ordered = sorted(self.playerDeck, key=deckSortKey)
        chosen = ordered[slot]
        self.playerDeck.remove(chosen)
        self.addToHand(chosen)
        if self.hoarding:
            self.hoarding = False
            return chosen
        spent, self.itemToUse = self.itemToUse, None
        return spent

    def wiseclock(self):
        """Every card steps one place around the ring: his lanes left to right,
        then yours right to left, and round again."""
        ring = [(self.leshyBattleCards, i) for i in range(N_LANES)] + \
               [(self.playerBattleCards, i) for i in reversed(range(N_LANES))]
        held = [row[i] for row, i in ring]
        for (row, i), c in zip(ring, [held[-1]] + held[:-1]):
            row[i] = c
        self.refreshAlphas(self.leshyBattleCards)
        self.refreshAlphas(self.playerBattleCards)

    def guard(self, lane: int, opposing: list[card | None]):
        """The leftmost guardian steps in front of a card just placed opposite it."""
        if opposing[lane] is not None or not self.reacts(opposing):
            return
        for i in range(N_LANES):
            g = opposing[i]
            if g is not None and g.isGuardian():
                opposing[lane] = g
                opposing[i] = None
                self.refreshAlphas(opposing)
                return

    def hasScavenger(self):
        return any(c is not None and c.isScavenger() for c in self.playerBattleCards)

    def springTrap(self, lane: int, cards: list[card | None]):
        """A steel trap's death takes the card opposite with it, and leaves its owner a pelt.
        Leshy has no hand, so only your own trap pays one."""
        opposing = self.leshyBattleCards if cards is self.playerBattleCards \
            else self.playerBattleCards
        victim = opposing[lane]
        if victim is not None:
            victim.kill()
            self.cardDied(victim, lane, opposing)
        if cards is self.playerBattleCards:
            self.addToHand(self.applyTotem(card(CARDS[cardName.WOLF_PELT]), self.playerTotem))

    def ringChime(self, defender: card, attacker: card, defenders: list[card | None]):
        """Strike a chime and every Daus on that side answers."""
        if defender.name is not cardName.CHIME:
            return
        for c in defenders:
            if c is not None and c.name is cardName.THE_DAUS:
                attacker.hurt(c.attack(), c, isRetaliation=True)

    def shedTail(self, lane: int, c: card, cards: list[card | None]):
        """Leave a tail to take the hit and slide aside, right first, then left."""
        for target in (lane + 1, lane - 1):
            if target not in range(N_LANES) or cards[target] is not None:
                continue
            d = c.definition
            c.definition = cardDef(d.name, d.type, d.hp, d.attack, d.cost, d.currency,
                                   [s for s in d.sigils if s is not sigil.LOOSE_TAIL])
            c.sigilMod = [s for s in c.sigilMod if s is not sigil.LOOSE_TAIL]
            cards[target] = c

            t = CARDS[cardName.TAIL]
            tailType = cardType.REPTILE if d.name is cardName.SKINK else t.type
            cards[lane] = card(cardDef(t.name, tailType, t.hp, t.attack,
                                       t.cost, t.currency, []),
                               sigilMod=list(c.sigilMod))
            self.refreshAlphas(cards)
            return cards[lane]
        return c

    def cardDied(self, c: card, lane: int, cards: list[card | None]):
        """Clear a dead card off the board and settle what its death owes.

        Clears the lane itself so that anything the death leaves behind is not
        overwritten by the caller.
        """
        c.onDeath()
        # Only your own dead leave bones behind, unless a scavenger is out to take his.
        if not c.isTerrain() and (cards is self.playerBattleCards or self.hasScavenger()):
            self.bones += 1
        cards[lane] = None

        if cards is self.playerBattleCards and c.isUnkillable():
            self.addToHand(c.snapshot())

        if c.isSteelTrap():
            self.springTrap(lane, cards)

        if c.isFrozen():
            cards[lane] = card(CARDS[cardName.OPOSSUM], sigilMod=list(c.sigilMod))
        elif c.name in SPAWNS_ON_DEATH:
            cards[lane] = card(CARDS[SPAWNS_ON_DEATH[c.name]])

        self.refreshAlphas(cards)

    def corpseEater(self, lane: int, cards: list[card | None]):
        """Maggots in hand take the place of a card that just died in combat. Leshy has no hand."""
        if cards is not self.playerBattleCards or cards[lane] is not None:
            return
        for i, c in enumerate(self.playerHand):
            if c.isCorpseEater():
                self.playerBattleCards[lane] = self.playerHand.pop(i)
                self.cardPlaced(c, lane, self.leshyBattleCards)
                return

    def breed(self, c: card):
        """A copy joins your hand, barren, so one mouse cannot fill the deck."""
        d = c.definition
        barren = cardDef(d.name, d.type, d.hp, d.attack, d.cost, d.currency,
                         [s for s in d.sigils if s is not sigil.FECUNDITY])
        self.addToHand(card(barren, attackMod=c.attackMod, hpMod=c.hpMod,
                            sigilMod=[s for s in c.sigilMod if s is not sigil.FECUNDITY]))

    def refreshAlphas(self, cards: list[card | None]):
        """An Alpha's bonus belongs to the lanes beside it, so the whole row is re-derived."""
        for i, c in enumerate(cards):
            if c is not None:
                c.laneMod = sum(1 for j in (i - 1, i + 1)
                                if j in range(N_LANES) and cards[j] is not None
                                and cards[j].isAlpha())

    def inheritable(self, c: card):
        """The granted sigils a spawned card takes from its spawner, minus the ones
        that spawn, or a spawned card would spawn again forever."""
        return [s for s in c.sigilMod if s not in SPAWNERS]

    def cardPlaced(self, c: card, lane: int, opposing: list[card | None]):
        """Sigils that fire when a card arrives on the board."""
        self.refreshAlphas(self.leshyBattleCards if opposing is self.playerBattleCards
                           else self.playerBattleCards)

        self.guard(lane, opposing)

        if c.isTrinketBearer() and opposing is self.leshyBattleCards:
            self.gainItem(random.choice(POSSIBLE_ITEMS))

        if c.isFecund() and opposing is self.leshyBattleCards:
            self.breed(c)

        if c.isHoarder() and opposing is self.leshyBattleCards and self.playerDeck:
            self.hoarding = True

        # Leshy has no hand, so only a warren of yours digs anything up.
        if c.isRabbitHole() and opposing is self.leshyBattleCards:
            # The rabbit inherits granted sigils, the totem's among them, so no applyTotem here.
            self.addToHand(card(CARDS[cardName.RABBIT], sigilMod=self.inheritable(c)))

        if c.isAntSpawner() and opposing is self.leshyBattleCards:
            self.addToHand(card(CARDS[cardName.WORKER_ANT], sigilMod=self.inheritable(c)))

        if c.isParasite() and opposing[lane] is None:
            hatches = random.random() < BROOD_RAVEN_CHANCE
            # The egg belongs to whichever side it hatches on, so it takes that totem.
            laid = self.playerTotem if opposing is self.playerBattleCards else self.leshyTotem
            opposing[lane] = self.applyTotem(card(CARDS[cardName.RAVEN_EGG if hatches
                                        else cardName.BROKEN_EGG]), laid)

    def getLane(self, c:card, cList: list[card|None]):
        for i in range(len(cList)):
            if c is cList[i]:
                return i

    def applyEndOfOwnTurn(self, battleCards: list[card | None]):
        frozenCards = list(battleCards)
        # Only your side digs: the bone counter is yours, Leshy never spends one.
        yours = battleCards is self.playerBattleCards
        for c in frozenCards:
            if c is None:
                continue
            c.fanned = False
            if yours and c.isBoneDigger():
                self.bones += 1
            movementType = c.movement
            if movementType is not None:
                movementAmount = c.movementAmount
                for j in range(movementAmount):
                    currLane = self.getLane(c, battleCards)
                    targetLane = currLane + c.direction
                    self.moveCard(c,currLane,targetLane,movementType, battleCards)
        self.refreshAlphas(battleCards)

    def applyEndOfOpponentTurn(self, battleCards: list[card | None]):
        for c in battleCards:
            if c is not None:
                c.endOfOpponentTurn()

    def encodeLanes(self):
        """The battlefield as (N_ROWS, N_LANES, CARD_FEATURES).

        Row 0 is the player's line, row 1 Leshy's, row 2 his queued cards.
        Empty slots are all zeros, so the occupied flag is what tells them
        apart from a 0/0 card.
        """
        rows = ((self.playerBattleCards, self.leshyBattleCards),
                (self.leshyBattleCards, self.playerBattleCards),
                (self.leshyNextCards, self.playerBattleCards))
        return np.stack([
            np.stack([EMPTY_SLOT if c is None
                      else c.encode(self.powerContextFor(own, lane, facing))
                      for lane, c in enumerate(own)])
            for own, facing in rows
        ])

    def encodeHand(self):
        """The hand as (MAX_HAND, HAND_FEATURES), sorted into a canonical order.

        Hand order carries no meaning in game, so sorting stops the model
        treating the same card in two different slots as two different things.
        """
        out = np.zeros((MAX_HAND, HAND_FEATURES), dtype=np.float32)
        ordered = sorted(self.playerHand, key=lambda c: (c.name.value, c.attack(), c.hp))
        ctx = self.powerContextFor(self.playerBattleCards, 0, [None] * N_LANES)
        for i, c in enumerate(ordered[:MAX_HAND]):
            out[i, :CARD_FEATURES] = c.encode(ctx)
            out[i, CARD_FEATURES] = c.cost / STAT_CAP
            out[i, CARD_FEATURES + 1] = 1.0 if c.currency is costType.BONES else 0.0
        return out

    def encodeDeck(self):
        """The deck as (MAX_DECK, CARD_FEATURES), sorted into a canonical order.

        Sorted rather than shuffled: what is left to draw is fair to see, the
        order it will arrive in is not.
        """
        out = np.zeros((MAX_DECK, CARD_FEATURES), dtype=np.float32)
        ctx = self.powerContextFor(self.playerBattleCards, 0, [None] * N_LANES)
        for i, c in enumerate(sorted(self.playerDeck, key=deckSortKey)[:MAX_DECK]):
            out[i] = c.encode(ctx)
        return out

    def encodeItems(self):
        """One row per item slot, each a one-hot of which item sits there."""
        out = np.zeros((MAX_ITEMS, len(itemName)), dtype=np.float32)
        for slot, i in enumerate(self.playerItems[:MAX_ITEMS]):
            out[slot, ITEM_INDEX[i]] = 1.0
        return out

    def encodeGlobals(self):
        """Everything that isn't a slot: the scale, and what's left to draw.

        The deck goes in as a count per card name, never as an ordered list —
        the order is the player's future draws and must stay hidden.
        """
        deckCounts = np.zeros(len(cardName), dtype=np.float32)
        for c in self.playerDeck:
            deckCounts[NAME_INDEX[c.name]] += 1.0

        scalars = np.array([
            np.clip(self.scales / 5.0, -1.0, 1.0),
            self.squirrelDeck / SQUIRREL_COUNT,
            len(self.playerDeck) / MAX_DECK,
            len(self.playerHand) / MAX_HAND,
            1.0 if self.hasSacrificed else 0.0,
            min(self.bones, BONE_CAP) / BONE_CAP,
            min(self.turn, MAX_TURNS) / MAX_TURNS,
            1.0 if self.hoarding else 0.0,
        ], dtype=np.float32)

        selected = np.zeros(HAND_FEATURES, dtype=np.float32)
        if self.cardToPlay is not None:
            selected[:CARD_FEATURES] = self.cardToPlay.encode(
                self.powerContextFor(self.playerBattleCards, 0, [None] * N_LANES))
            selected[CARD_FEATURES] = self.cardToPlay.cost / STAT_CAP
            selected[CARD_FEATURES + 1] = 1.0 if self.cardToPlay.currency is costType.BONES else 0.0

        # Only yours: your deck is names without sigils, while his totem already
        # shows on every card of his you can see.
        totemSigil = np.zeros(len(sigil), dtype=np.float32)
        if self.playerTotem is not None:
            totemSigil[SIGIL_INDEX[self.playerTotem.imposedSigil]] = 1.0

        held = np.zeros(len(itemName), dtype=np.float32)
        if self.itemToUse is not None:
            held[ITEM_INDEX[self.itemToUse]] = 1.0

        return np.concatenate([scalars, deckCounts / MAX_DECK, selected,
                               totemSigil, held])

    def encode(self):
        """The whole observable state: (lanes, hand, deck, items, globals)."""
        return (self.encodeLanes(), self.encodeHand(), self.encodeDeck(),
                self.encodeItems(), self.encodeGlobals())

    def drawCard(self):
        if not self.hasDrawnCard and self.playerDeck:
            self.addToHand(self.playerDeck.pop())
            self.hasDrawnCard = True
        else:
            return None
        
    def drawSquirrel(self):
        if not self.hasDrawnCard and self.squirrelDeck > 0:
            self.squirrelDeck-=1
            self.addToHand(self.makeSquirrel())
            self.hasDrawnCard = True
        else:
            return None