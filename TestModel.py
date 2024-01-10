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

def test_model(algo, nb_model_map):
    car = CarClient()
    check_env(car)
    match algo:
        case "PPO":
            model = A2C.load('./modelPPO/map{}'.format(nb_model_map))
            obs, info = car.reset()
            while True:
                action, _states = model.predict(obs)
                obs, rewards, terminated, info, autre = car.step(action)
        case "A2C":
            model = A2C.load('./modelA2C/map{}'.format(nb_model_map))
            obs, info = car.reset()
            while True:
                action, _states = model.predict(obs)
                obs, rewards, terminated, info, autre = car.step(action)
                print(terminated)
                if(terminated):
                    break



def thread_race(NB_CARS, NB_MAPS):
    RaceServer(NB_CARS, NB_MAPS).run()

if __name__ == '__main__':

    NB_MAPS = 2
    NB_MODEL_MAP = 4

    # Start Race Server
    race = threading.Thread(target=thread_race, args=(1, NB_MAPS))
    race.start()

    model = A2C.load("./modelA2C/map2")


    test_model("A2C", NB_MODEL_MAP)
