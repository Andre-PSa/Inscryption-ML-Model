# Inscryption RL

A reinforcement learning agent that plays **Kaycee's Mod**, the roguelike mode of
**Inscryption**, trained from
scratch against a hand-written engine of the game. No expert demonstrations, no
search — it learns entirely from win/loss and a handful of shaping rewards.

**It wins 95.7% of 33 transcribed encounters. Random play wins 6.6%.**

Everything here is written from the ground up: the game engine, the state
encoder, the action space, the training loop, and three tkinter tools for
watching and building battles.

---

## The game, in one minute

Kaycee's Mod is Inscryption's roguelike mode: repeated runs through Leshy's
cabin, each a sequence of battles with deck-building between them. A battle is a
card game played on **four lanes**. You and your
opponent (Leshy) each have a row; cards face each other across the lanes.

- Every card has **attack** and **health**. Ringing the bell ends your turn:
  each of your cards strikes the lane opposite it. If a card is there, it takes
  damage. **If the lane is empty, the damage goes to the scales.**
- The **scales** are the win condition. Push them **5 in your favour** and you
  win; 5 against you and you lose.
- Cards cost **blood** — paid by sacrificing cards already on your board — or
  **bones**, which you earn when one of *your own* cards dies. A free supply of 0/1 squirrels
  means you always have something to sacrifice, or something to throw in front
  of an attacker.
- **Sigils** are keyword abilities. A card with *Airborne* flies over blockers
  and hits the scales anyway; *Mighty Leap* blocks fliers; *Touch of Death*
  kills whatever it damages; *Worthy Sacrifice* pays three blood instead of one.

Three decisions in particular gave this agent trouble, and they come up
throughout the rest of this README:

- **Which lane to answer.** Two attackers can arrive on the same turn while you
  can only afford one card, so one lane has to be conceded or blocked.
- **Whether a card is worth what it costs.** Blood is paid by killing your own
  cards, so a 2-blood card means destroying two you already have. Upgrading a
  stoat into a slightly better stoat is a net loss of a card.
- **When to chump-block.** A free 0-attack squirrel thrown in front of an
  attacker you cannot yet kill absorbs a full hit and buys a turn to build
  toward the card that can.

---

## Benchmarks

Greedy evaluation, 100 episodes per encounter, against a uniform-random policy
over the same legal action mask.

| | agent | random |
|---|---|---|
| **overall** | **95.7%** | 6.6% |
| encounters solved at 100% | 25 of 33 | 0 of 33 |
| encounters below 50% | 1 of 33 | 33 of 33 |

The random policy's best encounter is 49%; it clears 30% on only two of the
thirty-three.

<details>
<summary>Per-encounter results</summary>

```
  1  100%    2   78%    3  100%    4  100%    5  100%    6  100%
  7  100%    8   49%    9  100%   10   87%   11  100%   12  100%
 13  100%   14  100%   15  100%   16   90%   17  100%   18  100%
 19   85%   20   85%   21  100%   22   88%   23  100%   24  100%
 25  100%   26  100%   27  100%   28  100%   29  100%   30   95%
 31  100%   32  100%   33  100%
```

</details>

Encounters are transcribed from real play. Several are deterministic — a fixed
deck against a fixed opponent script — so the agent either finds the line or it
does not.

Encounter 8 (49%) is the weakest: four consecutive turns of Adders and a Rattler.

---

## How the agent works

### Observation

The board is encoded as three tensors:

| | shape | contents |
|---|---|---|
| `lanes` | `(3, 4, 34)` | your line, Leshy's line, his queued row — 4 lanes each |
| `hand` | `(30, 36)` | one row per card, plus cost and currency |
| `globals` | `(116,)` | scales, bones, squirrels, deck composition, phase flags |

Each card is 34 numbers: occupied, attack, health, and a 31-wide one-hot of its
sigils. Stats are divided by a cap so inputs land in roughly 0–1.

