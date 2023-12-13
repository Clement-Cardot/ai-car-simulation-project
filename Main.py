import threading

import gymnasium as gym
from stable_baselines3.common.env_checker import check_env
from stable_baselines3 import DQN, A2C, PPO
from typing import Callable

from stable_baselines3.common.utils import set_random_seed
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.logger import configure

from CarClient import CarClient
from RaceServer import RaceServer


def make_env(rank: int, seed: int = 0) -> Callable:

    def _init() -> gym.Env:
        env = CarClient(rank)
        env.reset(seed=seed + rank)
        return env

    set_random_seed(seed)
    return _init

def train_multiproccess(algo, num_cpu=2):
    # Multi-processing
    car = SubprocVecEnv([make_env(i) for i in range(num_cpu)])
    match algo:
        case "DQN":
            DQNmodel = DQN("MlpPolicy", car).learn(total_timesteps=900000)
        case "A2C":
            A2Cmodel = A2C("MlpPolicy", car).learn(total_timesteps=900000)

def train_monoproccess(algo):
    car = CarClient()
    check_env(car)
    match algo:
        case "DQN":
            DQNmodel = DQN("MlpPolicy", car).learn(total_timesteps=900000)
        case "A2C":
            A2Cmodel = A2C("MlpPolicy", car).learn(total_timesteps=900000)

def thread_race(NB_CARS):
    RaceServer(NB_CARS).run()

if __name__ == '__main__':

    NB_CARS = 12

    # Start Race Server
    race = threading.Thread(target=thread_race, args=(NB_CARS,))
    race.start()

    if NB_CARS == 1:
        # Start Training with Mono Client
        train_monoproccess("A2C")
    else:
        # Start Training with AI Clients
        train_multiproccess("A2C", NB_CARS)