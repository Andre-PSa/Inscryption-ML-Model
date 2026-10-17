from dataclasses import dataclass

import numpy as np

from Card.cardData import cardDef, CARDS, GROWS_INTO
from Card.sigil import sigil, MOVEMENT
from Card.attackType import attackType
from Card.damageType import damageType
from Card.cardType import cardType
from Card.power import POWER

# Built from the enum, so adding a sigil widens the vector rather than shifting it.
SIGIL_INDEX = {s: i for i, s in enumerate(sigil)}

# occupied, attack, hp, direction, fanned, then one slot per sigil.
CARD_FEATURES = 5 + len(sigil)

# Stats are divided by this so inputs land roughly in 0..1.
STAT_CAP = 20.0

# Blood paid by sacrificing a card carrying Worthy Sacrifice.
WORTHY_BLOOD = 3


@dataclass
class card:
    definition: cardDef
    damage: int = 0
    attackMod: int = 0
    hpMod: int = 0
    sigilMod: list[sigil] = None
    direction: int = 1
    # Belongs to the lane, not the card: the board recomputes it from adjacent Alphas.
    laneMod: int = 0
    fanned: bool = False
    bees: int = 0

    def __post_init__(self):
        if self.sigilMod is None:
            self.sigilMod = []

    @property
    def name(self):
        return self.definition.name

    @property
    def sigils(self):
        """Everything this card has. Read-only — to grant one, append to
        sigilMod, since this builds a new list each call."""
        return self.definition.sigils + self.sigilMod

    @property
    def attType(self):
        """How it picks a target. Derived, so a sigil granted mid-battle
        takes effect immediately."""
        return attackType.AIR if self.fanned or sigil.AIRBORNE in self.sigils \
            else attackType.NORMAL

    @property
    def dmgType(self):
        """What its damage does. Independent of attType, so a card can be both
        airborne and lethal."""
        return damageType.DEATH if sigil.TOUCH_OF_DEATH in self.sigils \
            else damageType.NORMAL

    @property
    def type(self):
        return self.definition.type

    @property
    def cost(self):
        return self.definition.cost

    @property
    def currency(self):
        return self.definition.currency

    def attack(self, ctx=None):
        base = self.definition.attack
        if ctx is not None and self.name in POWER:
            base = POWER[self.name](self, ctx)
        if ctx is not None and ctx.opposite is not None and ctx.opposite.isAnnoying():
            base += 1
        power = base + self.attackMod + self.laneMod
        if ctx is not None and ctx.opposite is not None and ctx.opposite.isStinky() \
                and not self.isMadeOfStone():
            power -= 1
        return max(power, 0)

    @property
    def hp(self):
        return self.definition.hp + self.hpMod - self.damage

    @property
    def movement(self):
        for sig in self.sigils:
            if sig in MOVEMENT:
                return sig
        return None

    @property
    def movementAmount(self):
        return sum(1 for s in self.sigils if s in MOVEMENT)

    def addSigil(self, s: sigil):
        self.sigilMod.append(s)

    def isFree(self):
        return self.cost == 0

    def blocksAir(self):
        return sigil.MIGHTY_LEAP in self.sigils

    def isWaterborne(self):
        return sigil.WATERBORNE in self.sigils

    def isBurrower(self):
        return sigil.BURROWER in self.sigils

    def strikeOffsets(self):
        """Which lanes, relative to its own, one strike lands in."""
        targets = []
        if sigil.BIFURCATED_STRIKE in self.sigils:
            targets.extend([-1, 1])
        else:
            targets.append(0)
        if sigil.TRIFURCATED_STRIKE in self.sigils:
            if 0 not in targets:
                targets.append(0)
            targets.extend([-1, 1])
        if sigil.DOUBLE_STRIKE in self.sigils:
            targets.append(0)
        
        targets.sort()
        return targets

    def isCorpseEater(self):
        return sigil.CORPSE_EATER in self.sigils

    def isBoneDigger(self):
        return sigil.BONE_DIGGER in self.sigils

    def isRabbitHole(self):
        return sigil.RABBIT_HOLE in self.sigils

    def isUnkillable(self):
        return sigil.UNKILLABLE in self.sigils

    def snapshot(self):
        """A fresh copy as it stands now: same species, buffs and granted sigils, no damage."""
        return card(self.definition, attackMod=self.attackMod, hpMod=self.hpMod,
                    sigilMod=list(self.sigilMod))

    def hasBloodLust(self):
        return sigil.BLOOD_LUST in self.sigils

    def hasBees(self):
        return sigil.BEES_WITHIN in self.sigils

    def isHoarder(self):
        return sigil.HOARDER in self.sigils

    def isMorsel(self):
        return sigil.MORSEL in self.sigils

    def isAntSpawner(self):
        return sigil.ANT_SPAWNER in self.sigils

    def isAlpha(self):
        return sigil.LEADER in self.sigils

    def isFecund(self):
        return sigil.FECUNDITY in self.sigils

    def bloodValue(self):
        """What sacrificing this pays. A worthy sacrifice is worth three cards."""
        return WORTHY_BLOOD if sigil.WORTHY_SACRIFICE in self.sigils else 1

    def shedsTail(self):
        return sigil.LOOSE_TAIL in self.sigils

    def isTrinketBearer(self):
        return sigil.TRINKET_BEARER in self.sigils

    def isSteelTrap(self):
        return sigil.STEEL_TRAP in self.sigils

    def isScavenger(self):
        return sigil.SCAVENGER in self.sigils

    def isGuardian(self):
        return sigil.GUARDIAN in self.sigils

    def isSpiky(self):
        return sigil.SHARP_QUILLS in self.sigils

    def isStinky(self):
        return sigil.STINKY in self.sigils

    def isAnnoying(self):
        return sigil.ANNOYING in self.sigils

    def isArmored(self):
        return sigil.ARMORED in self.sigils

    def isMadeOfStone(self):
        return sigil.MADE_OF_STONE in self.sigils

    def isFrozen(self):
        return sigil.FROZEN_AWAY in self.sigils

    def isParasite(self):
        return sigil.BROOD_PARASITE in self.sigils

    def isTerrain(self):
        return self.type == cardType.TERRAIN

    def battle(self, defender: "card", ctx=None, reacts: bool = True):
        """Strike defender. Returns the damage that reaches the scale instead
        of landing on a card — the board decides which way that tips."""
        power = self.attack(ctx)
        #This shouldnt happen but just in case
        if defender is None or power == 0: return 0

        # Airborne flies over unless the defender can leap for it.
        if self.attType is attackType.AIR and not defender.blocksAir():
            return power

        defender.hurt(power, self, reacts=reacts)
        return 0

    def hurt(self, amount: int, source: "card" = None, isRetaliation: bool = False,
             reacts: bool = True):
        """Take damage, and bite back if spiky."""
        if amount > 0 and self.isArmored():
            d = self.definition
            self.definition = cardDef(d.name, d.type, d.hp, d.attack, d.cost, d.currency,
                                      [s for s in d.sigils if s is not sigil.ARMORED])
            self.sigilMod = [s for s in self.sigilMod if s is not sigil.ARMORED]
        else:
            if (source is not None
                    and source.dmgType is damageType.DEATH
                    and not self.isMadeOfStone()):
                # Lethal, but a big enough hit still overkills past zero.
                amount = max(amount, self.hp)
            self.damage += amount
            if amount > 0 and reacts and self.hasBees():
                self.bees += 1

        if self.isSpiky() and source is not None and not isRetaliation and reacts:
            source.hurt(1, self, isRetaliation=True)

    def kill(self):
        self.damage += self.hp

    def onDeath(self):
        pass

    def endOfOpponentTurn(self):
        """Sigils that fire at the end of opponent's turn."""
        if sigil.FLEDGLING in self.sigils:
            if self.name in GROWS_INTO:
                self.definition = CARDS[GROWS_INTO[self.name]]
            else:
                self.hpMod += 2
                self.attackMod += 1
            if sigil.FLEDGLING in self.sigilMod:
                self.sigilMod.remove(sigil.FLEDGLING)

    def encode(self, ctx=None):
        """This card as a fixed-width vector: occupied, attack, hp, direction, fanned, sigil flags."""
        v = np.zeros(CARD_FEATURES, dtype=np.float32)
        v[0] = 1.0
        v[1] = min(self.attack(ctx), STAT_CAP) / STAT_CAP
        v[2] = min(self.hp, STAT_CAP) / STAT_CAP
        v[3] = self.direction
        v[4] = 1.0 if self.fanned else 0.0
        for s in self.sigils:
            v[5 + SIGIL_INDEX[s]] = 1.0
        return v