Two details matter more than they look:

**The hand is kept in a canonical sorted order.** Slot 3 always refers to the
same card regardless of draw order, so the select-hand actions mean something
stable.

**The deck is encoded as counts per card name, never as a list.** The order of
the deck is the player's future draws, and the agent must not see it.

### Actions

A flat space of **53 actions**, with a boolean legality mask computed by the
board each step:

```
 0–29   select card from hand slot i
30–33   place the held card in lane i
34      draw from deck
35      draw a squirrel
36      ring the bell
37–52   sacrifice a set of lanes, indexed as a 4-bit mask
```

Illegal actions have their logits set to `-1e9` before the softmax — finite
rather than `-inf`, because `0 × -inf` produces `NaN` in the entropy term.

Sacrifices are a **bitmask over lanes** rather than a separate output head. An
earlier design used a second head and it did not improve: on any turn without a
sacrifice there was no path from its weights to the loss, so `tape.gradient`
returned `None` for them. Folding it into one action space puts every weight in
the gradient path on every step, and deleted a branch from three files.

### Network

~305k parameters, two heads on a shared trunk:

```
lanes   ──► Permute + Reshape ──► Dense(64)  ──► Flatten ─┐
hand    ──► Dense(16) per slot  ──────────────► Flatten ─┼─► Dense(256) ─► Dense(256) ─┬─► action (53)
globals ─────────────────────────────────────────────────┘                             └─► value (1, tanh)
```

The `Permute`/`Reshape` on the lanes is deliberate: it arranges the axes so one
shared `Dense` sees a whole lane — your card, his card, and his queued card —
and learns a matchup **once** for all four lanes rather than four times.

### Training

**PPO** with a value baseline and an entropy bonus.

| | |
|---|---|
| discount `γ` | 0.999 |
| clip ε | 0.2 |
| epochs per batch | 4 |
| episodes per batch | 8 |
| learning rate | 3e-4 (Adam) |
| entropy weight | 0.01 |

Each batch plays 8 full battles, flattens them into ~120 transitions, and takes
four clipped gradient passes over that same data. The clip bounds how far one
batch can move any action's probability, which is what makes reusing the data
sound.

### Rewards

```
win                     +1.0      kill an enemy card    +0.03
loss                    -1.0      your card dies        -0.005 … -0.025   by blood cost
                                  sacrifice a card      -0.001 … -0.025   by blood cost

per turn, turns 1–5     -0.005
per turn, turn 6 on     -0.050    a second term stacked on the first
```

The turn cost **escalates**: `REWARD_TURN` is charged every turn, and a separate
`REWARD_TURN_AFTER_5` of −0.045 is added on top from turn 6 onward.

Five turns is a deliberate allowance rather than a round number. In real play
most encounters are fully resolved by turn 3, and some end on turn 1; a battle
still going at turn 6 has become complicated. So the first five turns are nearly
free and the rate goes up tenfold after that, which charges for dragging a game
out without taxing one that simply takes a while to win.

The turn costs and the sacrifice costs both exist because of specific failures —
see below.

---

## Bottlenecks, and what fixed them

The win rate did not climb smoothly. It plateaued repeatedly, and almost every
plateau turned out to be a **bad incentive rather than a bug** — the engine was
mostly right, while the rewards were quietly telling the agent to do the wrong
thing.

Finding them took the same process each time: trace the agent's greedy play
action by action, compare it against a line that actually wins the encounter —
known from playing it by hand — and work out what was stopping the agent from
finding that line.

### 1. Stalling was mathematically optimal

The agent hit 0% on an encounter that random play won 18% of the time. The
trace showed why: it walled a 3-attack Rattler with free squirrels for **twelve
turns**, then lost when the squirrels ran out — while holding two Wolves in hand
it could never afford.

With `γ = 0.99` and ~4 actions per turn, delaying a terminal `-1` by ten turns
was worth `1 − 0.99⁴⁰ ≈ +0.33` discounted. Worse, running out the clock at
`MAX_TURNS` returned **0**, which beat losing outright. The reward was paying
the agent to procrastinate.

