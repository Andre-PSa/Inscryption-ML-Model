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

Work on the next iteration is ongoing.
