import re
import socket
import gymnasium as gym
import sys
import numpy as np
import math
import pygame
from gymnasium import spaces
from stable_baselines3.common.env_checker import check_env
from stable_baselines3 import A2C

import CarServer

ACTION_PACKET_REGEX = re.compile("^o((\d{1,3},?){5})r(\d+.\d+)t([01])$")
RESET_PACKET_REGEX = re.compile("^o((\d{1,3},?){5})$")

HOST = "127.0.0.1"
PORT = 1234

class CarClient(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, id=0):
        super(CarClient, self).__init__()

        # Define action and observation space
        # Output 2 * [-1 -> 1] for steering and acceleration
        self.action_space = spaces.Box(low=-1, high=1, shape=[2], dtype=np.float32)
        # Input 5 * [0 -> 1] for the 5 radars
        self.observation_space = spaces.Box(low=0, high=1, shape=[5], dtype=np.float32)

        self.conn = socket.socket()
        self.conn.connect((HOST, PORT))
        self.id = id
        self.conn.send(str(id).encode('utf-8'))
        ready = self.conn.recv(1024).decode('utf-8')
        if ready != "go":
            print("Server not ready")
            sys.exit(1)

    def step(self, action):
        print("Client {} step".format(self.id))
        steering_action = action[0]  # steering value between -1 and 1
        throttle_action = action[1]  # throttle value between -1 and 1
        action_packet = f"s{steering_action:.2f}t{throttle_action:.2f}"

        # Send Action To Server
        self.conn.send(action_packet.encode('utf-8'))

        # Wait for answer
        print("Client {} waiting step packet".format(self.id))
        answer = self.conn.recv(1024).decode('utf-8')
        # print("Client {} received: {}".format(self.id, answer))
        match = re.finditer(ACTION_PACKET_REGEX, answer).__next__()

        radars = [float(x) for x in match.group(1).split(',')]
        obs = np.array([0, 0, 0, 0, 0], dtype=np.float32)
        for i, radar in enumerate(radars):
            obs[i] = radar / CarServer.RADAR_MAX_LENGTH

        reward = float(match.group(3))
        terminated = bool(int(match.group(4)))

        return obs, reward, terminated, False, {}

    def reset(self, **kwargs):
        print("Client {} reset".format(self.id))
        # Send Reset Packet To Server
        self.conn.send("r".encode('utf-8'))

        # Wait for reset packet
        print("Client {} waiting reset packet".format(self.id))
        answer = self.conn.recv(1024).decode('utf-8')
        # print("Client {} received: {}".format(self.id, answer))
        match = re.finditer(RESET_PACKET_REGEX, answer).__next__()
        radars = [float(x) for x in match.group(1).split(',')]
        obs = np.array([0, 0, 0, 0, 0], dtype=np.float32)
        for i, radar in enumerate(radars):
            obs[i] = radar / CarServer.RADAR_MAX_LENGTH

        return obs, {}

    def close(self):
        self.conn.close()
        sys.exit(0)