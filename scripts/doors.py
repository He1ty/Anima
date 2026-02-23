import time

import pygame
import random

from scripts.particle import Particle
from scripts.spark import Spark
from pygame.sprite import collide_rect
from scripts.sound import *


class Door:
    def __init__(self, size, pos, d_type, d_id, flip, opening_speed, game):
        self.size = size
        self.pos = pos
        self.type = d_type
        self.opened = False
        self.action = "closed"
        self.game = game
        self.animation = self.game.assets[self.type + '/' + self.action].copy()
        self.flip = flip
        self.opening_speed = opening_speed
        self.last_time_interacted = 0
        self.id = d_id

        self.breaking_sound = pygame.mixer.Sound('assets/sounds/door_breaking.wav')

    def update(self):#for every frame the state of the door is updated(state/ open/ trnasitions)
        self.animation.update()

        if self.type == 'breakable_stalactite' and self.game.attacking and self.rect().colliderect(
                self.game.player.rect().inflate(32, 32)):
            pos = (self.rect().x + random.random() * self.rect().width,
                   self.rect().y + 5 + random.random() * self.rect().height)
            self.game.particles.append(
                Particle(self.game, 'crystal_fragment', pos, velocity=[-0.1, 1.2], frame=0))
            self.open()

        if self.action == "opening" and not self.opened:
            if time.time() - self.last_time_interacted >= self.opening_speed:
                self.set_action("opened")
                self.opened = True

        if self.action == "closing":
            self.opened = False
            if time.time() - self.last_time_interacted >= self.opening_speed:
                self.set_action("closed")

        if not self.opened and self.action == "opened":
            self.set_action("closed")
        elif self.opened and self.action != "opened":
            self.set_action("opened")

    def open(self):#mainly useful for the state of door and sound play
        if not self.opened:
            self.set_action("opening")
            self.last_time_interacted = time.time()

            if self.type == 'breakable_stalactite':
                self.breaking_sound.play()

    def close(self):#not useful for the moment but might in the future
        if self.opened:
            self.set_action("closing")
            self.last_time_interacted = time.time()

    def rect(self):#is very useful because when the door is broken the player has to be able to go through the updated frame
        if self.action == "opened":
            return pygame.Rect(self.pos[0], self.pos[1], 0, 0)
        else:
            return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

    def set_action(self, action):#load the animation for door breaking
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()

    def render(self, surf, offset=(0, 0)):#display the animation
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False),
                  (self.pos[0] - offset[0], self.pos[1] - offset[1]))

def doors_render_and_update(game, render_scroll):
    # Doors (Colliders updated for physics)
    ds = []
    for door in game.doors:
        door.update()
        door.render(game.display, offset=render_scroll)
        if not door.opened:
            ds.append(door.rect())
            if game.player.show_hitbox:
                k = door.rect().copy()
                k.x -= render_scroll[0]
                k.y -= render_scroll[1]
                pygame.draw.rect(game.display, (255, 0, 0), k, 1)
    game.doors_rects = ds