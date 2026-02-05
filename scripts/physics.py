#Heavily upgraded basic godot physics code that I then converted to Python --Aymeric
import time
from typing import reveal_type

import pygame as pg

import sys

import pygame
from time import sleep

import random
import math

from scripts.particle import Particle
from scripts.tilemap import Tilemap
from scripts.sound import *
from scripts.entities import deal_knockback, update_throwable_objects_action

class PhysicsPlayer:
    def __init__(self, game, tilemap, pos, size):

        # Hitbox util vars
        self.game = game
        self.pos = list(pos)  # [x, y]
        self.size = size
        self.velocity = [0, 0]  # [vel_x, vel_y]
        self.acceleration = [0.0, 0.0]
        self.show_hitbox = False

        # Constants for movement
        self.GRAVITY_DIRECTION = 1
        self.SPEED = 2.5
        self.DASH_SPEED = 6
        self.JUMP_VELOCITY = -6.5
        self.DASHTIME = 12
        self.JUMPTIME = 10
        self.DASH_COOLDOWN = 18
        self.FIRST_JUMP_WALLJUMP_COOLDOWN = 0
        self.WALLJUMP_COOLDOWN = 30

        self.COLLISION_DODGED_PIXELS = 4 # Number of pixels collision can dodge (ledge snapping/corner correction)

        self.dash_max_amt = 1

        # Vars related to constants
        self.dashtime_cur = 0  # Used to determine whether we are dashing or not. Also serves as a timer.

        #self.dash_cooldown = 0

        self.dash_amt = self.dash_max_amt
        self.tech_momentum_mult = 0

        # Direction vars
        self.last_direction = 1
        self.dash_direction = [0, 0]  # [dash_x, dash_y]

        # Keyboard and movement exceptions utils
        self.dict_kb = {"key_right": 0, "key_left": 0, "key_up": 0, "key_down": 0, "key_jump": 0, "key_dash": 0,
                        "key_noclip": 0}  # Used for reference
        self.anti_dash_buffer = False
        self.stop_dash_momentum = {"y": False, "x": False}
        self.holding_jump = False
        self.can_walljump = {"sliding": False, "wall": -1, "buffer": False, "timer": 0, "blocks_around": False,
                             "cooldown": 0, "allowed": True, "available": False, "count":0}
        self.max_walljumps = 3
        self.force_movement_direction = {"r":[False,0],"l":[False,0]}
        self.force_movement = ""
        
        
        self.prevent_walking = False
        # available used to know if you can walljump, wall to know where the wall is located,
        # buffer to deal with logic conflicts in collision_check, timer for walljump coyote time
        self.dash_cooldown_cur = 0
        self.noclip = False
        self.noclip_buffer = False

        self.is_stunned = False
        self.last_stun_time = 0
        self.stunned_by = None
        self.knockback_dir = [0, 0]
        self.knockback_strenght = 4
        self.knockback_duration = 0.5

        self.allowNoClip = True  # MANUALLY TURN IT ON HERE TO USE NOCLIP

        # Tilemap (stage)
        self.tilemap = tilemap
        self.ghost_images = []

        self.jumping = False

        self.facing = ""
        self.action = "idle"
        self.animation = self.game.assets['player/' + "idle"].copy()
        self.collision = {'left': False, 'right': False, 'bottom': False, 'top': False}
        self.get_block_on = {'left': False, 'right': False, 'top':False}
        self.air_time = 0
        self.disablePlayerInput = False

        # Système de son
        self.init_sound_system()

        # Variables pour gérer les états des sons
        self.was_on_floor = True  # Pour gérer le son d'atterrissage
        self.running_sound_playing = False
        self.run_sound_timer = 0
        self.run_sound_interval = 15  # Intervalle entre les répétitions du son de course
        self.last_action = "idle"  # Pour détecter les changements d'action

        self.rotation_angle = 0

    def init_sound_system(self):
        """Initialise le système de son avec tous les fichiers nécessaires"""
        # Dictionnaire qui stockera tous les sons
        base_path = "assets/sounds/player/"
        self.sounds = {
            'jump': base_path + "jump.wav",
            'dash': base_path + "dash.wav",
            'wall_jump': base_path + "wall_jump.wav",
            'land': base_path + "land.wav",
            'run': base_path + "run.wav",
            'walk': None,
            'stun': None
        }
        load_sounds(self, self.sounds)

    def play_sound(self, sound_key, force=False):
        """
        Joue un son spécifique

        Args:
            sound_key: La clé du son à jouer
            force: Si True, joue le son même s'il est déjà en cours
        """
        if sound_key in self.sounds and self.sounds[sound_key]:
            if force:
                self.sounds[sound_key].stop()

            # Vérifier si le son est déjà en cours de lecture
            if not pygame.mixer.Channel(0).get_busy() or force:
                self.sounds[sound_key].play(loops=0, maxtime=0, fade_ms=0)

    def update_sounds(self):
        """Met à jour et gère les sons en fonction de l'état du joueur"""

        # Son d'atterrissage
        if self.is_on_floor() and not self.was_on_floor:
            self.play_sound('land', True)

        # Mise à jour de l'état du sol pour le prochain frame
        self.was_on_floor = self.is_on_floor()

        # Son de course/marche
        if "run" in self.action:
            self.run_sound_timer += 1

            # Détermine si le joueur court ou marche
            sound_key = 'run' if abs(self.velocity[0]) > 1.5 else 'walk'

            # Joue le son à intervalles réguliers pour créer un effet de pas
            if self.run_sound_timer >= self.run_sound_interval:
                self.play_sound('run', True)
                self.run_sound_timer = 0
        else:
            self.run_sound_timer = 0

        # Détecte les changements d'action pour les événements ponctuels
        if self.action != self.last_action:
            if self.action in ["stun"]:
                self.play_sound('stun')

            self.last_action = self.action

    def physics_process(self, tilemap, dict_kb):
        """Input : tilemap (map), dict_kb (dict)
        output : sends new coords for the PC to move to in accordance with player input and stage data (tilemap)"""
        self.dict_kb = dict_kb
        self.force_player_movement_direction()
        self.force_player_movement()


        if self.disablePlayerInput:
            self.dict_kb = {"key_right": 0, "key_left": 0, "key_up": 0, "key_down": 0, "key_jump": 0, "key_dash": 0,
                            "key_noclip": 0}
            # Consider all keys as not pressed

        if self.is_stunned:
            # Calculate time since stun started
            stun_elapsed = time.time() - self.last_stun_time
            stun_duration = 0.2

            if stun_elapsed < stun_duration:
                if self.stunned_by:
                    self.velocity = list(deal_knockback(self.stunned_by, self, self.knockback_strenght, self.knockback_duration))

                # Jouer le son de stun
                if stun_elapsed < 0.05:  # Pour ne jouer le son qu'une fois au début du stun
                    self.play_sound('stun')

                # When stunned, only apply knockback and gravity
                self.gravity()
                self.apply_momentum()
                self.apply_animations()
                self.animation.update()
                return  # Skip the rest of the normal update logic
            else:
                self.stunned_by = None
                self.is_stunned = False
                self.knockback_dir = [0, 0]

        if self.is_on_floor():
            self.jumping = False

        if not self.is_on_floor() and self.can_walljump["sliding"] == False:
            # Spin speed (Adjust "8" to make it faster/slower)
            rotation_speed = 6.5

            # Spin based on direction (Clockwise if facing right, CCW if left)
            # We use last_direction so you keep spinning even if you stop pressing keys in mid-air
            if self.last_direction == 1:
                self.rotation_angle -= rotation_speed  # Negative is clockwise in Pygame
            else:
                self.rotation_angle += rotation_speed

            # Keep angle within 0-360 for cleanliness (optional)
            self.rotation_angle %= 360
        else:
            # Snap back to 0 when on the ground
            # You can also use a 'lerp' here if you want a smooth landing animation
            self.rotation_angle = 0

        if not self.noclip:
            if self.dict_kb["key_noclip"] == 1 and self.allowNoClip:
                self.noclip = True

            self.air_time += 1
            direction = self.get_direction("x")
            if direction != 0:
                self.last_direction = direction

            if not self.dashtime_cur > 0 and not self.prevent_walking:
                self.walk(direction)

            self.gravity()
            self.jump()
            self.dash()
            self.dash_momentum()

            self.apply_momentum()

            self.apply_animations()
            self.apply_particle()
            self.animation.update()

            # Mise à jour des sons
            self.update_sounds()

        else:
            self.pos[0] += self.SPEED * self.get_direction("x")
            self.pos[1] += self.SPEED * -self.get_direction("y")


            if self.dict_kb["key_noclip"] == 1:
                self.noclip = False


    def force_player_movement_direction(self):
        """forces some keys to be pressed"""
        if self.force_movement_direction["r"][0] or self.force_movement_direction["l"][0]:
            if self.force_movement_direction["l"][0]:
                self.walk(-1,1.5)
            else:
                self.walk(1,1.5)
            if (-1 < self.force_movement_direction["l"][1] < 1 and self.force_movement_direction["l"][0]) or (self.force_movement_direction["r"][0] and -1 < self.force_movement_direction["r"][1] < 1) or self.is_on_floor():
                self.force_movement_direction = {"r":[False,0],"l":[False,0]}
            elif self.force_movement_direction["l"][1] != -1 or self.force_movement_direction["r"][1] != -1:
                self.force_movement_direction["l"][1] -= 1
                self.force_movement_direction["r"][1] -= 1

    def force_player_movement(self):
        if self.force_movement != "":
            self.dict_kb["key_right"] = self.force_movement == "r"
            self.dict_kb["key_left"] = self.force_movement == "l"

    def walk(self, direction, mult=1):
        """Changes x velocity with gradual acceleration and deceleration."""
        target_speed = direction * self.SPEED * mult

        # Acceleration factor: how fast we reach target speed
        # Lower = more slippery/weighty, Higher = snappier
        accel = 0.15 if self.is_on_floor() else 0.1

        # Deceleration in case speed in higher than self.SPEED (dash for example)
        if abs(self.velocity[0]) > self.SPEED:
            accel = 0.2


        if direction != 0:
            # Gradually move current velocity toward target speed
            pass
            self.velocity[0] += (target_speed - self.velocity[0]) * accel
        else:
            # This handles the 'active' release of keys (handled in apply_momentum usually,
            # but kept here for logic consistency)
            pass

    def set_action(self, action):
        if action != self.action :
            self.action = action
            #self.animation = self.game.assets['player/' + self.action].copy()

    def apply_animations(self):
        """
        Handles animation state changes based on player movement state.
        Follows clear priority rules for animations.
        """
        # Reset animation flags
        animation_applied = False

        # Check if we just finished dashing this frame
        just_finished_dash = self.dashtime_cur == 0 and self.action in ("dash/right", "dash/left")

        # HIGHEST PRIORITY: Dash animations
        if self.dashtime_cur > 0:
            if self.dash_direction[0] == 1:
                self.set_action("dash/right")
                animation_applied = True
            elif self.dash_direction[0] == -1:
                self.set_action("dash/left")
                animation_applied = True
            elif self.dash_direction[0] == 0:  # Vertical dash
                self.set_action("dash/top")
                animation_applied = True

        # SECOND PRIORITY: Attack animation (moved up in priority)
        if not animation_applied and self.game.attacking and not self.animation.done:
            if self.last_direction == 1:
                self.set_action("attack/right")
                animation_applied = True
            elif self.last_direction == -1:
                self.set_action("attack/left")
                animation_applied = True

        # THIRD PRIORITY: Wall sliding
        if not animation_applied and (self.GRAVITY_DIRECTION == 1 and self.velocity[1] > 0 or self.GRAVITY_DIRECTION == -1 and self.velocity[1] < 0) and not self.is_on_floor() and self.can_walljump[
            "blocks_around"]:
            if self.collision["right"]:
                self.set_action("wall_slide/right")
                self.facing = "left"
                animation_applied = True
            elif self.collision["left"]:
                self.set_action("wall_slide/left")
                self.facing = "right"
                animation_applied = True

        if not animation_applied and (self.collision["right"] or self.collision["left"]):
            if self.is_on_floor():
                self.set_action("idle")
                animation_applied = True  # Add this line to prevent overriding
            elif self.action in ("wall_slide/right", "wall_slide/left"):
                if self.get_direction("x") == 1 or self.last_direction >= 0:
                    self.set_action('falling/right')
                else:
                    self.set_action('falling/left')
                animation_applied = True

        # FOURTH PRIORITY: Jumping/Falling
        if not animation_applied and not self.is_on_floor():
            # Initial jump
            if self.velocity[1] < 0 and self.air_time < 20:
                if self.get_direction("x") == 0:
                    self.set_action("jump/top")

                elif self.get_direction("x") == 1 and self.action != "jump/top":
                    self.set_action("jump/right")
                elif self.get_direction("x") == -1 and self.action != "jump/top":
                    self.set_action("jump/left")
                animation_applied = True
            # Falling
            else:
                if (self.get_direction("x") == 1 or (self.action == 'falling/right' and self.get_direction("x") != -1) or self.force_movement_direction["r"][0]) and not self.force_movement_direction["l"][0]:
                    self.set_action('falling/right')
                elif self.get_direction("x") == -1 or (self.action == 'falling/left' and self.get_direction("x") != 1) or self.force_movement_direction["l"][0]:
                    self.set_action('falling/left')
                elif self.get_direction("x") == 0:
                    self.set_action('falling/vertical')
                animation_applied = True

        # FIFTH PRIORITY: Running
        # Check if player is moving OR just finished a dash and is trying to move
        if not animation_applied and (
                (self.is_on_floor() and abs(self.velocity[0]) > 0.1) or
                (just_finished_dash and self.get_direction("x") != 0)
        ):
            if self.get_direction("x") > 0 or (just_finished_dash and self.dash_direction[0] > 0):
                self.set_action("run/right")
            else:
                self.set_action("run/left")
            animation_applied = True

        # LOWEST PRIORITY: Idle
        if not animation_applied:
            self.set_action("idle")

    def apply_particle(self):
        '''if self.velocity[1] < 0 and self.air_time < 20:
            self.game.particles.append(Particle(self.game, 'leaf', self.pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))'''

    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

    def is_on_floor(self):
        """Uses tilemap to heck if the player is standing on a surface based on gravity direction. used for gravity, jump, etc."""
        # Offset depends on gravity: +1 if normal (down), -1 if inverted (up)
        y_offset = self.GRAVITY_DIRECTION

        for rect in self.tilemap.physics_rects_under(self.pos, self.size, self.GRAVITY_DIRECTION) + self.game.doors_rects:
            entity_rect = pygame.Rect(self.pos[0], self.pos[1] + y_offset, self.size[0], self.size[1])
            if entity_rect.colliderect(rect):
                if self.GRAVITY_DIRECTION == 1:
                    return self.rect().bottom == rect.top and self.velocity[1] >= 0
                else:
                    return self.rect().top == rect.bottom and self.velocity[1] <= 0
        return False

    def gravity(self):
        """Handles gravity. Gives downwards momentum (capped at 5) if in the air, negates momentum if on the ground, gives back a dash if the
        player is missing some. Stops movement if no input is given."""
        if not self.is_on_floor() and not self.dashtime_cur > 0:
            # Reset vertical velocity if we just started sliding to prevent 'falling up' too fast
            if self.can_walljump["sliding"]:
                if self.acceleration[1] == 0.42:
                    self.velocity[1] = max(0, self.velocity[1] - 1.5)
                if self.can_walljump["count"] < self.max_walljumps - 1:
                    if self.velocity[1] == 0:
                        self.acceleration[1] = 0.05 * self.GRAVITY_DIRECTION
                else:
                    self.acceleration[1] = 0.008 * self.GRAVITY_DIRECTION # gravity acceleration while sliding (on wall)
            else:
                self.acceleration[1] = 0.42 * self.GRAVITY_DIRECTION # Normal gravity acceleration

            # Cap terminal velocity based on direction
            if self.GRAVITY_DIRECTION == 1:
                self.velocity[1] = min(7.0, self.velocity[1] + self.acceleration[1])
            else:
                self.velocity[1] = max(-7.0, self.velocity[1] + self.acceleration[1])

        elif self.is_on_floor():
            self.pos[1] = int(self.pos[1]) # Take only the integer part in order to avoid some pixels overlap
            # (for example when we jump, if player stops at 80.399999, we make sure that player coordinate is at 80 before setting vertical velocity to 0)
            if (self.GRAVITY_DIRECTION == 1 and self.velocity[1] > 0) or \
           (self.GRAVITY_DIRECTION == -1 and self.velocity[1] < 0):
                self.velocity[1] = 0


            #Resets dash amount and walljump count
            if self.dashtime_cur < 5 and self.dash_amt == 0:
                self.dash_amt = self.dash_max_amt

            self.can_walljump["count"] = 0

            # Stop unintended horizontal movement if no input is given
            if self.get_direction("x") == 0 and not self.is_stunned and self.dashtime_cur == 0:
                self.velocity[0] = 0

    def disallow_movement(self, bool):
        """allows to disable or re-enable player movement. Bool as parameter, True to disable, False to enable movement."""
        self.disablePlayerInput = bool

    def jump(self):
        """Handles player jump and super/hyperdash tech"""

        if self.dict_kb["key_jump"] == 0:
            self.holding_jump = False


        if self.dict_kb["key_jump"] == 1:
            # Jumping
            if self.is_on_floor() and not self.holding_jump:  # Jump on the ground
                self.jump_logic_helper()

                # Jouer le son de saut
                self.jumping = True
                self.play_sound('jump', True)

                # Tech
                if self.dashtime_cur != 0:
                    self.dashtime_cur = 0
                    self.tech_momentum_mult = pow(abs(self.dash_direction[0]) + abs(self.dash_direction[1]), 0.4)
                    self.velocity[0] = self.get_direction("x") * self.DASH_SPEED * self.tech_momentum_mult * 2
                    self.velocity[1] = self.velocity[1] / self.tech_momentum_mult if self.tech_momentum_mult != 0 else 0

            # Walljump
            elif not self.holding_jump and \
                    self.can_walljump["blocks_around"] and self.can_walljump["cooldown"] < 1 and self.can_walljump[
                "allowed"]:
                if self.can_walljump["sliding"]:
                    self.jump_logic_helper()

                    # Jouer le son de wall jump
                    self.play_sound('wall_jump', True)

                    if self.can_walljump["wall"] == self.get_direction("x") :  # Jumping into the wall direction
                        self.velocity[0] = -self.can_walljump["wall"] * self.SPEED
                        self.velocity[1] *= 1
                    else:  # Jumping away from the wall
                        self.wall_jump_logic_helper()

                    self.can_walljump["count"] += 1
                    self.can_walljump["sliding"] = False

                else:
                    self.jump_logic_helper()

                    # Jouer le son de wall jump
                    self.play_sound('wall_jump', True)
                    self.can_walljump["cooldown"] = self.WALLJUMP_COOLDOWN
                    self.wall_jump_logic_helper()

    def jump_logic_helper(self):
        """Avoid code redundancy"""
        self.velocity[1] = self.JUMP_VELOCITY * self.GRAVITY_DIRECTION
        self.holding_jump = True

    def wall_jump_logic_helper(self):
        self.velocity[0] = 0
        if self.can_walljump["wall"] == 1:
            self.force_movement_direction["l"] = [True, 22]
            self.force_movement_direction["r"] = [False, 0]
        else:
            self.force_movement_direction["r"] = [True, 22]
            self.force_movement_direction["l"] = [False, 0]

    def dash(self):
        """Handles player dash."""
        self.dash_cooldown_cur = max(self.dash_cooldown_cur - 1, 0)
        if not self.anti_dash_buffer:
            if self.dict_kb["key_dash"] == 1 and self.dash_cooldown_cur == 0: #and self.dash_direction != [0, -1]:
                self.dash_direction = [self.get_direction("x"), self.get_direction("y")]
                if self.game.player_grabbing:
                    update_throwable_objects_action(self.game)
                if self.dash_amt > 0:
                    if self.dash_direction == [0, 0]:
                        self.dash_direction[0] = self.last_direction
                    self.dashtime_cur = self.DASHTIME
                    self.stop_dash_momentum["y"], self.stop_dash_momentum["x"] = False, False
                    self.dash_amt -= 1

                    # Jouer le son de dash
                    self.play_sound('dash', force=True)

                self.anti_dash_buffer = True
                self.dash_cooldown_cur = self.DASH_COOLDOWN

            if (self.dashtime_cur != 0 and self.get_direction("x") == -self.dash_direction[0] and self.get_direction("x") != 0 or
                    (self.get_direction("y") == -self.dash_direction[1] and self.get_direction("y") != 0)):
                self.dashtime_cur = 0

        else:
            if self.dict_kb["key_dash"] == 0:
                self.anti_dash_buffer = False

    def dash_momentum(self):
        """Applies momentum from dash. Manage momentum when dash ends."""
        if self.dashtime_cur > 0:
            self.dash_ghost_trail()
            self.dashtime_cur -= 1
            move_x = self.dash_direction[0]
            move_y = -self.dash_direction[1]

            # Calculate the magnitude (length) of the direction
            magnitude = math.sqrt(move_x ** 2 + move_y ** 2)

            if magnitude > 0:
                # Divide by magnitude to "normalize" the vector to a length of 1
                self.velocity[0] = (move_x / magnitude) * self.DASH_SPEED
                self.velocity[1] = (move_y / magnitude) * self.DASH_SPEED
            if self.dashtime_cur == 0:
                self.velocity[1] = abs(self.velocity[1])/self.velocity[1] if self.velocity[1] != 0 else 0
                if self.collision["left"] or self.collision["right"]:
                    self.velocity[0] = 0

        self.update_ghost_trail()

    def collision_check(self, axe):
        """Checks for collision using tilemap"""
        entity_rect = self.rect()

        tilemap = self.tilemap
        b_r = set()
        b_l = set()
        b_t = set()

        # Handle Vertical Collision First
        if axe == "y":
            backup_velo = self.velocity[1]

            self.can_walljump["buffer"] = False
            self.can_walljump["timer"] = max(0, self.can_walljump["timer"] - 1)

            if self.can_walljump["timer"] == 0:
                self.can_walljump["sliding"] = False

            for rect in tilemap.physics_rects_under(self.pos, self.size, self.GRAVITY_DIRECTION) + self.game.doors_rects:
                if entity_rect.colliderect(rect):
                    if (self.GRAVITY_DIRECTION == 1 and self.velocity[1] > 0) or (self.GRAVITY_DIRECTION == -1 and self.velocity[1] < 0):
                        # --- GROUND CORNER CORRECTION ---
                        # If falling and clipping a corner, try to nudge onto the ledge
                        nudged = False
                        if rect not in self.game.doors_rects:
                            for i in range(1, self.COLLISION_DODGED_PIXELS + 1):
                                # Check Right nudge
                                if not any(
                                        pygame.Rect(self.pos[0] + i, self.pos[1], self.size[0], self.size[1]).colliderect(r)
                                        for r in tilemap.physics_rects_under([self.pos[0] + i, self.pos[1]], self.size, self.GRAVITY_DIRECTION)):
                                    self.pos[0] += i
                                    nudged = True
                                    break
                                # Check Left nudge
                                if not any(
                                        pygame.Rect(self.pos[0] - i, self.pos[1], self.size[0], self.size[1]).colliderect(r)
                                        for r in tilemap.physics_rects_under([self.pos[0] - i, self.pos[1]], self.size, self.GRAVITY_DIRECTION)):
                                    self.pos[0] -= i
                                    nudged = True
                                    break

                        if not nudged:
                            if self.GRAVITY_DIRECTION == 1:
                                self.pos[1] = rect.top - entity_rect.height
                                self.collision['bottom'] = True
                            elif self.GRAVITY_DIRECTION == -1:
                                self.pos[1] = rect.bottom
                                self.collision['top'] = True
                            #self.velocity[1] = 0 #Not necessary since we already sets vertical velocity to 0 inside gravity function
                            self.can_walljump["buffer"] = True
                            self.can_walljump["sliding"] = False

            for rect in tilemap.physics_rects_around(self.pos, self.size) + self.game.doors_rects:
                if entity_rect.colliderect(rect):
                    if (self.GRAVITY_DIRECTION == 1 and self.velocity[1] < 0) or (self.GRAVITY_DIRECTION == -1 and self.velocity[1] > 0):
                        # If jumping and hitting a head-block corner, nudge to the side
                        nudged = False
                        if rect not in self.game.doors_rects:
                            for i in range(1, self.COLLISION_DODGED_PIXELS + 1):
                                # Try nudging Right
                                if not any(
                                        pygame.Rect(self.pos[0] + i, self.pos[1], self.size[0], self.size[1]).colliderect(r)
                                        for r in tilemap.physics_rects_around([self.pos[0] + i, self.pos[1]], self.size)):
                                    self.pos[0] += i
                                    nudged = True
                                    break
                                # Try nudging Left
                                if not any(
                                        pygame.Rect(self.pos[0] - i, self.pos[1], self.size[0], self.size[1]).colliderect(r)
                                        for r in tilemap.physics_rects_around([self.pos[0] - i, self.pos[1]], self.size)):
                                    self.pos[0] -= i
                                    nudged = True
                                    break

                        if not nudged:
                            if self.GRAVITY_DIRECTION == 1:
                                self.pos[1] = rect.bottom
                                self.collision['top'] = True
                            elif self.GRAVITY_DIRECTION == -1:
                                self.pos[1] = rect.top - entity_rect.height
                                self.collision['bottom'] = True
                            self.velocity[1] = 0
                            self.can_walljump["buffer"] = True
                            self.can_walljump["sliding"] = False

                    self.stop_dash_momentum["y"] = True

                if ((self.GRAVITY_DIRECTION == 1 and entity_rect.y - self.size[1] < rect.y < entity_rect.y and entity_rect.x + self.size[0] > rect.x and entity_rect.x < rect.x + rect.width) or
                        (self.GRAVITY_DIRECTION == -1 and entity_rect.y < rect.y < entity_rect.y + self.size[1] and entity_rect.x + self.size[0] > rect.x and entity_rect.x < rect.x + rect.width)):
                    b_t.add(True)

            self.get_block_on["top"] = bool(b_t)
            entity_rect.y -= backup_velo

        if axe == "x":
            if self.can_walljump["cooldown"]:
                self.can_walljump["cooldown"] = max(self.can_walljump["cooldown"]-1,0)
            for rect in tilemap.physics_rects_around(self.pos, self.size) + self.game.doors_rects:
                if entity_rect.colliderect(rect):
                    # --- HORIZONTAL CORNER CORRECTION ---
                    # If hitting a wall, try to nudge the player Up or Down to bypass the corner
                    nudged = False
                    if rect not in self.game.doors_rects:
                        for i in range(1, self.COLLISION_DODGED_PIXELS + 1):
                            # 1. Try nudging UP (Useful for stepping onto a ledge automatically)
                            if not any(
                                    pygame.Rect(self.pos[0], self.pos[1] - i, self.size[0], self.size[1]).colliderect(r) for
                                    r in tilemap.physics_rects_around([self.pos[0], self.pos[1] - i], self.size)):
                                self.pos[1] = self.pos[1] - i
                                nudged = True
                                break
                            # 2. Try nudging DOWN (Useful for clearing a ceiling corner)
                            if not any(
                                    pygame.Rect(self.pos[0], self.pos[1] + i, self.size[0], self.size[1]).colliderect(r) for
                                    r in tilemap.physics_rects_around([self.pos[0], self.pos[1] + i], self.size)):
                                self.pos[1] = self.pos[1] + i
                                nudged = True
                                break

                    if not nudged:
                        if self.velocity[0] > 0:
                            entity_rect.right = rect.left
                            self.collision['right'] = True
                            #self.anti_dash_buffer = True
                            #self.dash_cooldown = 5

                        if self.velocity[0] < 0:
                            entity_rect.left = rect.right
                            self.collision['left'] = True
                            #self.anti_dash_buffer = True
                            #self.dash_cooldown = 5
                        self.pos[0] = entity_rect.x
                        self.stop_dash_momentum["x"] = True
                if entity_rect.x - self.size[0] < rect.x < entity_rect.x:
                    b_l.add(True)
                if entity_rect.x + self.size[0] > rect.x > entity_rect.x:
                    b_r.add(True)

            self.get_block_on["left"] = bool(b_l)
            self.get_block_on["right"] = bool(b_r)

    def collision_check_walljump_helper(self,axis):
        """Avoids redundancy"""
        #The condition checks if there is no buffer, if player is falling, if they are not on floor, if there are blocks around, if key corresponding to the axis is pressed and if count < max_walljumps
        if (not self.can_walljump["buffer"] and (self.GRAVITY_DIRECTION == 1 and self.velocity[1] > 0 or self.GRAVITY_DIRECTION == -1 and self.velocity[1] < 0) and
                not self.is_on_floor() and self.can_walljump["blocks_around"] and (self.dict_kb["key_left"] if axis == -1 else self.dict_kb["key_right"]) and self.can_walljump["count"] < self.max_walljumps):
            if not self.can_walljump["sliding"]:
                self.can_walljump["cooldown"] = self.FIRST_JUMP_WALLJUMP_COOLDOWN
            self.can_walljump["sliding"] = True
            self.can_walljump["wall"] = axis
            self.can_walljump["timer"] = 2
        elif self.can_walljump["wall"] != axis:
            self.can_walljump["wall"] = axis

    def apply_momentum(self):
        """Applies velocity to the coords of the object. Slows down movement depending on environment"""
        self.can_walljump["blocks_around"] = (self.tilemap.solid_check((self.rect().centerx + 8.5*self.last_direction, self.rect().y + 2), transparent_check=False) or
                                              self.tilemap.solid_check((self.rect().centerx + 8.5*self.last_direction, self.rect().bottom - 2), transparent_check=False))

        if int(self.velocity[0]) > 0 or not self.get_block_on["left"]:
            self.collision["left"] = False
        if int(self.velocity[0]) < 0 or not self.get_block_on["right"]:
            self.collision["right"] = False
        if self.velocity[1] > 0:
            self.collision["bottom"] = False
        if self.velocity[1] < 0 or not self.get_block_on["top"]:
            self.collision["top"] = False

        self.pos[0] += self.velocity[0]
        self.collision_check("x")

        self.pos[1] += self.velocity[1]
        self.collision_check("y")

        if self.collision["right"]:
            self.collision_check_walljump_helper(1)
        if self.collision["left"]:
            self.collision_check_walljump_helper(-1)

        if not( not self.can_walljump["buffer"] and (self.GRAVITY_DIRECTION == 1 and self.velocity[1] > 0 or self.GRAVITY_DIRECTION == -1 and self.velocity[1] < 0) and not self.is_on_floor() and self.can_walljump[
            "blocks_around"]):
            self.can_walljump["sliding"] = False

        if not self.is_stunned:
            if self.is_on_floor():
                self.air_time = 0
                # If no input, apply floor friction (0.85 = slide a bit, 0.1 = stop instantly)
                if self.get_direction("x") == 0 and self.dashtime_cur == 0:
                    self.velocity[0] *= 0.8
            else:
                # Air resistance/deceleration when not pressing anything in air
                if self.get_direction("x") == 0:
                    if abs(self.velocity[0]) < 2 and not self.jumping:
                        self.velocity[0] *= 0.1
                    else:
                        self.velocity[0] *= 0.98
        else:
            self.velocity[0] *= 0.95

    def get_direction(self, axis):
        """Gets the current direction the player is holding towards. Takes an axis as argument ('x' or 'y')
        returns : -1 if left/down, 1 if right/up. 0 if bad arguments"""
        if axis == "x":
            return self.dict_kb["key_right"] - self.dict_kb["key_left"]
        elif axis == "y":
            return self.dict_kb["key_up"] - self.dict_kb["key_down"]

    def dash_ghost_trail(self):
        """Creates ghost images that fade out over time."""
        # Store current position and image with a timer
        ghost = {
            "pos": [self.rect().centerx, self.rect().centery],  # Assuming self.pos is a list or has a copy method
            "img": self.animation.img().copy(),  # Create a copy of the current image
            "lifetime": 20,  # How long the ghost remains visible (in frames)
            "angle": self.rotation_angle
        }

        # Add to list of ghost images
        self.ghost_images.append(ghost)

        # Max number of ghost images to prevent using too much memory
        max_ghosts = 20
        if len(self.ghost_images) > max_ghosts:
            self.ghost_images.pop(0)

    def update_ghost_trail(self):
        for ghost in self.ghost_images[:]:
            ghost["lifetime"] -= 1
            if ghost["lifetime"] <= 0:
                self.ghost_images.remove(ghost)

    def render(self, surf, offset=(0, 0)):
        # 1. Draw Ghosts
        for ghost in self.ghost_images[:]:
            alpha = int(255 * (ghost["lifetime"] / 20) ** 2)
            ghost_surf = ghost["img"].copy()

            # Apply transparency
            ghost_surf.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
            ghost_surf.fill((109, 156, 159, 70), special_flags=pygame.BLEND_RGBA_MIN)
            ghost_surf.set_alpha(alpha)

            # Rotate Ghost
            if ghost["angle"] != 0:
                ghost_surf = pygame.transform.rotate(ghost_surf, ghost["angle"])

            # Calculate Ghost Center
            # Note: We use the ghost's original position + half size to find the center
            ghost_center_x = ghost["pos"][0] - offset[0] + self.size[0] // 2
            ghost_center_y = ghost["pos"][1] - offset[1] + self.size[1] // 2

            # Get the new rect centered on that point
            ghost_rect = ghost_surf.get_rect(center=(ghost_center_x, ghost_center_y))

            # Apply your manual offsets (-8, -5/-12) if they were for visual alignment
            # (You might need to tweak these depending on your sprite art)
            ghost_rect.x -= 8
            ghost_rect.y -= 5 if self.GRAVITY_DIRECTION == 1 else 10 if self.GRAVITY_DIRECTION == -1 else 0

            surf.blit(ghost_surf, ghost_rect)

        # 2. Draw Player
        img = self.animation.img().convert_alpha()

        if self.GRAVITY_DIRECTION == -1:
            img = pygame.transform.flip(img, False, True)

        if self.can_walljump['count'] >= 1:
            # Create a red surface the same size as the image
            red_mask = pygame.Surface(img.get_size()).convert_alpha()

            # Update color depending on fatigue level (based on walljump count)
            removal_factor = 255 * ((self.can_walljump["count"]-1)/self.max_walljumps)
            color = (0, removal_factor, removal_factor, 0)
            red_mask.fill(color)

            # It keeps the alpha channel of the original sprite so only the player turns red.
            img.blit(red_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        if self.rotation_angle != 0:
            # Rotate the image
            rotated_img = pygame.transform.rotate(img, self.rotation_angle)

            # Calculate the center of the hitbox relative to the screen
            center_x = self.pos[0] - offset[0] + self.size[0] // 2
            center_y = self.pos[1] - offset[1] + self.size[1] // 2

            # Get a new rectangle for the rotated image, centered on the hitbox center
            new_rect = rotated_img.get_rect(center=(center_x, center_y))

            # Blit at the calculated coordinates
            surf.blit(rotated_img, new_rect)
        else:
            # Standard drawing if no rotation
            surf.blit(img, (self.pos[0] - offset[0], self.pos[1] - offset[1]))

        if self.show_hitbox:
            debug_rect = self.rect().copy()
            debug_rect.x -= offset[0]
            debug_rect.y -= offset[1]
            pygame.draw.rect(surf, (255, 0, 0), debug_rect, 1)
