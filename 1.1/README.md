# Inscryption RL — 1.1

The second iteration of the game engine behind the agent. It plays a much larger
slice of Kaycee's Mod than [1.0](../1.0): more encounters, the full card pool,
items, and a Leshy who chooses where his cards go.

**The trained model wins 87% of the 54 encounters it trained on, and 73% of 12
it never saw. Random play wins 9.9% and 7.4% of them.**

The observation and action layout changed from 1.0, so 1.0's model cannot load
here. `model.keras` in this folder is a new one.

## Results

12 encounters are held out of training, one picked at random from each group of
related encounters (the same deck, the same scripted drills, or the same run):
1, 3, 7, 12, 16, 19, 29, 32, 39, 45, 59 and 61. The model trained on the other
54 for 20,000 batches of 8 battles, which took 51 minutes.

| | Encounters | Model | Random play |
|---|---|---|---|
| Trained on | 54 | 87% | 9.9% |
| Held out | 12 | 73% | 7.4% |

The model plays greedily, 100 battles per encounter. Random play is 1,000
battles per encounter.

<details>
<summary>Per-encounter results (* = held out)</summary>

```
  1   81%*   2  100%    3   90%*   4  100%    5  100%    6  100%
  7   92%*   8    8%    9   92%   10   94%   11   84%   12   75%*
 13  100%   14   97%   15  100%   16   48%*  17  100%   18   99%
 19   88%*  20   90%   21  100%   22   52%   23  100%   24  100%
 25  100%   26  100%   27  100%   28   88%   29  100%*  30  100%
 31  100%   32  100%*  33   92%   34   69%   35   90%   36   89%
 37   96%   38   42%   39   52%*  40   74%   41   65%   42   89%
 43   94%   44  100%   45   63%*  46   98%   47   87%   48   79%
 49   91%   50   85%   51  100%   52  100%   53   99%   54  100%
 55   95%   56   49%   57   97%   58   81%   59   18%*  60  100%
 61   74%*  62   96%   63   81%   64   57%   65   63%   66   15%
```

</details>

How the agent sees the board, how it is trained, and why it is built that way
are covered in [DESIGN.md](DESIGN.md).

## What's new since 1.0

- **66 encounters**, up from 33, transcribed from real runs.
- **The full card pool**: 111 cards.
- **36 of the 47 sigils work**, including Bifurcated, Trifurcated and Double
  Strike, Touch of Death, Armored, Loose Tail, Sharp Quills, Burrower, Guardian,
  Corpse Eater, Unkillable, Bees Within, Blood Lust, Morsel, Hoarder, Fledgling,
  Ant Spawner, Rabbit Hole, Brood Parasite, Fecundity, Steel Trap, Leader and
  Stinky. A card made by Ant Spawner, Rabbit Hole or Fecundity carries the
  sigils its maker was given, except those three.
- **Items**: all 13, in two slots. Using one, aiming it at a lane, and picking a
  card from the deck (Lens, Hoarder) are their own actions.
- **Leshy places his own cards.** An encounter lists the cards he plays each
  turn; he queues each one opposite a card of yours that can hurt him if he can,
  then in an empty lane, then anywhere free. Ties are broken at random. A card
  with no free queue spot is lost.
- **Totems on both sides**, each touching only its own side's cards.
- **Run modifiers**: an encounter can make every squirrel from the pile
  Waterborne.
- **Hourglass**: Leshy's side stops reacting until his skipped turn.
- **Dynamic attack**: ants, Red Hart, Lammergeier and the tentacles compute
  their power from the board, and the agent sees that number.

### What the agent sees and does

| Input | Shape |
|---|---|
| Lanes (your line, his line, his queue) | 3 × 4 × 52 |
| Hand | 30 × 54 |
| Deck | 99 × 52 |
| Items | 2 × 13 |
| Everything else (scale, bones, turn, held card, totem, …) | 233 |

Each card carries its attack, health, movement direction, whether it is fanned,
and one flag per sigil. There are 158 actions; the network has 573,287
parameters.

### Rewards

| Event | Reward |
|---|---|
| Win | +0.8 |
| Loss, or running out of turns | −1.0 |
| Each enemy card killed | +0.024 |
| Each point of damage past the 5 needed to win | +0.04 |
| Losing one of your cards | −0.005 to −0.025, rising with its blood cost |
| Sacrificing one of your cards | −0.001 to −0.025, rising with its blood cost |
| Each turn | −0.005, and −0.025 more after turn 5 |

