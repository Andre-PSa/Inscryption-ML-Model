"""PPO with a value baseline.

Play whole battles, discount what they scored, and push the action head toward
the moves that beat what the value head expected. Each batch is reused for a
few passes, with the update clipped so a pass cannot walk far from the policy
that collected it.
"""

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


def predict(model, obs):
    """One board through the model. Adds and strips the batch dimension."""
    lanes, hand, glob = obs
    action, value = model([lanes[None], hand[None], glob[None]], training=False)
    return action.numpy()[0], float(value.numpy()[0, 0])


def softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def runEpisode(env, model, rng):
    """Play one battle, recording every action-head decision."""
    obs = env.reset()
    lanes, hands, globs, actions, masks, rewards, logProbs = [], [], [], [], [], [], []
    done = False

    while not done:
        mask = env.board.legalActions()
        if not mask.any():
            break

        actScores, _ = predict(model, obs)
        probs = softmax(np.where(mask, actScores, MASKED))
        action = int(rng.choice(N_ACTIONS, p=probs))

        lanes.append(obs[0])
        hands.append(obs[1])
        globs.append(obs[2])
        actions.append(action)
        masks.append(mask)
        # The policy that chose this, kept so later passes can measure their drift from it.
        logProbs.append(np.log(probs[action] + 1e-10))

        obs, reward, done = env.step(action)
        rewards.append(reward)

    return (np.array(lanes), np.array(hands), np.array(globs),
            np.array(actions, dtype=np.int32), np.array(masks),
            np.array(rewards, dtype=np.float32),
            np.array(logProbs, dtype=np.float32))


def discountedReturns(rewards):
    """What each step eventually earned, counting later rewards less."""
    out = np.zeros_like(rewards)
    running = 0.0
    for i in reversed(range(len(rewards))):
        running = rewards[i] + GAMMA * running
        out[i] = running
    return out


@tf.function
def trainStep(model, opt, lanes, hands, globs, actions, masks, returns, oldTaken):
    with tf.GradientTape() as tape:
        actLogits, values = model([lanes, hands, globs], training=True)
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


def train(batches=200, seed=0, model=None):
    rng = np.random.default_rng(seed)
    env = environment(rng=__import__("random").Random(seed))
    model = model if model is not None else buildNetwork()
    opt = optimizers.Adam(LEARNING_RATE)

    for batch in range(batches):
        episodes = [runEpisode(env, model, rng) for _ in range(EPISODES_PER_BATCH)]
        episodes = [e for e in episodes if len(e[3]) > 0]
        if not episodes:
            continue

        lanes = tf.constant(np.concatenate([e[0] for e in episodes]))
        hands = tf.constant(np.concatenate([e[1] for e in episodes]))
        globs = tf.constant(np.concatenate([e[2] for e in episodes]))
        actions = tf.constant(np.concatenate([e[3] for e in episodes]))
        masks = tf.constant(np.concatenate([e[4] for e in episodes]))
        returns = tf.constant(np.concatenate([discountedReturns(e[5]) for e in episodes]))
        oldTaken = tf.constant(np.concatenate([e[6] for e in episodes]))

        # The same games, read several times; the clip keeps the later reads honest.
        for _ in range(EPOCHS_PER_BATCH):
            policyLoss, valueLoss = trainStep(model, opt, lanes, hands, globs,
                                              actions, masks, returns, oldTaken)

        if batch % 10 == 0:
            wins = sum(1 for e in episodes if e[5][-1] >= REWARD_WIN * 0.9)
            totals = [e[5].sum() for e in episodes]
            print(f'batch {batch:>4}  '
                  f'wins {wins}/{len(episodes)}  '
                  f'reward {np.mean(totals):+.3f}  '
                  f'policy {float(policyLoss):+.4f}  '
                  f'value {float(valueLoss):.4f}')

    return model
