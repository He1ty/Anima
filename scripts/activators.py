import pygame
import time
import json
import random
from scripts.particle import Particle
from scripts.display import move_visual, screen_shake

ACTIVATORS_LAYER = "1"

class Activator:
    def __init__(self, game, pos, a_type, size=(16, 16), i=0):#Define basic attributes, that will be useful to track multiple elements from the lever(Position, activated, etc)
        self.game = game
        self.pos = pos
        self.type = a_type
        self.rect = pygame.Rect(pos[0], pos[1], size[0], size[1])
        self.state = 0
        self.last_interaction_time = 0
        self.interaction_cooldown = 0.5
        self.id = i
        self.activated = "progressive_teleporter" not in self.type

    def toggle(self):#Basically change the state of the lever from activated to not activated. Takes into account the countdown(useful for silly people trying to destroy the game)
        current_time = time.time()
        if current_time - self.last_interaction_time >= self.interaction_cooldown:
            self.state = int(not self.state)
            self.last_interaction_time = current_time

            return True
        return False

    def can_interact(self, player_rect, interaction_distance=2):#Check if the player can "touch" the lever.
        can_interact = self.rect.colliderect(player_rect.inflate(interaction_distance, interaction_distance))
        return can_interact and self.activated

    def render(self, surface, offset=(0, 0)):#Just display the marvellous lever design of our dear designer
        surface.blit(self.game.assets[self.type][self.state], (self.pos[0] - offset[0], self.pos[1] - offset[1]))

def load_activators_actions(map_id):
    try:
        with open(f"data/maps/{map_id}.json", "r") as file:
            actions_data = json.load(file)
            return actions_data["tilemap"][ACTIVATORS_LAYER]

    except Exception as e:
        print(f"Error loading activators actions: {e}")
        return {"levers": {}, "buttons": {}}

def update_teleporter(game, t_id):
    if t_id is not None:
        action = game.activators_actions[str(game.level)]["teleporters"][str(t_id)]
        if time.time() - game.last_teleport_time < action["time"] - 0.2:
            pos = (game.player.rect().x + random.random() * game.player.rect().width,
                   game.player.rect().y + 5 + random.random() * game.player.rect().height)
            game.particles.append(
                Particle(game, 'crystal_fragment', pos, velocity=[-0.1, -4], frame=0))
            pass
        else:
            game.last_teleport_time = time.time()
            game.player.pos = action["dest"].copy()
            game.teleporting = False
            game.tp_id = None

def update_activators_actions(game, level):
    for activator in game.activators:
        if activator.can_interact(game.player.rect()):
            activator_pos = f"{activator.pos[0]//game.tile_size};{activator.pos[1]//game.tile_size}"
            action = game.activators_actions[activator_pos]
            if action["infos_type"] == "visual_and_door":
                for door in game.doors:
                    if door.id == action["door_id"]:
                        activator.toggle()
                        move_visual(game, int(action["visual_duration"]), door.pos)
                        activator.activated = False
                        door.open()
                        screen_shake(game, 10)
                        break

            if action["infos_type"] == "improve_tp_progress":
                teleporters = [tp for tp in game.activators if "teleporter" in tp.type]
                for tp in teleporters:
                    if tp.id == action["tp_id"]:
                        activator.toggle()
                        move_visual(game, 1, tp.pos)
                        activator.activated = False
                        tp.state += int(action["amount"])
                        if tp.state == 4:
                            tp.activated = True
                        break

            if action["infos_type"] in ("normal_tp", "progressive_tp"):
                game.last_teleport_time = time.time()
                game.teleporting = True
                game.tp_id = str(activator.id)

def render_activators(game, render_scroll):
    for activator in game.activators:
        activator.render(game.display, offset=render_scroll)

class CameraSetup:
    def __init__(self, game, camera):
        self.game = game
        self.type = camera["infos_type"]
        self.scroll_limits = {"x":[int(x) for x in camera["x_limits"].split(";")],
                              "y":[int(y) for y in camera["y_limits"].split(";")]}
        self.size = [int(s) for s in camera["size"].split(";")]
        self.pos = camera["pos"]
        self.rect = pygame.Rect(self.pos[0], self.pos[1], self.size[0]*self.game.tile_size, self.size[1]*self.game.tile_size)
        if "center" in camera:
            self.center = [int(coordinate) for coordinate in camera["center"].split(";")]
        self.previous_infos = {}

        self.activated = True
        self.player_entry_side = None
        self.initial_state = {"x":[int(x) for x in camera["x_limits"].split(";")],
                              "y":[int(y) for y in camera["y_limits"].split(";")]}

    def get_player_entry_side(self):
        player_rect = self.game.player.rect()


        if self.is_colliding(player_rect) and self.player_entry_side is None:
            #If player is on same camera_setup y level
            if player_rect.bottom <= self.rect.bottom and player_rect.top >= self.rect.top:
                if player_rect.left < self.rect.left <= player_rect.right:
                    self.player_entry_side = "left"
                elif player_rect.right > self.rect.right >= player_rect.left:
                    self.player_entry_side = "right"
            #Else
            elif (player_rect.bottom <= self.rect.bottom and player_rect.top <= self.rect.top) or (player_rect.top >= self.rect.top and player_rect.bottom >= self.rect.bottom) :
                if player_rect.top < self.rect.top <= player_rect.bottom:
                    self.player_entry_side = "top"
                elif player_rect.bottom > self.rect.bottom >= player_rect.top:
                    self.player_entry_side = "bottom"
        elif self.has_passed():
            self.player_entry_side = None


    def is_colliding(self, player_rect, interaction_distance = -1):  # Check if the player can "touch" the lever.
        is_colliding = self.rect.colliderect(player_rect.inflate(interaction_distance, interaction_distance))
        return is_colliding

    def has_passed(self):
        player_rect = self.game.player.rect()
        if self.player_entry_side == "top" and player_rect.top > self.rect.bottom:
            return True
        if self.player_entry_side == "bottom" and player_rect.bottom < self.rect.top:
            return True
        if self.player_entry_side == "right" and player_rect.right < self.rect.left:
            return True
        if self.player_entry_side == "left" and player_rect.left > self.rect.right:
            return True

    def update(self):
        if self.has_passed():
            self.player_entry_side = None
            #First of, save previous "room" camera settings
            self.previous_infos["scroll_limits"] = self.game.scroll_limits.copy()
            if self.game.camera_center is not None:
                self.previous_infos["center"] = self.game.camera_center

            self.game.scroll_limits = self.scroll_limits
            if hasattr(self, "center"):
                self.game.camera_center = self.center
            else:
                self.game.camera_center = None
            self.scroll_limits = self.previous_infos["scroll_limits"]
            if hasattr(self, "center"):
                self.center = self.previous_infos["center"]
            self.activated = False
        else:
            self.activated = True

        self.get_player_entry_side()