**Fix:** three changes, none of which works alone —

```
γ  0.99 → 0.999      a reward 40 steps out is worth 96% of face, not 67%
per-turn penalty     -0.005, rising to -0.050 after turn 5
stalling             now scores REWARD_LOSS instead of 0
```

**Result:** 0% → 100%, and the turn count fell from 12.0 to 5.2. Every other
encounter's turn count dropped too.

### 2. Sacrificing was free, on purpose

Blood is paid by killing your own cards, so **every blood card ever played costs
you board presence**. Price that too harshly and the agent learns to avoid blood
cards altogether — which is most of the game. The reward deliberately left
sacrifices unpriced to keep it willing to pay.

Zero turned out to be too far in that direction. The agent would play a
squirrel, sacrifice it for a stoat, sacrifice the stoat for a bullfrog —
**three cards spent to put one on the board** — because nothing in the reward
noticed. In one encounter it burned three cards from a five-card deck on turn one.

**Fix:** price sacrifices by blood cost via a lookup table, tuned to discourage
churn without discouraging payment. Spending a free card stays nearly free
(−0.001 for a squirrel, against −0.005 for losing one in combat), while spending
a real card costs exactly what losing it in combat costs.

### 3. Selecting a card could not be undone

Once a card was selected, `legalActions` offered **only** sacrifice sets. That
was deliberate: a selected card cannot be swapped for a different one, because
the board has not changed and a swap could only ever reach a card that was
already selectable — so swap actions would be pure noise in the action space.

What it also removed, unintentionally, was the option to put the card back.
Selecting became an irreversible commitment to spending your own board. A trace
showed what that costs: the agent killed a bat correctly, then **sacrificed the
very card it had just used to do it**, because selecting its next card left it
no other legal move.

**Fix:** offer *ring the bell* during a pending sacrifice. One line — the turn
machinery already returned an unplaced card to hand, so the escape existed and
simply was not on the menu.

### 4. The flier encounters needed drills, not engine changes

Three encounters sat at 0% for the entire project, all of them featuring fliers.
The obvious diagnosis was that the agent could not handle Airborne, and the
mask fix above looked like the answer.

It was not. The evaluation immediately after that fix still showed the hardest
of them at **0%**. What moved it was **training data**: ten purpose-built
encounters, six drilling Airborne in isolation and four drilling the specific
skills that encounter needs — answering two simultaneous 2-damage threats,
chump-blocking with free squirrels, and committing two bodies to afford the one
card that can kill the attacker.

**Result:** an encounter that had been 0% in *every* prior evaluation reached
**78%**, and another went 0% → 100%.

The caveat is that the mask fix and the first six drills shipped together, so
their contributions cannot be separated. The one clean data point is that the
mask fix alone was demonstrably not enough.

### 5. One update per eight battles

Plain REINFORCE took a single gradient step per batch and threw the games away.
Collection is ~98% of wall-clock — all of it batch-size-1 forward passes — so
the data was by far the expensive part.

**Fix:** PPO. Four clipped passes over each batch instead of one. The clip is
what makes reuse valid: after the first pass the weights have moved, so the
stored data describes a policy that no longer exists, and the importance ratio
corrects for the drift while the clip bounds it. Measured, the ratio reaches
about ±6% by the fourth pass — well inside the ±20% clip, so all four passes
contribute real gradient.

---

## Running it

```bash
pip install tensorflow numpy
python creator.py
```

### Start here: the encounter creator

`creator.py` is the way in. It loads any of the 33 encounters onto an editable
board, or lets you build one from nothing, and then **plays it** — either
yourself or with the trained agent driving.

It is a paint-style editor. Pick a card from the palette, and its full
stat line appears — attack, health, tribe, cost and every sigil it carries.
Click any slot to place it: Leshy's line, your line, or a cell in his move
schedule. Right-click clears a slot.

