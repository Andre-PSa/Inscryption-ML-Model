"""PPO with a value baseline.

Play whole battles, discount what they scored, and push the action head toward
the moves that beat what the value head expected. Each batch is reused for a
few passes, with the update clipped so a pass cannot walk far from the policy
that collected it.
"""

import time

import numpy as np
import tensorflow as tf
from keras import optimizers

from Board.board import N_ACTIONS
from Env.environment import environment, REWARD_WIN
from Model.network import buildNetwork

GAMMA = 0.999 #γⁿ
LEARNING_RATE = 3e-4 
VALUE_WEIGHT = 0.5
ENTROPY_WEIGHT = 0.01
EPISODES_PER_BATCH = 8

# Passes over each collected batch. More squeezes the same games harder, until
# the data no longer describes the policy reading it.
EPOCHS_PER_BATCH = 4

# How far one batch may move any action's probability, either way.
CLIP = 0.2

# Finite rather than -inf, which would give NaN where it meets a zero probability.
MASKED = -1e9


_COMPILED = {}


def compiled(model):
    """The model's forward pass as a graph, built once per model. Called eagerly it
    is an order of magnitude slower, and it runs once for every round of play."""
    if id(model) not in _COMPILED:
        @tf.function(reduce_retracing=True)
        def forward(lanes, hand, deck, items, glob):
            return model([lanes, hand, deck, items, glob], training=False)
        _COMPILED[id(model)] = forward
    return _COMPILED[id(model)]


def predict(model, obs):
    """One board through the model. Adds and strips the batch dimension."""
    lanes, hand, deck, items, glob = obs
    action, value = compiled(model)(lanes[None], hand[None], deck[None], items[None],
                                    glob[None])
    return action.numpy()[0], float(value.numpy()[0, 0])


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def runEpisodes(envs, model, rng):
    """Play one battle per environment side by side, recording every action-head
    decision. Each round sends the boards of every battle still going through the
    model together, so a call costs about the same for all of them as for one."""
    obs = [env.reset() for env in envs]
    records = [{"lanes": [], "hands": [], "decks": [], "items": [], "globs": [],
                "actions": [], "masks": [], "rewards": [], "logProbs": []} for _ in envs]
    live = list(range(len(envs)))

    while live:
        masks = {i: envs[i].board.legalActions() for i in live}
        live = [i for i in live if masks[i].any()]
        if not live:
            break

        actScores, _ = compiled(model)(*[np.stack([obs[i][part] for i in live])
                                         for part in range(5)])
        actScores = actScores.numpy()

        still = []
        for row, i in enumerate(live):
            probs = softmax(np.where(masks[i], actScores[row], MASKED))
            action = int(rng.choice(N_ACTIONS, p=probs))

            r = records[i]
            r["lanes"].append(obs[i][0])
            r["hands"].append(obs[i][1])
            r["decks"].append(obs[i][2])
            r["items"].append(obs[i][3])
            r["globs"].append(obs[i][4])
            r["actions"].append(action)
            r["masks"].append(masks[i])
            # The policy that chose this, kept so later passes can measure their drift from it.
            r["logProbs"].append(np.log(probs[action] + 1e-10))

            obs[i], reward, done = envs[i].step(action)
            r["rewards"].append(reward)
            if not done:
                still.append(i)
        live = still

    return [(np.array(r["lanes"]), np.array(r["hands"]), np.array(r["decks"]),
             np.array(r["items"]), np.array(r["globs"]),
             np.array(r["actions"], dtype=np.int32), np.array(r["masks"]),
             np.array(r["rewards"], dtype=np.float32),
             np.array(r["logProbs"], dtype=np.float32))
            for r in records]


def discountedReturns(rewards):
    """What each step eventually earned, counting later rewards less."""
    out = np.zeros_like(rewards)
    running = 0.0
    for i in reversed(range(len(rewards))):
        running = rewards[i] + GAMMA * running
        out[i] = running
    return out


@tf.function(reduce_retracing=True)
def trainStep(model, opt, lanes, hands, decks, items, globs, actions, masks,
              returns, oldTaken):
    with tf.GradientTape() as tape:
        actLogits, values = model([lanes, hands, decks, items, globs], training=True)
        actLogits = tf.where(masks, actLogits, MASKED)

        logProbs = tf.nn.log_softmax(actLogits)
        taken = tf.gather(logProbs, actions, batch_dims=1)

        values = tf.squeeze(values, axis=-1)
        advantage = returns - values

        # stop_gradient: a yardstick for the policy, not something it may shrink.
        advantage = tf.stop_gradient(advantage)

        # 1.0 on the first pass, drifting as the weights move away from the collector.
        ratio = tf.exp(taken - oldTaken)
        clipped = tf.clip_by_value(ratio, 1.0 - CLIP, 1.0 + CLIP)
        # The pessimistic branch: no credit for overshooting, full penalty for going wrong.
        policyLoss = -tf.reduce_mean(tf.minimum(ratio * advantage, clipped * advantage))
        valueLoss = tf.reduce_mean(tf.square(returns - values))

        entropy = -tf.reduce_sum(tf.nn.softmax(actLogits) * logProbs, axis=-1)
        loss = (policyLoss
                + VALUE_WEIGHT * valueLoss
                - ENTROPY_WEIGHT * tf.reduce_mean(entropy))

    grads = tape.gradient(loss, model.trainable_variables)
    opt.apply_gradients(zip(grads, model.trainable_variables))
    return policyLoss, valueLoss


def clock(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}"


def train(batches=200, seed=0, model=None, encounters=None):
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    pick = __import__("random").Random(seed)
    envs = [environment(encounters=encounters, rng=pick) for _ in range(EPISODES_PER_BATCH)]
    model = model if model is not None else buildNetwork()
    opt = optimizers.Adam(LEARNING_RATE)
    opt.build(model.trainable_variables)

    for batch in range(batches):
        episodes = runEpisodes(envs, model, rng)
        episodes = [e for e in episodes if len(e[5]) > 0]
        if not episodes:
            continue

        lanes = tf.constant(np.concatenate([e[0] for e in episodes]))
        hands = tf.constant(np.concatenate([e[1] for e in episodes]))
        decks = tf.constant(np.concatenate([e[2] for e in episodes]))
        items = tf.constant(np.concatenate([e[3] for e in episodes]))
        globs = tf.constant(np.concatenate([e[4] for e in episodes]))
        actions = tf.constant(np.concatenate([e[5] for e in episodes]))
        masks = tf.constant(np.concatenate([e[6] for e in episodes]))
        returns = tf.constant(np.concatenate([discountedReturns(e[7]) for e in episodes]))
        oldTaken = tf.constant(np.concatenate([e[8] for e in episodes]))

        # The same games, read several times; the clip keeps the later reads honest.
        for _ in range(EPOCHS_PER_BATCH):
            policyLoss, valueLoss = trainStep(model, opt, lanes, hands, decks, items,
                                              globs, actions, masks, returns,
                                              oldTaken)

        if batch % 10 == 0:
            wins = sum(1 for e in episodes if e[7][-1] >= REWARD_WIN * 0.9)
            totals = [e[7].sum() for e in episodes]
            print(f'batch {batch:>4}  '
                  f'wins {wins}/{len(episodes)}  '
                  f'reward {np.mean(totals):+.3f}  '
                  f'policy {float(policyLoss):+.4f}  '
                  f'value {float(valueLoss):.4f}  '
                  f'{clock(time.perf_counter() - start)}')

    print(f'trained {batches} batches in {clock(time.perf_counter() - start)}')
    return model
