import pygame
import sys


class Race:

    WIDTH = 1920
    HEIGHT = 1080

    CAR_SIZE_X = 60
    CAR_SIZE_Y = 60

    def __init__(self):
        # Initialize PyGame And The Display
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.FULLSCREEN)

        # Init pygame assets
        self.clock = pygame.time.Clock()
        self.SPRITE = pygame.image.load('assets/car.png').convert()  # Convert Speeds Up A Lot
        self.SPRITE = pygame.transform.scale(self.SPRITE, (self.CAR_SIZE_X, self.CAR_SIZE_Y))
        self.MAP = pygame.image.load('assets/map2.png').convert()  # Convert Speeds Up A Lot
        self.font = pygame.font.SysFont("Arial", 30)

        # Create an empty list of cars
        self.cars = []
        self.gen = 1
        self.best_reward = 0

        # Draw Map
        self.draw()

    def draw(self):
        # Draw Map
        self.screen.blit(self.MAP, (0, 0))

        # Draw Cars
        for car in self.cars:
            car.draw()

        # Display Info
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
        text = self.font.render("Generation: " + str(self.gen), True, (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (900, 460)
        self.screen.blit(text, text_rect)

        text = self.font.render("Best Reward: " + str(self.best_reward), True, (0, 0, 0))
        text_rect = text.get_rect()
        text_rect.center = (900, 500)
        self.screen.blit(text, text_rect)

    # TODO: implement
    def set_best_reward(self):
        actual_reward = self.cars[0].get_reward()
        if actual_reward > self.best_reward:
            self.best_reward = actual_reward