import sys
import math
import os
import json
import pygame
import random
import time

# --- Game Script Imports ---
# These modules handle specific game logic like physics, entities, and UI.
from scripts.entities import *
from scripts.utils import *
from scripts.tilemap import Tilemap
from scripts.physics import PhysicsPlayer
from scripts.particle import Particle
from scripts.activators import *
from scripts.user_interface import Menu, start_menu
from scripts.saving import Save, save_game
from scripts.doors import Door
from scripts.display import *
from scripts.text import load_game_texts, display_bottom_text, update_bottom_text
from scripts.spark import Spark
from scripts.sound import set_game_volume, change_music
from scripts.modes import *
from scripts.pickup import Pickup


class Game:
    """
    The primary Engine class for 'Anima'.

    This class manages the core game loop, state transitions (menus to gameplay),
    asset loading, level streaming, and the rendering pipeline (lighting, particles, UI).
    """

    def __init__(self, full_setup=True):
        """
        Initializes the Pygame context, display settings, and global game variables.
        Loads all base assets and prepares the internal state for the first level.
        """
        if full_setup:
            pygame.init()

            # --- Window Setup ---
            pygame.display.set_caption("Anima")
            # The actual window size
            self.screen = pygame.display.set_mode((960, 576), pygame.RESIZABLE)
            # The internal rendering surface (half size for a pixel-art aesthetic)
            self.display = pygame.Surface((480, 288))
            self.clock = pygame.time.Clock()

        # --- State Management ---
        # Controls which 'loop' the game is currently running
        self.state = "START_SCREEN"
        self.game_initialized = False

        # --- Icon Setup ---
        try:
            icon_img = pygame.image.load("assets/images/logo.png").convert_alpha()
            icon_img = pygame.transform.smoothscale(icon_img, (32, 32))
            pygame.display.set_icon(icon_img)
        except FileNotFoundError:
            pass

        self.fullscreen = False
        self.tile_size = 16

        # --- Entity Configuration ---
        # Defines animation durations, sizes, and looping behavior for every entity type
        self.e_info = {
            "picko": {"left/right": ["run"], "size": (16, 16),
                      "img_dur": {"idle": 12, "run": 8, "attack": 3, "death": 3, "hit": 5},
                      "loop": {"idle": True, "run": True, "attack": False, "death": False, "hit": False}},
            "glorbo": {"left/right": [], "size": (16, 16),
                       "img_dur": {"idle": 12, "run": 8, "attack": 3, "death": 3, "hit": 5},
                       "loop": {"idle": True, "run": True, "attack": False, "death": False, "hit": False}},
            "vine": {"left/right": [], "size": (16, 48),
                     "img_dur": {"warning": 12, "attack": 1, "retreat": 3},
                     "loop": {"warning": True, "attack": False, "retreat": False}},
            "blue_rock": {"left/right": [], "size": (16, 16),
                          "img_dur": {"intact": 1, "breaking": 2},
                          "loop": {"intact": False, "breaking": False}},
        }

        # --- Door Configuration ---
        self.d_info = {
            "vines_door_h": {"size": (64, 16), "img_dur": 5},
            "vines_door_v": {"size": (16, 64), "img_dur": 5},
            "breakable_stalactite": {"size": (16, 48), "img_dur": 1},
            "blue_vine_door_v": {"size": (16, 64), "img_dur": 5},
            "blue_vine_door_h": {"size": (64, 16), "img_dur": 5}
        }

        self.b_info = {"green_cave/0": {"size": self.display.get_size()}}
        self.environments = {"green_cave": (0, 1, 2), "blue_cave": (3, 4, 5)}
        self.spawners = {}

        # --- Camera Constraints ---
        # Defines min/max X and Y coordinates the camera can scroll to on very first spawn
        self.scroll_limits = {"x": (16, 656), "y": (-176, 144)}
        self.camera_center = None

        # --- Asset Loading ---
        self.assets = {
            'particle/leaf': Animation(load_images('particles/leaf'), loop=5),
            'particle/crystal': Animation(load_images('particles/crystal'), loop=1000),
            'particle/crystal_fragment': Animation(load_images('particles/crystal_fragment'), loop=1),
            'full_heart': load_image('full_heart.png', (16, 16)),
            'half_heart': load_image('half_heart.png', (16, 16)),
            'empty_heart': load_image('empty_heart.png', (16, 16)),
            'glorbo_projectile': load_image('projectiles/glorbo_projectile.png', (16, 16)),
            'missile': load_image('projectiles/missile.png', (16, 16)),
            'checkpoint/1': Animation(load_images('checkpoint/activated'), img_dur=10),
            'checkpoint/0': load_images('checkpoint/deactivated')
        }

        # Dynamically load assets from folders using helper functions
        self.assets.update(load_activators())
        self.assets.update(load_doors(self.d_info))
        self.assets.update(load_tiles())
        self.assets.update(load_entities(self.e_info))
        self.assets.update(load_player())
        self.assets.update(load_backgrounds(self.b_info))
        self.assets.update(load_pickups())

        # --- Map Object Caching ---
        # Pre-loads and pairs interactive objects for efficient lookup during level loading
        self.doors_id_pairs = []
        self.levers_id_pairs = []
        self.buttons_id_pairs = []
        self.tp_id_pairs = []

        for env in self.environments:
            self.doors_id_pairs += [(door, 0) for door in load_doors('editor', env)]
            self.levers_id_pairs += [(lever, 0) for lever in load_activators(env) if "lever" in lever]
            self.buttons_id_pairs += [(button, 0) for button in load_activators(env) if "button" in button]
            self.tp_id_pairs += [(tp, 0) for tp in load_activators(env) if "teleporter" in tp]

        # --- Audio System ---
        self.sound_running = False
        self.volume = 0.5
        self.current_music_path = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self.sound_running = True
        except Exception as e:
            print(f"Error initializing sound: {e}")

        # --- Input & Level Tracking ---
        self.dict_kb = {"key_right": 0, "key_left": 0, "key_up": 0, "key_down": 0,
                        "key_jump": 0, "key_dash": 0, "key_noclip": 0, "key_attack": 0}

        self.tilemap = Tilemap(self, self.tile_size)
        self.level = 0
        #Start level
        self.default_level = self.level

        self.active_checkpoint_anim = None

        self.activators = []
        self.projectiles = []
        self.activators_actions = load_activators_actions(self.level)
        self.spawner_pos = {}

        self.checkpoints = []
        self.current_checkpoint = None
        self.sections = {0: (0, 1, 2)}

        self.levels = {i:{} for i in range(len(os.listdir("data/maps")))}


        # --- Player Stats & Combat ---
        self.player = PhysicsPlayer(self, self.tilemap, (100, 0), (16, 16))
        self.player_hp = 100
        self.player_dmg = 50
        self.player_attack_time = 0.03
        self.player_attack_dist = 20
        self.player_last_attack_time = 0
        self.holding_attack = False
        self.attacking = False
        self.player_attacked = False

        self.teleporting = False
        self.tp_id = None
        self.last_teleport_time = 0
        self.screenshake = 0
        self.cutscene = False
        self.game_texts = load_game_texts()
        self.bottom_text = None
        self.doors_rects = []

        # --- Lighting System ---
        self.darkness_level = 255
        self.light_radius = 10
        self.light_soft_edge = 200
        self.light_emitting_tiles = []
        self.light_emitting_objects = []

        # Define light behaviors for different game objects
        self.light_properties = {
            "player": {"radius": 100, "intensity": 250, "edge_softness": 255, "color": (255, 255, 255),
                       "flicker": False},
            "torch": {"radius": 80, "intensity": 220, "edge_softness": 30, "color": (255, 180, 100), "flicker": True},
            "crystal": {"radius": 120, "intensity": 200, "edge_softness": 50, "color": (100, 180, 255),
                        "flicker": False},
            "glowing_mushroom": {"radius": 80, "intensity": 80, "edge_softness": 500, "color": (160, 230, 180),
                                 "flicker": False},
            "lava": {"radius": 100, "intensity": 210, "edge_softness": 40, "color": (255, 120, 50), "flicker": True}
        }

        self.light_infos = {i: {"darkness_level": 180, "light_radius": 200} for i in range(5)}
        self.light_mask = pygame.Surface((self.light_radius * 2, self.light_radius * 2), pygame.SRCALPHA)
        create_light_mask(self.light_radius)
        self.player_light = self.light_properties["player"]

        # --- Interactions & VFX ---
        self.moving_visual = False
        self.player_grabbing = False
        self.damage_flash_active = False
        self.damage_flash_end_time = 0
        self.damage_flash_duration = 100
        self.particles = []
        self.sparks = []

        # --- Menu & System Configuration ---
        self.selected_language = "English"
        self.menu = Menu(self)
        self.keyboard_layout = "AZERTY"
        self.save_system = Save(self)
        self.current_slot = None  # Tracking the active save slot

        # --- Modes configuration ---
        self.current_mode = "default"

        # --- Hitboxes
        self.show_spikes_hitboxes = False

        self.playtime = 0
        self.menu_time = 0

    def toggle_hitboxes(self):
        self.player.show_hitbox = not self.player.show_hitbox
        self.show_spikes_hitboxes = not self.show_spikes_hitboxes
        #self.tilemap.show_collisions = not self.tilemap.show_collisions

    def get_environment(self, level):
        """
        Retrieves the environment string (e.g., 'green_cave') for a given level ID.

        Args:
            level (int): The ID of the current level.

        Returns:
            str: The name of the environment category.
        """
        for environment in self.environments:
            if level in self.environments[environment]:
                return environment
        return "green_cave"

    def get_key_map(self):
        """
        Maps physical keys to game actions based on the current keyboard layout setting.

        Returns:
            dict: A mapping of pygame key constants to internal action strings.
        """
        layout = self.keyboard_layout.lower()
        if layout == "azerty":
            return {pygame.K_z: "key_up", pygame.K_s: "key_down", pygame.K_q: "key_left",
                    pygame.K_d: "key_right", pygame.K_g: "key_dash", pygame.K_SPACE: "key_jump",
                    pygame.K_n: "key_noclip"}
        return {pygame.K_w: "key_up", pygame.K_s: "key_down", pygame.K_a: "key_left",
                pygame.K_d: "key_right", pygame.K_g: "key_dash", pygame.K_SPACE: "key_jump",
                pygame.K_n: "key_noclip"}

    def load_level(self, map_id, transition_effect=True):
        """
        Loads level data from a JSON file, extracts entities, and sets up level-specific logic.

        Args:
            map_id (int): The index of the level to load.
            :param map_id:
            :param transition_effect:
        """
        self.tilemap.load("data/maps/" + str(map_id) + ".json")
        mult=0.5
        self.display = pygame.Surface((960*mult, 576*mult))
        self.light_emitting_tiles = []
        self.light_emitting_objects = []
        self.activators_actions = load_activators_actions(self.level)

        # --- Checkpoints & Traps ---
        self.checkpoints = self.tilemap.extract([("checkpoint", 0)])

        self.pickups = []
        for pickup in self.tilemap.extract([(p, 0) for p in sorted(os.listdir(BASE_IMG_PATH + 'pickups'))]):
            self.pickups.append(Pickup(self, pickup["pos"], pickup["type"]))

        self.spikes = []
        spike_types = [("spikes", 0), ("spikes", 1)]
        spike_block_types = []
        for n in range(9):
            spike_block_types += [("spike_roots", n)]


        for spike in self.tilemap.extract(spike_types, keep=True):
            self.spikes.append(DamageBlock(self, spike["pos"], self.assets[spike["type"]][spike["variant"]], hitbox_type='spike', rotation=spike["rotation"]))

        for spike_block in  self.tilemap.extract(spike_block_types, keep=True):
            self.spikes.append(DamageBlock(self, spike_block["pos"], self.assets[spike_block["type"]][spike_block["variant"]], hitbox_type='spike_block', rotation=spike_block["rotation"]))

        # --- Objects & Particles ---
        self.throwable = []
        for o in self.tilemap.extract([('throwable', 0)]):
            self.throwable.append(Throwable(self, "blue_rock", o['pos'], (16, 16)))

        self.leaf_spawners = []
        for plant in self.tilemap.extract([('vine_decor', 3), ('vine_decor', 4), ('vine_decor', 5),
                                           ('mossy_stone_decor', 15), ('mossy_stone_decor', 16)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + plant['pos'][0], 4 + plant['pos'][1], 23, 13))

        self.crystal_spawners = []
        for mushroom in self.tilemap.extract([("blue_decor", 14), ("blue_decor", 15)], keep=True):
            register_light_emitting_tile(self, (mushroom['pos'][0] + 8, mushroom['pos'][1] + 8), "glowing_mushroom")
            self.crystal_spawners.append(pygame.Rect(4 + mushroom['pos'][0], 4 + mushroom['pos'][1], 23, 13))

        # Initial setup for enemies and interactive objects
        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1), ('spawners', 3)]):
            if spawner['variant'] == 0:
                if self.current_checkpoint is None:
                    self.spawners[str(map_id)] = spawner["pos"].copy()
                    self.spawner_pos[str(map_id)] = spawner["pos"]
                    self.player.pos = spawner["pos"].copy()
                    self.spawn_point = {"pos": spawner["pos"].copy(), "level": map_id, "scroll_limits": self.scroll_limits, "camera_center": self.camera_center, "cameras": {}}
            elif spawner['variant'] == 1:
                self.enemies.append(Enemy(self, "picko", spawner['pos'], (16, 16), 100,
                                          {"attack_distance": 20, "attack_dmg": 10, "attack_time": 1.5}))
            elif spawner['variant'] == 3:
                self.enemies.append(DistanceEnemy(self, "glorbo", spawner['pos'], (16, 16), 100,
                                                  {"attack_distance": 100, "attack_dmg": 10, "attack_time": 1.5}))

        self.activators = []
        for activator in self.tilemap.extract(self.levers_id_pairs + self.buttons_id_pairs + self.tp_id_pairs):
            a = Activator(self, activator['pos'], activator['type'], i=activator["id"])
            a.state = activator["variant"]
            self.activators.append(a)

        self.doors = []
        for door in self.tilemap.extract(self.doors_id_pairs):
            door_type = door["type"]
            speed = int(door["opening_time"])
            door_id = door["id"]
            self.doors.append(
                Door(self.d_info[door_type]["size"], door["pos"], door_type, door_id, False, speed, self))

        self.camera_setup = []
        for camera in self.tilemap.extract(["camera_setup"]):
            self.camera_setup.append(CameraSetup(self, camera))

        # Set scroll on player spawn position at the very start (before any save), it updates later in load_game function in saving.py
        target_x = (self.player.rect().centerx if self.camera_center is None else self.camera_center[0]) - self.display.get_width() / 2
        min_x, max_x = self.scroll_limits["x"]
        max_x -= self.display.get_width()
        target_x = max(min_x, min(target_x, max_x))
        target_y = (self.player.rect().centery if self.camera_center is None else self.camera_center[1]) - self.display.get_height()/2
        min_y, max_y = self.scroll_limits["y"]
        max_y -= self.display.get_height()
        target_y = max(min_y, min(target_y, max_y))

        self.scroll = [target_x, target_y]


        self.transitions = self.tilemap.extract([("transition", 0)])

        # Reset VFX and interaction pools
        self.interactable = self.throwable.copy() + self.activators.copy()
        self.cutscene = False
        self.particles = []
        self.sparks = []
        self.transition = -30 if transition_effect else 0
        self.max_falling_depth = 50000000000
        update_light(self)

    def update_transitions(self):
        for transition in self.transitions:
            if (self.player.rect().left <= transition['pos'][0] <= self.player.rect().right <= transition['pos'][0] + self.tile_size and
                    self.player.rect().bottom >= transition['pos'][1] >= self.player.rect().top):
                self.level = int(transition["destination"])
                self.load_level(self.level, transition_effect=False)
                self.player.pos = [transition["dest_pos"][0] * 16, transition["dest_pos"][1] * 16]

    def update_teleport(self, render_scroll):
        for checkpoint in self.checkpoints:
            if not self.tilemap.pos_visible(self.display, checkpoint["pos"], render_scroll, additional_offset=(16, 16)):
                continue
            pos = checkpoint["pos"]

            if self.current_checkpoint == checkpoint:
                checkpoint["state"] = 1

                # 1. Only create the animation object if we haven't already!
                if self.active_checkpoint_anim is None:
                    self.active_checkpoint_anim = self.assets['checkpoint/1'].copy()
                    # Restore the frame from data if it exists (for loading saves)
                    if "frame" in checkpoint:
                        self.active_checkpoint_anim.frame = checkpoint["frame"]

                # 2. Update the PERSISTENT animation object
                self.active_checkpoint_anim.update()

                # 3. Sync the frame number back to the dict (so saving still works)
                checkpoint["frame"] = self.active_checkpoint_anim.frame

                # 4. Render using the persistent object
                self.display.blit(self.active_checkpoint_anim.img(),
                                  (pos[0] - render_scroll[0], pos[1] - render_scroll[1]))
                continue

            checkpoint["state"] = 0
            img = self.assets['checkpoint/0'].copy()[0]
            self.display.blit(img, (pos[0] - render_scroll[0], pos[1] - render_scroll[1]))
            if ((pos[0] <= self.player.pos[0] <= pos[0] + self.tile_size or pos[0] <= self.player.pos[0] + 16 <= pos[0] + self.tile_size) and
                    pos[1] >= self.player.pos[1] >= pos[1] - 16 and
                    self.current_checkpoint != checkpoint):

                self.current_checkpoint = checkpoint

                if self.spawn_point["pos"] == self.current_checkpoint["pos"] :
                    continue
                self.spawn_point = {"pos": self.current_checkpoint["pos"], "level": self.level, "scroll_limits": self.scroll_limits, "camera_center": self.camera_center, "cameras": {}}
                for camera in self.camera_setup:
                    if camera.initial_state != camera.scroll_limits:
                        self.spawn_point["cameras"][str(camera.initial_state)] = {}
                        self.spawn_point["cameras"][str(camera.initial_state)][
                            "scroll_limits"] = camera.scroll_limits
                        if hasattr(camera, "center"):
                            self.spawn_point["cameras"][str(camera.initial_state)]["center"] = camera.center
                save_game(self, self.current_slot)

    def update_pickups(self, render_scroll):
        for pickup in self.pickups:
            if self.tilemap.pos_visible(self.display, pickup.pos, render_scroll):
                pickup.update()
                pickup.render(self.display, render_scroll)

    def update_spawn(self):
        # Define respawn point based on current section or checkpoint
        if self.current_checkpoint is None:
            for section in self.sections.keys():
                if self.level in self.sections[section]:
                    try:
                        self.spawn_point = {"pos": self.spawner_pos[str(section)], "level": section}
                    except KeyError:
                        pass

    def update_particles(self, render_scroll):
        for rect in self.leaf_spawners:
            if not self.tilemap.pos_visible(self.display, (rect.x, rect.y), offset=render_scroll, additional_offset=(100, 100)):
                continue
            if random.random() * 49999 < rect.width * rect.height:
                pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

    def update_projectile(self, render_scroll):
        for projectile in self.projectiles[:]:
            projectile['pos'][0] += projectile['direction'][0]
            projectile['pos'][1] += projectile['direction'][1]
            projectile['timer'] += 1
            img = self.assets[projectile['type']].convert_alpha()
            self.display.blit(img, (projectile['pos'][0] - img.get_width() / 2 - render_scroll[0],
                                    projectile['pos'][1] - img.get_height() / 2 - render_scroll[1]))

            # Remove projectiles on wall collision or timeout
            if self.tilemap.solid_check(projectile['pos']) or projectile['timer'] > 360:
                self.projectiles.remove(projectile)
            elif self.player.rect().collidepoint(projectile['pos']):
                self.player_hp -= projectile.get('damage', 10)
                self.damage_flash_active = True
                self.damage_flash_end_time = pygame.time.get_ticks() + self.damage_flash_duration
                self.projectiles.remove(projectile)

    def update_enemies(self, render_scroll):
        for enemy in self.enemies.copy():
            enemy.update(self.tilemap, (0, 0))
            enemy.render(self.display, offset=render_scroll)
            if enemy.hp <= 0 or enemy.pos[1] > self.max_falling_depth:
                enemy.set_action("death")
                if enemy.animation.done: self.enemies.remove(enemy)

    def update_camera_setup(self):
        for camera in self.camera_setup:
            camera.update()

    def throwable_update(self, render_scroll):
        for o in self.throwable:
            o.update(self.tilemap, (0, 0))
            o.render(self.display, offset=render_scroll)

    def spike_hitbox_update(self, render_scroll):
        for spike_hitbox in self.spikes:
            if not self.player.noclip:
                if not spike_hitbox.circle_hitbox:
                    if self.player.rect().colliderect(spike_hitbox.rect()):
                        deal_dmg(self, spike_hitbox, "player", 200, 0.5)
                else:
                    dx = self.player.pos[0] - spike_hitbox.pos[0]
                    dy = self.player.pos[1] - spike_hitbox.pos[1]
                    distance = math.sqrt(dx ** 2 + dy ** 2)
                    if distance < (self.player.size[0]/2 + spike_hitbox.size.get_width()/2) and self.player.rect().colliderect(spike_hitbox.rect()):
                        deal_dmg(self, spike_hitbox, "player", 200, 0.5)


            if self.show_spikes_hitboxes:
                spike_hitbox.render(self.display, spike_hitbox.circle_hitbox, offset=render_scroll)

    def doors_update(self, render_scroll):
        # Doors (Colliders updated for physics)
        ds = []
        for door in self.doors:
            door.update()
            door.render(self.display, offset=render_scroll)
            if not door.opened:
                ds.append(door.rect())
                if self.player.show_hitbox:
                    k = door.rect().copy()
                    k.x -= render_scroll[0]
                    k.y -= render_scroll[1]
                    pygame.draw.rect(self.display, (255, 0, 0), k, 1)
        self.doors_rects = ds

    def spark_update(self, render_scroll):
        for spark in self.sparks[:]:
            if spark.update(): self.sparks.remove(spark)
            spark.render(self.display, offset=render_scroll)

    def particle_render(self, render_scroll):
        for particle in self.particles[:]:
            if not self.tilemap.pos_visible(self.display, particle.pos, offset=render_scroll, additional_offset=(100, 100)):
                self.particles.remove(particle)
                continue
            if particle.update(): self.particles.remove(particle)
            particle.render(self.display, offset=render_scroll)

    def death_handling(self):
        if self.player.pos[1] > self.max_falling_depth or self.player_hp <= 0:
            kill_player(self, self.screen, self.spawn_point["pos"], self.spawn_point["level"])
            for key in self.dict_kb.keys(): self.dict_kb[key] = 0
            self.player_hp = 100

    def damage_effect_update(self):
        if self.damage_flash_active:
            if pygame.time.get_ticks() < self.damage_flash_end_time:
                screen_shake(self, 16)
                screen_width, screen_height = self.screen.get_size()
                border_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
                elapsed = pygame.time.get_ticks() - (self.damage_flash_end_time - self.damage_flash_duration)
                progress = min(1.0, elapsed / self.damage_flash_duration)
                alpha = int(240 * (1 - progress))
                pygame.draw.rect(border_surface, (0, 0, 0, alpha), (0, 0, screen_width, screen_height), 100)
                self.screen.blit(border_surface, (0, 0))
            else:
                self.damage_flash_active = False

    def prerender_update(self):
        self.update_camera_setup()
        update_camera(self)
        render_scroll = (round(self.scroll[0]), round(self.scroll[1]))

        display_level_bg(self, self.level)
        return render_scroll

    def prerender_over_update(self, render_scroll):

        if not self.game_initialized:
            self.start_time = time.time()

        self.update_transitions()

        if self.transition < 0: self.transition += 1

        self.update_teleport(render_scroll)

        if self.teleporting: update_teleporter(self, self.tp_id)

        self.screenshake = max(0, self.screenshake - 1)

        self.update_pickups(render_scroll)

        self.player.disablePlayerInput = self.cutscene or self.moving_visual or self.teleporting

        self.update_particles(render_scroll)


        #Projectiles
        #self.update_projectile(render_scroll)

        # 4. Tilemap & Entities

        for activator in self.activators: activator.render(self.display, offset=render_scroll)

        # self.update_enemies(render_scroll)

        # 5. Player & Physics
        # attacking_update(self)

    def post_render_update(self, render_scroll):

        #self.throwable_update(render_scroll)

        self.spike_hitbox_update(render_scroll)

        self.particle_render(render_scroll)

        # 6. Foreground & Lighting
        display_level_fg(self, self.level)
        apply_lighting(self, render_scroll)

        self.doors_update(render_scroll)

        #self.spark_update(render_scroll)

        # --- Final UI Blits ---
        update_bottom_text(self)
        if self.cutscene:
            draw_cutscene_border(self.display)
        else:
            #draw_health_bar(self)
            pass

        # Persist enemy and object state for the level
        self.levels[self.level]["enemies"] = self.enemies.copy()
        self.levels[self.level]["activators"] = self.activators.copy()
        self.levels[self.level]["doors"] = self.doors.copy()

        # Handle Circle Transition Effect
        if self.transition:
            transition_surf = pygame.Surface(self.display.get_size())
            pygame.draw.circle(transition_surf, (255, 255, 255),
                               (self.display.get_width() // 2, self.display.get_height() // 2),
                               (30 - abs(self.transition)) * 8)
            transition_surf.set_colorkey((255, 255, 255))
            self.display.blit(transition_surf, (0, 0))

        # Scaling internal display to window size with screenshake
        screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2,
                              random.random() * self.screenshake - self.screenshake / 2)
        self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), screenshake_offset)

        # Damage Vignette Effect
        #self.damage_effect_update()

        pygame.display.update()

        # --- Death Handling ---
        self.death_handling()

        if not self.game_initialized:
            self.game_initialized = True
            if not os.path.exists(f"saves/save_{self.current_slot}.json"):
                save_game(self, self.current_slot)

        # --- Input Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.menu.menu_display()
                    for key in self.dict_kb.keys(): self.dict_kb[key] = 0
                if event.key == pygame.K_e:
                    # Interact with items or levers
                    update_throwable_objects_action(self)
                    if not self.player_grabbing: update_activators_actions(self, self.level)
                if event.key == pygame.K_F11: toggle_fullscreen(self)
                if event.key == pygame.K_f and not self.holding_attack:
                    self.dict_kb["key_attack"] = 1
                    self.holding_attack = True
                if event.key == pygame.K_h:
                    self.toggle_hitboxes()
                if event.key == pygame.K_r:
                    kill_player(self, self.screen, self.spawn_point["pos"], self.spawn_point["level"],
                                animation=False, transition=True)
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_f:
                    self.dict_kb["key_attack"] = 0
                    self.holding_attack = False
            # Generic keyboard state mapping
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                state = 1 if event.type == pygame.KEYDOWN else 0
                key_map = self.get_key_map()
                if event.key in key_map: self.dict_kb[key_map[event.key]] = state

        self.clock.tick(60)


    def main_game_logic(self):
        """
        The core gameplay loop. Handles physics, collision, rendering order,
        entity updates, and UI blitting. This is called once per frame while state is 'PLAYING'.
        """
        render_scroll = self.prerender_update()

        self.tilemap.render(self.display, offset=render_scroll)
        self.player.physics_process(self.tilemap, self.dict_kb)

        self.prerender_over_update(render_scroll)

        self.post_render_update(render_scroll)

    def run(self):
        """
        The main program entry point.
        This function implements a state machine to switch between the Intro, Profile Menu, and Gameplay.
        """
        while True:
            if self.state == "START_SCREEN":
                change_music(self,
                             "assets/sounds/GV2space-ambient-music-interstellar-space-journey-8wlwxmjrzj8_MDWW6nat.wav")
                # start_menu is a blocking call (usually handles its own internal loop)
                action = start_menu(self)
                if action == "play":
                    self.state = "PROFILE_SELECT"
                elif action == "settings":
                    self.menu.options_visible = True
                    self.menu.menu_display()
                elif action == "quit":
                    pygame.quit()
                    sys.exit()

            elif self.state == "PROFILE_SELECT":
                change_music(self,
                             "assets/sounds/GV2space-ambient-music-interstellar-space-journey-8wlwxmjrzj8_MDWW6nat.wav")
                # If a profile is chosen, start the game; otherwise return to intro
                if self.menu.profile_selection_menu():
                    self.state = "PLAYING"
                else:
                    self.state = "START_SCREEN"

            elif self.state == "PLAYING":
                # Dynamic music based on level ID

                change_music(self, "assets/sounds/" + f"map_{str(self.level)}" + ".wav")
                self.main_game_logic()


if __name__ == "__main__":
    # Instantiate the game and start the loop
    Game().run()