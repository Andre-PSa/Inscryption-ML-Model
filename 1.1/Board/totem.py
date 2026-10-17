from dataclasses import dataclass
from Card.cardType import cardType
from Card.sigil import sigil

@dataclass
class totem:
    affectedType: cardType
    imposedSigil: sigil