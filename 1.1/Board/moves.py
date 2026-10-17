from dataclasses import dataclass
from Card.card import card

@dataclass
class move():
    cards: list[card]
