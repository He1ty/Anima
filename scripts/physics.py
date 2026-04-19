#Heavily upgraded basic godot physics code that I then converted to Python --Aymeric
import math
import time
import random
from typing import override

from scripts.sound import *
from scripts.entities import deal_knockback


class Entity:
    GRAVITY_ACCELERATION = 0.35
    GRAVITY_DIRECTION = 1
    COLLISION_DODGED_PIXELS = 4  # Number of pixels collision can dodge (ledge snapping/corner correction)

    def __init__(self, game, tilemap, pos, size):
        self.game = game
        self.pos = list(pos)  # [x, y]
        self.size = size
        self.velocity: list[int | float] = [0, 0]  # [vel_x, vel_y]
        self.acceleration = [0.0, 0.0]
        self.tilemap = tilemap

        self.was_on_floor = False

        self.collision = {'left': False, 'right': False, 'bottom': False, 'top': False}
        self.get_block_on: dict[str, bool] = {'left': False, 'right': False, 'top': False, 'bottom': False}


        # Hitbox util vars
        self.show_hitbox = False

    @property
    def rect(self):
        return pygame.Rect(round(self.pos[0]), round(self.pos[1]), self.size[0], self.size[1])

    def _nudge_condition(self, rect):
        return rect not in self.game.doors_rects

    def _collision_actions(self, axe):
        return

    def apply_momentum(self, dt):
        """Applies velocity to the coords of the object. Slows down movement depending on environment"""

        self.pos[0] += self.velocity[0] * dt
        self.collision_check("x", dt)

        self.pos[1] += self.velocity[1] * dt
        self.collision_check("y", dt)

    def collision_check(self, axe, dt):
        """Checks for collision using tilemap"""
        entity_rect = self.rect
        tilemap = self.tilemap
        b_r = set()
        b_l = set()
        b_t = set()
        b_b = set()

        # Handle Vertical Collision First
        if axe == "y":

            if self.velocity[1] > 0 or not self.get_block_on["bottom"]:
                self.collision["bottom"] = False
            if self.velocity[1] < 0 or not self.get_block_on["top"]:
                self.collision["top"] = False


            for rect in tilemap.physics_rects_around(self.rect, self.GRAVITY_DIRECTION):
                if entity_rect.colliderect(rect):
                    if (self.GRAVITY_DIRECTION == 1 and self.velocity[1] > 0) or (
                            self.GRAVITY_DIRECTION == -1 and self.velocity[1] < 0):
                        # --- GROUND CORNER CORRECTION ---
                        # If falling and clipping a corner, try to nudge onto the ledge
                        nudged = False
                        if self._nudge_condition(rect):
                            for i in range(1, self.COLLISION_DODGED_PIXELS + 1):
                                right_shifted_hitbox_rect = pygame.Rect(round(self.pos[0]) + i, round(self.pos[1]), self.size[0],
                                                    self.size[1])
                                if not any(
                                        right_shifted_hitbox_rect.colliderect(r)
                                        for r in tilemap.physics_rects_around(right_shifted_hitbox_rect,
                                                                             self.GRAVITY_DIRECTION)):
                                    self.pos[0] += i
                                    nudged = True
                                    break
                                # Check Left nudge
                                left_shifted_hitbox_rect = pygame.Rect(round(self.pos[0]) - i, round(self.pos[1]), self.size[0],
                                                    self.size[1])
                                if not any(left_shifted_hitbox_rect.colliderect(r)
                                        for r in tilemap.physics_rects_around(left_shifted_hitbox_rect,
                                                                             self.GRAVITY_DIRECTION)):
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

                block_under_entitys_feet = ((self.GRAVITY_DIRECTION == 1 and entity_rect.y + self.size[
                    1] >= rect.y > entity_rect.y and entity_rect.x + self.size[
                         0] > rect.x and entity_rect.x < rect.x + rect.width) or
                        (self.GRAVITY_DIRECTION == -1 and entity_rect.y > rect.y >= entity_rect.y - self.size[
                            1] and entity_rect.x + self.size[0] > rect.x and entity_rect.x < rect.x + rect.width))

                if block_under_entitys_feet:
                    b_b.add(True)

            for rect in tilemap.physics_rects_around(self.rect, self.GRAVITY_DIRECTION):
                if entity_rect.colliderect(rect):
                    if (self.GRAVITY_DIRECTION == 1 and self.velocity[1] < 0) or (
                            self.GRAVITY_DIRECTION == -1 and self.velocity[1] > 0):
                        # If jumping and hitting a head-block corner, nudge to the side
                        nudged = False
                        if self._nudge_condition(rect):
                            for i in range(1, self.COLLISION_DODGED_PIXELS + 1):
                                # Try nudging Right
                                right_shifted_hitbox_rect = pygame.Rect(round(self.pos[0]) + i, round(self.pos[1]), self.size[0],
                                                    self.size[1])
                                if not any(
                                        right_shifted_hitbox_rect.colliderect(r)
                                        for r in
                                        tilemap.physics_rects_around(right_shifted_hitbox_rect, self.GRAVITY_DIRECTION)):
                                    self.pos[0] += i
                                    nudged = True
                                    break
                                # Try nudging Left
                                left_shifted_hitbox_rect = pygame.Rect(round(self.pos[0]) - i, round(self.pos[1]), self.size[0],
                                                    self.size[1])
                                if not any(
                                        left_shifted_hitbox_rect.colliderect(r)
                                        for r in
                                        tilemap.physics_rects_around(left_shifted_hitbox_rect, self.GRAVITY_DIRECTION)):
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
                            self._collision_actions(axe)


                block_on_entitys_head = ((self.GRAVITY_DIRECTION == 1 and entity_rect.y - self.size[
                    1] <= rect.y < entity_rect.y and entity_rect.x + self.size[
                         0] > rect.x and entity_rect.x < rect.x + rect.width) or
                        (self.GRAVITY_DIRECTION == -1 and entity_rect.y <= rect.y < entity_rect.y + self.size[
                            1] and entity_rect.x + self.size[0] > rect.x and entity_rect.x < rect.x + rect.width))

                if block_on_entitys_head:
                    b_t.add(True)

            if self.is_on_floor():
                self.pos[1] = round(self.pos[1])

            self.get_block_on["top"] = bool(b_t)
            self.get_block_on["bottom"] = bool(b_b)

        if axe == "x":
            if int(self.velocity[0]) > 0 or not self.get_block_on["left"] or self.velocity[0] == 0:
                self.collision["left"] = False
            if int(self.velocity[0]) < 0 or not self.get_block_on["right"] or self.velocity[0] == 0:
                self.collision["right"] = False

            for rect in tilemap.physics_rects_around(self.rect, self.GRAVITY_DIRECTION):
                if entity_rect.colliderect(rect):
                    # --- HORIZONTAL CORNER CORRECTION ---
                    # If hitting a wall, try to nudge the player Up or Down to bypass the corner
                    nudged = False
                    if self._nudge_condition(rect):
                        for i in range(1, self.COLLISION_DODGED_PIXELS + 1):
                            # 1. Try nudging UP (Useful for stepping onto a ledge automatically)
                            top_shifted_hitbox = pygame.Rect(round(self.pos[0]), round(self.pos[1]) - i, self.size[0], self.size[1])
                            if not any(
                                    top_shifted_hitbox.colliderect(r)
                                    for
                                    r in tilemap.physics_rects_around(top_shifted_hitbox, self.GRAVITY_DIRECTION)):
                                self.pos[1] = self.pos[1] - i
                                nudged = True
                                break
                            # 2. Try nudging DOWN (Useful for clearing a ceiling corner)
                            bottom_shifted_hitbox = pygame.Rect(round(self.pos[0]), round(self.pos[1]) + i, self.size[0], self.size[1])
                            if not any(
                                    bottom_shifted_hitbox.colliderect(r)
                                    for
                                    r in tilemap.physics_rects_around(bottom_shifted_hitbox, self.GRAVITY_DIRECTION)):
                                self.pos[1] = self.pos[1] + i
                                nudged = True
                                break

                    if not nudged:

                        if self.velocity[0] > 0:
                            entity_rect.right = rect.left
                            self.collision['right'] = True

                        if self.velocity[0] < 0:
                            entity_rect.left = rect.right
                            self.collision['left'] = True
                        self.pos[0] = entity_rect.x
                        self._collision_actions(axe)

            for rect in tilemap.physics_rects_around(self.rect, self.GRAVITY_DIRECTION):
                if ((self.GRAVITY_DIRECTION == 1 and (entity_rect.y - self.size[1] < rect.y <= entity_rect.y or
                                                      entity_rect.y + self.size[1] > rect.y >= entity_rect.y)) or
                        (self.GRAVITY_DIRECTION == -1 and (entity_rect.y <= rect.y < entity_rect.y + self.size[1] or
                                                           entity_rect.y >= rect.y > entity_rect.y + self.size[1]))):
                    if entity_rect.x - self.size[0] <= rect.x < entity_rect.x:
                        b_l.add(True)

                    if entity_rect.x + self.size[0] >= rect.x > entity_rect.x:
                        b_r.add(True)

            self.get_block_on["left"] = bool(b_l)
            self.get_block_on["right"] = bool(b_r)


    def is_on_floor(self):
        """Uses tilemap to heck if the player is standing on a surface based on gravity direction. used for gravity, jump, etc."""
        # Offset depends on gravity: +1 if normal (down), -1 if inverted (up)
        y_offset = self.GRAVITY_DIRECTION

        for rect in self.tilemap.physics_rects_around(self.rect, self.GRAVITY_DIRECTION):
            entity_rect = pygame.Rect(round(self.pos[0]), round(self.pos[1]) + y_offset, self.size[0], self.size[1])
            if entity_rect.colliderect(rect):
                if self.GRAVITY_DIRECTION == 1:
                    return self.rect.bottom == rect.top and self.velocity[1] >= 0
                else:
                    return self.rect.top == rect.bottom and self.velocity[1] <= 0
        return False

    def gravity(self, dt):
        """Handles gravity. Gives downwards momentum (capped at 6) if in the air, negates momentum if on the ground.
        Stops movement if no input is given."""

        self.acceleration[1] = self.GRAVITY_ACCELERATION

        if self.is_on_floor():
            self.velocity[1] = 0
        else:
            if self.GRAVITY_DIRECTION == 1:
                self.velocity[1] = min(6.0, self.velocity[1] + (self.acceleration[1] * self.GRAVITY_DIRECTION * dt))
            else:
                self.velocity[1] = max(-6.0, self.velocity[1] + (self.acceleration[1] * self.GRAVITY_DIRECTION * dt))

