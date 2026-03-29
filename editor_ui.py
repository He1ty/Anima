import math
import sys

from scripts.activators import Activator
from scripts.camera import Camera, CameraSetup
from scripts.display import Shader
from scripts.doors import Door
from scripts.entities import DamageBlock, Throwable, Enemy, DistanceEnemy
from scripts.game import Game
from scripts.physics import PhysicsPlayer
from scripts.pickup import Pickup
from scripts.saving import Save
from scripts.sound import Sound
from scripts.tile import TileManager
from scripts.user_interface import Menu
from scripts.utils import load_image, create_rect_alpha, load_tiles
from scripts.button import EditorButton, LevelCarousel, EnvironmentButton, SimpleButton, Dropdown, IconButton
from scripts.text import load_game_font
from scripts.utils import *
from scripts.tilemap import Tilemap
import pygame

import os
import copy
import json
import shutil
import re

class Selector:
    def __init__(self, editor_instance):
        self.editor = editor_instance
        self.pos = self.editor.mpos_scaled
        self.initial_pos = self.pos
        self.rect = pygame.Rect(self.pos[0], self.pos[1], 0, 0)
        self.rect_displayed = False
        self.link = []
        self.link_pivot = None

    def get_coordinates_in_rect(self, rect):
        grid = []
        for x in range(rect.left//self.editor.tile_size, rect.right//self.editor.tile_size + 1):
            for y in range(rect.top//self.editor.tile_size, rect.bottom//self.editor.tile_size + 1):
                grid.append(f"{x};{y}")

        return grid

    def get_link_pivot(self, link):
        left, right, top, bottom = (float(link[0].split(";")[0]), float(link[0].split(";")[0]), float(link[0].split(";")[1]), float(link[0].split(";")[1]))
        for loc in link:
            pos = [float(coord) for coord in loc.split(";")]
            if pos[0] < left:
                left = pos[0]
            elif pos[0] > right:
                right = pos[0]

            if pos[1] < top:
                top = pos[1]
            elif pos[1] > bottom:
                bottom = pos[1]

        return [(right+left)/2, (top+bottom)/2]



    def draw(self, surface):
        if self.rect_displayed:
            overlay = pygame.Surface(self.rect.size)
            overlay.fill((10,10,100))
            surface.blit(overlay, (self.rect.left - self.editor.scroll[0], self.rect.top - self.editor.scroll[1]))

    def rect_pos_update(self):
        self.pos = [self.editor.mpos_scaled[0] + self.editor.scroll[0],
                    self.editor.mpos_scaled[1] + self.editor.scroll[1]]
        distx = self.pos[0] - self.initial_pos[0]
        disty = self.pos[1] - self.initial_pos[1]
        left = self.initial_pos[0]
        top = self.initial_pos[1]
        if distx < 0:
            left = self.pos[0]
        if disty < 0:
            top = self.pos[1]
        self.rect = pygame.Rect(left,
                                top,
                                abs(distx),
                                abs(disty))

    def tile_has_link(self, tile_pos):
        if self.editor.ignore_links:
            return []
        if self.editor.current_layer in self.editor.tilemap.links:
            for group in self.editor.tilemap.links[self.editor.current_layer]:
                if tile_pos in group:
                    return group
        return []

    def get_link_in_rect(self, rect, check_offgrid=True):
        link = []
        ongrid = self.get_coordinates_in_rect(rect)
        for tile_pos in ongrid:
            if tile_pos in self.editor.tilemap.tilemap[self.editor.current_layer]:
                tile_link = self.tile_has_link(tile_pos)
                if tile_link:
                    if not set(tile_link).issubset(set(link)):
                        link += tile_link
                else:
                    link.append(tile_pos)

        if check_offgrid and self.editor.current_layer in self.editor.tilemap.offgrid_tiles:
            for tile_pos in self.editor.tilemap.offgrid_tiles[self.editor.current_layer]:
                pos = [float(val) for val in tile_pos.split(";")]
                if (rect.left <= pos[0] <= rect.right and
                        rect.top <= pos[1] <= rect.bottom):
                    tile_link = self.tile_has_link(tile_pos)
                    if tile_link:
                        if not set(tile_link).issubset(set(link)):
                            link += tile_link
                    else:
                        link.append(tile_pos)

        if link:
            self.link_pivot = self.get_link_pivot(link)
        else:
            self.link_pivot = None

        return link

    def delete_link(self):
        if self.link:
            for tile_loc in self.link:
                space = self.editor.check_tile_space(tile_loc)
                if space == "tilemap":
                    del self.editor.tilemap.tilemap[self.editor.current_layer][tile_loc]
                else:
                    del self.editor.tilemap.offgrid_tiles[self.editor.current_layer][tile_loc]
            self.link = []

    def unlink_link(self, link):
        current_layer = self.editor.current_layer
        tilemap = self.editor.tilemap

        tilemap.links[current_layer].remove(link)
        if not tilemap.links[current_layer]:
            del tilemap.links[current_layer]

    def link_link(self):
        current_layer = self.editor.current_layer

        if current_layer in self.editor.tilemap.links:
            groups = self.editor.tilemap.links[current_layer]
            for group in groups:
                if set(group).issubset(set(self.link)) and group != self.link:
                    self.unlink_link(group)
        else:
            self.editor.tilemap.links[current_layer] = []

        if current_layer not in self.editor.tilemap.links:
            self.editor.tilemap.links[current_layer] = []
        self.editor.tilemap.links[current_layer].append(self.link.copy())

    # TODO group selection ("PLUS" icon) UI
    def add_link_to_group(self):
        group_id = str(input("group id: "))
        for tile_loc in self.editor.selector.link:
            if group_id not in self.editor.tilemap.tag_groups:
                self.editor.tilemap.tag_groups[group_id] = {"tiles": [],
                                                            "tags": {}}
            self.editor.tilemap.tag_groups[group_id]["tiles"].append((tile_loc, self.editor.current_layer))

    def remove_link_from_group(self):
        group_id = str(input("group id: "))
        for tile_loc in self.editor.selector.link:
            self.editor.tilemap.tag_groups[group_id]["tiles"].remove((tile_loc, self.editor.current_layer))
            if self.editor.tilemap.tag_groups[group_id] == {"tiles": [], "tags": {}}:
                del self.editor.tilemap.tag_groups[group_id]

    def handle_selection_rect(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 :
                button_collision = False
                for button in self.editor.ui.on_selection_buttons:
                    if button.rect.collidepoint(self.editor.mpos):
                        button_collision = True
                if not self.rect_displayed and not button_collision:
                    self.rect_displayed = True
                    self.initial_pos = self.pos

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.rect_displayed:
                    self.rect_displayed = False
                    group = self.get_link_in_rect(self.rect)
                    if group:
                        self.link = list(set(self.link) | (set(group)))
                    else:
                        self.link = []

        self.rect_pos_update()

    def handle_event(self, event):
        if event:
            self.handle_selection_rect(event)

class LevelManager:
    def __init__(self, editor_instance):
        self.editor = editor_instance

    def get_file_name(self, map_id):
        return f"{map_id:03d}.json"

    def get_next_file_id(self):
        existing_ids = []
        # 1. Look at actual files on disk
        if os.path.exists('data/maps/'):
            for f in os.listdir('data/maps/'):
                if f.endswith('.json'):
                    match = re.search(r'\d+', f)
                    if match:
                        existing_ids.append(int(match.group()))

        if not existing_ids:
            return 1
        return max(existing_ids) + 1

    def delete_map(self, level_id):
        # Remove ONLY from active maps. We leave it in editor.environments
        # so environments.json retains it if the user quits without a full_save.
        if level_id in self.editor.active_maps:
            self.editor.active_maps.remove(level_id)

        # Re-route the user to an existing level if they deleted the one they are on
        if self.editor.level_id == level_id:
            if self.editor.active_maps:
                self.change_level(self.editor.active_maps[-1])
            else:
                # Fallback if they deleted the very last map
                new_id = self.get_next_file_id()
                self.editor.active_maps.append(new_id)
                self.change_level(new_id)

    def map_data_reset(self):
        file_name = self.get_file_name(self.editor.level_id)
        filepath = f'data/maps/{file_name}'

        try:
            self.editor.tilemap.load(filepath)
        except FileNotFoundError:
            if not os.path.exists('data/maps/'):
                os.makedirs('data/maps/')
            with open(filepath, 'w') as f:
                json.dump({'tilemap': {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}, "5": {}, "6": {}},
                           'tilesize': 16, 'offgrid': {}}, f)
            self.editor.tilemap.load(filepath)

        self.editor.reload()

    def change_level(self, new_level_id):
        # Save current level before moving to the next
        if self.editor.level_id in self.editor.active_maps:
            current_file_name = self.get_file_name(self.editor.level_id)

            if self.editor.tilemap.tilemap != {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}, "5": {}, "6": {}}:
                self.editor.tilemap.save(f'data/maps/{current_file_name}')

        self.editor.level_id = new_level_id
        self.map_data_reset()

    def full_save(self):
        # 1. Save current map to disk
        if self.editor.level_id in self.editor.active_maps:
            current_file_name = self.get_file_name(self.editor.level_id)
            self.editor.tilemap.save(f'data/maps/{current_file_name}')

        # 2. Re-sequence IDs sequentially for surviving active_maps
        sorted_active = sorted(self.editor.active_maps)
        id_mapping = {old_id: (index + 1) for index, old_id in enumerate(sorted_active)}

        temp_dir = 'data/maps/temp_save'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # 3. Move valid files to temp directory with new names
        for old_id in sorted_active:
            new_id = id_mapping[old_id]

            old_file = self.get_file_name(old_id)
            new_file = self.get_file_name(new_id)

            src = f'data/maps/{old_file}'
            dst = f'{temp_dir}/{new_file}'

            if os.path.exists(src):
                shutil.copy2(src, dst)

        # 4. Clear old files and replace with temp
        for f in os.listdir('data/maps/'):
            if f.endswith('.json'):
                os.remove(f'data/maps/{f}')

        for f in os.listdir(temp_dir):
            shutil.move(f'{temp_dir}/{f}', f'data/maps/{f}')
        os.rmdir(temp_dir)

        # 5. Update running active maps
        self.editor.active_maps = list(id_mapping.values())
        self.editor.level_id = id_mapping.get(self.editor.level_id, 1)

        print("Full Save Complete: Maps reordered and deleted files removed.")

class PlayTest(Game):
    MENU_STATE = "MENU"
    PLAYING_STATE = "PLAYING"

    def __init__(self, editor_instance):
        # ── 1. Window & display ────────────────────────────────────────────────
        self.screen = editor_instance.screen
        self.display = editor_instance.display
        self.clock = pygame.time.Clock()
        self.debug_mode = False

        self.editor = editor_instance
        self.level_manager = editor_instance.level_manager
        self.tilemap = editor_instance.tilemap.copy(self)

        # ── 5. Level & map data ────────────────────────────────────────────────
        self.level_id = editor_instance.level_id
        self.environment = editor_instance.current_environment
        self.environments = editor_instance.environments.copy()
        self.level = self.level_manager.get_file_name(self.level_id)

        self.b_info = {
            "1": {"animated": True, "img_dur": 6, "loop": True, "path": f"environments/white_space/images/backgrounds"},
            "2": {"animated": False, "path": f"environments/green_cave/images/backgrounds"},
        }

        self.tile_size = self.tilemap.tile_size

        self.master_volume = 1
        player_sfx = "assets/player/sounds/"

        self.music_sound_manager = Sound(self, {
            'title_screen': "assets/ui/sounds/Title-screen-ambient-music.wav",
            'level_1': f"assets/environments/white_space/sounds/map_1.wav",
            'level_2': f"assets/environments/green_cave/sounds/map_2.wav",
        }, is_music=True, master_volume=self.master_volume, volume=1)

        self.sound_effect_manager = Sound(self, {
            "dash": player_sfx + 'dash.wav',
            "jump": player_sfx + 'jump.wav',
            "run": player_sfx + 'run.wav',
            "wall_jump": player_sfx + 'wall_jump.wav',
            "land": player_sfx + 'land.wav',
            "walk": None,
            "stun": None,
        }, is_music=False, master_volume=self.master_volume, volume=0.5)


        # ── 3. Save & settings ─────────────────────────────────────────────────
        self.save_system = Save(self)
        self.current_slot = None

        self.languages = ["Français", "English", "Español"]
        self.selected_language = self.languages[1]
        self.fullscreen = False
        self.vsync_on = False
        self.brightness = 0.5

        # ── 4. Keybindings ─────────────────────────────────────────────────────
        self.keyboard_layout = "AZERTY"
        self.key_map = {
            "key_up": pygame.K_z,
            "key_down": pygame.K_s,
            "key_left": pygame.K_q,
            "key_right": pygame.K_d,
            "key_jump": pygame.K_SPACE,
            "key_dash": pygame.K_g,
            "key_interact": pygame.K_e,
            "key_noclip": pygame.K_n,
            "key_hitbox": pygame.K_h,
            "key_select": pygame.K_RETURN,
        }
        self.keybindings = {}
        self.dict_kb = {
            "key_right": 0, "key_left": 0, "key_up": 0, "key_down": 0,
            "key_jump": 0, "key_dash": 0, "key_noclip": 0,
        }

        # ── 6. Assets ──────────────────────────────────────────────────────────
        self.assets = {}
        self.assets.update(load_tiles())
        self.assets.update(load_player())
        self.assets.update(load_backgrounds(self.b_info, self.level_id))
        self.assets.update(load_particles())

        self.doors_id_pairs = []
        self.levers_id_pairs = []
        self.buttons_id_pairs = []
        self.tp_id_pairs = []

        # ── 7. Camera ──────────────────────────────────────────────────────────
        self.camera = Camera(self)
        self.camera_center = None
        self.scroll_limits_per_level = {
            "1": {"x": (0, 0), "y": (-1230, 1233)},
            "2": {"x": (64, 624), "y": (-176, 144)},
        }
        self.scroll_limits = self.scroll_limits_per_level["1"]
        self.screenshake = 0

        # ── 8. Tilemap ─────────────────────────────────────────────────────────
        #self.activators_actions = load_activators_actions(self.level, self.tilemap.layers["activators"])
        self.doors_rects = []
        self.show_spikes_hitboxes = False

        # ── 9. Player ──────────────────────────────────────────────────────────
        self.player = PhysicsPlayer(self, self.tilemap, editor_instance.player_start, (16, 16))
        self.player_dead = False
        self.death_counter = 0

        self.collected_souls = []
        self.nb_souls = 0

        self.checkpoints = []
        self.current_checkpoint = None
        self.active_checkpoint_anim = None

        # ── 10. Activators & interactables ────────────────────────────────────
        self.activators = []
        self.projectiles = []
        self.teleporting = False
        self.tp_id = None
        self.last_teleport_time = 0
        self.player_grabbing = False

        # ── 11. Game state & flow ─────────────────────────────────────────────
        self.state = self.PLAYING_STATE
        self.previous_state = None
        self.game_initialized = False
        self.current_mode = "default"

        self.cutscene = False
        #self.game_texts = load_game_texts()
        self.bottom_text = None

        self.attacking = False
        self.holding_attack = False

        # ── 12. Lighting ──────────────────────────────────────────────────────
        self.darkness_level = 255
        self.light_radius = 10
        self.light_soft_edge = 200
        self.light_emitting_tiles = []
        self.light_emitting_objects = []

        self.light_properties = {
            "player": {"radius": 100, "intensity": 250, "edge_softness": 255, "color": (255, 255, 255),
                       "flicker": False},
            "torch": {"radius": 80, "intensity": 220, "edge_softness": 30, "color": (255, 180, 100), "flicker": True},
            "crystal": {"radius": 120, "intensity": 200, "edge_softness": 50, "color": (100, 180, 255),
                        "flicker": False},
            "glowing_mushroom": {"radius": 80, "intensity": 80, "edge_softness": 500, "color": (160, 230, 180),
                                 "flicker": False},
            "lava": {"radius": 100, "intensity": 210, "edge_softness": 40, "color": (255, 120, 50), "flicker": True},
        }
        self.light_infos = {i: {"darkness_level": 180, "light_radius": 200} for i in range(5)}
        self.player_light = self.light_properties["player"]

        self.shader = Shader(self)
        self.light_mask = pygame.Surface((self.light_radius * 2, self.light_radius * 2), pygame.SRCALPHA)
        self.shader.create_light_mask(self.light_radius)

        # ── 13. VFX & combat ──────────────────────────────────────────────────
        self.particles = []
        self.sparks = []
        self.moving_visual = False

        self.damage_flash_active = False
        self.damage_flash_end_time = 0
        self.damage_flash_duration = 100

        self.fake_tiles_opacity = 255
        self.fake_tiles_colliding_group = []
        if hasattr(self, "fake_tile_groups"):
            delattr(self, "fake_tile_groups")

        # ── 14. UI & menu ─────────────────────────────────────────────────────
        self.menu = Menu(self)

        # ── 15. Timers & counters ─────────────────────────────────────────────
        self.playtime = 0
        self.menu_time = 0

    def save_game(self, slot=1):
        return False

    def load_game(self, slot=1):
        return False

    def load_level(self, map_id, transition_effect=True):
        """
        Loads level data from a JSON file, extracts entities, and sets up level-specific logic.

        Args:
            map_id (int): The index of the level to load.
            :param map_id:
            :param transition_effect:
        """
        self.environment = self.level_manager.get_environment_by_id(self.level_id)
        map_name = self.level_manager.get_file_name(map_id)
        self.assets = {}
        self.assets.update(load_tiles(self.environment))
        self.assets.update(load_player())
        self.assets.update(load_backgrounds(self.b_info, self.environment))
        self.assets.update(load_particles(self.environment))

        self.tilemap.tile_size = self.tile_size
        self.light_emitting_tiles = []
        self.light_emitting_objects = []
        #self.activators_actions = load_activators_actions(map_name, self.tilemap.layers["activators"])

        # --- Checkpoints & Traps ---
        self.checkpoints = self.tilemap.extract([("checkpoint", 0)])

        self.pickups = []
        for pickup in self.tilemap.extract([(p, 0) for p in sorted(os.listdir(f"{BASE_IMG_PATH}environments/{self.environment}/images/tiles/pickups"))]):
            if pickup["pos"] not in self.collected_souls:
                self.pickups.append(Pickup(self, pickup["pos"], pickup["type"]))

        self.spikes = []
        spike_types = []
        for s in ("spikes", "gluy_spikes", "purpur_spikes"):
            for n in range(3):
                spike_types.append((s, n))

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
            self.shader.register_light_emitting_tile((mushroom['pos'][0] + 8, mushroom['pos'][1] + 8), "glowing_mushroom")
            self.crystal_spawners.append(pygame.Rect(4 + mushroom['pos'][0], 4 + mushroom['pos'][1], 23, 13))

        # Initial setup for enemies and interactive objects
        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1), ('spawners', 3)]):
            if spawner['variant'] == 1:
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
        '''for door in self.tilemap.extract(self.doors_id_pairs):
            door_type = door["type"]
            speed = int(door["opening_time"])
            door_id = door["id"]
            self.doors.append(
                Door(self.d_info[door_type]["size"], door["pos"], door_type, door_id, False, speed, self))'''

        self.camera_setup = []
        for camera in self.tilemap.extract(["camera_setup"]):
            self.camera_setup.append(CameraSetup(self, camera))

        if not hasattr(self, "fake_tile_groups"):
            self.fake_tile_groups = []
            """for fake_tile in self.tilemap.extract(fake_tiles_id_pairs, keep=True, layers=tuple(self.tilemap.layers["fake_tiles"])):
                fake_tile["pos"][0] = fake_tile["pos"].copy()[0] // self.tile_size
                fake_tile["pos"][1] = fake_tile["pos"].copy()[1] // self.tile_size
                g_check = True
                for group in self.fake_tile_groups:
                    if fake_tile in group:
                        g_check = False
                        continue
                if g_check:
                    group = self.tilemap.get_same_type_connected_tiles(fake_tile, self.tilemap.layers["fake_tiles"])
                    if group not in self.fake_tile_groups:
                        self.fake_tile_groups.append(group)
        self.tilemap.extract(fake_tiles_id_pairs, layers=tuple(self.tilemap.layers["fake_tiles"]))"""

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


        self.transitions = []

        # Reset VFX and interaction pools
        self.interactable = self.throwable.copy() + self.activators.copy()
        self.cutscene = False
        self.particles = []
        self.sparks = []
        self.transition = -30 if transition_effect else 0
        self.max_falling_depth = 50000000000
        self.shader.update_light()

    def leave(self):
        self.editor.state = "MapEditor"
        self.state = self.PLAYING_STATE
        self.editor.screen = self.screen
        self.editor.screen_width, self.editor.screen_height = self.screen.get_size()
        self.editor.screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        self.editor.ui.reload()
        self.music_sound_manager.stop('title_screen')

    def run(self):
        """
        The main program entry point.
        This function implements a state machine to switch between the Intro, Profile Menu, and Gameplay.
        """
        match self.state:
            case self.MENU_STATE:
                self.menu.draw()
                if self.menu.menu_state == self.menu.TITLE_STATE:
                    self.leave()
            case self.PLAYING_STATE:
                self.main_game_logic()
                self.menu.draw_player_souls()
        self.apply_brightness()
        pygame.display.update()

