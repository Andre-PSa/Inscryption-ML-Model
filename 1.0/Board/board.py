from dataclasses import dataclass
from enum import Enum, auto
from Card.card import card, CARD_FEATURES, STAT_CAP, SIGIL_INDEX
from Card.cardData import CARDS, cardDef
from Card.cardName import cardName
from Card.costType import costType
from Card.attackType import attackType
from Card.sigil import sigil
from Board.totem import totem
from Board.moves import move
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
N_ACTIONS = ACT_SACRIFICE_SET + N_SACRIFICE_SETS   # 53


def laneSet(mask: int):
    """The lanes a sacrifice-set bitmask names."""
    return [i for i in range(N_LANES) if mask >> i & 1]

# Neither side is obliged to act, so a stalled battle still has to end.
MAX_TURNS = 50

# The encoder clips here; past this many bones, more changes no decision.
BONE_CAP = 20.0

# Brood Parasite lays a broken egg most of the time, a raven egg occasionally.
BROOD_RAVEN_CHANCE = 0.10

# Two extra numbers board cards don't need: the cost, and whether it is bones.
HAND_FEATURES = CARD_FEATURES + 2

# Reused for every empty slot, so it must never be written to.
EMPTY_SLOT = np.zeros(CARD_FEATURES, dtype=np.float32)

NAME_INDEX = {n: i for i, n in enumerate(cardName)}