## Running it

```bash
pip install tensorflow numpy
python creator.py              # build or load an encounter, then play it or watch the agent
python play.py 12              # play encounter 12 yourself
python main.py train 2000      # train for 2000 batches of 8 battles on the 54, saved to model.keras
python main.py eval            # per-encounter win rate table, with trained-on and held-out totals
python main.py watch 12        # record the agent playing encounter 12 and open the viewer
```

`main.py train` warm-starts from `model.keras` when it exists and still fits the
board, and builds a fresh network when it does not. Delete or move `model.keras`
to train from scratch.

In the player, hovering a card on the board or in the hand shows its stats and
every sigil it carries.

### The encounter creator

`creator.py` loads any of the 66 encounters onto an editable board, or builds
one from nothing, and then plays it, either yourself or with the trained agent.

Pick a card from the palette and its stat line appears: attack, health, tribe,
cost and every sigil it carries. Click a slot to place it; right-click clears
it. Hovering any placed card, or a card in the deck list, shows its stats the
same way.

- **Load a saved encounter**: drop any of the 66 onto the board, then edit it.
- **Modifiers**: attack and health steppers plus a list of all 47 sigils, so a
  card can be placed as a buffed or sigil-granted copy. Attack stops at 0 and
  health at 1.
- **Deck**: build it card by card, or start from the Vanilla or Goat preset.
- **Starting items**: one picker per item slot.
- **Waterborne squirrels**: every squirrel drawn from the pile is Waterborne.
- **Leshy's line and your line**: the cards already on the board when the
  battle starts, in fixed lanes.
- **Leshy's moves**: one row per turn, holding the cards he plays that turn.
  The box a card sits in does not matter, since Leshy picks the lane himself.
  Add and remove turns; an empty turn in the middle is a turn he plays nothing,
  and it is kept.
- **PLAY** opens the encounter in the player, **VIEW** records the trained
  agent playing it and opens the viewer, and **COPY** puts it on the clipboard
  as Python, ready to paste into `Board/encounters.py`.

Totems are not in the creator. To give an encounter one, add `playerTotem` or
`leshyTotem` to the copied source by hand.

## Known limitations

- **11 sigils do nothing yet**: Brittle, Repulsive, Many Lives, Bone King, Dam
  Builder, Bellist, Amorphous, Finical Hatchling, Kraken Waterborne, and the
  boss sigils Omni Strike and Tidal Lock. None of them appears in an encounter.
- **No boss fights** and **no map**: each encounter is a single battle.

## Next steps

### Near term

- **A larger dataset.** Keep transcribing battles from real runs, to reach 100+
  encounters.
- **Grouped k-fold cross-validation.** The current result rests on a single
  held-out split. Encounters that share a deck, a scripted drill or a run are
  closely related, so the folds will be grouped the same way the held-out set
  is: a group never sits on both sides of a split. Averaging over folds gives a
  generalization estimate that does not depend on which 12 encounters happened
  to be held out.
- **Other RL algorithms**, compared against the current PPO under the same
  folds and the same training budget:
  - Generalized Advantage Estimation in place of the current Monte Carlo
    returns, sweeping λ
  - A2C, as a synchronous actor-critic baseline
  - the DQN family (Double DQN, Dueling, prioritized replay), as off-policy
    value-based methods
  - Discrete SAC, for entropy-regularized off-policy learning
  - IMPALA with V-trace, for off-policy-corrected actor-learner training
  - AlphaZero/MuZero-style search

### Further out

The long-term goal is an agent that plays the real game, not only the
simulation. That splits into three models:

- **A battle translator**, possibly a computer vision model, that reads the
  game's battle screen and builds the matching simulated state: the lanes,
  Leshy's queue, the hand, the items and the scale. The trained policy then
  chooses moves on that state, and each move is played back into the game, in
  real time.
- **A map translator**: a computer vision model that turns the run's map into a
  graph, with one node per event and an edge per path between them.
- **A pathing model** that decides which path to take through that graph, based
  on the current items, the deck's composition and the translated map graph.

## Layout

```
Board/      the board, encounters, Leshy's moves, totems
Card/       cards, sigils, dynamic attack
Env/        the RL environment and its rewards
Item/       items
Model/      the network, PPO training, replay recording
creator.py  encounter creator
play.py     play a battle yourself
viewer.py   watch a recorded battle
main.py     train, evaluate, watch
```