class Player(Entity):

    # Constants for movement
    SPEED = 2.1
    DASH_SPEED = 6
    JUMP_VELOCITY = -6
    DASHTIME = 10
    JUMPTIME = 8
    MIN_JUMPTIME = 2
    COYOTE_TIME = 3
    WALLJUMP_PUSHAWAY_TIME = 10
    DASH_COOLDOWN = 18
    DASH_STARTUP_FRAMES = 3

    def __init__(self, game, tilemap, pos, size):
        super().__init__(game, tilemap, pos, size)

        # DASH ATTRIBUTES
        self.dash_max_amt = 1
        self.dash_amt = self.dash_max_amt
        self.dash_startup_cur = 0
        self.dashtime_cur = 0  # Used to determine whether we are dashing or not. Also serves as a timer.
        self.dash_cooldown_cur = 0
        self.dash_direction = [0, 0]  # [dash_x, dash_y]
        self.dash_started_in_air = False
        self.anti_dash_buffer = False
        self.shadow_dash = False
        self.stop_dash_momentum = {"y": False, "x": False}

        # JUMP ATTRIBUTES
        self.coyote_cur = 0
        self.jumptime_cur = 0
        self.jump_buffering_cur = 0
        self.jump_multiplier = 1
        self.jumping = False
        self.holding_jump = False

        # SUPERJUMP ATTRIBUTES
        self.superjump = False
        self.tech_momentum_mult = 0

        # WALLJUMP ATTRIBUTES
        self.max_walljumps = 3
        self.can_walljump = {"sliding": False, "wall": 0, "buffer": False, "timer": 0, "blocks_around": False,
                             "allowed": True, "count": 0}
        self.climbing_walljump = False
        self.walljump_fatigue_frame_count = 0
        self.walljump_push_away_cur = 0
        self.wall_slide_acceleration_stabilized = False

        # SLIME PHYSICS ATTRIBUTES
        self.visual_scale = [1.0, 1.0]
        self.spring_velocity = [0.0, 0.0]  # Internal "jiggle" velocity
        self.stiffness = 0.15  # How fast it snaps back
        self.damping = 0.8  # How much it wobbles (lower = more wobbly)
        self.wall_trails = []

        # LAST FRAME VARIABLES
        self.last_direction = 1
        self.last_velocity = [0, 0]  # To catch velocity right before collision
        self.last_on_floor_velocity = [0, 0]
        self.last_pressed_x = 0
        self.prev_kb_x = {"key_right": 0, "key_left": 0}
        self.last_stun_time = 0

        # Keyboard and movement exceptions utils
        self.dict_kb = {"key_right": 0, "key_left": 0, "key_up": 0, "key_down": 0, "key_jump": 0, "key_dash": 0,
                        "key_noclip": 0}  # Used for reference

        self.force_movement_direction = {"r": [False, 0], "l": [False, 0]}
        self.force_movement = ""

        self.prevent_walking = False
        self.noclip = False
        self.noclip_buffer = False
        self.holding_n = False

        self.is_stunned = False
        self.stunned_by = None
        self.knockback_dir = [0, 0]
        self.knockback_strenght = 4
        self.knockback_duration = 0.5

        self.air_time = 0

        self.allowNoClip = True  # MANUALLY TURN IT ON HERE TO USE NOCLIP

        self.ghost_images = []

        self.facing = ""
        self.action = "idle"
        self.last_action = "idle"  # Pour détecter les changements d'action
        self.animation = self.game.assets['player/idle'].copy()
        self.disablePlayerInput = False
        self.collide_with_passable_blocks = True

        # Variables pour gérer les états des sons
        self.running_sound_playing = False
        self.run_sound_timer = 0
        self.run_sound_interval = 15  # Intervalle entre les répétitions du son de course

        self.rotation_angle = 0

    def update_sounds(self):
        """Update the player sounds depending on the player state"""

        # Landing sounds
        if self.is_on_floor() and not self.was_on_floor and self.air_time > 2:
            self.game.play_se('land')

        # Mise à jour de l'état du sol pour le prochain frame
        self.was_on_floor = self.is_on_floor()

        # Son de course/marche
        if "run" in self.action:
            self.run_sound_timer += 1

            # Détermine si le joueur court ou marche
            sound_key = 'run' if abs(self.velocity[0]) > 1.5 else 'walk'

            # Joue le son à intervalles réguliers pour créer un effet de pas
            if self.run_sound_timer >= self.run_sound_interval:
                self.game.play_se('run')
                self.run_sound_timer = 0
        else:
            self.run_sound_timer = 0

        # Détecte les changements d'action pour les événements ponctuels
        if self.action != self.last_action:
            if self.action in ["stun"]:
                self.game.play_se('stun')

            self.last_action = self.action

    def physics_process(self, dict_kb, dt):
        """Input : tilemap (map), dict_kb (dict)
        output : sends new coords for the PC to move to in accordance with player input and stage data (tilemap)"""
        self.dict_kb = dict_kb
        if dict_kb["key_right"] and not self.prev_kb_x["key_right"]:
            self.last_pressed_x = 1
        if dict_kb["key_left"] and not self.prev_kb_x["key_left"]:
            self.last_pressed_x = -1
        self.prev_kb_x["key_right"] = dict_kb["key_right"]
        self.prev_kb_x["key_left"] = dict_kb["key_left"]
        # self.force_player_movement_direction()
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
                    self.velocity = list(
                        deal_knockback(self.stunned_by, self, self.knockback_strenght, self.knockback_duration))

                # Jouer le son de stun
                if stun_elapsed < 0.05:  # Pour ne jouer le son qu'une fois au début du stun
                    self.game.play_se('stun')

                # When stunned, only apply knockback and gravity
                self.gravity(dt)
                self.apply_momentum(dt)
                return  # Skip the rest of the normal update logic
            else:
                self.stunned_by = None
                self.is_stunned = False
                self.knockback_dir = [0, 0]

        if self.is_on_floor() or self.can_walljump["sliding"]:
            self.air_time = 0
            self.climbing_walljump = False
            self.jumping = False
            self.superjump = False
            self.jump_multiplier = 1
            if self.dashtime_cur == 0:
                self.dash_started_in_air = False

        if self.is_on_floor():
            self.was_on_floor = True
            # Resets dash amount and walljump count
            if self.dashtime_cur <= self.DASHTIME * 2/3:
                self.dash_amt = self.dash_max_amt

            self.can_walljump["count"] = 0

        else:
            self.was_on_floor = False

        if self.collision["right"] or self.collision["left"]:
            if self.superjump:
                self.velocity[0] = 0
            self.superjump = False


        rotation_speed = 4.5
        if not self.is_on_floor() and not self.can_walljump["sliding"] and self.air_time > 2:
            # Spin speed (Adjust "8" to make it faster/slower
            # Spin based on direction (Clockwise if facing right, CCW if left)
            # We use last_direction so you keep spinning even if you stop pressing keys in mid-air

            if not self.can_walljump["sliding"] or self.rotation_angle % 90 != 0:
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

        if self.dict_kb["key_noclip"] == 1 and self.game.debug_mode and not self.holding_n:
            self.noclip = not self.noclip
            self.holding_n = True

        if self.dict_kb["key_noclip"] == 0:
            self.holding_n = False

        if not self.noclip:
            self.air_time += 1 * dt
            direction = self.get_direction("x")
            if direction != 0:
                self.last_direction = direction

            self.walk(direction, dt)

            self.jump(dt)
            self.jump_momentum(dt)
            self.dash(dt)
            self.dash_momentum(dt)

            self.gravity(dt)
            self.x_friction(dt)
            self.apply_momentum(dt)
            self.walljump_collision_check()

            self.apply_particle()
            self.update_slime_deformation(dt)
            self.update_wall_trails(dt)

            # Mise à jour des sons
            self.update_sounds()

        else:
            self.pos[0] += self.SPEED * self.get_direction("x")
            self.pos[1] += self.SPEED * -self.get_direction("y")

        if not self.is_on_floor():
            pass

    def force_player_movement_direction(self):
        """forces some keys to be pressed"""
        if self.force_movement_direction["r"][0] or self.force_movement_direction["l"][0]:
            if self.force_movement_direction["l"][0]:
                self.walk(-1, 1)
            else:
                self.walk(1, 1)
            if (-1 < self.force_movement_direction["l"][1] < 1 and self.force_movement_direction["l"][0]) or (
                    self.force_movement_direction["r"][0] and -1 < self.force_movement_direction["r"][
                1] < 1) or self.is_on_floor():
                self.force_movement_direction = {"r": [False, 0], "l": [False, 0]}
            elif self.force_movement_direction["l"][1] != -1 or self.force_movement_direction["r"][1] != -1:
                self.force_movement_direction["l"][1] -= 1
                self.force_movement_direction["r"][1] -= 1

    def force_player_movement(self):
        if self.force_movement != "":
            self.dict_kb["key_right"] = self.force_movement == "r"
            self.dict_kb["key_left"] = self.force_movement == "l"

    def walk(self, direction, dt, mult=1):
        """Changes x velocity with gradual acceleration and deceleration."""

        if not self.dashtime_cur > 0 and not self.prevent_walking:
            target_speed = direction * self.SPEED * mult

            # Acceleration factor: how fast we reach target speed
            # Lower = more slippery/weighty, Higher = snappier
            accel = 0.15 if self.is_on_floor() else 0.15

            if self.walljump_push_away_cur > 0:
                accel = 0.001

            # Deceleration in case speed in higher than self.SPEED (dash for example)
            if abs(self.velocity[0]) > self.SPEED:
                accel = 0.2

            if direction != 0 or self.dash_direction[0] != 0:
                # Gradually move current velocity toward target speed
                self.velocity[0] += (target_speed - self.velocity[0]) * min(accel * dt, 1.0)

    def set_action(self, action):
        if action != self.action:
            self.action = action
            # self.animation = self.game.assets['player/' + self.action].copy()

    def apply_particle(self):
        '''if self.velocity[1] < 0 and self.air_time < 20:
            self.game.particles.append(Particle(self.game, 'leaf', self.pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))'''

    def gravity(self, dt):
        """Handles gravity. Gives downwards momentum (capped at 6) if in the air, negates momentum if on the ground.
        Stops movement if no input is given."""

        self.acceleration[1] = self.GRAVITY_ACCELERATION

        if self.jumping:

            if self.holding_jump:
                if (self.velocity[1] < 1 and self.GRAVITY_DIRECTION == 1 or
                                      self.velocity[1] > 1 and self.GRAVITY_DIRECTION == -1):
                    self.acceleration[1] /= 1.5

            else:
                self.acceleration[1] *= 1.5


        self.y_friction()

        if self.is_on_floor():
            self.velocity[1] = 0
        else:
            if self.GRAVITY_DIRECTION == 1:
                self.velocity[1] = min(6.0, self.velocity[1] + (self.acceleration[1] * self.GRAVITY_DIRECTION * dt))
            else:
                self.velocity[1] = max(-6.0, self.velocity[1] + (self.acceleration[1] * self.GRAVITY_DIRECTION * dt))

    def y_friction(self):
        if not self.dashtime_cur > 0 and self.dash_startup_cur <= 0:
            if self.can_walljump["sliding"]:
                if self.wall_slide_acceleration_stabilized:

                    if self.can_walljump["count"] < self.max_walljumps - 1:
                        self.acceleration[1] = 0.05  # gravity acceleration while sliding

                    elif self.can_walljump["count"] == self.max_walljumps - 1:
                        self.acceleration[
                            1] = 0.008  # gravity acceleration while sliding (last jump)

                    else:
                        self.acceleration[
                            1] = self.GRAVITY_ACCELERATION  # gravity acceleration while sliding (no more jumps left, walljump fatigue)

                else:
                    self.velocity[1] = max(0, self.velocity[1] - 2)
                    if self.velocity[1] == 0:
                        self.wall_slide_acceleration_stabilized = True
            else:
                self.wall_slide_acceleration_stabilized = False

    def x_friction(self, dt):
        if not self.is_stunned:
            if self.is_on_floor():

                if self.dashtime_cur == 0:
                    self.dash_direction = [0, 0]

                # If no input, apply floor friction (0.85 = slide a bit, 0.1 = stop instantly)
                if self.get_direction("x") == 0 and self.dashtime_cur == 0:
                    self.velocity[0] = 0
            else:
                # Air resistance/deceleration when not pressing anything in air
                if self.get_direction("x") == 0:
                    # If player is colliding on a block
                    if (self.collision["right"] and self.velocity[0] > 0) or (self.collision["left"] and self.velocity[0] < 0):
                        self.velocity[0] = 0
                    # If player is slow-walking
                    elif abs(self.velocity[0]) < 2 and not self.jumping:
                        self.velocity[0] *= math.pow(0.1, dt)
                    # Normal air resistance
                    else:
                        self.velocity[0] *= math.pow(0.98, dt)
        else:
            self.velocity[0] *= math.pow(0.95, dt)


    def disallow_movement(self, boolean):
        """allows to disable or re-enable player movement. Bool as parameter, True to disable, False to enable movement."""
        self.disablePlayerInput = boolean


    def jump(self, dt):
        """Handles player jump and super/hyperdash tech"""
        self.coyote_cur = max(self.coyote_cur - dt, 0)
        self.walljump_push_away_cur =  max(self.walljump_push_away_cur - dt, 0)
        self.can_walljump["timer"] = max(0, self.can_walljump["timer"] - dt)

        self.can_walljump["buffer"] = False

        if self.can_walljump["timer"] <= 0:
            self.can_walljump["sliding"] = False

        if not (not self.can_walljump["buffer"] and not self.is_on_floor() and self.can_walljump[
            "blocks_around"] and self.can_walljump["timer"]):
            self.can_walljump["sliding"] = False

        if self.is_on_floor():
            self.coyote_cur = self.COYOTE_TIME

        if self.dict_kb["key_jump"] == 0:
            if self.jumptime_cur and self.holding_jump:
                if self.JUMPTIME - self.jumptime_cur < self.MIN_JUMPTIME:
                    self.jumptime_cur = self.MIN_JUMPTIME
                else:
                    self.jumptime_cur = dt

            self.holding_jump = False
            self.jump_buffering_cur = 0


        if self.dict_kb["key_jump"] == 1:

            self.collide_with_passable_blocks = False

            # Jumping
            if self.dash_startup_cur <= 0:
                # Jump on the ground
                if (self.is_on_floor() or self.coyote_cur) and not self.holding_jump:
                    self.jump_setup_helper()
                    self.game.play_se('jump')

                    # Jumps on dash
                    if self.dashtime_cur != 0:
                        if self.jump_buffering_cur <= 3:
                            self.dashtime_cur = 0
                            self.tech_momentum_mult = pow(abs(self.dash_direction[0]) + abs(self.dash_direction[1]), 0.5)

                            # Bottom Jump
                            if self.dash_direction[0] == 0:
                                pass
                            # Superjumps
                            else:

                                # Angular input superjump
                                if self.dash_direction[1] == -1:
                                    self.velocity[0] = 3 * self.get_direction("x") * self.DASH_SPEED * self.tech_momentum_mult
                                    self.jump_multiplier = 1.4 / self.tech_momentum_mult if self.tech_momentum_mult != 0 else 0

                                # On floor mono superjump
                                elif self.dash_direction[1] == 0:
                                    self.velocity[0] = 3 * self.get_direction("x") * self.DASH_SPEED * self.tech_momentum_mult
                                    self.jump_multiplier = 1 * self.tech_momentum_mult if self.tech_momentum_mult != 0 else 0

                                self.superjump = True

                        else:
                            self.jumptime_cur = 0
                            self.jumping = False
                            self.holding_jump = True

                # Walljump
                elif not self.holding_jump and self.can_walljump["allowed"]:
                    self.walljump()

                self.jump_buffering_cur += dt

                if self.jumptime_cur:
                    self.holding_jump = True

        if self.superjump:
            if self.air_time < 60:
                self.dash_ghost_trail()
                self.update_ghost_trail()

    def jump_setup_helper(self):
        self.jumptime_cur = self.JUMPTIME
        self.jumping = True
        self.jump_multiplier = 1

    def jump_momentum(self, dt):
        if self.jumptime_cur > 0:
            self.jumptime_cur = max(0, self.jumptime_cur - dt)
            self.velocity[1] = self.jump_multiplier * self.JUMP_VELOCITY * self.GRAVITY_DIRECTION
            if self.jumptime_cur <= 0:
                mult = 2
                self.velocity[1] = (abs(self.velocity[1]) / self.velocity[1]) * mult if self.velocity[1] != 0 else 0


    def wall_jump_animation_helper(self):
        self.visual_scale = [0.6, 1.4]
        self.spring_velocity = [0.2, -0.1]  # Add some outward jiggle

    def walljump(self):
        horizontal_boost_climbing_walljump = 2.5
        horizontal_boost_walljump = 2

        if self.can_walljump["sliding"] and self.can_walljump["count"] < self.max_walljumps:
            self.walljump_setup_helper()
            self.can_walljump["count"] += 1

            #Climbing WallJump
            if self.get_direction("x") == self.can_walljump["wall"]:
                self.climbing_walljump = True
                self.velocity[0] = -self.can_walljump["wall"] * horizontal_boost_climbing_walljump

            #Leaving Walljump
            else:
                self.velocity[0] = -self.can_walljump["wall"] * horizontal_boost_walljump
                self.last_direction = -self.last_direction
                self.walljump_push_away_cur = self.WALLJUMP_PUSHAWAY_TIME

            self.wall_jump_animation_helper()

        # This walljump is triggered considering the blocks_around offset
        elif self.can_walljump["blocks_around"] and self.jump_buffering_cur <= 3:

            # Super Walljump
            if self.dashtime_cur:
                self.super_walljump_logic_helper()
                tmp = self.jump_multiplier
                self.walljump_setup_helper()
                self.jumptime_cur += 4
                self.jump_multiplier = tmp


            elif not self.climbing_walljump and (self.can_walljump["count"] >= self.max_walljumps or self.get_direction("x") != self.can_walljump["wall"]):
                #Leaving Walljump
                self.walljump_setup_helper()
                self.velocity[0] = -self.can_walljump["wall"] * horizontal_boost_walljump
                self.last_direction = -self.last_direction
                self.walljump_push_away_cur = self.WALLJUMP_PUSHAWAY_TIME

            self.wall_jump_animation_helper()

        else:
            pass

    def walljump_sliding_check(self, axis):
        # The condition checks if there is no buffer,
        # if they are not on floor,
        # if there are blocks around,
        # if key corresponding to the axis is pressed and

        conditions = (not self.can_walljump["buffer"]
                      and
                      not ((self.holding_jump
                            and
                           (self.velocity[1] <= 0 and self.GRAVITY_DIRECTION == 1)
                            or
                            (self.velocity[1] >= 0 and self.GRAVITY_DIRECTION == -1)
                            )
                           )
                      and
                      not self.is_on_floor()
                      and
                      (self.get_block_on["left"] if axis == -1 else self.get_block_on["right"])
                      and
                      (self.dict_kb["key_left"] if axis == -1 else self.dict_kb["key_right"]))

        if conditions:
            self.can_walljump["sliding"] = True
            self.can_walljump["timer"] = self.COYOTE_TIME
            self.jumptime_cur = 0

    def walljump_collision_check(self):
        vertical_offset = 2
        horizontal_offset = 2 + 8.5

        check_right = (self.tilemap.solid_check((self.rect.centerx + horizontal_offset * 1, self.rect.y + vertical_offset),
                                                transparent_check=False) or
                       self.tilemap.solid_check((self.rect.centerx + horizontal_offset * 1, self.rect.bottom - vertical_offset),
                                                transparent_check=False))
        check_left = (self.tilemap.solid_check((self.rect.centerx + horizontal_offset * (-1), self.rect.y + 2),
                                               transparent_check=False) or
                      self.tilemap.solid_check((self.rect.centerx + horizontal_offset * (-1), self.rect.bottom - vertical_offset),
                                               transparent_check=False))
        if check_right and check_left:
            self.can_walljump["blocks_around"] = (
                    self.tilemap.solid_check(
                        (self.rect.centerx + horizontal_offset * self.last_direction, self.rect.y + vertical_offset),
                        transparent_check=False) or
                    self.tilemap.solid_check(
                        (self.rect.centerx + horizontal_offset * self.last_direction, self.rect.bottom - vertical_offset),
                        transparent_check=False))

            self.can_walljump["wall"] = self.last_direction
        else:
            self.can_walljump["blocks_around"] = check_right or check_left
            if check_right:
                self.can_walljump["wall"] = 1
            elif check_left:
                self.can_walljump["wall"] = -1
            else:
                self.can_walljump["wall"] = 0

        if self.can_walljump["blocks_around"] and self.can_walljump["wall"]:
            self.walljump_sliding_check(self.can_walljump["wall"])

    def walljump_setup_helper(self):
        self.jump_setup_helper()
        self.air_time = 0
        self.dashtime_cur = 0
        # Needed, since in next frame, u need to wait collisions to be checked in order to get your sliding value updated
        self.can_walljump["sliding"] = False

    def super_walljump_logic_helper(self):
        max_y_boost = 1.3
        min_y_boost = 1.1


        # Super walljump
        if self.dash_direction[1] == 1:
            self.velocity[0] = 2.5 * -self.can_walljump["wall"] - self.can_walljump["wall"]*(0.6/self.DASHTIME)*(self.dashtime_cur-self.DASHTIME)
            self.jump_multiplier = min_y_boost -self.GRAVITY_DIRECTION*((max_y_boost-min_y_boost)/self.DASHTIME)*(self.dashtime_cur-self.DASHTIME)
            self.superjump = True


    def dash(self, dt):
        """Handles player dash."""
        self.dash_startup_cur = max(self.dash_startup_cur - dt, 0)
        self.dash_cooldown_cur = max(self.dash_cooldown_cur - dt, 0)
        if not self.anti_dash_buffer:
            if self.dict_kb["key_dash"] == 1 and self.dash_cooldown_cur <= 0:
                if self.dash_amt > 0:
                    self.game.camera.screen_shake(10)
                    self.dashtime_cur = self.DASHTIME
                    self.dash_startup_cur = self.DASH_STARTUP_FRAMES
                    self.dash_cooldown_cur = self.DASH_COOLDOWN
                    self.stop_dash_momentum["y"], self.stop_dash_momentum["x"] = False, False
                    self.dash_amt -= 1
                    self.velocity = [0, 0]

                    # Jouer le son de dash
                    self.game.play_se('dash')
                    # self.play_sound('dash', force=True)
                if not self.is_on_floor():
                    self.dash_started_in_air = True
                self.anti_dash_buffer = True

        else:
            if self.dict_kb["key_dash"] == 0:
                self.anti_dash_buffer = False

    def dash_momentum(self, dt):
        """Applies momentum from dash. Manage momentum when dash ends."""
        if self.dash_startup_cur <= 0:
            if self.dashtime_cur > 0:
                if self.dashtime_cur == self.DASHTIME:
                    self.dash_direction = [self.get_direction("x"), self.get_direction("y")]
                    if self.dash_direction == [0, 0]:
                        if self.get_block_on["left"]:
                            self.dash_direction[0] = 1
                        elif self.get_block_on["right"]:
                            self.dash_direction[0] = -1
                        else:
                            self.dash_direction[0] = self.last_direction

                self.dash_ghost_trail()
                self.dashtime_cur = max(0, self.dashtime_cur - dt)
                move_x = self.dash_direction[0]
                move_y = -self.dash_direction[1]

                # Calculate the magnitude (length) of the direction
                magnitude = math.sqrt(move_x ** 2 + move_y ** 2)

                if magnitude > 0.0:
                    # Divide by magnitude to "normalize" the vector to a length of 1
                    self.velocity[1] = (move_y / magnitude) * self.DASH_SPEED
                    self.velocity[0] = (move_x / magnitude) * self.DASH_SPEED

                if self.dashtime_cur <= 0:
                    self.wall_slide_acceleration_stabilized = False
                    mult = 2
                    self.velocity[1] = (abs(self.velocity[1]) / self.velocity[1]) * mult if self.velocity[1] != 0 else 0
                    if self.collision["left"] or self.collision["right"]:
                        self.velocity[0] = 0

                # When dash is canceled with opposite direction
                if (self.get_direction("x") == -self.dash_direction[0] and self.get_direction("x") != 0 or
                        (self.get_direction("y") == -self.dash_direction[1] and self.get_direction("y") != 0)):
                    self.dashtime_cur = 0
                    if self.dash_direction[1] == 1:
                        self.superjump = True


            self.update_ghost_trail()


    @override
    def _nudge_condition(self, rect):
        return rect not in self.game.doors_rects and self.dashtime_cur and (
                self.dash_direction[0] == 0 or self.dash_direction[1] == 0)
    @override
    def _collision_actions(self, axe):
        #Left and Right collision
        if axe == "x":
            self.stop_dash_momentum["x"] = True

        #Top collision
        if axe == "y":
            self.can_walljump["buffer"] = True
            self.can_walljump["sliding"] = False
            self.jumptime_cur = 0


    def get_direction(self, axis):
        """Gets the current direction the player is holding towards. Takes an axis as argument ('x' or 'y')
        returns : -1 if left/down, 1 if right/up. 0 if bad arguments"""
        if axis == "x":
            right = self.dict_kb["key_right"]
            left = self.dict_kb["key_left"]
            if right and left:
                return self.last_pressed_x
            return right - left

        elif axis == "y":
            return self.dict_kb["key_up"] - self.dict_kb["key_down"]

    def dash_ghost_trail(self):
        """Creates ghost images that fade out over time."""
        # Store current position and image with a timer

        ghost = {
            "pos": [self.rect.centerx, self.rect.centery],  # Assuming self.pos is a list or has a copy method
            "img": self.animation.img().copy(),  # Create a copy of the current image
            "lifetime": 20,  # How long the ghost remains visible (in frames)
            "angle": self.rotation_angle
        }

        if self.superjump:
            ghost["color"] = (224, 239, 162, 40)

        # Add to list of ghost images
        self.ghost_images.append(ghost)

        # Max number of ghost images to prevent using too much memory
        max_ghosts = 50
        if len(self.ghost_images) > max_ghosts:
            self.ghost_images.pop(0)

    def update_ghost_trail(self):
        for ghost in self.ghost_images[:]:
            ghost["lifetime"] -= 1
            if ghost["lifetime"] <= 0:
                self.ghost_images.remove(ghost)

    def update_slime_deformation(self, dt):
        # 1. Friction/Spring Physics: Move scale back to 1.0 like a spring

        # Stabilizes the spring effect in order to low its duration (so it doesn't spring during 80000 years)
        if 0.95 <= self.visual_scale[0] <= 1.2:
            self.visual_scale[0] = 1
        if 0.95 <= self.visual_scale[1] <= 1.2:
            self.visual_scale[1] = 1

        # Force = -k * x
        force_x = -self.stiffness * (self.visual_scale[0] - 1.0)
        force_y = -self.stiffness * (self.visual_scale[1] - 1.0)

        # Acceleration = Force (mass is 1)
        self.spring_velocity[0] = (self.spring_velocity[0] + force_x * dt) * self.damping
        self.spring_velocity[1] = (self.spring_velocity[1] + force_y * dt) * self.damping

        self.visual_scale[0] += self.spring_velocity[0] * dt
        self.visual_scale[1] += self.spring_velocity[1] * dt


        # 2. Impact Detection (The "Splash")
        # Landing on Floor
        if self.is_on_floor() and abs(self.last_velocity[1]) > 2:
            impact = abs(self.last_velocity[1]) * 0.05
            self.visual_scale = [1.0 + impact, 1.0 - impact]  # Widen and flatten

        # Hitting a Wall (Wall Splash)
        if not self.rotation_angle and (self.collision['left'] or self.collision['right']) and abs(
                self.last_velocity[0]) > 1:
            impact = abs(self.last_velocity[0]) * 0.08
            self.visual_scale = [1.0 - impact, 1.0 + impact]  # Thin and tall'''

        # 3. Jumping Stretch
        if self.jumping and abs(self.velocity[1]) > 4:
            self.visual_scale = [0.8, 1.2]  # Stretch upward when leaving ground

        # Capture velocity for the next frame's impact calculation
        self.last_velocity = list(self.velocity)


    def update_wall_trails(self, dt):
        """Spawn and age wall trail segments when the player is sliding on a wall."""
        TRAIL_LIFETIME       = 50   # frames a segment lives
        TRAIL_SPAWN_INTERVAL = 1    # continuous: one segment every N frames
        TRAIL_WIDTH          = 5    # pixel width of each segment


        trail_color          = self.animation.img().convert_alpha().get_at((5, 10))[:-1]
        if self.dash_amt == 0:
            trail_color = (180, 180, 180)

        if not hasattr(self, '_trail_timer'):
            self._trail_timer = 0
        if not hasattr(self, '_was_wall_sliding'):
            self._was_wall_sliding = False

        is_wall_sliding = (
            self.can_walljump["sliding"]
            and (self.collision["left"] or self.collision["right"])
        )

        is_splatting = (self.dashtime_cur
            and (self.collision["left"] or self.collision["right"]))


        if is_wall_sliding or is_splatting:

            wall_side = "right" if self.collision["right"] else "left"


            seg_x = float(self.pos[0] + self.size[0]) if wall_side == "right" else float(self.pos[0])

            ts = self.tilemap.tile_size

            # Tile column the wall is in
            if wall_side == "right":
                wall_tile_x = round((self.pos[0] + self.size[0]) // ts)
            else:
                wall_tile_x = round((self.pos[0] - 1) // ts)

            # Player occupies these tile rows
            player_tile_top    = round(self.pos[1] // ts)
            player_tile_bottom = round((self.pos[1] + self.size[1] - 1) // ts)

            # Scan the wall column: find the topmost and bottommost solid tile
            # that overlaps with the player's vertical span
            block_top    = None
            block_bottom = None
            for tile_row in range(player_tile_top, player_tile_bottom + 1):
                loc = f"{wall_tile_x};{tile_row}"
                is_solid = False
                for layer in self.tilemap.tilemap:
                    if loc in self.tilemap.tilemap[layer]:
                        tile_id = self.tilemap.tile_manager.unpack_tile(
                            self.tilemap.tilemap[layer][loc]
                        )[0]
                        tile_type = self.tilemap.tile_manager.tiles[tile_id].type
                        from scripts.tilemap import PHYSICS_TILES
                        if tile_type in PHYSICS_TILES:
                            is_solid = True
                            break
                if is_solid:
                    tile_top    = tile_row * ts
                    tile_bottom = tile_top + ts
                    if block_top    is None or tile_top    < block_top:    block_top    = tile_top
                    if block_bottom is None or tile_bottom > block_bottom: block_bottom = tile_bottom

            if block_top is not None:
                # Clamp trail to intersection of player and block span
                trail_top    = max(int(self.pos[1]),                block_top)
                trail_bottom = min(int(self.pos[1] + self.size[1]), block_bottom)
            else:
                # No block found in column — skip spawning entirely
                trail_top    = 0
                trail_bottom = 0

            def _seg(y):
                return {
                    "x": seg_x,
                    "y": float(y),
                    "wall": wall_side,
                    "lifetime": TRAIL_LIFETIME,
                    "max_lifetime": TRAIL_LIFETIME,
                    "width": TRAIL_WIDTH,
                    "color": trail_color,
                }

            just_hit_wall = not self._was_wall_sliding
            if just_hit_wall:
                if trail_bottom > trail_top:
                    step = max(2, (trail_bottom - trail_top) // 8)
                    for row in range(trail_top, trail_bottom + step, step):
                        self.wall_trails.append(_seg(min(row, trail_bottom)))
                self._trail_timer = 0
            else:
                self._trail_timer += dt
                if self._trail_timer >= TRAIL_SPAWN_INTERVAL and trail_bottom > trail_top:
                    self._trail_timer = 0
                    mid_y = self.pos[1] + self.size[1] // 2
                    self.wall_trails.append(_seg(max(trail_top, min(trail_bottom, mid_y))))

        else:
            self._trail_timer = 0

        self._was_wall_sliding = is_wall_sliding

        # Age — positions stay frozen, only lifetime changes
        for seg in self.wall_trails:
            seg["lifetime"] -= dt
        self.wall_trails = [s for s in self.wall_trails if s["lifetime"] > 0]

    def render_wall_trails(self, surf, offset=(0, 0)):
        """Draw wall trail segments with alpha fade. Positions are frozen world coords."""
        for seg in self.wall_trails:
            t = seg["lifetime"] / seg["max_lifetime"]   # 1.0 → 0.0

            alpha = int(220 * t)
            if alpha <= 0:
                continue

            height = max(2, int(8 * t))
            width  = max(1, int(seg["width"] * t))

            # Convert frozen world position to screen coords — offset only, no drift added
            x = int(seg["x"]) - offset[0]
            y = int(seg["y"]) - offset[1]

            if seg["wall"] == "left":
                x -= width

            seg_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            r, g, b = seg["color"]
            seg_surf.fill((r, g, b, alpha))
            surf.blit(seg_surf, (x, y))

    def collide_with(self, rect, static_rect=False, rotating_rect=True):
        if static_rect and not rotating_rect:
            return self.rect.colliderect(rect)

        base_rect = self.rect

        # If there's no rotation, stick to the lightning-fast AABB standard check
        if self.rotation_angle % 360 == 0:
            if not static_rect:
                return base_rect.colliderect(rect)
            else:
                return base_rect.colliderect(rect) and self.rect.colliderect(rect)

        # --- TRUE ROTATED HITBOX VIA PYGAME MASKS ---

        # 1. Create a solid surface representing the player's exact base hitbox
        hitbox_surf = pygame.Surface(self.size, pygame.SRCALPHA)
        hitbox_surf.fill((255, 255, 255, 255))

        # 2. Rotate that surface by the player's angle
        rotated_surf = pygame.transform.rotate(hitbox_surf, self.rotation_angle)

        # 3. Generate a precise mask from the rotated surface
        player_mask = pygame.mask.from_surface(rotated_surf)

        # 4. Get the new rect of the rotated surface so we can properly anchor it
        rotated_rect = rotated_surf.get_rect(center=base_rect.center)

        # 5. Create a simple, completely filled mask for the target 'rect'
        target_mask = pygame.Mask(rect.size, fill=True)

        # 6. Calculate the relative coordinate offset between the two masks
        offset_x = rect.x - rotated_rect.x
        offset_y = rect.y - rotated_rect.y

        # 7. Return True if any "1" pixels overlap in the two masks
        if not static_rect:
            return player_mask.overlap(target_mask, (int(offset_x), int(offset_y))) is not None
        else:
            return ((player_mask.overlap(target_mask, (int(offset_x), int(offset_y))) is not None)
                    and self.rect.colliderect(rect))

    def render(self, surf, offset=(0, 0)):
        pos = [round(self.pos[0]), round(self.pos[1])]
        # 1. Draw Ghosts
        for ghost in self.ghost_images[:]:
            alpha = int(255 * (ghost["lifetime"] / 20) ** 2)
            ghost_surf = ghost["img"].copy()

            ghost_surf.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
            ghost_surf.fill((109, 156, 159, 70) if "color" not in ghost else ghost["color"],
                            special_flags=pygame.BLEND_RGBA_MIN)
            ghost_surf.set_alpha(alpha)

            if ghost["angle"] != 0:
                ghost_surf = pygame.transform.rotate(ghost_surf, ghost["angle"])

            ghost_center_x = ghost["pos"][0] - offset[0] + self.size[0] // 2
            ghost_center_y = ghost["pos"][1] - offset[1] + self.size[1] // 2
            ghost_rect = ghost_surf.get_rect(center=(ghost_center_x, ghost_center_y))
            ghost_rect.x -= 8
            ghost_rect.y -= 5 if self.GRAVITY_DIRECTION == 1 else 10 if self.GRAVITY_DIRECTION == -1 else 0

            surf.blit(ghost_surf, ghost_rect)

        img = self.animation.img().convert_alpha()

        new_w = round(self.size[0] * self.visual_scale[0])
        new_h = round(self.size[1] * self.visual_scale[1])
        scaled_img = pygame.transform.smoothscale(img, (new_w, new_h))

        render_x = pos[0] - offset[0] - (new_w - self.size[0]) // 2
        render_y = pos[1] - offset[1] - (new_h - self.size[1])

        if self.collision['left']:
            render_x = pos[0] - offset[0]
        elif self.collision['right']:
            render_x = pos[0] - offset[0] - (new_w - self.size[0])

        if self.GRAVITY_DIRECTION == -1:
            scaled_img = pygame.transform.flip(scaled_img, False, True)
            render_y = pos[1] - offset[1]

        color_mask = pygame.Surface(scaled_img.get_size()).convert_alpha()

        if self.dash_amt == 0:
            scaled_img = pygame.transform.grayscale(scaled_img)
            color = (0, self.dashtime_cur * 6, self.dashtime_cur * 8, 0)
            color_mask.fill(color)
            scaled_img.blit(color_mask, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.dashtime_cur != 0:
            scaled_img = pygame.transform.grayscale(scaled_img)
            color = (0, self.DASHTIME * 6, self.DASHTIME * 8, 0)
            color_mask.fill(color)
            scaled_img.blit(color_mask, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        if self.max_walljumps - self.can_walljump['count'] <= 1:
            self.walljump_fatigue_frame_count += 1
            removal_factor = 255
            color = (80, removal_factor, removal_factor, 0)
            color_mask.fill(color)
            if self.walljump_fatigue_frame_count > (25 if self.can_walljump['count'] == self.max_walljumps - 1 else 5):
                scaled_img = pygame.transform.grayscale(scaled_img)
                scaled_img.blit(color_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            if self.walljump_fatigue_frame_count > (30 if self.can_walljump['count'] == self.max_walljumps - 1 else 10):
                self.walljump_fatigue_frame_count = 0

        if self.rotation_angle != 0:
            final_img = pygame.transform.rotate(scaled_img, self.rotation_angle)
            center_x = pos[0] - offset[0] + self.size[0] // 2
            center_y = pos[1] - offset[1] + self.size[1] // 2
            blit_rect = final_img.get_rect(center=(center_x, center_y))
        else:
            final_img = scaled_img
            blit_rect = pygame.Rect(render_x, render_y, final_img.get_width(), final_img.get_height())

        # --- TILE CLIPPING (always applied) ---
        solid_rects = self.game.tilemap.physics_rects_around(self.rect, self.GRAVITY_DIRECTION)
        if solid_rects:
            keep_mask = pygame.Surface(final_img.get_size(), pygame.SRCALPHA)
            keep_mask.fill((255, 255, 255, 255))
            for tile_rect in solid_rects:
                local_x = tile_rect.x - offset[0] - blit_rect.x
                local_y = tile_rect.y - offset[1] - blit_rect.y
                pygame.draw.rect(keep_mask, (255, 255, 255, 0),
                                 (local_x, local_y, tile_rect.width, tile_rect.height))
            final_img.blit(keep_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        surf.blit(final_img, blit_rect)

        if self.show_hitbox:
            base_rect = self.rect
            if self.rotation_angle % 360 != 0:
                hitbox_surf = pygame.Surface(self.size, pygame.SRCALPHA)
                hitbox_surf.fill((255, 255, 255, 255))
                rotated_surf = pygame.transform.rotate(hitbox_surf, self.rotation_angle)
                player_mask = pygame.mask.from_surface(rotated_surf)
                rotated_rect = rotated_surf.get_rect(center=base_rect.center)
                outline = player_mask.outline()
                shifted_outline = [
                    (p[0] + rotated_rect.x - offset[0], p[1] + rotated_rect.y - offset[1])
                    for p in outline
                ]
                if len(shifted_outline) > 2:
                    pygame.draw.lines(surf, (0, 255, 0), True, shifted_outline, 1)
            else:
                standard_rect = base_rect.copy()
                standard_rect.x -= offset[0]
                standard_rect.y -= offset[1]
                pygame.draw.rect(surf, (0, 255, 0), standard_rect, 1)

            debug_rect = self.rect.copy()
            debug_rect.x -= offset[0]
            debug_rect.y -= offset[1]
            pygame.draw.rect(surf, (255, 0, 0), debug_rect, 1)