class EditorSimulation:
    SW = 960
    SH = 600

    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Editor")
        self.screen_width = self.SW
        self.screen_height = self.SH
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.display = pygame.Surface((self.screen_width / 2, self.screen_height / 2))
        self.clock = pygame.time.Clock()
        self.zoom = 1
        self.scroll = [0, 0]
        self.movement = [0, 0, 0, 0]

        self.current_tool = "Brush"
        self.current_environment = "white_space"
        self.selecting_environment_mode = False

        # Undo/Redo
        self.history = []
        self.history_index = -1
        self.max_history = 50
        self.temp_snapshot = None

        # LevelManager — doit être créé AVANT d'utiliser active_maps/environments
        self.level_manager = LevelManager(self)

        self.active_maps = []
        for ids in os.listdir("data/maps"):
            self.active_maps.append(int(ids[:-5]))
        self.active_maps.sort()

        self.level_id = self.active_maps[0] if self.active_maps else 1

        self.tile_group = 0
        self.tile_variant = 0

        self.environments = load_editor_tiles()
        self.categories = {}
        for category_dict in self.environments.values():
            for category_name, category_tiles in category_dict.items():
                if category_name in self.categories:
                    self.categories[category_name].update(category_tiles)
                else:
                    self.categories[category_name] = category_tiles

        self.assets = {}
        for category in self.environments.values():
            for tile in category.values():
                self.assets.update(tile)



        self.tile_type = next(iter(self.environments[next(iter(self.environments))][next(iter(self.environments[next(iter(self.environments))]))]))

        self.showing_all_layers = False
        self.current_layer = "0"
        self.current_category = 0

        self.tilemap = Tilemap(self)

        self.tile_size = self.tilemap.tile_size

        try:
            file_name = self.level_manager.get_file_name(self.level_id)
            filepath = f'data/maps/{file_name}'
            self.tilemap.load(filepath)
        except FileNotFoundError:
            pass

        self.clicking = False
        self.rotation = 0
        self.state = "MapEditor"

        self.mpos = pygame.mouse.get_pos()
        self.main_area_width = self.screen_width
        self.main_area_height = self.screen_height

        scale_x = 960 / (self.screen.get_size()[0])
        scale_y = 600 / (self.screen.get_size()[1])
        self.mpos_scaled = ((self.mpos[0] / 2) * scale_x * self.zoom,
                            (self.mpos[1] / 2) * scale_y * self.zoom)

        self.mpos_scaled_onclick = self.mpos_scaled

        self.mpos_in_mainarea = self.mpos[0] < self.main_area_width and self.mpos[1] < self.main_area_height

        self.ongrid = True

        self.selector = Selector(self)

        self.holding_i = False
        self.holding_b = False
        self.holding_y = False
        self.holding_tab = False

        self.moved_link = {"ongrid": {}, "offgrid": {}}
        self.player_start = (0, 0)

        self.infos_per_type_per_category = {
            "Levers": {
                "visual_and_door": {"id": int, "visual_duration": int, "door_id": int},
                "test": {"id": int, "info 1": int, "info 2": str}
            },
            "Teleporters": {
                "normal_tp": {"id": int, "dest": str, "time": int},
                "progressive_tp": {"id": int, "dest": str, "time": int}
            },
            "Buttons": {
                "improve_tp_progress": {"id": int, "amount": int, "tp_id": int},
            },
            "Transitions": {
                "transition": {"destination": int,
                               "dest_pos": list}
            },
            "Cameras": {
                "non-static": {
                    "size": list,
                    "x_limits": list,
                    "y_limits": list
                },
                "static": {"size": list,
                           "center": list,
                           "x_limits": list,
                           "y_limits": list
                           }
            },
            "Doors": {
                "non_interactable": {
                    "id": int,
                    "opening_time": int}}

        }
        self.types_per_categories = {t: set(self.infos_per_type_per_category[t].keys()) for t in
                                     self.infos_per_type_per_category}

        self.ui = UI(self)
        self.playtest = None#PlayTest(self)
        self.ignore_links = False

        self.save_action()

    def create_snapshot(self):
        # Creates a deep copy of the current map state
        return {
            'tilemap': copy.deepcopy(self.tilemap.tilemap),
            'offgrid': copy.deepcopy(self.tilemap.offgrid_tiles),
            'links': copy.deepcopy(self.tilemap.links),
            'selected_link': copy.deepcopy(self.selector.link)
        }

    def save_action(self):
        # 1. Create snapshot
        snapshot = self.create_snapshot()

        # 2. If we aren't at the end of history (because we undid), cut the future
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        # 3. Add new state
        self.history.append(snapshot)
        self.history_index += 1

        # 4. Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1

    def restore_snapshot(self, snapshot):
        # 1. Load data
        self.tilemap.tilemap = copy.deepcopy(snapshot['tilemap'])
        self.tilemap.offgrid_tiles = copy.deepcopy(snapshot['offgrid'])
        self.tilemap.links = copy.deepcopy(snapshot['links'])
        self.selector.link = copy.deepcopy(snapshot['selected_link'])

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_snapshot(self.history[self.history_index])
            print(f"Undo: Step {self.history_index}")

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_snapshot(self.history[self.history_index])
            print(f"Redo: Step {self.history_index}")

    def get_infos_tile_category(self, tile):
        for tile_category in self.infos_per_type_per_category:
            if tile_category.lower()[:-1] in tile["type"]:
                return tile_category

    def get_categories(self):
        self.current_category = 0
        self.tile_type = next(iter(self.environments[next(iter(self.environments))][next(iter(self.environments[next(iter(self.environments))]))]))

    def get_assets(self):
        self.assets = {}
        self.assets = {}
        for category in self.environments.values():
            for tile in category.values():
                self.assets.update(tile)

    def sizeofmaps(self):
        return len(self.active_maps)

    def check_tile_space(self, tile_loc):
        current_layer = self.current_layer
        tilemap = self.tilemap
        if current_layer in tilemap.tilemap:
            if tile_loc in tilemap.tilemap[current_layer]:
                return "tilemap"
        if current_layer in tilemap.offgrid_tiles:
            if tile_loc in tilemap.offgrid_tiles[current_layer]:
                return "offgrid"
        return None

    def reload(self):
        self.scroll = [0, 0]
        self.get_categories()
        self.get_assets()

        self.history = []
        self.history_index = -1
        self.selector.link = []
        self.save_action()  # Save the initial state (Index 0)

    def mpos_update(self):
        self.mpos = pygame.mouse.get_pos()
        self.main_area_width = self.screen_width
        self.main_area_height = self.screen_height
        if self.mpos[0] < self.main_area_width and self.mpos[
            1] < self.main_area_height:  # Only if mouse is over main area
            # Scale mouse position to account for display scaling
            scale_x = 960 / (self.screen.get_size()[0])
            scale_y = 600 / (self.screen.get_size()[1])
            self.mpos_scaled = ((self.mpos[0] / 2) * scale_x * self.zoom,
                                (self.mpos[1] / 2) * scale_y * self.zoom)
            self.tile_pos = (int((self.mpos_scaled[0] + self.scroll[0]) // self.tilemap.tile_size),
                             int((self.mpos_scaled[1] + self.scroll[1]) // self.tilemap.tile_size))
        else:
            # Default values if out of bounds to prevent crash
            self.tile_pos = (0, 0)
            self.mpos_scaled = (0, 0)

        self.tile_pos_onclick = (int((self.mpos_scaled_onclick[0] + self.scroll[0]) // self.tilemap.tile_size),
                             int((self.mpos_scaled_onclick[1] + self.scroll[1]) // self.tilemap.tile_size))
        self.mpos_in_mainarea = self.mpos[0] < self.main_area_width and self.mpos[1] < self.main_area_height

    def move_visual_to(self, tile_pos):
        scale_x = 960 / self.screen.get_size()[0]
        scale_y = 600 / self.screen.get_size()[1]
        pos = [0,0]
        if self.current_layer in self.tilemap.tilemap:
            if tile_pos in self.tilemap.tilemap[self.current_layer]:
                pos = [int(val) for val in tile_pos.split(";")]
        if self.current_layer in self.tilemap.offgrid_tiles:
            if tile_pos in self.tilemap.offgrid_tiles[self.current_layer]:
                pos = [int(float(val)/self.tilemap.tile_size) for val in tile_pos.split(";")]

        self.scroll[0] = (pos[0] * 16 - self.screen_width * scale_x) // (
                2 * int(2 * self.zoom))
        self.scroll[1] = pos[1] * 16 - self.screen_height * scale_y // (2 * int(2 * self.zoom))

    def handle_brush_tool(self):
        self.selector.link = []
        self.moved_link = {"ongrid":{}, "offgrid":{}}
        if self.clicking:
            t = self.tile_type
            t_id = self.tilemap.tile_manager.get_id(t)
            t_groups = self.tilemap.tile_manager.tiles[t_id].groups
            if self.ongrid:
                tile_loc = str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])
                self.tilemap.tilemap[self.current_layer][tile_loc] = (
                    self.tilemap.tile_manager.pack_tile(t_id, self.tile_variant, self.rotation))

            else:
                if self.current_layer not in self.tilemap.offgrid_tiles:
                    self.tilemap.offgrid_tiles[self.current_layer] = {}
                tile_loc = str(self.mpos_scaled[0] + self.scroll[0])+";"+ str(self.mpos_scaled[1] + self.scroll[1])
                self.tilemap.offgrid_tiles[self.current_layer][tile_loc] = (
                    self.tilemap.tile_manager.pack_tile(t_id, self.tile_variant, self.rotation))



            if t_groups:
                for group_id in t_groups:
                    self.tilemap.tag_groups[group_id]["tiles"].append((tile_loc, self.current_layer))

    def handle_eraser_tool(self):
        self.selector.link = []
        if self.clicking:
            tile_loc = str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])
            if tile_loc in self.tilemap.tilemap[self.current_layer]:
                del self.tilemap.tilemap[self.current_layer][tile_loc]


            if self.current_layer in self.tilemap.offgrid_tiles:
                for loc in self.tilemap.offgrid_tiles[self.current_layer].copy():
                    pos = [float(val) for val in loc.split(";")]
                    tile_id, variant, rot, flip_h, flip_v  = self.tilemap.tile_manager.unpack_tile(self.tilemap.offgrid_tiles[self.current_layer][loc])
                    images = self.tilemap.tile_manager.tiles[tile_id].images.copy()
                    if isinstance(images, Animation):
                        tile_img = images.img()
                    else:
                        tile_img = images[variant]
                    tile_r = pygame.Rect(pos[0] - self.scroll[0],
                                         pos[1] - self.scroll[1],
                                         tile_img.get_width(),
                                         tile_img.get_height())
                    if tile_r.collidepoint(self.mpos_scaled):  # Check both to be safe
                        del self.tilemap.offgrid_tiles[self.current_layer][loc]

            tile_link = self.selector.tile_has_link(tile_loc)
            if tile_link:
                self.tilemap.links[self.current_layer].remove(tile_link)
                tile_link.remove(tile_loc)
                self.tilemap.links[self.current_layer].append(tile_link)

    def handle_move_tool(self, event):
        if self.clicking:
            tilepos_onclick = (int((self.mpos_scaled_onclick[0]) // self.tilemap.tile_size),
                               int((self.mpos_scaled_onclick[1]) // self.tilemap.tile_size))
            mpos_scaled_onclick = (
                self.mpos_scaled_onclick[0] - self.scroll[0], self.mpos_scaled_onclick[1] - self.scroll[1])
            if self.selector.link:
                for loc in self.selector.link:
                    offgrid_tile = False
                    if loc in self.tilemap.tilemap[self.current_layer]:
                        pass
                    else:
                        offgrid_tile = True

                    pos = [float(val) for val in loc.split(";")]

                    if self.ongrid:
                        # Convert to tile units if offgrid, otherwise pos is already in tile units
                        tx = pos[0] // self.tilemap.tile_size if offgrid_tile else pos[0]
                        ty = pos[1] // self.tilemap.tile_size if offgrid_tile else pos[1]


                        x, y = tx + self.tile_pos[0] - tilepos_onclick[0], ty + self.tile_pos[1] - tilepos_onclick[1]
                        self.moved_link["offgrid"] = {}
                        self.moved_link["ongrid"][loc] = f"{int(x)};{int(y)}"
                    else:
                        # Convert to pixel units if ongrid, otherwise pos is already in pixels
                        px = pos[0] * self.tile_size if not offgrid_tile else pos[0]
                        py = pos[1] * self.tile_size if not offgrid_tile else pos[1]
                        x, y = px + self.mpos_scaled[0] - mpos_scaled_onclick[0], py + self.mpos_scaled[1] - \
                               mpos_scaled_onclick[1]
                        self.moved_link["ongrid"] = {}
                        self.moved_link["offgrid"][loc] = f"{x};{y}"

        if self.selector.link:
            can_place_check = True
            if self.moved_link["ongrid"]:
                for tile_loc in self.selector.link:
                    if (self.moved_link["ongrid"][tile_loc] in self.tilemap.tilemap[self.current_layer] and
                            self.moved_link["ongrid"][tile_loc] not in self.moved_link["ongrid"]):
                        can_place_check = False
                        break
            elif self.moved_link["offgrid"]:
                for tile_loc in self.selector.link:
                    if self.current_layer in self.tilemap.offgrid_tiles:
                        if (self.moved_link["offgrid"][tile_loc] in self.tilemap.offgrid_tiles[self.current_layer] and
                                self.moved_link["offgrid"][tile_loc] not in self.moved_link["offgrid"]):
                            can_place_check = False
                            break

            if self.clicking and event.type == pygame.MOUSEBUTTONUP:
                current_state = self.create_snapshot()
                # Simply comparing the dicts detects if anything changed
                if current_state != self.temp_snapshot:
                    self.save_action()


                if event.button == 1 and self.selector.link:
                    if can_place_check:
                        tilemap_tmp = {}
                        offgrid_tmp = {}
                        if self.moved_link["ongrid"]:

                            for tile_loc in self.selector.link:
                                space = self.check_tile_space(tile_loc)
                                if space == "tilemap":
                                    tilemap_tmp[tile_loc] = self.tilemap.tilemap[self.current_layer][tile_loc]
                                    del self.tilemap.tilemap[self.current_layer][tile_loc]
                                else:
                                    offgrid_tmp[tile_loc] = self.tilemap.offgrid_tiles[self.current_layer][tile_loc]
                                    del self.tilemap.offgrid_tiles[self.current_layer][tile_loc]


                            for tile_loc in self.selector.link:
                                new_loc = self.moved_link["ongrid"][tile_loc]
                                if tile_loc in tilemap_tmp:
                                    tmp = tilemap_tmp[tile_loc]

                                else:  # <=> tile_loc in self.tilemap.offgrid_tiles[self.current_layer]
                                    tmp = offgrid_tmp[tile_loc]
                                    pos = [int(float(val)) for val in new_loc.split(";")]
                                    new_loc = f"{pos[0]};{pos[1]}"

                                if self.current_layer not in self.tilemap.tilemap:
                                    self.tilemap.tilemap[self.current_layer] = {}

                                self.tilemap.tilemap[self.current_layer][new_loc] = tmp

                            if self.current_layer in self.tilemap.links:
                                for link in self.tilemap.links[self.current_layer]:
                                    edited_link = link.copy()
                                    for tile_loc in link:
                                        if tile_loc in self.moved_link["ongrid"]:
                                            edited_link.remove(tile_loc)
                                            edited_link.append(self.moved_link["ongrid"][tile_loc])
                                    if edited_link != link:
                                        self.tilemap.links[self.current_layer].remove(link)
                                        self.tilemap.links[self.current_layer].append(edited_link)

                            self.selector.link = list(self.moved_link["ongrid"].values())
                            self.selector.link_pivot = self.selector.get_link_pivot(self.selector.link)

                        elif self.moved_link["offgrid"]:
                            for tile_loc in self.selector.link:
                                space = self.check_tile_space(tile_loc)
                                if space == "tilemap":
                                    tilemap_tmp[tile_loc] = self.tilemap.tilemap[self.current_layer][tile_loc]
                                    del self.tilemap.tilemap[self.current_layer][tile_loc]
                                else:
                                    offgrid_tmp[tile_loc] = self.tilemap.offgrid_tiles[self.current_layer][tile_loc]
                                    del self.tilemap.offgrid_tiles[self.current_layer][tile_loc]

                            for tile_loc in self.selector.link:
                                new_loc = self.moved_link["offgrid"][tile_loc]
                                if tile_loc in tilemap_tmp:
                                    tmp = tilemap_tmp[tile_loc]
                                else:  # <=> tile_loc in self.tilemap.offgrid_tiles[self.current_layer]
                                    tmp = offgrid_tmp[tile_loc]

                                if self.current_layer not in self.tilemap.offgrid_tiles:
                                    self.tilemap.offgrid_tiles[self.current_layer] = {}
                                self.tilemap.offgrid_tiles[self.current_layer][new_loc] = tmp

                            if self.current_layer in self.tilemap.links:
                                for link in self.tilemap.links[self.current_layer]:
                                    edited_link = link.copy()
                                    for tile_loc in link:
                                        if tile_loc in self.moved_link["offgrid"]:
                                            edited_link.remove(tile_loc)
                                            edited_link.append(self.moved_link["offgrid"][tile_loc])
                                    if edited_link != link:
                                        self.tilemap.links[self.current_layer].remove(link)
                                        self.tilemap.links[self.current_layer].append(edited_link)

                            self.selector.link = list(self.moved_link["offgrid"].values())
                            self.selector.link_pivot = self.selector.get_link_pivot(self.selector.link)


                    self.moved_link = {"ongrid": {}, "offgrid": {}}

    def handle_selection_tool(self, event):
        self.selector.handle_event(event)

    def handle_map_editor(self, event):


        if self.ui.toolbar_rect.collidepoint(self.mpos) or self.ui.assets_section_rect.collidepoint(self.mpos):
            self.clicking = False

        if self.mpos_in_mainarea:
            match self.current_tool:
                case "Brush":
                    self.handle_brush_tool()
                case "Eraser":
                    self.handle_eraser_tool()
                case "Selection":
                    self.handle_selection_tool(event)
                case "Move":
                    self.handle_move_tool(event)

        if event.type == pygame.MOUSEWHEEL:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                self.zoom -= 0.1 * event.y
                self.zoom = max(0.2, min(self.zoom, 8))
            else:
                self.tile_variant = (self.tile_variant + event.y) % len(
                    self.assets[self.tile_type])
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (1, 3):  # Left or Right click
                self.temp_snapshot = self.create_snapshot()

            if event.button == 1:
                self.clicking = True
                self.mpos_scaled_onclick = (self.mpos_scaled[0] + self.scroll[0], self.mpos_scaled[1] + self.scroll[1])
            if event.button == 3:
                self.right_clicking = True
        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:

                if event.key == pygame.K_g:
                    self.state = "PlayTest"
                    self.zoom = 1
                    self.playtest.display = pygame.Surface((480 * self.zoom, 300 * self.zoom))
                    self.playtest.SCREEN_WIDTH, self.playtest.SCREEN_HEIGHT = self.screen.get_size()
                    self.playtest.load_settings()
                    self.playtest.load_level(self.level_id)

                if event.key == pygame.K_u:
                    self.ignore_links = not self.ignore_links

                if event.key == pygame.K_w:
                    self.undo()
                if event.key == pygame.K_y:
                    self.redo()
                if event.key == pygame.K_DOWN:
                    if self.current_layer == "0":
                        print("Layer 0, can't go down")
                    else:
                        self.tilemap.tilemap[self.current_layer], self.tilemap.tilemap[
                            str(int(self.current_layer) - 1)] \
                            = self.tilemap.tilemap[str(int(self.current_layer) - 1)], \
                            self.tilemap.tilemap[self.current_layer]
                        self.current_layer = str(int(self.current_layer) - 1)
                        print(f"Current layer moved to layer {self.current_layer}")
                if event.key == pygame.K_UP:
                    if self.tilemap.tilemap[self.current_layer] == {} and str(
                            int(self.current_layer) + 1) not in self.tilemap.tilemap:
                        print("This layer is the last layer, can't go up")
                    else:
                        self.tilemap.tilemap[self.current_layer], self.tilemap.tilemap[
                            str(int(self.current_layer) + 1)] \
                            = self.tilemap.tilemap[str(int(self.current_layer) + 1)], \
                            self.tilemap.tilemap[self.current_layer]
                        self.current_layer = str(int(self.current_layer) + 1)
                        print(f"Current layer moved to layer {self.current_layer}")
                if event.key == pygame.K_d:
                    self.selector.link = []
            else:

                if event.key == pygame.K_i and not self.holding_i:
                    self.holding_i = True
                if event.key == pygame.K_DOWN:
                    if self.current_layer == "0":
                        print("Layer 0, can't make any new layer under this one")
                    else:
                        self.current_layer = str(int(self.current_layer) - 1)
                        self.selector.link = []
                        print(f"Current layer : {self.current_layer}")
                    if self.current_layer not in self.tilemap.tilemap:
                        self.tilemap.tilemap[self.current_layer] = {}
                if event.key == pygame.K_UP:
                    if int(self.current_layer) + 1 == len(self.tilemap.tilemap.keys()) and \
                            self.tilemap.tilemap[self.current_layer] == {}:
                        print("This layer is empty, can't make any new layer")
                    else:
                        self.current_layer = str(int(self.current_layer) + 1)
                        self.selector.link = []
                        print(f"Current layer : {self.current_layer}")

                    if self.current_layer not in self.tilemap.tilemap:
                        self.tilemap.tilemap[self.current_layer] = {}
                if event.key == pygame.K_TAB and not self.holding_tab:
                    self.showing_all_layers = not self.showing_all_layers
                    self.holding_tab = True
                if event.key == pygame.K_LSHIFT:
                    self.shift = True
                # Show camera setup zones
                if event.key == pygame.K_b and not self.holding_b:
                    self.current_tool = "Brush"
                    self.rotation = 0
                    self.holding_b = True
                if event.key == pygame.K_e:
                    self.current_tool = "Eraser"
                    self.rotation = 0

                if event.key == pygame.K_q:
                    self.movement[0] = True
                if event.key == pygame.K_d:
                    self.movement[1] = True
                if event.key == pygame.K_z:
                    self.movement[2] = True
                if event.key == pygame.K_s:
                    self.movement[3] = True

                if event.key == pygame.K_g:
                    self.ongrid = not self.ongrid
                if event.key == pygame.K_t:
                    self.tilemap.autotile(self.current_layer)
                    self.save_action()
                if event.key == pygame.K_o:
                    self.level_manager.full_save()

                if event.key == pygame.K_c:
                    print((self.tile_pos[0] * 16, self.tile_pos[1] * 16))
                if event.key == pygame.K_r:
                    self.rotation = (self.rotation + 1) % 4
                # Unused key
                if event.key == pygame.K_y and not self.holding_y:
                    pass
                # Shortcut for placing camera setup
                if event.key == pygame.K_k:
                    self.tilemap.tilemap[self.current_layer][
                        str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])] = {
                        'type': "camera_setup",
                        'pos': self.tile_pos
                    }
                    tile = self.tilemap.tilemap[self.current_layer][
                        str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])]
                    tile_category = self.get_infos_tile_category(tile)
                    self.setup_edit_window(tile_category, tile)
                    self.save_action()
                # Shortcut for placing transitions
                if event.key == pygame.K_p:
                    dest = "0"  # Default value
                    self.tilemap.tilemap[self.current_layer][
                        str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])] = {
                        'type': "transition",
                        'variant': self.tile_variant,
                        'pos': self.tile_pos,
                        'destination': dest,
                        'dest_pos': [0, 0]}
                    tile = self.tilemap.tilemap[self.current_layer][
                        str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])]
                    tile_category = self.get_infos_tile_category(tile)
                    self.setup_edit_window(tile_category, tile)
                    self.save_action()
                # Shortcut for placing checkpoints
                if event.key == pygame.K_j:
                    self.tilemap.tilemap[self.current_layer][
                        str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])] = {
                        'type': "checkpoint",
                        'variant': 0,
                        'pos': self.tile_pos,
                        'state': 0
                    }
                    self.save_action()

                if event.key == pygame.K_DELETE:
                    self.selector.delete_link()

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_y:
                self.holding_y = False
            if event.key == pygame.K_b:
                self.holding_b = False
            if event.key == pygame.K_i:
                self.holding_i = False
            if event.key == pygame.K_q:
                self.movement[0] = False
            if event.key == pygame.K_d:
                self.movement[1] = False
            if event.key == pygame.K_z:
                self.movement[2] = False
            if event.key == pygame.K_s:
                self.movement[3] = False
            if event.key == pygame.K_TAB:
                self.holding_tab = False
            if event.key == pygame.K_LSHIFT:
                self.shift = False

    def render_brush_tool(self):
        current_tile_img = self.assets[self.tile_type][self.tile_variant].copy()
        current_tile_img.set_alpha(100)
        current_tile_img = pygame.transform.rotate(current_tile_img, self.rotation * -90)

        if self.ongrid:
            self.display.blit(current_tile_img, (self.tile_pos[0] * self.tilemap.tile_size - self.scroll[0],
                                                 self.tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
        else:
            self.display.blit(current_tile_img, self.mpos_scaled)

    def render_move_tool(self):
        grid = "ongrid"
        if self.moved_link["offgrid"]:
            grid = "offgrid"

        if self.moved_link[grid]:
            self.tilemap.set_render_filter(self.selector.link, 0)

            for old_loc, loc in self.moved_link[grid].items():
                x, y = (float(val) for val in loc.split(";"))
                if old_loc in self.tilemap.tilemap[self.current_layer]:
                    tile_id, variant, rot, flip_h, flip_v = self.tilemap.tile_manager.unpack_tile(
                        self.tilemap.tilemap[self.current_layer][old_loc]
                    )
                else:
                    tile_id, variant, rot, flip_h, flip_v = self.tilemap.tile_manager.unpack_tile(
                        self.tilemap.offgrid_tiles[self.current_layer][old_loc]
                    )

                tile_img = self.tilemap.tile_manager.get_tile_img(tile_id, variant)
                if grid == "ongrid":
                    draw_pos = (x * self.tilemap.tile_size - self.scroll[0], y * self.tilemap.tile_size - self.scroll[1])
                else:
                    draw_pos = (x - self.scroll[0], y - self.scroll[1])

                self.display.blit(tile_img, draw_pos)

    def render_selection_tool(self):
        self.selector.draw(self.display)

    def render_map_editor(self):
        match self.current_tool:
            case "Brush":
                self.render_brush_tool()
            case "Selection":
                self.render_selection_tool()
            case "Move":
                self.render_move_tool()
        self.render_map()
        self.render_display()
        self.ui.draw()

    def render_map(self):
        self.scroll[0] += (self.movement[1] - self.movement[0]) * 8
        self.scroll[1] += (self.movement[3] - self.movement[2]) * 8
        render_scroll = (int(self.scroll[0]), int(self.scroll[1]))


        self.tilemap.set_render_filter(self.selector.link, (152, 242, 255, 50))

        self.tilemap.render(self.display, offset=render_scroll,
                            precise_layer=self.current_layer if not self.showing_all_layers else None,
                            with_player=False)

        self.tilemap.render_filters = {}

    def render_display(self):
        changing_size = False
        screenshot = self.screen.copy()

        if self.display.get_size() != (int(480 * self.zoom), int(300 * self.zoom)):
            self.display = pygame.Surface((480 * self.zoom, 300 * self.zoom))
            changing_size = True

        scaled_display = pygame.transform.scale(self.display, self.screen.get_size())

        self.screen.blit(scaled_display, (0, 0))

        if changing_size:
            self.screen.blit(screenshot, (0, 0))


    def run(self):
        while True:
            match self.state:
                case "MapEditor":
                    self.display.fill((0, 0, 0))
                    self.mpos_update()
                    for event in pygame.event.get():
                        if self.current_tool == "LevelSelector":
                            pass
                        else:
                            self.handle_map_editor(event)
                        self.ui.handle_ui_event(event)

                        if event.type == pygame.MOUSEBUTTONUP:
                            if event.button == 1:
                                self.clicking = False
                                self.waiting_for_click_release = False
                            if event.button == 3:
                                self.right_clicking = False
                            if event.button in (1, 3) and self.temp_snapshot:
                                current_state = self.create_snapshot()
                                # Simply comparing the dicts detects if anything changed
                                if current_state != self.temp_snapshot:
                                    self.save_action()
                        if event.type == pygame.KEYUP:
                            if event.key == pygame.K_LSHIFT:
                                self.shift = False
                        if event.type == pygame.VIDEORESIZE:
                            # Update screen dimensions
                            self.screen_width = max(event.w, 480)  # Minimum width
                            self.screen_height = max(event.h, 300)  # Minimum height
                            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height),
                                                                  pygame.RESIZABLE)
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()

                    self.render_map_editor()
                    self.clock.tick(60)

                case "PlayTest":
                    self.playtest.run()
            pygame.display.update()

