import pygame
import time
import json
import random
from scripts.particle import Particle

ACTIVATORS_LAYER = "2"

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
                        game.camera.move_visual(int(action["visual_duration"]), door.pos)
                        activator.activated = False
                        door.open()
                        game.camera.screen_shake(10)
                        break

            if action["infos_type"] == "improve_tp_progress":
                teleporters = [tp for tp in game.activators if "teleporter" in tp.type]
                for tp in teleporters:
                    if tp.id == action["tp_id"]:
                        activator.toggle()
                        game.move_visual(1, tp.pos)
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





