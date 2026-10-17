# Inscryption RL

A reinforcement learning agent that plays Inscryption's Kaycee's Mod, trained
with PPO against a game engine written from scratch.

## 1.0

[`1.0/`](1.0) is the first iteration — the engine, the agent, the trained
weights and the tools, frozen together in a working state. It wins **95.7%** of
33 transcribed encounters, against **6.6%** for random play.

```bash
cd 1.0
pip install tensorflow numpy
python creator.py
```

[`1.0/README.md`](1.0/README.md) explains how it works, what each reward term is
for, and the bottlenecks that had to be solved along the way.

## 1.1

[`1.1/`](1.1) is the second iteration: 66 encounters, the full card pool,
items, and a Leshy who chooses where his cards go. 12 of the encounters are
held out of training. The trained model wins **87%** of the 54 it trained on and
**73%** of the 12 it never saw, against **9.9%** and **7.4%** for random play.

```bash
cd 1.1
pip install tensorflow numpy
python creator.py
```

[`1.1/README.md`](1.1/README.md) covers what changed since 1.0, the results per
encounter, and how to build encounters with the creator.
[`1.1/DESIGN.md`](1.1/DESIGN.md) covers how the agent is built and trained, and
why.

> **Comparing the two:** 1.0 had no train/test split, so its 95.7% is measured
> on the same encounters it trained on. 1.1's model trained for 20,000 batches,
> on a game that is a lot more complex than 1.0's.

## Where the encounters come from

Every encounter is transcribed by hand from real play: the deck, the items,
Leshy's cards turn by turn, and any run modifiers, entered into the encounter
creator and pasted into `Board/encounters.py`.

Doing this by hand is tedious. The plan is an auto-transcriber that runs the
game by itself and records its battles as encounters. However, this will
require building a separate model that can traverse the game's map and make
decisions about which encounters to play, which is a much harder problem than
just playing the battles themselves.

It will be done, in time.

## AI usage

This project was built with the help of Claude Code, Anthropic's AI coding
assistant.

- **The game environment:** I wrote the vast majority of 1.0's environment myself. Much
  of what 1.1 added to it was written by Claude Code, from rules I specified,
  and revised by me.
- **The model and training:** written with Claude Code, under my direction. I
  specified each part and reviewed every change before it went in.
- **The encounters** all come from my own runs of the game, transcribed from my
  play.
- **The documentation** was drafted with Claude Code and revised by me.