class UI:
    TOOLBAR_COLOR = (64,64,64)
    ASSETS_SECTION_COLOR = (32,32,32)
    PADDING = 5

    def __init__(self, editor_instance):
        self.editor = editor_instance
        self.editor_previous_tool = self.editor.current_tool
        self.screen = editor_instance.screen
        self.screen_width, self.screen_height = self.screen.get_size()

        self.level_carousel = None

        self.title_font = load_game_font(24)
        self.buttons_font = load_game_font(18)

        self.state = "Editor"

        self.toolbar_width = self.screen_width * 5 / 96
        self.toolbar_default_width = self.screen_width * 5 / 96
        self.toolbar_rect = pygame.Rect(self.screen_width - self.toolbar_default_width, 0,self.screen_width * 5 / 96,self.screen_height)
        self.toolbar_buttons_width = self.toolbar_rect.width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_rect.width * (3 / 5)
        self.tools_buttons = []
        self.tools_buttons_labels = ["Brush", "Eraser", "Selection", "Move", "Properties", "LevelSelector"]
        self.check_buttons = []
        self.check_buttons_labels = ["On grid"]
        self.on_selection_buttons = []
        self.on_selection_buttons_labels = ["Plus","Link","Unlink","IgnoreLinks"]
        #self.tools_buttons_images = {tool: load_image(f"ui/{tool.lower()}.png") for tool in self.tools_buttons_labels}
        self.buttons_images = {"Brush": load_image("ui/brush.png"),
                               "Eraser": load_image("ui/eraser.png"),
                               "Selection": load_image("ui/selection.png"),
                               "Move": load_image("ui/move.png"),
                               "LevelSelector": load_image("ui/level_selector.png"),
                               "On grid": load_image("ui/ongrid.png"),
                               "Properties" : load_image("ui/properties.png"),
                               "Link": load_image("ui/link.png"),
                               "Unlink": load_image("ui/unlink.png"),
                               "Plus":load_image("ui/plus.png"),
                               "IgnoreLinks": load_image("ui/skull.png")}

        self.spectial_buttons_labels = {"Brush": [],
                                        "Eraser": [],
                                        "Selection": []}

        self.selection_rect = pygame.Rect(0,0,0,0)
        self.selecting = False
        self.selection_pos = None



        self.assets_section_default_width = self.screen_width * 20/96
        self.assets_section_rect = pygame.Rect(self.screen_width - self.toolbar_rect.width - self.assets_section_default_width,
                                               self.screen_height - self.screen_width * 25/96,
                                               self.screen_width * 20 / 96, self.screen_width * 25 / 96)

        self.current_category = 0
        self.categories = editor_instance.categories
        self.current_category_name = list(self.editor.categories.keys())[self.current_category]

        self.assets_section_buttons_width = self.assets_section_rect.width * (1 / 6)
        self.assets_section_buttons_height = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons = []
        self.assets_section_buttons_labels = ["Previous", "Next"]
        self.assets_section_buttons_images = {"Previous": pygame.transform.flip(load_image("ui/next.png"), True, False),
                                              "Next": load_image("ui/next.png")}
        self.assets_button_width = self.assets_section_rect.width * (1 / 10)
        self.assets_button_height = self.assets_section_rect.width * (1 / 10)
        self.assets_buttons = []

        self.properties_section_default_width = self.screen_width * 20 / 96
        self.properties_section_rect = pygame.Rect(
            self.screen_width - self.toolbar_rect.width - self.properties_section_default_width,
            self.screen_height - self.screen_width * 25 / 96,
            self.screen_width * 20 / 96, self.screen_width * 25 / 96)

        self.properties_section_buttons_width = self.properties_section_rect.width * (1 / 8)
        self.properties_section_buttons_height = self.properties_section_rect.width * (1 / 8)
        self.properties_section_buttons = []


        self.init_buttons()
        self.closing = False

    def init_buttons(self):
        self.tools_buttons = []
        self.assets_section_buttons = []
        self.check_buttons = []
        self.on_selection_buttons = []

        button_x, button_y = self.toolbar_rect.width/2, self.toolbar_rect.width/2
        for label in self.tools_buttons_labels:
            button = EditorButton(label, self.buttons_images[label],
                                  (button_x, button_y),
                                  self.toolbar_buttons_width,
                                  self.toolbar_buttons_height,
                                  (64,64,64),
                                  self.screen_width / self.editor.SW)

            if label == self.tools_buttons_labels[-2]:
                button_y = self.screen_height - 1*self.toolbar_buttons_height
            else:
                button_y += self.toolbar_buttons_height + (self.PADDING/self.editor.SH)*self.screen_height
            self.tools_buttons.append(button)

        button_x, button_y = (30/self.editor.SW)*self.screen_width, (20/self.editor.SH)*self.screen_height
        for label in self.assets_section_buttons_labels:
            button = EditorButton(label, self.assets_section_buttons_images[label], (button_x, button_y), self.assets_section_buttons_width, self.assets_section_buttons_height, (24,24,24), self.screen_width/self.editor.SW)
            button_x = self.assets_section_rect.width - button_x
            self.assets_section_buttons.append(button)

        self.level_carousel = LevelCarousel(self.screen_width / 2, self.screen_height / 2,
                                            (self.screen_width * 5 / 16, self.screen_height * 3 / 10),
                                            self.editor.active_maps + [None])


        button_x,button_y = self.toolbar_rect.width/2, self.toolbar_rect.height-3*self.toolbar_buttons_height
        for label in self.check_buttons_labels:
            button = EditorButton(label, self.buttons_images[label],
                                  (button_x, button_y),
                                  0.7*self.toolbar_buttons_width,
                                  0.7*self.toolbar_buttons_height,
                                  (64, 64, 64),

                                  resize=0.8)
            button_y -= 0.7*self.toolbar_buttons_height - (self.PADDING/self.editor.SH)*self.screen_height
            self.check_buttons.append(button)

        self.init_assets_buttons(self.categories)

        button_x,button_y = self.toolbar_rect.x - self.toolbar_rect.width/2 , self.toolbar_rect.width/2
        for label in self.on_selection_buttons_labels:
            color = ()
            if label == "Plus":
                button_y = self.toolbar_buttons_height
                color = (42, 90, 57)
            if label == "Link":
                button_y = self.screen_height - self.toolbar_buttons_height
                color = (98, 171, 212)
            if label == "Unlink":
                color = (235, 217, 103)
            if label == "IgnoreLinks":
                color = (255,0,0)
            if color:
                #TODO new button type for IgnoreLinks button, which can toggled (clicked while activated or not)
                button = IconButton(label,self.buttons_images[label],(button_x, button_y),self.toolbar_buttons_width,
                           self.toolbar_buttons_height,color,resize=0.8)
                button_y -= self.toolbar_buttons_height + 5*(self.PADDING/self.editor.SH)*self.screen_height
                self.on_selection_buttons.append(button)


    def init_assets_buttons(self, categories):
        self.assets_buttons = []

        initial_x = (20 / self.editor.SW) * self.screen_width

        button_x, button_y = initial_x, (60 / self.editor.SH) * self.screen_height
        for tile in categories[self.current_category_name]:
            img = categories[self.current_category_name][tile].copy()[0]
            button = EditorButton(tile, img, (button_x, button_y), self.assets_button_width, self.assets_button_height,
                                  (24, 24, 24),resize=0.9)
            if button_x + self.assets_button_width + self.PADDING*self.screen_width/self.editor.SW > self.assets_section_rect.width - self.assets_button_width:
                button_y = (button_y + self.assets_button_height + self.PADDING*self.screen_height/self.editor.SH %
                            self.screen_height)
                button_x = initial_x
            else:
                button_x = ((button_x + self.assets_button_width + self.PADDING*self.screen_width/self.editor.SW) %
                            (self.assets_section_rect.width - self.assets_button_width))
            if button_x < initial_x:
                button_x = initial_x
            if button_y + self.assets_button_height/2 > self.assets_section_rect.height:
                self.assets_section_rect.height += self.assets_button_height + self.PADDING*self.screen_height/self.editor.SH
            self.assets_buttons.append(button)

    def render_toolbar(self):

        overlay = pygame.Surface((self.toolbar_rect.width, self.toolbar_rect.height))
        overlay.fill(self.TOOLBAR_COLOR)

        for button in self.tools_buttons:
            button.draw(overlay)
            if button.label == self.editor.current_tool:
                button.activated = True
            else:
                button.activated = False
        for button in self.check_buttons:
            button.draw(overlay)
            if button.label == "On grid" and self.editor.ongrid:
                button.activated = True
            else:
                button.activated = False
        self.toolbar_rect.x,self.toolbar_rect.y = (self.screen_width - self.toolbar_rect.width, 0)

        self.screen.blit(overlay, (self.toolbar_rect.x,self.toolbar_rect.y))

    def render_assets_section(self, x, y):
        if self.assets_section_rect.width == 0 and not self.closing:
            self.reload_assets_section_rect()
        self.assets_section_rect.x,self.assets_section_rect.y = x,y
        overlay = pygame.Surface((self.assets_section_rect.width, self.assets_section_rect.height))
        overlay.fill(self.ASSETS_SECTION_COLOR)

        category_text = self.title_font.render(self.current_category_name, True, (255, 255, 255))
        category_x = (self.assets_section_rect.width - category_text.get_width())/2
        category_y = (10 / self.editor.SH) * self.screen_height
        overlay.blit(category_text, (category_x, category_y))

        for button in self.assets_buttons:
            button.draw(overlay)
            if button.label == self.editor.tile_type:
                button.activated = True
            else:
                button.activated = False

        for button in self.assets_section_buttons:
            button.draw(overlay)

        self.screen.blit(overlay, self.assets_section_rect.topleft)

    def render_level_selector(self):
        overlay = create_rect_alpha((0, 0, 0), (0, 0, self.screen_width, self.screen_height), 100)
        self.level_carousel.draw(overlay)
        self.level_carousel.update()
        self.screen.blit(overlay, (0, 0))

    def render_on_selection(self, centerx):
        for button in self.on_selection_buttons:

            match button.label:
                case "Link":
                    if len(self.editor.selector.link) > 1:
                        button.activated = True
                    else:
                        button.activated = False

                case "Plus":
                    if len(self.editor.selector.link) >= 1:
                        button.activated = True
                    else:
                        button.activated = False

                case "IgnoreLinks":
                    pass

                case _ :
                    button.activated = False
                    if self.editor.current_layer in self.editor.tilemap.links:
                        for link in self.editor.tilemap.links[self.editor.current_layer]:
                            if set(link).issubset(set(self.editor.selector.link)):
                                button.activated = True
                                break

            button.rect.centerx = centerx
            button.draw(self.screen)


    def check_closed(self):
        if self.closing:
            self.toolbar_rect.width = max(0, self.toolbar_rect.width - 5)
            match self.editor.current_tool:
                case "Brush":
                    self.assets_section_rect.width = max(0, self.assets_section_rect.width - 20)
        else:
            self.toolbar_rect.width = min(self.toolbar_default_width, self.toolbar_rect.width + 5)
            match self.editor.current_tool:
                case "Brush":
                    self.assets_section_rect.width = min(self.assets_section_default_width, self.assets_section_rect.width + 20)

    def reload(self):
        self.screen_width, self.screen_height = self.editor.screen.get_size()

        self.title_font = load_game_font(int((24/self.editor.SH)*self.screen_height))
        self.buttons_font = load_game_font(int((18/self.editor.SH)*self.screen_height))

        self.toolbar_default_width = self.screen_width * 5 / 96
        self.toolbar_rect = pygame.Rect(self.screen_width - self.toolbar_default_width, 0, self.screen_width * 5 / 96,
                                        self.screen_height)
        self.toolbar_default_width = self.screen_width * 5/96
        self.toolbar_buttons_width = self.toolbar_rect.width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_rect.width * (3 / 5)


        self.assets_section_default_width = self.screen_width * 20 / 96
        self.reload_assets_section_rect()
        self.assets_section_buttons_width = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons_height = self.assets_section_rect.width * (1 / 8)
        self.assets_button_width = self.assets_section_rect.width * (1 / 10)
        self.assets_button_height = self.assets_section_rect.width * (1 / 10)
        self.init_assets_buttons(self.categories)

        self.init_buttons()

    def reload_assets_section_rect(self):
        self.assets_section_rect = pygame.Rect(
            self.screen_width - self.toolbar_rect.width - self.assets_section_default_width,
            self.screen_height - self.screen_width * 25 / 96,
            self.screen_width * 20 / 96, self.screen_width * 25 / 96)

    def reload_assets_section(self):
        categories = self.categories
        self.current_category = 0
        self.current_category_name = list(categories.keys())[self.current_category]
        self.init_assets_buttons(categories)

    def clear_sections_rect(self):
        if self.editor.current_tool != "Brush":
            if self.assets_section_rect.width:
                self.assets_section_rect.width = 0

    def draw(self):

        self.clear_sections_rect()
        self.check_closed()
        self.render_toolbar()
        match self.editor.current_tool:
            case "Brush":
                self.render_assets_section(self.screen_width - self.toolbar_rect.width  - self.assets_section_rect.width,
                                   self.screen_height - self.assets_section_rect.height)
            case "LevelSelector":
                    self.render_level_selector()
            case "Properties":
                pass
            case "Selection" | "Move":
                self.render_on_selection(self.toolbar_rect.x - 30*(self.screen_width/self.editor.SW))

    def handle_ui_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.closing = not self.closing
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                print("Saving to disk...")
                self.editor.level_manager.full_save()
        if event.type == pygame.VIDEORESIZE:
            self.reload()
            match self.editor.current_tool:
                case "Brush":
                    self.reload_assets_section_rect()
        if event.type == pygame.QUIT:
            pygame.quit()
        self.handle_toolbar_event(event)
        match self.editor.current_tool:
            case "Brush":
                self.handle_assets_section_event(event)
            case "LevelSelector":
                self.handle_level_selector_event(event)
            case "Properties":
                pass
            case "Selection"|"Move":
                self.handle_on_selection_event(event)

    def handle_toolbar_event(self, event):
        for button in self.tools_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width, 0)):
                self.editor.rotation = 0
                self.editor_previous_tool = self.editor.current_tool
                self.editor.current_tool = button.label
        for button in self.check_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width, 0)):
                match button.label:
                    case "On grid":
                        self.editor.ongrid = not self.editor.ongrid

    def handle_assets_section_event(self, event):
        categories = self.categories
        for button in self.assets_section_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                                                  self.screen_height - self.assets_section_rect.height)):
                if button.label == "Next":
                    self.current_category = (self.current_category + 1) % len(categories)
                elif button.label == "Previous":
                    self.current_category = (self.current_category - 1) % len(categories)
                button.activated = True
                self.current_category_name = list(categories.keys())[self.current_category]
                self.init_assets_buttons(categories)
            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION and not button.is_selected(
                    event,
                    offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                            self.screen_height - self.assets_section_rect.height)):
                button.activated = False
        for button in self.assets_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                                                  self.screen_height - self.assets_section_rect.height)):
                self.editor.rotation = 0
                self.editor.tile_type = button.label
                self.editor.tile_variant = 0

    def handle_level_selector_event(self, event):
        level_selector_state = self.level_carousel.handle_event(event)
        match level_selector_state:
            case "AddLevel":
                new_id = self.editor.level_manager.get_next_file_id()

                if new_id not in self.editor.active_maps:
                    self.editor.active_maps.append(new_id)
                # Refresh carousel mapping
                self.level_carousel.levels = self.editor.active_maps + [None]
                self.level_carousel.selected = self.editor.active_maps.index(new_id)

                self.editor.level_manager.change_level(new_id)

                self.reload_assets_section()
                self.editor.current_tool = self.editor_previous_tool
            case "DeleteLevel":
                deleted_id = self.level_carousel.levels[self.level_carousel.selected]
                self.level_carousel.levels.pop(self.level_carousel.selected)
                self.editor.level_manager.delete_map(deleted_id)
                self.level_carousel.levels = self.editor.active_maps + [None]
                self.level_carousel.selected = max(0, self.level_carousel.selected - 1)
            case "LoadLevel":
                loaded_id = self.level_carousel.levels[self.level_carousel.selected]
                self.editor.level_manager.change_level(loaded_id)
                self.editor.current_tool = self.editor_previous_tool
                self.reload_assets_section()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.editor.current_tool = self.editor_previous_tool

    def handle_on_selection_event(self, event):
        for button in self.on_selection_buttons:
            if button.handle_event(event):
                match button.label:
                    case "Link":
                        self.editor.selector.link_link()
                    case "Unlink":
                        if self.editor.current_layer in self.editor.tilemap.links:
                            for group in self.editor.tilemap.links[self.editor.current_layer]:
                                if set(group).issubset(set(self.editor.selector.link)):
                                    self.editor.selector.unlink_link(group)
                    case "Plus":
                        self.editor.selector.add_link_to_group()
                    case "IgnoreLinks":
                        self.editor.ignore_links = True


if __name__ == "__main__":
    editor = EditorSimulation()
    editor.run()