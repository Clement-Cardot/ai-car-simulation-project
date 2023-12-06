import gymnasium as gym
import sys
import numpy as np
import math
import pygame
from gymnasium import spaces
from stable_baselines3.common.env_checker import check_env
from stable_baselines3 import A2C

from Race import Race


class Car(gym.Env):
    """Custom Environment that follows gym interface"""
    metadata = {'render.modes': ['human']}

    WIDTH = 1920
    HEIGHT = 1080

    BORDER_COLOR = (255, 255, 255, 255)  # Color To Crash on Hit

    CAR_SIZE_X = 60
    CAR_SIZE_Y = 60

    MIN_SPEED = 5
    MAX_SPEED = 40

    MAX_THROTTLE = 15
    MAX_STEERING = 8

    RADAR_MAX_LENGTH = 300

    def __init__(self, race):
        super(Car, self).__init__()
        self.race = race
        self.race.cars.append(self)

        # Define action and observation space
        # Output 2 * [0 -> 1] for steering and acceleration
        self.action_space = spaces.Box(low=-1, high=1, shape=[2], dtype=np.float32)
        # Input 5 * [0 -> 1] for the 5 radars
        self.observation_space = spaces.Box(low=0, high=1, shape=[5], dtype=np.float32)

        # Load Car Sprite and Rotate
        self.rotated_sprite = self.race.SPRITE

        # Starting Position
        self.position = [830, 920]
        self.angle = 0
        self.speed = 0
        self.speed_set = False  # Flag For Default Speed Later on

        self.center = [self.position[0] + self.CAR_SIZE_X / 2, self.position[1] + self.CAR_SIZE_Y / 2]  # Calculate Center

        self.radars = []  # List For Sensors / Radars
        self.drawing_radars = []  # Radars To Be Drawn

        self.alive = True  # Boolean To Check If Car is Crashed

        self.distance = 0  # Distance Driven
        self.time = 0  # Time Passed

    def step(self, action):
        self.action(action)
        self.update()
        obs = self.get_data()
        reward = self.get_reward()
        terminated = not self.is_alive()

        self.race.draw()

        return obs, reward, terminated, False, {}

    def reset(self, **kwargs):
        self.race.set_best_reward()
        self.rotated_sprite = self.race.SPRITE

        # Starting Position
        self.position = [830, 920]
        self.angle = 0
        self.speed = 0
        self.speed_set = False  # Flag For Default Speed Later on

        self.center = [self.position[0] + self.CAR_SIZE_X / 2,
                       self.position[1] + self.CAR_SIZE_Y / 2]  # Calculate Center

        self.radars = []  # List For Sensors / Radars
        self.drawing_radars = []  # Radars To Be Drawn

        self.alive = True  # Boolean To Check If Car is Crashed

        self.distance = 0  # Distance Driven
        self.time = 0  # Time Passed

        # Run first tick
        self.update()
        observation = self.get_data()
        info = {}
        return observation, info  # reward, done, info can't be included

    def close(self):
        sys.exit(0)

    def draw(self):
        self.race.screen.blit(self.rotated_sprite, self.position)  # Draw Sprite
        # Optionally Draw All Sensors / Radars
        for radar in self.radars:
            position = radar[0]
            pygame.draw.line(self.race.screen, (0, 255, 0), self.center, position, 1)
            pygame.draw.circle(self.race.screen, (0, 255, 0), position, 5)

    def check_collision(self):
        self.alive = True
        corners = self.calculate_corners()
        for point in corners:
            # If Any Corner Touches Border Color -> Crash
            # Assumes Rectangle
            if self.race.MAP.get_at((int(point[0]), int(point[1]))) == self.BORDER_COLOR:
                self.alive = False
                break

    def check_radar(self, degree):
        length = 0
        x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
        y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

        # While We Don't Hit BORDER_COLOR AND length < 300 (just a max) -> go further and further
        while not self.race.MAP.get_at((x, y)) == self.BORDER_COLOR and length < self.RADAR_MAX_LENGTH:
            length = length + 1
            x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
            y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

        # Calculate Distance To Border And Append To Radars List
        dist = int(math.sqrt(math.pow(x - self.center[0], 2) + math.pow(y - self.center[1], 2)))
        self.radars.append([(x, y), dist])

    def update(self):
        # Set The Speed To 20 For The First Time
        # Only When Having 4 Output Nodes With Speed Up and Down
        if not self.speed_set:
            self.speed = self.MIN_SPEED
            self.speed_set = True

        # Get Rotated Sprite And Move Into The Right X-Direction
        # Don't Let The Car Go Closer Than 20px To The Edge
        self.rotated_sprite = self.rotate_center(self.race.SPRITE, self.angle)
        self.position[0] += math.cos(math.radians(360 - self.angle)) * self.speed
        self.position[0] = max(self.position[0], 20)
        self.position[0] = min(self.position[0], self.WIDTH - 120)

        # Increase Distance and Time
        self.distance += self.speed
        self.time += 1

        # Same For Y-Position
        self.position[1] += math.sin(math.radians(360 - self.angle)) * self.speed
        self.position[1] = max(self.position[1], 20)
        self.position[1] = min(self.position[1], self.WIDTH - 120)

        # Calculate New Center
        self.center = [int(self.position[0]) + self.CAR_SIZE_X / 2, int(self.position[1]) + self.CAR_SIZE_Y / 2]

        self.calculate_corners()

        # Check Collisions And Clear Radars
        self.check_collision()
        self.radars.clear()

        # From -90 To 120 With Step-Size 45 Check Radar
        for d in range(-90, 120, 45):
            self.check_radar(d)

    def calculate_corners(self):
        # Calculate Four Corners
        # Length Is Half The Side
        length = 0.5 * self.CAR_SIZE_X
        left_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 30))) * length,
                    self.center[1] + math.sin(math.radians(360 - (self.angle + 30))) * length]
        right_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 150))) * length,
                     self.center[1] + math.sin(math.radians(360 - (self.angle + 150))) * length]
        left_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 210))) * length,
                       self.center[1] + math.sin(math.radians(360 - (self.angle + 210))) * length]
        right_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 330))) * length,
                        self.center[1] + math.sin(math.radians(360 - (self.angle + 330))) * length]
        return [left_top, right_top, left_bottom, right_bottom]

    def get_data(self):
        # Get Distances To Border
        radars = self.radars
        return_values = np.array([0, 0, 0, 0, 0], dtype=np.float32)
        for i, radar in enumerate(radars):
            return_values[i] = radar[1] / self.RADAR_MAX_LENGTH

        return return_values

    def is_alive(self):
        # Basic Alive Function
        return self.alive

    def get_reward(self):
        # Calculate Reward (Maybe Change?)
        # return self.distance / 50.0
        return self.distance / (self.CAR_SIZE_X / 2)

    def rotate_center(self, image, angle):
        # Rotate The Rectangle
        rectangle = image.get_rect()
        rotated_image = pygame.transform.rotate(image, angle)
        rotated_rectangle = rectangle.copy()
        rotated_rectangle.center = rotated_image.get_rect().center
        rotated_image = rotated_image.subsurface(rotated_rectangle).copy()
        return rotated_image

    def action(self, action):
        steering_action = action[0]  # steering value between -1 and 1
        throttle_action = action[1]  # throttle value between -1 and 1

        self.angle = self.angle + steering_action * self.MAX_STEERING
        self.speed = self.speed + throttle_action * self.MAX_THROTTLE

        if self.speed > self.MAX_SPEED:
            self.speed = self.MAX_SPEED
        elif self.speed < self.MIN_SPEED:
            self.speed = self.MIN_SPEED


if __name__ == '__main__':
    new_race = Race()
    env = Car(new_race)
    # It will check your custom environment and output additional warnings if needed
    check_env(env)
    # Define and Train the agent
    model = A2C("MlpPolicy", env).learn(total_timesteps=10000)