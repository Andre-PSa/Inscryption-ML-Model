# Design of the 1.1 agent

How the agent sees the game, what it can do, how it learns, and why each piece
is built the way it is. Timings were measured on the development machine; win
rates come from `python main.py eval`.

```
Board/   the game engine: rules, legal-action mask, state encoder
Env/     wraps a battle as reset / step / reward / done
Model/   the network, and PPO training on top of the environment
```

The engine knows nothing about learning. Rewards live in `Env/environment.py`,
so the rules and the incentives can change independently.

---

## 1. Observation

`board.encode()` returns five tensors:

| Input | Shape | Contents |
|---|---|---|
| `lanes` | 3 × 4 × 52 | your line, Leshy's line, his queued row; 4 lanes each |
| `hand` | 30 × 54 | one row per card in hand, plus its cost and currency |
| `deck` | 99 × 52 | one row per card left in the deck |
| `items` | 2 × 13 | one row per item slot, a one-hot of the item in it |
| `globals` | 233 | scale, squirrels left, deck and hand size, bones, turn, the held card, your totem, the held item, card counts by name, sacrifice and Hoarder flags |

Each card is 52 numbers: occupied, attack, health, movement direction, whether
it is fanned, and one flag per sigil (47).

**Attack is computed in context.** Some cards' power depends on the board: ants
count ants, the Red Hart counts sacrifices made, the Hand Tentacle counts cards
in hand, Stinky lowers the attack of the card facing it. Each card is encoded with the attack it would actually deal in
its position, so the model sees the number the engine will use.

**The hand and the deck are sorted into a canonical order.** Order in the hand
carries no meaning in the game, so sorting stops the model treating the same
card in two different slots as two different things. For the deck, the order is
the player's future draws: what is left to draw is fair to see, the order it
will arrive in is not.

**The deck is encoded card by card.** In 1.0 the deck was only a count per card
name, so a campfire-buffed Wolf in the deck looked identical to a plain one
until it was drawn. In 1.1 every deck card carries its own stats and granted
sigils.

---

## 2. Actions

One flat space of **158 actions**, with a legality mask computed by the board at
every step:

```
  0–29    select the card in hand slot i
 30–33    place the selected card in lane i
 34       draw from the deck
 35       draw a squirrel
 36       ring the bell
 37–52    sacrifice a set of lanes, as a 4-bit mask
 53–54    use the item in slot i
 55–58    aim the item at Leshy's lane i
 59–157   take deck slot i (Magnifying Glass, Hoarder)
```

**Sacrifices are a bitmask in the same action space, not a second head.** 1.0
first tried a separate sacrifice head. On any turn without a sacrifice there was
no path from its weights to the loss, so their gradients came back as `None`.
Folding sacrifices into the one action space keeps every weight in the gradient
path on every step.

**Items follow the same pattern.** Using an item, aiming it at a lane, and
picking a card out of the deck are separate actions, so a multi-step item is a
sequence of ordinary choices under the same mask.

---

## 3. Network

573,287 parameters, two heads on a shared trunk:

```
lanes   ─► Permute + Reshape ─► Dense(64) per lane ─► Flatten ─┐
hand    ─► Dense(16) per slot ────────────────────► Flatten ─┤
deck    ─► Dense(8)  per slot ────────────────────► Flatten ─┼─► Dense(256) ─► Dense(256) ─┬─► action (158)
items   ─► Dense(8)  per slot ────────────────────► Flatten ─┤                             └─► value (1, tanh)
globals ─────────────────────────────────────────────────────┘
```

**Lanes are arranged lane-major.** `Permute` and `Reshape` put your card, his
card and his queued card for one lane side by side, so one shared `Dense` sees a
whole lane at once and learns a matchup once for all four lanes, not four times.

**Hand, deck and items use a shared `Dense` per slot** in the same way. The deck
gets fewer units than the hand: it has 99 slots, and every unit is multiplied by
99 when it is flattened into the trunk.

**The value head ends in `tanh`**, an estimate in −1..+1 of how the battle ends.
The terminal rewards are kept inside that range for that reason: a larger one
would saturate it.

---

## 4. Rewards

| Event | Reward |
|---|---|
| Win | +0.8 |
| Loss, or reaching turn 50 | −1.0 |
| Each enemy card killed | +0.024 |
| Each point of damage past the 5 needed to win | +0.04 |
| Losing one of your cards | −0.005 to −0.025, rising with its blood cost |
| Sacrificing one of your cards | −0.001 to −0.025, rising with its blood cost |
| Each turn | −0.005, and −0.025 more after turn 5 |

