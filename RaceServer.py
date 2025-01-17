import socket
import sys
import threading
import time

import pygame

from CarServer import CarServer

HOST = "0.0.0.0"
PORT = 1236

WIDTH = 1920
HEIGHT = 1080

CAR_SIZE_X = 60
CAR_SIZE_Y = 60


class RaceServer:

    def __init__(self, NB_CARS=1, NB_MAPS=1):
        self.NB_CARS = NB_CARS
        # Initialize a socket server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((HOST, PORT))

        # Initialize PyGame And The Display
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

        # Init pygame assets
        self.clock = pygame.time.Clock()
        self.SPRITE = pygame.image.load('assets/car.png').convert()  # Convert Speeds Up A Lot
        self.SPRITE = pygame.transform.scale(self.SPRITE, (CAR_SIZE_X, CAR_SIZE_Y))
        self.MAP = pygame.image.load('assets/map{}.png'.format(NB_MAPS)).convert()  # Convert Speeds Up A Lot
        self.font = pygame.font.SysFont("Arial", 30)

        # Create an empty list of cars
        self.cars = []
        self.time = time.time()
        self.lastFrameTime = round(time.time() * 1000)
        self.fpsBuffer = []
        self.best_reward = 0

        # Draw Map
        self.draw()
        print("Server ready for running !")

    def call_car_step(self, car):
        car.step()

    def run(self):
        print("Server : Server running !")
        print("Server : waiting for {} clients!".format(self.NB_CARS))
        self.server.listen(self.NB_CARS)
        # Wait for clients
        for i in range(self.NB_CARS):
            conn, addr = self.server.accept()
            car_id = conn.recv(1024).decode('utf-8')
            car = CarServer(car_id, conn, addr, self.screen, self.SPRITE, self.MAP)
            self.cars.append(car)
            print("Server : New Car connected id:", car_id)

        print("Server : All clients connected !")
        print("Server : Start in 3 seconds !")
        for i in range(3):
            print("Server : {}".format(3 - i))
            pygame.time.wait(1000)

        print("Server : GO !")
        for car in self.cars:
            car.conn.send("go".encode('utf-8'))

        tick = 0
        # Main Loop
        while len(self.cars) > 0:
            # print("\n\nServer : tick {}".format(tick))
            car_thread = []
            for index, car in enumerate(self.cars):
                car_thread.append(threading.Thread(target=self.call_car_step, args=(car,)))
                car_thread[index].start()

            for index, car in enumerate(self.cars):
                car_thread[index].join()
                if not self.cars[index].isConnected:
                    self.cars.pop(index)
                    del car

            self.draw()
            tick += 1

        # Close connections
        print('terminado')
        for car in self.cars:
            car.conn.close()

    def draw(self):
        # Draw Map
        self.screen.blit(self.MAP, (0, 0))

        # Draw Cars
        for car in self.cars:
            car.draw()
            # text = self.font.render("s: " + str(car.current_sector), True, (100, 100, 100))
            # text_rect = text.get_rect()
            # text_rect.center = (car.position[0], car.position[1])
            # self.screen.blit(text, text_rect)
            # if car.sectorReward > self.sectorReward :
            #     self.sectorReward = car.sectorReward


        # Display Info
        self.set_best_reward()
        self.set_fps()
        self.display_info()

        # Exit On Quit Event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    sys.exit(0)

        pygame.display.flip()
        self.clock.tick(60)  # 60 FPS

    def display_info(self):
        # Display Info
        text = self.font.render("Time: " + str(round(time.time() - self.time)) + "s", True, (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (900, 460)
        self.screen.blit(text, text_rect)

        text = self.font.render("Best Reward: " + str(self.best_reward), True, (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (900, 500)
        self.screen.blit(text, text_rect)

        text = self.font.render("FPS: " + str(round(sum(self.fpsBuffer) / len(self.fpsBuffer))), True, (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (900, 540)
        self.screen.blit(text, text_rect)

    def set_fps(self):
        if len(self.fpsBuffer) == 100:
            self.fpsBuffer.pop(0)

        self.fpsBuffer.append(1000 / (round(time.time() * 1000) - self.lastFrameTime))
        self.lastFrameTime = round(time.time() * 1000)


    def set_best_reward(self):
        for car in self.cars:
            actual_reward = car.get_reward()
            if actual_reward > self.best_reward:
                self.best_reward = round(actual_reward, 2)
