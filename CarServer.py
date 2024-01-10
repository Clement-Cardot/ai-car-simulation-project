import math
import re
from typing import Iterator

import pygame

ACTION_PACKET_REGEX = re.compile("^s(-?[01]\.\d+)t(-?[01]\.\d+)$")

BORDER_COLOR = (255, 255, 255, 255)  # Color To Crash on Hit

SECTOR1_COLOR = (0, 0, 255, 255)
SECTOR2_COLOR = (0, 255, 0, 255)
SECTOR3_COLOR = (255, 0, 0, 255)

WIDTH = 1920
HEIGHT = 1080

CAR_SIZE_X = 60
CAR_SIZE_Y = 60

MIN_SPEED = 10
MAX_SPEED = 40

MAX_THROTTLE = 15
MAX_STEERING = 8

RADAR_MAX_LENGTH = 300

class CarServer:

    def __init__(self, car_id, conn, addr, screen, SPRITE, MAP):
        # Socket Connection to AI Client
        self.car_id = car_id
        self.conn = conn
        self.addr = addr
        self.isConnected = True

        self.screen = screen
        # Load Car Sprite and Rotate
        self.SPRITE = SPRITE
        self.MAP = MAP
        self.rotated_sprite = SPRITE

        # Starting Position
        self.position = [830, 920]
        self.angle = 0
        self.speed = 0
        self.speed_set = False  # Flag For Default Speed Later on

        self.center = [self.position[0] + CAR_SIZE_X / 2,
                       self.position[1] + CAR_SIZE_Y / 2]  # Calculate Center

        self.radars = []  # List For Sensors / Radars
        self.drawing_radars = []  # Radars To Be Drawn

        self.alive = True  # Boolean To Check If Car is Crashed

        self.distance = 0  # Distance Driven
        self.time = 0  # Time Passed

        self.current_sector = 0
        self.turnCount = 1

        self.reward = 0
        self.sectorReward = 0
        self.distReward = 0

    def step(self):
        #print("Server Car {} step".format(self.car_id))
        # Receive Action From Client
        # print("Server Car {} WAIT".format(self.car_id))
        action = 'r'
        while (action == 'r'):

            action = self.conn.recv(1024)
            if action == 0:
                print('deconnected')
                self.conn.close()
                self.isConnected = False
                return
            action = action.decode('utf-8')
            # print("Server Car {} received: {}".format(self.car_id, action))

            if action == "r":
                self.reset()
            else:
                try:
                    match: Iterator = re.finditer(ACTION_PACKET_REGEX, action).__next__()
                except StopIteration:
                    print("Server Car {}: Invalid action packet received: '{}'".format(self.car_id, action))

                steering = float(match.group(1))
                throttle = float(match.group(2))

                # Execute action
                self.action([steering, throttle])

                # Update car state
                self.update()

                # Get return data
                obs = self.radars
                reward = self.get_reward()
                terminated = not self.is_alive()

                # Send data to client
                self.conn.sendall(str.encode("o" + str(obs[0][1])
                                             + "," + str(obs[1][1])
                                             + "," + str(obs[2][1])
                                             + "," + str(obs[3][1])
                                             + "," + str(obs[4][1])
                                             + "r" + f"{reward:.2f}"
                                             + "t" + str(int(terminated))))

    def reset(self):
        #print("Server Car {} RESET".format(self.car_id))
        self.rotated_sprite = self.SPRITE

        # Starting Position
        self.position = [830, 920]
        self.angle = 0
        self.speed = 0
        self.speed_set = False  # Flag For Default Speed Later on

        self.center = [self.position[0] + CAR_SIZE_X / 2,
                       self.position[1] + CAR_SIZE_Y / 2]  # Calculate Center

        self.radars = []  # List For Sensors / Radars
        self.drawing_radars = []  # Radars To Be Drawn

        self.alive = True  # Boolean To Check If Car is Crashed

        self.distance = 0  # Distance Driven
        self.time = 0  # Time Passed

        self.current_sector = 0
        self.turnCount = 1

        self.reward = 0
        self.sectorReward = 0
        self.distReward = 0

        # Run first tick
        self.update()
        obs = self.radars

        # Send data to client
        self.conn.sendall(str.encode("o" + str(obs[0][1])
                                     + "," + str(obs[1][1])
                                     + "," + str(obs[2][1])
                                     + "," + str(obs[3][1])
                                     + "," + str(obs[4][1])))

    def action(self, action):
        steering_action = action[0]  # steering value between -1 and 1
        throttle_action = action[1]  # throttle value between -1 and 1

        self.angle = self.angle + steering_action * MAX_STEERING
        self.speed = self.speed + throttle_action * MAX_THROTTLE

        if self.speed > MAX_SPEED:
            self.speed = MAX_SPEED
        elif self.speed < MIN_SPEED:
            self.speed = MIN_SPEED

    def update(self):
        # Set The Speed To 20 For The First Time
        # Only When Having 4 Output Nodes With Speed Up and Down
        if not self.speed_set:
            self.speed = MIN_SPEED
            self.speed_set = True

        # Get Rotated Sprite And Move Into The Right X-Direction
        # Don't Let The Car Go Closer Than 20px To The Edge
        self.rotated_sprite = self.rotate_center(self.SPRITE, self.angle)
        self.position[0] += math.cos(math.radians(360 - self.angle)) * self.speed
        self.position[0] = max(self.position[0], 20)
        self.position[0] = min(self.position[0], WIDTH - 120)

        # Increase Distance and Time
        self.distance += self.speed
        self.time += 1

        # Same For Y-Position
        self.position[1] += math.sin(math.radians(360 - self.angle)) * self.speed
        self.position[1] = max(self.position[1], 20)
        self.position[1] = min(self.position[1], WIDTH - 120)

        # Calculate New Center
        self.center = [int(self.position[0]) + CAR_SIZE_X / 2, int(self.position[1]) + CAR_SIZE_Y / 2]

        self.calculate_corners()

        # Check Collisions And Clear Radars
        self.check_collision()
        self.radars.clear()

        # From -90 To 120 With Step-Size 45 Check Radar
        for d in range(-90, 120, 45):
            self.check_radar(d)

    def is_alive(self):
        # Basic Alive Function
        return self.alive

    def get_reward(self):
        # Calculate Reward (Maybe Change?)
        #return self.distance / 50.0
        # return self.distance / (CAR_SIZE_X / 2)

        result = 0
        if self.time :
            self.distReward = self.distance/1000 + self.distance / (50 * self.time)
        else:
            self.distReward = self.distance/1000 + self.distance / 50

        result -= self.sectorReward
        result += self.distReward
        self.reward = result

        return result

    def rotate_center(self, image, angle):
        # Rotate The Rectangle
        rectangle = image.get_rect()
        rotated_image = pygame.transform.rotate(image, angle)
        rotated_rectangle = rectangle.copy()
        rotated_rectangle.center = rotated_image.get_rect().center
        rotated_image = rotated_image.subsurface(rotated_rectangle).copy()
        return rotated_image

    def calculate_corners(self):
        # Calculate Four Corners
        # Length Is Half The Side
        length = 0.5 * CAR_SIZE_X
        left_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 30))) * length,
                    self.center[1] + math.sin(math.radians(360 - (self.angle + 30))) * length]
        right_top = [self.center[0] + math.cos(math.radians(360 - (self.angle + 150))) * length,
                     self.center[1] + math.sin(math.radians(360 - (self.angle + 150))) * length]
        left_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 210))) * length,
                       self.center[1] + math.sin(math.radians(360 - (self.angle + 210))) * length]
        right_bottom = [self.center[0] + math.cos(math.radians(360 - (self.angle + 330))) * length,
                        self.center[1] + math.sin(math.radians(360 - (self.angle + 330))) * length]
        return [left_top, right_top, left_bottom, right_bottom]

    def check_radar(self, degree):
        length = 0
        x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
        y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

        # While We Don't Hit BORDER_COLOR AND length < 300 (just a max) -> go further and further
        # while not self.MAP.get_at((x, y)) == BORDER_COLOR and length < RADAR_MAX_LENGTH:
        #     length = length + 1
        #     x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
        #     y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

        while 0 <= x < self.MAP.get_width() and 0 <= y < self.MAP.get_height() and (
                self.MAP.get_at((x, y)) != BORDER_COLOR and
                self.MAP.get_at((x, y)) != SECTOR1_COLOR and
                self.MAP.get_at((x, y)) != SECTOR2_COLOR and
                self.MAP.get_at((x, y)) != SECTOR3_COLOR) and length < RADAR_MAX_LENGTH:

            length = length + 1
            x = int(self.center[0] + math.cos(math.radians(360 - (self.angle + degree))) * length)
            y = int(self.center[1] + math.sin(math.radians(360 - (self.angle + degree))) * length)

            new_sector = 0
            if self.MAP.get_at((x, y)) == SECTOR1_COLOR:
                if self.current_sector == 2:
                    new_sector = 1
                self.current_sector = 1
            if self.MAP.get_at((x, y)) == SECTOR2_COLOR:
                if self.current_sector == 3:
                    new_sector = 1
                self.current_sector = 2
            if self.MAP.get_at((x, y)) == SECTOR3_COLOR:
                if self.current_sector == 1:
                    new_sector = 1
                    self.turnCount += 1
                self.current_sector = 3

            if new_sector:
                self.sectorReward += self.current_sector * 1000 / (self.time / self.turnCount)

        # Calculate Distance To Border And Append To Radars List
        dist = int(math.sqrt(math.pow(x - self.center[0], 2) + math.pow(y - self.center[1], 2)))
        self.radars.append([(x, y), dist])

    def check_collision(self):
        self.alive = True
        corners = self.calculate_corners()
        for point in corners:
            # If Any Corner Touches Border Color -> Crash
            # Assumes Rectangle
            if self.MAP.get_at((int(point[0]), int(point[1]))) == BORDER_COLOR:
                self.alive = False
                break

    def draw(self):
        self.screen.blit(self.rotated_sprite, self.position)  # Draw Sprite
        # Optionally Draw All Sensors / Radars
        for radar in self.radars:
            position = radar[0]
            pygame.draw.line(self.screen, (0, 255, 0), self.center, position, 1)
            pygame.draw.circle(self.screen, (0, 255, 0), position, 5)