- **Load a saved encounter** — drop any of the 33 onto the board, then edit it
- **Modifiers** — attack and health steppers plus a list of all 31 sigils, so a
  card can be placed as a campfire-buffed or sigil-granted copy. Stats are
  clamped so nothing goes below 0 attack or 1 health
- **Deck** — build card by card, or start from a preset
- **Leshy's moves** — add and remove turns; an empty turn in the middle is a
  turn he does nothing, and it is preserved
- **PLAY** opens the encounter in the interactive player
- **VIEW** records the trained agent playing it and opens the replay viewer
- **COPY** puts the encounter on your clipboard as Python, ready to paste into
  `Board/encounters.py`

Everything round-trips: load an encounter, hit COPY, and you get back the source
it was defined with.

### The rest

```bash
python main.py eval           # per-encounter win rate table
python main.py watch 6        # record the agent playing encounter 6, open the viewer
python main.py train 2000     # train, warm-starting from model.keras if present
python play.py 2              # play encounter 2 yourself
```

### The viewer

`viewer.py` steps through a recorded battle frame by frame, with the board, both
lines, Leshy's queue, the scales and the agent's own value estimate at each step.
Space plays, arrows step, F11 fullscreen.

Cards carry a **stable identity** through the replay, so the viewer can diff
consecutive frames and animate what actually moved — a burrower sliding to block,
a sprinter running down the line, a card fading out as it dies.

---

## What's missing

This is one battle, not the game. Honest list:

**No run structure.** A Kaycee's Mod run is a map of battles with deck-building
between them — card choices, campfire buffs, sigil transfers, totems, and the
challenge modifiers that scale a run's difficulty. This engine models a **single
encounter** in isolation. Totems are implemented (one per side, each affecting
only its owner's cards) but no encounter uses them yet.

**12 of 31 sigils are declared but inert:**
`BIFURCATED_STRIKE`, `TRIFURCATED_STRIKE`, `LOOSE_TAIL`, `BEES_WITHIN`,
`UNDYING`, `MANY_LIVES`, `BONE_KING`, `TRINKET_BEARER`, `ANT_SPAWNER`,
`DAM_BUILDER`, `HOARDER`, `STINKY`. The multi-strike ones are waiting on a
`getAttacks` rewrite; double strike is currently special-cased.

**Per-copy card modifications are invisible in the observation.** A campfire-buffed
6/4 wolf sitting in your deck encodes identically to a plain 3/2 one, because the
deck is a histogram of card *names*. It only becomes visible once drawn into hand.

**The training set is the evaluation set.** All 33 encounters are trained on, so
95.7% measures competence on known boards, not generalisation to unseen ones.

**Sample efficiency.** ~98% of training time is TensorFlow dispatch on
batch-size-1 forward passes during episode collection. Measured, 64 boards put
through the network together cost 0.19 ms each, against 10.88 ms for one alone.

---

## Layout

```
Board/     board.py       rules, legal-action mask, state encoder
           encounters.py  33 transcribed battles
           moves.py       Leshy's scripted turns
           totem.py
Card/      card.py        a card in play: per-copy state, derived properties
           cardData.py    frozen definitions, shared between copies
           sigil.py       cardName.py  cardType.py  costType.py
Env/       environment.py reset / step / reward / done
Model/     network.py     the two-headed network
           train.py       PPO loop
           replay.py      records a battle to JSON
main.py    train · eval · watch · record
play.py    play a battle yourself
viewer.py  step through a recorded battle
creator.py design an encounter
```

The card model uses a **flyweight split**: `cardDef` holds the frozen species
data shared by every copy, while `card` holds everything per-copy — damage,
stat modifiers, granted sigils, facing direction. `attack`, `hp` and `sigils`
are derived properties, so a sigil granted mid-battle takes effect immediately
and a card that grows keeps the buffs it was carrying.
