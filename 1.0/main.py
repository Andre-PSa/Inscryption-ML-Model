"""Entry points.

    python main.py train [batches]      train and save to model.keras
    python main.py watch [encounter]    record a battle and open the viewer
    python main.py eval [episodes]      greedy win rate per encounter
    python main.py record [encounter]     record a replay, no viewer

Every command runs without a saved model, using an untrained one — a decent way
to check the plumbing before committing to a long run.
"""

import os
import sys

MODEL_PATH = "model.keras"
REPLAY_PATH = "replay.json"


def loadModel():
    """The saved model if there is one and it still fits the board, otherwise a fresh one."""
    import keras
    from Board.board import board
    from Model.network import buildNetwork

    if not os.path.exists(MODEL_PATH):
        print(f"no {MODEL_PATH} yet, using an untrained network")
        return buildNetwork()

    model = keras.models.load_model(MODEL_PATH)
    # A new sigil widens each card, a new card name widens the globals. Ask the encoder.
    wanted = tuple(part.shape[-1] for part in board().encode())
    saved = tuple(int(part.shape[-1]) for part in model.inputs)
    if saved == wanted:
        print(f"loaded {MODEL_PATH}")
        return model

    print(f"{MODEL_PATH} is stale: it takes {saved}, the board now encodes {wanted}. "
          f"Retrain with 'python main.py train'.")
    return buildNetwork()


def train(batches=200):
    from Model.train import train as runTraining

    model = runTraining(batches=batches, model=loadModel())
    model.save(MODEL_PATH)
    print(f"saved {MODEL_PATH}")


def record(encounter=0, greedy=True):
    from Model.replay import writeReplay

    return writeReplay(loadModel(), REPLAY_PATH,
                       encounterIndex=encounter, greedy=greedy)


def watch(encounter=0):
    from viewer import watch as openViewer

    record(encounter)
    openViewer(REPLAY_PATH)


def evaluate(episodes=100):
    import numpy as np
    from Board.board import result
    from Board.encounters import ENCOUNTERS
    from Env.environment import environment
    from Model.train import predict, MASKED

    model = loadModel()
    env = environment()

    print(f"\n{'encounter':<12}{'wins':>7}{'rate':>8}{'turns':>9}")
    print("-" * 36)

    won = 0
    for index in range(len(ENCOUNTERS)):
        wins = turns = 0
        for _ in range(episodes):
            obs = env.reset(index=index)
            done, steps = False, 0
            while not done and steps < 400:
                mask = env.board.legalActions()
                if not mask.any():
                    break
                actScores, _ = predict(model, obs)
                obs, _, done = env.step(int(np.argmax(np.where(mask, actScores, MASKED))))
                steps += 1
            wins += env.outcome is result.WIN
            turns += env.board.turn
        won += wins
        print(f"{index + 1:<12}{wins:>7}{wins / episodes:>7.0%}{turns / episodes:>9.1f}")

    total = episodes * len(ENCOUNTERS)
    print("-" * 36)
    print(f"{'all':<12}{won:>7}{won / total:>7.0%}")
    print("\nrandom play wins about 13% — beat that by a clear margin.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "watch"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else None

    if command == "train":
        train(arg or 200)
    elif command == "watch":
        watch((arg - 1) if arg else 0)
    elif command == "record":
        record((arg - 1) if arg else 0)
    elif command == "eval":
        evaluate(arg or 100)
    else:
        raise SystemExit(__doc__)
