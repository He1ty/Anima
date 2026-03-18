import sys
from sys import exception

from scripts.utils import load_image, create_rect_alpha
from scripts.button import EditorButton, LevelCarousel, EnvironmentButton, SimpleButton
from scripts.text import load_game_font
from scripts.utils import load_editor_tiles, load_tiles, load_images
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
        self.group = []

    def get_coordinates_in_rect(self, rect):
        grid = []
        for x in range(rect.left//self.editor.tile_size, rect.right//self.editor.tile_size + 1):
            for y in range(rect.top//self.editor.tile_size, rect.bottom//self.editor.tile_size + 1):
                grid.append(f"{x};{y}")

        return grid

    def get_group_in_rect(self, rect, check_offgrid=True):
        group = []
        ongrid = self.get_coordinates_in_rect(rect)
        for coordinate in ongrid:
            if coordinate in self.editor.tilemap.tilemap[self.editor.current_layer]:
                group.append(coordinate)

        if check_offgrid and self.editor.current_layer in self.editor.tilemap.offgrid_tiles:
            for coordinate in self.editor.tilemap.offgrid_tiles[self.editor.current_layer]:
                pos = list(coordinate.split(";"))
                if self.rect.left <= pos[0] <= self.rect.right or self.rect.top <= pos[1] <= self.rect.bottom:
                    group.append(coordinate)

        return group

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

    def handle_selection_rect(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 :
                if not self.rect_displayed:
                    self.rect_displayed = True
                    self.initial_pos = self.pos

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.rect_displayed = False
                self.group = self.get_group_in_rect(self.rect)

        self.rect_pos_update()

    def handle_event(self, event):
        if event:
            self.handle_selection_rect(event)

class LevelManager:
    def __init__(self, editor_instance):
        self.editor = editor_instance

    def get_env_prefix(self, env_name):
        # Converts "green_cave" to "gc", "white_space" to "ws"
        return "".join([word[0] for word in env_name.split("_")])

    def get_file_name(self, env_name, map_id):
        prefix = self.get_env_prefix(env_name)
        return f"{prefix}{map_id:03d}.json"

    def get_environment_by_id(self, map_id, environments_dict=None):
        if environments_dict is None:
            environments_dict = self.editor.environments
        for env, ids in environments_dict.items():
            if map_id in ids:
                return env
        return "white_space"

    def get_next_file_id(self):
        existing_ids = []
        # 1. Look at actual files on disk
        if os.path.exists('data/maps/'):
            for f in os.listdir('data/maps/'):
                if f.endswith('.json'):
                    match = re.search(r'\d+', f)
                    if match:
                        existing_ids.append(int(match.group()))

        # 2. Look at environments in memory (to catch unsaved creations)
        for ids in self.editor.environments.values():
            existing_ids.extend(ids)

        if not existing_ids:
            return 1
        return max(existing_ids) + 1

    def delete_map(self, level_id):
        # Remove ONLY from active maps. We leave it in editor.environments
        # so environments.json retains it if the user quits without a full_save.
        if level_id in self.editor.active_maps:
            self.editor.active_maps.remove(level_id)

        # Re-route the user to an existing level if they deleted the one they are on
        if self.editor.level == level_id:
            if self.editor.active_maps:
                self.change_level(self.editor.active_maps[-1])
            else:
                # Fallback if they deleted the very last map
                new_id = self.get_next_file_id()
                env = list(self.editor.environments.keys())[0] if self.editor.environments else "white_space"
                if env not in self.editor.environments:
                    self.editor.environments[env] = []
                self.editor.environments[env].append(new_id)
                self.editor.active_maps.append(new_id)
                self.change_level(new_id)

    def map_data_reset(self):
        env = self.get_environment_by_id(self.editor.level)
        file_name = self.get_file_name(env, self.editor.level)
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
        if self.editor.level in self.editor.active_maps:
            env = self.get_environment_by_id(self.editor.level)
            current_file_name = self.get_file_name(env, self.editor.level)

            if self.editor.tilemap.tilemap != {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}, "5": {}, "6": {}}:
                self.editor.tilemap.save(f'data/maps/{current_file_name}')

        self.editor.level = new_level_id
        self.map_data_reset()

    def load_environments(self):
        path = 'data/environments.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {"white_space": [], "green_cave": [], "blue_cave": []}

    def save_environments(self):
        with open('data/environments.json', 'w') as f:
            json.dump(self.editor.environments, f, indent=4)

    def full_save(self):
        # 1. Save current map to disk
        if self.editor.level in self.editor.active_maps:
            env = self.get_environment_by_id(self.editor.level)
            current_file_name = self.get_file_name(env, self.editor.level)
            self.editor.tilemap.save(f'data/maps/{current_file_name}')

        # 2. Re-sequence IDs sequentially for surviving active_maps
        sorted_active = sorted(self.editor.active_maps)
        id_mapping = {old_id: (index + 1) for index, old_id in enumerate(sorted_active)}

        temp_dir = 'data/maps/temp_save'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        new_environments = {k: [] for k in self.editor.environments.keys()}

        # 3. Move valid files to temp directory with new names
        for old_id in sorted_active:
            env_name = self.get_environment_by_id(old_id)
            new_id = id_mapping[old_id]

            old_file = self.get_file_name(env_name, old_id)
            new_file = self.get_file_name(env_name, new_id)

            src = f'data/maps/{old_file}'
            dst = f'{temp_dir}/{new_file}'

            if os.path.exists(src):
                shutil.copy2(src, dst)

            new_environments[env_name].append(new_id)

        # 4. Clear old files and replace with temp
        for f in os.listdir('data/maps/'):
            if f.endswith('.json'):
                os.remove(f'data/maps/{f}')

        for f in os.listdir(temp_dir):
            shutil.move(f'{temp_dir}/{f}', f'data/maps/{f}')
        os.rmdir(temp_dir)

        # 5. Overwrite the in-memory environments dict with the cleansed version
        self.editor.environments = new_environments
        self.save_environments()

        # 6. Update running active maps
        self.editor.active_maps = list(id_mapping.values())
        self.editor.level = id_mapping.get(self.editor.level, 1)

        print("Full Save Complete: Maps reordered and deleted files removed.")

class EditorSimulation:
    SW = 960
    SH = 600

    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Editor")
        self.screen_width = 960
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.display = pygame.Surface((self.screen_width / 2, self.screen_height / 2))
        self.clock = pygame.time.Clock()
        self.zoom = 1
        self.scroll = [0, 0]
        self.movement = [0, 0, 0, 0]

        self.current_tool = "Brush"
        self.level = 0
        self.current_environment = "white_space"
        self.selecting_environment_mode = False

        # Undo/Redo
        self.history = []
        self.history_index = -1
        self.max_history = 50
        self.temp_snapshot = None

        # LevelManager — doit être créé AVANT d'utiliser active_maps/environments
        self.level_manager = LevelManager(self)
        self.environments = self.level_manager.load_environments()

        # Hydrate active_maps from environments.json
        self.active_maps = []
        for ids in self.environments.values():
            self.active_maps.extend(ids)
        self.active_maps.sort()


        self.level = self.active_maps[0] if self.active_maps else 1

        self.tile_group = 0
        self.tile_variant = 0

        self.categories = load_editor_tiles(self.current_environment)
        self.assets = {}
        for tile in self.categories.values():
            self.assets.update(tile)
        self.assets.update({"spawners": load_images("player/spawner"),
                            "transition": load_images("transition")})

        self.tile_type = next(iter(self.categories[next(iter(self.categories))]))

        self.showing_all_layers = False
        self.current_layer = "0"
        self.current_category = 0

        self.tilemap = Tilemap(self)

        self.tile_size = self.tilemap.tile_size

        try:
            file_name = self.level_manager.get_file_name(self.current_environment, self.level)
            filepath = f'data/maps/{file_name}'
            self.tilemap.load(filepath)
        except FileNotFoundError:
            pass

        self.save_action()

        self.ui = UI(self)

        self.clicking = False
        self.rotation = 0
        self.state = "MapEditor"

        self.mpos = pygame.mouse.get_pos()
        self.main_area_width = self.screen_width
        self.main_area_height = self.screen_height

        scale_x = 960 / (self.screen.get_size()[0])
        scale_y = 576 / (self.screen.get_size()[1])
        self.mpos_scaled = ((self.mpos[0] / 2) * scale_x * self.zoom,
                            (self.mpos[1] / 2) * scale_y * self.zoom)

        self.mpos_in_mainarea = self.mpos[0] < self.main_area_width and self.mpos[1] < self.main_area_height

        self.ongrid = True

        self.selector = Selector(self)

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

        self.holding_i = False
        self.holding_b = False
        self.holding_y = False
        self.holding_tab = False

    def create_snapshot(self):
        # Creates a deep copy of the current map state
        return {
            'tilemap': copy.deepcopy(self.tilemap.tilemap)
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
        self.categories = {}
        self.categories = load_editor_tiles(self.level_manager.get_environment_by_id(self.level))
        self.current_category = 0
        self.tile_type = next(iter(self.categories[next(iter(self.categories))]))

    def get_assets(self):
        self.assets = {}
        for tile in self.categories.values():
            self.assets.update(tile)
        self.assets.update({"spawners": load_images("player/spawner"),
                            "transition": load_images("transition")})

    def sizeofmaps(self):
        return len(self.active_maps)

    def reload(self):
        self.scroll = [0, 0]
        self.get_categories()
        self.get_assets()

        self.history = []
        self.history_index = -1
        self.save_action()  # Save the initial state (Index 0)

    def mpos_update(self):
        self.mpos = pygame.mouse.get_pos()
        self.main_area_width = self.screen_width
        self.main_area_height = self.screen_height
        if self.mpos[0] < self.main_area_width and self.mpos[
            1] < self.main_area_height:  # Only if mouse is over main area
            # Scale mouse position to account for display scaling
            scale_x = 960 / (self.screen.get_size()[0])
            scale_y = 576 / (self.screen.get_size()[1])
            self.mpos_scaled = ((self.mpos[0] / 2) * scale_x * self.zoom,
                                (self.mpos[1] / 2) * scale_y * self.zoom)
            self.tile_pos = (int((self.mpos_scaled[0] + self.scroll[0]) // self.tilemap.tile_size),
                             int((self.mpos_scaled[1] + self.scroll[1]) // self.tilemap.tile_size))
        else:
            # Default values if out of bounds to prevent crash
            self.tile_pos = (0, 0)
            self.mpos_scaled = (0, 0)

        self.mpos_in_mainarea = self.mpos[0] < self.main_area_width and self.mpos[1] < self.main_area_height

    def handle_map_editor(self, event):


        if self.ui.toolbar_rect.collidepoint(self.mpos) or self.ui.assets_section_rect.collidepoint(self.mpos):
            self.clicking = False
        if self.mpos_in_mainarea:
            match self.current_tool:
                case "Brush":
                    if self.clicking:
                        if self.ongrid:
                            if "Activators" in self.categories:
                                if self.tile_type in self.categories["Activators"] and self.current_layer not in \
                                        self.tilemap.layers["activators"]:
                                    self.tilemap.layers["activators"] += [self.current_layer]

                            if "fake" in self.tile_type and self.current_layer not in \
                                    self.tilemap.layers["fake_tiles"]:
                                self.tilemap.layers["fake_tiles"] += [self.current_layer]

                            if self.tile_type == "spawners" and self.tile_variant == 0 and not self.tilemap.extract(
                                [("spawners", 0)], keep=True):
                                self.tilemap.layers["player"] = [self.current_layer]

                            if self.tile_type == "spawners" and self.tile_variant == 0 and self.tilemap.extract(
                                [("spawners", 0)], keep=True):
                                print("Player spawner alredy placed in this map")
                            else:
                                t = self.tile_type
                                self.tilemap.tilemap[self.current_layer][str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])] = {
                                    'type': t,
                                    'variant': self.tile_variant,
                                    'pos': self.tile_pos}

                                tile = self.tilemap.tilemap[self.current_layer][
                                    str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])]

                                if "spike" in t:
                                    self.tilemap.tilemap[self.current_layer][str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])][
                                        "rotation"] = self.rotation

                                else:
                                    """
                                    for c in self.infos_per_type_per_category:
                                        if c.lower()[:-1] in t:
                                            tile_category = self.get_infos_tile_category(tile)
                                            self.setup_edit_window(tile_category, tile)
                                            break"""

                        else:
                            if self.current_layer not in self.tilemap.offgrid_tiles:
                                self.tilemap.offgrid_tiles[self.current_layer] = {}
                            self.tilemap.offgrid_tiles[self.current_layer][
                                str(self.mpos_scaled[0] + self.scroll[0]) +
                                ";"
                                + str(self.mpos_scaled[1] + self.scroll[1])] = \
                                {'type': self.tile_type,
                                 'variant': self.tile_variant,
                                 'pos': (
                                     self.mpos_scaled[0] + self.scroll[0],
                                     self.mpos_scaled[1] + self.scroll[1])}

                case "Eraser":
                    if self.clicking:
                        tile_loc = str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])
                        if tile_loc in self.tilemap.tilemap[self.current_layer]:
                            del self.tilemap.tilemap[self.current_layer][tile_loc]

                        if self.current_layer in self.tilemap.offgrid_tiles:
                            for pos in self.tilemap.offgrid_tiles[self.current_layer].copy():
                                tile = self.tilemap.offgrid_tiles[self.current_layer][pos]
                                tile_img = self.assets[tile['type']][tile['variant']]
                                tile_r = pygame.Rect(tile['pos'][0] - self.scroll[0],
                                                     tile['pos'][1] - self.scroll[1],
                                                     tile_img.get_width(),
                                                     tile_img.get_height())
                                if tile_r.collidepoint(self.mpos_scaled) or tile_r.collidepoint(
                                        self.mpos):  # Check both to be safe
                                    del self.tilemap.offgrid_tiles[self.current_layer][pos]

                case "Selection":
                    self.selector.handle_event(event)

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
            if event.button == 3:
                self.right_clicking = True
        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
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
            else:
                if event.key == pygame.K_i and not self.holding_i:
                    self.edit_properties_mode_on = not self.edit_properties_mode_on
                    self.holding_i = True
                if event.key == pygame.K_DOWN:
                    if self.current_layer == "0":
                        print("Layer 0, can't make any new layer under this one")
                    else:
                        self.current_layer = str(int(self.current_layer) - 1)
                        self.selector.group = []
                        print(f"Current layer : {self.current_layer}")
                    if self.current_layer not in self.tilemap.tilemap:
                        self.tilemap.tilemap[self.current_layer] = {}

                if event.key == pygame.K_UP:
                    if int(self.current_layer) + 1 == len(self.tilemap.tilemap.keys()) and \
                            self.tilemap.tilemap[self.current_layer] == {}:
                        print("This layer is empty, can't make any new layer")
                    else:
                        self.current_layer = str(int(self.current_layer) + 1)
                        self.selector.group = []
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
                    self.holding_b = True
                if event.key == pygame.K_e:
                    self.current_tool = "Eraser"

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
                    self.tilemap.autotile()
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

    def render_map(self):
        self.scroll[0] += (self.movement[1] - self.movement[0]) * 8
        self.scroll[1] += (self.movement[3] - self.movement[2]) * 8
        render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

        mask_opacity = 120 if self.selector.group else 255

        self.tilemap.render(self.display, offset=render_scroll,
                            precise_layer=self.current_layer if not self.showing_all_layers else None,
                            with_player=False,
                            mask_opacity=mask_opacity,
                            exception_coordinates = tuple(self.selector.group))
        
    def render_map_editor(self):
        current_tile_img = self.assets[self.tile_type][self.tile_variant].copy()
        current_tile_img.set_alpha(100)

        match self.current_tool:
            case "Brush":
                if 'spike' in self.tile_type:
                    current_tile_img = pygame.transform.rotate(current_tile_img, self.rotation * -90)
                if self.ongrid:
                    self.display.blit(current_tile_img, (self.tile_pos[0] * self.tilemap.tile_size - self.scroll[0],
                                                     self.tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
                else:
                    self.display.blit(current_tile_img, self.mpos_scaled)

            case "Selection":
                self.selector.draw(self.display)

    def render_display(self):
        changing_size = False
        screenshot = self.screen.copy()

        if self.display.get_size() != (int(480 * self.zoom), int(288 * self.zoom)):
            self.display = pygame.Surface((480 * self.zoom, 288 * self.zoom))
            changing_size = True

        scaled_display = pygame.transform.scale(self.display, self.screen.get_size())

        self.screen.blit(scaled_display, (0, 0))

        if changing_size:
            self.screen.blit(screenshot, (0, 0))

    def run(self):
        while True:
            self.mpos_update()
            for event in pygame.event.get():
                match self.state:
                    case "MapEditor":
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
                    self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.display.fill((0, 0, 0))
            match self.state:
                case "MapEditor":
                    self.render_map_editor()

            self.render_map()
            self.render_display()
            self.ui.draw()
            self.clock.tick(60)
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
        self.tools_buttons_labels = ["Brush", "Eraser", "Selection", "LevelSelector"]
        self.check_buttons = []
        self.check_buttons_labels = ["On grid"]
        #self.tools_buttons_images = {tool: load_image(f"ui/{tool.lower()}.png") for tool in self.tools_buttons_labels}
        self.buttons_images = {"Brush": load_image("ui/brush.png"),
                               "Eraser": load_image("ui/eraser.png"),
                               "Selection": load_image("ui/selection.png"),
                               "LevelSelector": load_image("ui/level_selector.png"),
                               "On grid": load_image("ui/ongrid.png")}

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
        self.current_category_name = list(self.editor.categories.keys())[self.current_category]

        self.assets_section_buttons_width = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons_height = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons = []
        self.assets_section_buttons_labels = ["Previous", "Next"]
        self.assets_section_buttons_images = {"Previous": pygame.transform.flip(load_image("ui/next.png"), True, False),
                                              "Next": load_image("ui/next.png")}
        self.assets_button_width = self.assets_section_rect.width * (1 / 10)
        self.assets_button_height = self.assets_section_rect.width * (1 / 10)
        self.assets_buttons = []

        self.environment_selector_state = False
        self.environment_selector_buttons_labels = list(self.editor.environments.keys())
        #self.environment_selection_buttons_images = {env: load_image(f"ui/{env}_palette.png") for env in self.environment_selection_buttons_labels}
        self.environment_selector_buttons_images = {env: load_image(f"ui/skull.png") for env in
                                                    self.environment_selector_buttons_labels}
        self.environment_selector_buttons = []
        self.environment_selector_buttons_width = self.screen_width * (1 / 5)
        self.environment_selector_buttons_height = self.screen_height * (1 / 4)
        self.environment_selector_confirmation_button = None
        self.selected_environment = "white_space"


        self.init_buttons()
        self.closing = False

    def init_buttons(self):
        self.tools_buttons = []
        self.assets_section_buttons = []
        self.environment_selector_buttons = []
        self.check_buttons = []

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

        button_x, button_y = ((10/self.editor.SW) * self.screen_width + self.environment_selector_buttons_width / 2,
                              (10/self.editor.SH) * self.screen_height + self.environment_selector_buttons_height / 2)
        initial_x = (10 / self.editor.SW) * self.screen_width
        for label in self.environment_selector_buttons_labels:
            button = EnvironmentButton(label,
                                       self.environment_selector_buttons_images[label],
                                       (button_x, button_y),
                                       self.environment_selector_buttons_width,
                                       self.environment_selector_buttons_height,
                                       (32, 32, 32))
            if (button_x + 10 * self.screen_width / self.editor.SW >
                    self.screen_width - self.assets_section_rect.width - 10 * self.screen_width / self.editor.SW):
                button_y = button_y + self.screen_height + 10*self.screen_height/self.editor.SH % self.screen_height
                button_x = initial_x
            else:
                button_x = (button_x + self.environment_selector_buttons_width + 10 * self.screen_width / self.editor.SW) % (
                            self.screen_width - self.environment_selector_buttons_width)
            if button_x < initial_x:
                button_x = initial_x
            if button_y + self.screen_height / 2 > self.screen_height:
                self.screen_height += self.screen_height + 10*self.screen_height/self.editor.SH

            self.environment_selector_buttons.append(button)

        button_x, button_y = (self.screen_width - 100*self.screen_width/self.editor.SW, self.screen_height - 100*self.screen_height/self.editor.SH)
        self.environment_selector_confirmation_button = SimpleButton("Confirm", self.title_font, (button_x, button_y), (0, 0, 0), (64, 64, 64))

        self.init_assets_buttons(self.editor.categories)

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

        self.screen.blit(overlay, (self.assets_section_rect.x,self.assets_section_rect.y))

    def render_level_selector(self):
        overlay = create_rect_alpha((0, 0, 0), (0, 0, self.screen_width, self.screen_height), 100)
        self.level_carousel.draw(overlay)
        self.level_carousel.update()
        self.screen.blit(overlay, (0, 0))

    def render_environment_selector(self):
        overlay = create_rect_alpha((0, 0, 0), (0, 0, self.screen_width, self.screen_height), 200)

        for button in self.environment_selector_buttons:
            button.draw(overlay)
            if button.label == self.selected_environment:
                button.activated = True
            else:
                button.activated = False

        self.environment_selector_confirmation_button.draw(overlay)

        self.screen.blit(overlay, (0, 0))

    def check_closed(self):
        if self.closing:
            self.toolbar_rect.width = max(0, self.toolbar_rect.width - 5)
            self.assets_section_rect.width = max(0, self.assets_section_rect.width - 20)
        else:
            self.toolbar_rect.width = min(self.toolbar_default_width, self.toolbar_rect.width + 5)
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
        self.assets_section_rect = pygame.Rect(
            self.screen_width - self.toolbar_rect.width - self.assets_section_default_width,
            self.screen_height - self.screen_width * 25 / 96,
            self.screen_width * 20 / 96, self.screen_width * 25 / 96)
        self.assets_section_buttons_width = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons_height = self.assets_section_rect.width * (1 / 8)
        self.assets_button_width = self.assets_section_rect.width * (1 / 10)
        self.assets_button_height = self.assets_section_rect.width * (1 / 10)
        self.init_buttons()

    def reload_assets_section(self):
        self.current_category = 0
        self.current_category_name = list(self.editor.categories.keys())[self.current_category]
        self.init_assets_buttons(self.editor.categories)

    def draw(self):

        self.check_closed()
        self.render_toolbar()
        match self.editor.current_tool:
            case "Brush":
                self.render_assets_section(self.screen_width - self.toolbar_rect.width  - self.assets_section_rect.width,
                                   self.screen_height - self.assets_section_rect.height)
            case "LevelSelector":
                if self.environment_selector_state:
                    self.render_environment_selector()
                else:
                    self.render_level_selector()

    def handle_ui_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.closing = not self.closing
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                print("Saving to disk...")
                self.editor.level_manager.full_save()
        if event.type == pygame.VIDEORESIZE:
            self.reload()
        if event.type == pygame.QUIT:
            pygame.quit()
        self.handle_toolbar_event(event)
        match self.editor.current_tool:
            case "Brush":
                self.handle_assets_section_event(event)
            case "LevelSelector":
                if self.environment_selector_state:
                    self.handle_environment_selector_event(event)
                else:
                    self.handle_level_selector_event(event)

    def handle_toolbar_event(self, event):
        for button in self.tools_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width, 0)):
                self.editor_previous_tool = self.editor.current_tool
                self.editor.current_tool = button.label
        for button in self.check_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width, 0)):
                match button.label:
                    case "On grid":
                        self.editor.ongrid = not self.editor.ongrid


    def handle_assets_section_event(self, event):
        for button in self.assets_section_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                                                  self.screen_height - self.assets_section_rect.height)):
                if button.label == "Next":
                    self.current_category = (self.current_category + 1) % len(self.editor.categories)
                elif button.label == "Previous":
                    self.current_category = (self.current_category - 1) % len(self.editor.categories)
                button.activated = True
                self.current_category_name = list(self.editor.categories.keys())[self.current_category]
                self.init_assets_buttons(self.editor.categories)
            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION and not button.is_selected(
                    event,
                    offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                            self.screen_height - self.assets_section_rect.height)):
                button.activated = False
        for button in self.assets_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                                                  self.screen_height - self.assets_section_rect.height)):
                self.editor.tile_type = button.label
                self.editor.tile_variant = 0

    def handle_environment_selector_event(self, event):
        for button in self.environment_selector_buttons:
            if button.handle_event(event):
                self.selected_environment = button.label

        if self.environment_selector_confirmation_button.handle_event(event):
            # Create the map with a globally new ID
            new_id = self.editor.level_manager.get_next_file_id()

            if self.selected_environment not in self.editor.environments:
                self.editor.environments[self.selected_environment] = []

            self.editor.environments[self.selected_environment].append(new_id)
            self.editor.active_maps.append(new_id)
            self.editor.active_maps.sort()

            # Immediately save environment changes so creations persist without full_save
            self.editor.level_manager.save_environments()

            # Refresh carousel mapping
            self.level_carousel.levels = self.editor.active_maps + [None]
            self.level_carousel.selected = self.editor.active_maps.index(new_id)

            self.editor.level_manager.change_level(new_id)

            self.reload_assets_section()
            self.editor.current_tool = self.editor_previous_tool
            self.environment_selector_state = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.environment_selector_state = False

    def handle_level_selector_event(self, event):
        level_selector_state = self.level_carousel.handle_event(event)
        match level_selector_state:
            case "AddLevel":
                self.environment_selector_state = True
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


if __name__ == "__main__":
    editor = EditorSimulation()
    editor.run()