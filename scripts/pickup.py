from multiprocessing.process import active_children

import pygame
import time
import math

from scripts.utils import round_up


class Pickup:

    def __init__(self, game, pos, pickup_type):
        self.pos = pos
        self.initial_pos = pos.copy()
        self.type = pickup_type
        self.game = game
        self.state = "idle"
        self.animation = self.game.assets[self.type+"/"+self.state]
        self.size = self.animation.images[0].get_size()
        self.taking_time = 0
        self.animations_duration = {
            "doubledashball":
                            {"idle": 8,
                             "taking": 1,
                             "taken": 4,
                             "appearing": 3},
            "soul":
                    {"idle": 5,
                 "taking": 3},

                                    }
        self.recharging_per_type = {
                                        "doubledashball": 3,

                                    }
        if self.type in self.recharging_per_type:
            self.recharging_time = self.recharging_per_type[self.type]  # in seconds

    def update(self):

        if self.state == "idle":
            self.animation.img_duration = self.animations_duration[self.type][self.state]
            if self.player_is_touching():

                if self.type == "doubledashball":
                    self.game.player.dash_amt = 2
                    self.animation.frame = 0
                    self.state = "taking"


                if self.game.player.dashtime_cur != 0:
                    if self.type == "soul":
                        self.game.collected_souls += 1

                    self.animation.frame = 0
                    self.state = "taking"

            if self.type == "soul":

                comeback_frequency = 5
                moving_frequency = 5

                player_rect = self.game.player.rect()
                x_dist = player_rect.centerx - self.initial_rect().centerx
                y_dist = player_rect.centery - self.initial_rect().centery
                x_sign = (x_dist / abs(x_dist)) if x_dist != 0 else self.prev_x_sign if hasattr(self,
                                                                                                "prev_x_sign") else 0
                self.prev_x_sign = x_sign
                y_sign = (y_dist / abs(y_dist)) if y_dist != 0 else self.prev_y_sign if hasattr(self,
                                                                                                "prev_y_sign") else 0
                self.prev_y_sign = y_sign

                inner_r = max(16 - math.pow((x_dist ** 2) + (y_dist ** 2), 0.5), 0)


                if x_sign < 0:
                    self.pos[0] = max(self.initial_pos[0], self.pos[0] + x_dist / comeback_frequency)
                else:
                    self.pos[0] = min(self.initial_pos[0], self.pos[0] + x_dist / comeback_frequency)

                if y_sign < 0:
                    self.pos[1] = max(self.initial_pos[1], self.pos[1] + y_dist / comeback_frequency)
                else:
                    self.pos[1] = min(self.initial_pos[1], self.pos[1] + y_dist / comeback_frequency)

                if self.initial_rect().colliderect(self.game.player.rect().inflate(4, 4)):

                    player_relative_angle = -x_sign*(math.atan(y_dist / x_dist) if x_dist else y_sign*math.pi/2)

                    if x_sign < 0:
                        self.pos[0] = min(self.pos[0] - inner_r*math.cos(player_relative_angle + math.pi)/moving_frequency,
                                          self.initial_pos[0] - inner_r*math.cos(player_relative_angle + math.pi))
                    else:
                        self.pos[0] = max(self.pos[0] + inner_r * math.cos(player_relative_angle + math.pi) / moving_frequency,
                            self.initial_pos[0] + inner_r * math.cos(player_relative_angle + math.pi))

                    if y_sign < 0:
                        self.pos[1] = min(self.pos[1] - inner_r*math.sin(player_relative_angle + math.pi)/moving_frequency,
                                          self.initial_pos[1] - inner_r*math.sin(player_relative_angle + math.pi))
                    else:
                        self.pos[1] = max(self.pos[1] - inner_r*math.sin(player_relative_angle + math.pi)/moving_frequency,
                                          self.initial_pos[1] - inner_r*math.sin(player_relative_angle + math.pi))



        elif self.state == "taking":
            self.animation.img_duration = self.animations_duration[self.type][self.state]
            if self.animation.done:
                self.animation.done = False
                self.animation.frame = 0
                self.state = "taken"
                self.taking_time = time.time()

        elif self.state == "taken":
            if "taken" in self.animations_duration[self.type]:
                self.animation.img_duration = self.animations_duration[self.type][self.state]
                if time.time() - self.taking_time >= self.recharging_time:
                    self.state = "appearing"
            else:
                self.game.pickups.remove(self)

        elif self.state == "appearing":
            self.animation.img_duration = self.animations_duration[self.type][self.state]
            if self.animation.done:
                self.animation.done = False
                self.animation.frame = 0
                self.state = "idle"

        self.animation.update()

    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

    def initial_rect(self):
        return pygame.Rect(self.initial_pos[0], self.initial_pos[1], self.size[0], self.size[1])

    def player_is_touching(self):
        return self.rect().colliderect(self.game.player.rect().inflate(0, 0))

    def render(self, surf, offset=(0, 0)): #display the animation
        self.animation = self.game.assets[self.type + "/" + self.state]
        surf.blit(self.animation.img(),
                  (self.pos[0] - offset[0], self.pos[1] - offset[1]))

def pickups_render_and_update(game, offset):
        for pickup in game.pickups:
            if game.tilemap.pos_visible(game.display, pickup.pos, offset):
                pickup.update()
                pickup.render(game.display, offset)