Deaths are found by diffing the board by card identity before and after each half
of a round, not by counting cards. A sigil that creates a card (Corpse Maggots, a
Brood Parasite's egg) therefore cannot cancel out a death that actually
happened.

Two of these terms exist because of failures found in 1.0:

- **The turn cost.** With γ = 0.99 and no turn cost, delaying a certain loss was
  worth more than taking it, and running out the clock scored 0, which beat
  losing. The agent walled a Rattler with squirrels for twelve turns and then
  lost. Raising γ to 0.999, charging per turn, and scoring the clock running out
  as a loss together took that encounter from 0% to 100%.
- **The sacrifice cost.** With sacrifices free, the agent would sacrifice a
  squirrel for a Stoat and the Stoat for a Bullfrog, spending three cards to put
  one on the board. Pricing sacrifices by blood cost stopped that. Spending a
  squirrel stays almost free, so the agent stays willing to pay for blood cards.

In 1.1 every positive reward was scaled by 0.8 from 1.0's values, the extra turn
cost after turn 5 went from −0.045 to −0.025, and the reward for damage past 5
is new.

---

## 5. Training: PPO

### Why PPO

1.0 started with plain REINFORCE: play a batch of battles, take one gradient
step, throw the games away. Playing the games was by far the expensive part, so
using each one for a single step wasted most of the work. PPO takes several
clipped passes over the same batch instead. In 1.0, the probability ratio
reached about ±6% by the fourth pass, inside the ±20% clip, so all four passes
contributed gradient.

### The update

Each batch plays 8 full battles with the current policy, sampling every move
from the masked softmax. It records each move's board, action, mask, reward and
the log-probability the policy gave that action (`oldTaken`).

Returns are discounted Monte Carlo returns, `G_t = r_t + γ·G_{t+1}`, with
γ = 0.999. At about 4 moves per turn, a reward 40 moves away is worth 96% of its
face value instead of 67% at γ = 0.99.

Then 4 passes over the whole batch at once, each minimizing

```
ratio      = exp(log π(a|s) − oldTaken)
advantage  = stop_gradient(G − V(s))
policy     = −mean( min(ratio · advantage, clip(ratio, 0.8, 1.2) · advantage) )
value      = mean( (G − V(s))² )
loss       = policy + 0.5 · value − 0.01 · mean(entropy)
```

- **The ratio** corrects for the policy having moved since the games were
  played. On the first pass it is exactly 1, and that pass's gradient equals
  REINFORCE with a baseline.
- **The clip** stops the gradient once an action's probability has moved more
  than 20% either way, so one batch can only nudge the policy.
- **The advantage** uses the value head as a baseline. `stop_gradient` keeps it a
  yardstick for the policy rather than something the policy can shrink.
- **The entropy bonus** keeps the policy from becoming deterministic too early.

| | |
|---|---|
| γ | 0.999 |
| clip ε | 0.2 |
| passes per batch | 4 |
| battles per batch | 8 |
| optimizer | Adam, learning rate 3e-4 |
| value weight | 0.5 |
| entropy weight | 0.01 |

Training samples moves from the softmax so the policy keeps exploring.
Evaluation plays the single highest-scoring legal move.

---

## 6. Making it fast

The 20,000-batch training run took 51 minutes 41 seconds, about 0.155 s per
batch. Three changes got it there.

### 6.1 The forward pass as a graph

Every move of every training battle needs one forward pass. Called eagerly,
Keras runs each layer from Python and dispatches each operation separately. For
one board the arithmetic is tiny, so that overhead was almost the whole cost:
**17–18 ms per call**.

`compiled(model)` wraps the forward pass in `tf.function`. TensorFlow traces the
function once, recording its tensor operations as a graph, and later calls run
the whole graph in the C++ runtime. The graph holds handles to the weight
variables, not copies, so it always reads the current weights and never has to
be rebuilt after an update. **1.4–1.6 ms per call.**

### 6.2 Stopping the update from retracing

`trainStep` was already a `tf.function`, but a graph is built for specific input
shapes. Every batch has a different number of moves, so every batch was a new
shape, and TensorFlow rebuilt the graph each time, about **1.1 s per batch**.
With `reduce_retracing=True`, after a few shapes it builds one graph that accepts
any batch length. **About 0.04 s per batch** after warm-up.

Together, 10 batches went from **42.6 s to 6.6 s**.

The Adam optimizer is built against the model's variables before the first
update (`opt.build`). Otherwise it creates its variables inside the traced
function on the first call, which fails when a second model is trained in the
same process.

### 6.3 Playing the batch's battles side by side

Profiling 80 battles after 6.1 and 6.2:

| Part | Share of time | Per move |
|---|---|---|
| forward pass | 78.7% | 1.435 ms |
| `env.step` (engine, rewards, encoding) | 12.4% | 0.227 ms |
| softmax, sampling, bookkeeping | 7.0% | |
| `env.reset` | 1.0% | |
| `legalActions` | 0.9% | 0.016 ms |

The engine is about a fifth of the time, so rewriting it in a faster language
could save at most that fifth. The forward pass was still the target, and most
of its 1.4 ms is the fixed cost of a call rather than arithmetic.

`runEpisodes` plays the 8 battles of a batch in lockstep. Each round, the boards
of every battle still going are stacked and sent through the network in one
call; each battle then samples and plays its own move. A dense layer computes
`X·W + b`. Stacking boards makes `X` taller, one row per board, while `W` stays
the same, and row i of the result depends only on row i of `X`. No layer in this
network mixes rows, so each board gets exactly the result it would get alone
(largest difference measured: 1e-7). Battles drop out of the stack as they end.

It runs in one process, so the engine steps still run one after another; only
the forward pass is shared.

**30 batches went from 13.1 s to 8.1 s.** The gain is limited by battle lengths
within a batch: in one measured batch they were 4, 66, 16, 10, 10, 9, 4 and 15
moves, so for the last 50 rounds only one battle was left and each call
served a single board.

---

## 7. Evaluation

**A held-out test set.** 1.0 trained and evaluated on the same 33 encounters, so
its 95.7% measures play on boards it had seen. In 1.1 the 66 encounters are put
into 12 groups of closely related encounters: the same deck, the same scripted
drills, or the same run. One encounter from each group, picked at random with
seed 0, is held out of training: 1, 3, 7, 12, 16, 19, 29, 32, 39, 45, 59 and 61.

**Greedy play, 100 battles per encounter.** The baseline is a uniform-random
policy over the same legal-action mask, 1,000 battles per encounter.

| | Encounters | Model | Random |
|---|---|---|---|
| Trained on | 54 | 87% | 9.9% |
| Held out | 12 | 73% | 7.4% |

This is a single split. Grouped k-fold cross-validation over the same 12 groups
is the next step, so the estimate does not depend on which 12 encounters were
held out.
