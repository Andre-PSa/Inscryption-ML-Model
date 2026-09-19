from dataclasses import dataclass
from Card.card import card

@dataclass
class move():
    lane1: list[card]
    lane2: list[card]
    lane3: list[card]
    lane4: list[card]

    def getLaneCard(self, lane: int):
        match(lane):
            case 0:
                if self.lane1:
                    return self.lane1.pop(0)
            case 1:
                if self.lane2:
                    return self.lane2.pop(0)
            case 2:
                if self.lane3:
                    return self.lane3.pop(0)
            case 3:
                if self.lane4:
                    return self.lane4.pop(0)
        return None

    def isEmpty(self):
        return(not (self.lane1 or self.lane2 or self.lane3 or self.lane4))