def handSortKey(c: card):
    """Hand order means nothing in game, so the hand is kept in one canonical
    order. The encoder's hand slots and the select-hand action ids both index
    straight into it, so this is the single definition both rely on."""
    return (c.name.value, c.attack, c.hp)

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

    #TODO: Add the rest of the player's possible actions
    def populate_board(self, playerCards: list[card | None], leshyCards: list[card | None],
                       playerDeck: list[card | None], leshyNextCards: list[card | None], leshyMoves: list[move],
                       playerTotem: totem = None, leshyTotem: totem = None):
        self.playerTotem = playerTotem
        self.leshyTotem = leshyTotem
        self.playerBattleCards = [self.applyTotem(c, playerTotem) for c in playerCards]
        self.leshyBattleCards = [self.applyTotem(c, leshyTotem) for c in leshyCards]
        self.leshyNextCards = [self.applyTotem(c, leshyTotem) for c in leshyNextCards]
        self.playerDeck = [self.applyTotem(c, playerTotem) for c in playerDeck]
        self.leshyMoveSequence = leshyMoves
        random.shuffle(self.playerDeck)

        #fair hand
        for i in range(len(self.playerDeck)):
            if self.playerDeck[i].cost <=1:
                self.addToHand(self.playerDeck.pop(i))
                break
            #If no cards with 0 or 1 cost, just take one normally
            if i == len(self.playerDeck):
                self.addToHand(self.playerDeck.pop())
        
        #-1 for fair hand
        for i in range(INITIAL_DRAW - 1):
            self.addToHand(self.playerDeck.pop())
        self.addToHand(self.applyTotem(card(CARDS[cardName.SQUIRREL]), playerTotem))
        self.squirrelDeck-= 1

        self.refillLeshyQueue()
        self.hasDrawnCard = True

    def applyTotem(self, c: card | None, t: totem):
        """Grant a totem's sigil. Called once per card created, never on transfer."""
        if c is not None and t is not None and c.type is t.affectedType:
            c.addSigil(t.imposedSigil)
        return c

    def refillLeshyQueue(self):
        """Pull the current move's cards into the preview row, and retire that
        move once it has nothing left to give."""
        if not self.leshyMoveSequence:
            return
        for lane in range(N_LANES):
            if self.leshyNextCards[lane] is None:
                self.leshyNextCards[lane] = self.applyTotem(
                    self.leshyMoveSequence[0].getLaneCard(lane), self.leshyTotem)
        if self.leshyMoveSequence[0].isEmpty():
            self.leshyMoveSequence.pop(0)


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

        self.hasSacrificed = True
        for cardIdx in cardIdxToSacrifice:
            self.playerBattleCards[cardIdx].kill()
            self.cardDied(self.playerBattleCards[cardIdx], cardIdx, self.playerBattleCards)

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
        if actionId >= ACT_SACRIFICE_SET:
            return self.sacrificeCards(laneSet(actionId - ACT_SACRIFICE_SET))
        if actionId == ACT_RING_BELL:
            return self.endPlayerTurn()
        return None

    def endPlayerTurn(self):
        """Ring the bell: every player card strikes the lane opposite it."""
        if self.hasSacrificed:
            return None

        if self.cardToPlay is not None:
            self.addToHand(self.cardToPlay)
            self.cardToPlay = None
        
        for lane, attacker in enumerate(self.playerBattleCards):
            if attacker is None or attacker.attack == 0:
                continue

            self.strikeLane(lane, attacker, self.playerBattleCards,
                            self.leshyBattleCards, 1, self.leshyNextCards)

        if (self.squirrelDeck > 0 or self.playerDeck):
            self.hasDrawnCard = False
        self.turn += 1

        self.applyEndOfOwnTurn(self.playerBattleCards)
        self.applyEndOfOpponentTurn(self.leshyBattleCards)

        if self.scales >= 5:
            return result.WIN
        return result.NOT_FINISHED


    def strike(self, lane: int, attacker: card, defenders: list[card|None],
               sign: int, queued: list[card|None] = None):
        """One attack into a lane, carrying overkill through to whatever is queued behind it."""
        defender = defenders[lane]
        overkill_target = queued[lane] if queued is not None else None
        if defender is None:
            defender = self.burrow(lane, defenders, attacker)

        if defender is None or defender.isWaterborne():
            self.scales += sign * attacker.attack
            return

        self.scales += sign * attacker.battle(defender)

        if defender.hp <= 0:
            self.cardDied(defender, lane, defenders)
            self.corpseEater(lane, defenders)
            if overkill_target is not None:
                overkill_target.hurt(-defender.hp, attacker)
                if overkill_target.hp <= 0:
                    self.cardDied(overkill_target, lane, queued)

    def strikeLane(self, lane: int, attacker: card, attackers: list[card|None],
                   defenders: list[card|None], sign: int, queued: list[card|None] = None):
        """Every strike one attacker gets, stopping early if something kills it back."""
        for _ in range(2 if attacker.strikesTwice() else 1):
            self.strike(lane, attacker, defenders, sign, queued)
            # Quills can kill the attacker on the way in.
            if attacker.hp <= 0:
                self.cardDied(attacker, lane, attackers)
                self.corpseEater(lane, attackers)
                return

    def leshyTurn(self):
        for lane, next_card in enumerate(self.leshyNextCards):
            if next_card is None:
                continue
            if self.leshyBattleCards[lane] is None:
                self.leshyBattleCards[lane] = next_card
                self.leshyNextCards[lane] = None
                self.cardPlaced(next_card, lane, self.playerBattleCards)

        for lane, attacker in enumerate(self.leshyBattleCards):
            if attacker is None or attacker.attack == 0:
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

    def cardDied(self, c: card, lane: int, cards: list[card | None]):
        """Clear a dead card off the board and settle what its death owes.

        Clears the lane itself so that anything the death leaves behind is not
        overwritten by the caller.
        """
        c.onDeath()
        # Only your own dead leave bones behind; Leshy keeps his.
        if not c.isTerrain() and cards is self.playerBattleCards:
            self.bones += 1
        cards[lane] = None

        if c.isFrozen():
            cards[lane] = card(CARDS[cardName.OPOSSUM], sigilMod=list(c.sigilMod))

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

    def cardPlaced(self, c: card, lane: int, opposing: list[card | None]):
        """Sigils that fire when a card arrives on the board."""
        self.refreshAlphas(self.leshyBattleCards if opposing is self.playerBattleCards
                           else self.playerBattleCards)

        if c.isFecund() and opposing is self.leshyBattleCards:
            self.breed(c)

        # Leshy has no hand, so only a warren of yours digs anything up.
        if c.isRabbitHole() and opposing is self.leshyBattleCards:
            # The rabbit inherits granted sigils, the totem's among them, so no applyTotem here.
            self.addToHand(card(CARDS[cardName.RABBIT], sigilMod=list(c.sigilMod)))

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
        rows = (self.playerBattleCards, self.leshyBattleCards, self.leshyNextCards)
        return np.stack([
            np.stack([EMPTY_SLOT if c is None else c.encode() for c in row])
            for row in rows
        ])

    def encodeHand(self):
        """The hand as (MAX_HAND, HAND_FEATURES), sorted into a canonical order.

        Hand order carries no meaning in game, so sorting stops the model
        treating the same card in two different slots as two different things.
        """
        out = np.zeros((MAX_HAND, HAND_FEATURES), dtype=np.float32)
        ordered = sorted(self.playerHand, key=lambda c: (c.name.value, c.attack, c.hp))
        for i, c in enumerate(ordered[:MAX_HAND]):
            out[i, :CARD_FEATURES] = c.encode()
            out[i, CARD_FEATURES] = c.cost / STAT_CAP
            out[i, CARD_FEATURES + 1] = 1.0 if c.currency is costType.BONES else 0.0
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
        ], dtype=np.float32)

        selected = np.zeros(HAND_FEATURES, dtype=np.float32)
        if self.cardToPlay is not None:
            selected[:CARD_FEATURES] = self.cardToPlay.encode()
            selected[CARD_FEATURES] = self.cardToPlay.cost / STAT_CAP
            selected[CARD_FEATURES + 1] = 1.0 if self.cardToPlay.currency is costType.BONES else 0.0

        # Only yours: your deck is names without sigils, while his totem already
        # shows on every card of his you can see.
        totemSigil = np.zeros(len(sigil), dtype=np.float32)
        if self.playerTotem is not None:
            totemSigil[SIGIL_INDEX[self.playerTotem.imposedSigil]] = 1.0

        return np.concatenate([scalars, deckCounts / MAX_DECK, selected, totemSigil])

    def encode(self):
        """The whole observable state: (lanes, hand, globals)."""
        return self.encodeLanes(), self.encodeHand(), self.encodeGlobals()

    def drawCard(self):
        if not self.hasDrawnCard and self.playerDeck:
            self.addToHand(self.playerDeck.pop())
            self.hasDrawnCard = True
        else:
            return None
        
    def drawSquirrel(self):
        if not self.hasDrawnCard and self.squirrelDeck > 0:
            self.squirrelDeck-=1
            self.addToHand(self.applyTotem(card(CARDS[cardName.SQUIRREL]), self.playerTotem))
            self.hasDrawnCard = True
        else:
            return None