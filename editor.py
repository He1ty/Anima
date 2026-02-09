import sys
import pygame
import json
import os
import shutil
import copy

from unicodedata import category

# Assuming these exist in your project structure
from scripts.utils import load_image, load_images, load_tiles, load_doors, load_activators, load_pickups
from scripts.tilemap import Tilemap
from scripts.button import Button
from scripts.activators import load_activators_actions

RENDER_SCALE = 2.0
SIDEBAR_WIDTH = 200
UNDERBAR_HEIGHT = 200


class LevelManager:

    def __init__(self, editor_instance):
        self.editor = editor_instance

    # Helper to get the actual File ID from the UI Level Index
    def get_file_id(self, ui_level):
        if 0 <= ui_level < len(self.editor.active_maps):
            return self.editor.active_maps[ui_level]
        return 0

    def get_next_file_id(self):
        # We look at actual files on disk to avoid conflicts
        existing_files = [int(f.split('.')[0]) for f in os.listdir('data/maps/') if f.endswith('.json')]
        # Also look at active maps in memory (in case we created one but haven't saved yet)
        all_ids = set(existing_files + self.editor.active_maps)
        if not all_ids:
            return 0
        return max(all_ids) + 1

    def delete_current_map(self):
        if not self.editor.active_maps:
            return

        # 1. Remove the current File ID from our active list
        # We don't touch the file system yet!
        del self.editor.active_maps[self.editor.level]

        # 2. Determine new level index
        # If we deleted the last map, go to the previous one
        if self.editor.level >= len(self.editor.active_maps):
            self.editor.level = max(0, len(self.editor.active_maps) - 1)

        # 3. If list is empty, create a fresh map 0 immediately
        if len(self.editor.active_maps) == 0:
            self.editor.active_maps.append(0)
            self.editor.level = 0

        # 4. Reload the view
        # We call change_level but pass the *same* index (or adjusted one),
        # which now points to a different File ID because the list shifted.
        # We need to manually trigger the load logic without saving the "deleted" map
        self.map_data_reset()

    def map_data_reset(self):
        # Load new level (using new file ID)
        new_file_id = self.get_file_id(self.editor.level)

        try:
            self.editor.tilemap.load('data/maps/' + str(new_file_id) + '.json')
        except FileNotFoundError:
            # Create the file if it doesn't exist (e.g. new map)
            with open('data/maps/' + str(new_file_id) + '.json', 'w') as f:
                json.dump({'tilemap': {}, 'tilesize': 16, 'offgrid': []}, f)
            self.editor.tilemap.load('data/maps/' + str(new_file_id) + '.json')

        self.editor.scroll = [0, 0]

        # Reload assets
        new_env = self.editor.get_environment(self.editor.level)
        self.editor.assets = self.editor.base_assets | load_tiles(new_env)
        self.editor.assets.update(load_doors('editor', new_env))
        self.editor.assets.update(load_activators(new_env))
        self.editor.assets.update(load_pickups())

        # ... (rest of function: update tile_list, ids, etc) ...
        self.editor.tile_list = list(self.editor.assets)
        self.editor.levers_ids = set()
        self.editor.doors_ids = set()
        self.editor.buttons_ids = set()
        self.editor.tps_ids = set()
        self.editor.tile_group = 0
        self.editor.tile_variant = 0


        self.editor.history = []
        self.editor.history_index = -1
        self.editor.save_action()  # Save the initial state (Index 0)

    def change_level(self, new_level):
        # Save current level (using current file ID)
        current_file_id = self.get_file_id(self.editor.level)
        if self.editor.tilemap.tilemap != {}:
            self.editor.tilemap.save('data/maps/' + str(current_file_id) + '.json')
            self.editor.save_edited_values()

        self.editor.level = new_level

        self.map_data_reset()

    def load_environments(self):
        path = 'data/environments.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                # Convert lists back to specific types if needed, json loads arrays as lists
                return json.load(f)
        else:
            # Default fallback if file doesn't exist
            return {"green_cave": [0, 1, 2], "blue_cave": []}

    def save_environments(self):
        with open('data/environments.json', 'w') as f:
            json.dump(self.editor.environments, f, indent=4)

    def full_save(self):
        # 1. Save current map state first
        current_file_id = self.get_file_id(self.editor.level)
        self.editor.tilemap.save('data/maps/' + str(current_file_id) + '.json')
        self.editor.save_edited_values()

        # 2. Create a mapping of Old File ID -> New File ID (0, 1, 2...)
        id_mapping = {}
        for index, file_id in enumerate(self.editor.active_maps):
            id_mapping[file_id] = index

        # 3. Process Files: Move everything to a temp folder first to avoid collisions
        # (e.g. renaming 2->1 while 1 exists)
        temp_dir = 'data/maps/temp_save'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Move valid active maps to temp with their NEW names
        for file_id in self.editor.active_maps:
            src = f'data/maps/{file_id}.json'
            dst = f'{temp_dir}/{id_mapping[file_id]}.json'
            if os.path.exists(src):
                shutil.copy2(src, dst)  # Copy is safer than move

        # 4. Clear the main maps folder
        for f in os.listdir('data/maps/'):
            if f.endswith('.json'):
                os.remove(f'data/maps/{f}')

        # 5. Move files back from temp
        for f in os.listdir(temp_dir):
            shutil.move(f'{temp_dir}/{f}', f'data/maps/{f}')
        os.rmdir(temp_dir)

        # 6. Rebuild Environments with new IDs
        new_environments = {k: [] for k in self.editor.environments}

        for env_name in self.editor.environments:
            for old_id in self.editor.environments[env_name]:
                # Only keep IDs that are in our active list
                if old_id in id_mapping:
                    new_id = id_mapping[old_id]
                    new_environments[env_name].append(new_id)

        self.editor.environments = new_environments
        self.save_environments()

        # 7. Reset active maps to sequential order
        self.editor.active_maps = list(range(len(self.editor.active_maps)))

        print("Full Save Complete: Maps reordered and deleted files removed.")

class Editor:

    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Editor")
        self.screen_width = 960 + SIDEBAR_WIDTH
        self.screen_height = 576
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.display = pygame.Surface((480, 288))

        self.clock = pygame.time.Clock()

        self.underbar = pygame.Surface((self.screen.get_size()[0] - SIDEBAR_WIDTH, UNDERBAR_HEIGHT))
        self.properties_window = pygame.Surface((280, 250))

        self.tile_size = 16

        self.base_assets = {
            'spawners': load_images('spawners'),
            'transition': load_images('transition'),
            'throwable': load_images('entities/elements/blue_rock/intact'),
            'checkpoint': load_images('checkpoint/deactivated'),
        }

        self.level_manager = LevelManager(self)

        self.environments = self.level_manager.load_environments()
        # This maps the UI index (0, 1, 2) to the File ID (0.json, 5.json, etc.)
        # Initially, it's just a sequence [0, 1, 2, ... N] based on existing files
        total_files = sum(1 for entry in os.listdir('data/maps/') if os.path.isfile(os.path.join('data/maps/', entry)))
        self.active_maps = list(range(total_files))

        self.selecting_environment_mode = False
        self.confirm_delete_mode = False

        # --- UNDO/REDO SYSTEM ---
        self.history = []
        self.history_index = -1
        self.max_history = 50  # Limit steps to save memory
        self.temp_snapshot = None  # Used to detect changes during mouse drags
        # ------------------------

        self.level = 0

        self.base_assets.update(load_doors('editor', self.get_environment(self.level)))


        self.categories = {}

        self.assets = self.base_assets | load_tiles(self.get_environment(self.level))
        self.assets.update(load_doors('editor', self.get_environment(self.level)))
        self.assets.update(load_activators(self.get_environment(self.level)))
        self.assets.update(load_pickups())
        self.get_categories()

        self.category_changed = False
        self.activators_categories_shown = False
        self.current_infos_tile_category = "All"
        self.selecting_infos_tile_category = False

        self.edited_tile = None
        self.edited_tile_category = None

        self.edited_type = None #Type in self.infos_per_type_per_category[edited_tile_category]
        self.edited_info = ""
        self.edited_value = None
        self.edited_value_type = None #Edited value type (python types: int, str, list...)

        # Added Transitions to the info structure
        self.infos_per_type_per_category = {
            "Levers": {
                "visual_and_door": {"visual_duration": int, "door_id": int},
                "test": {"info 1": int, "info 2": str}
            },
            "Teleporters": {
                "normal_tp": {"dest": str, "time": int},
                "progressive_tp": {"dest": str, "time": int}
            },
            "Buttons": {
                "improve_tp_progress": {"amount": int, "tp_id": int},
            },
            "Transitions": {
                "transition": {"destination": int,
                               "dest_pos": list}
            },
        }
        self.types_per_categories = {t: set(self.infos_per_type_per_category[t].keys()) for t in
                                     self.infos_per_type_per_category}

        self.movement = [False, False, False, False]

        self.tilemap = Tilemap(self, self.tile_size)

        self.showing_all_layers = False

        try:
            self.tilemap.load('data/maps/' + str(self.level) + '.json')
        except FileNotFoundError:
            pass

        self.scroll = [0, 0]

        self.tile_list = list(self.assets)
        self.tile_group = 0
        self.tile_variant = 0

        self.zoom = 1
        self.edit_properties_mode_on = False
        self.edit_background_mode_on = False
        self.make_background_invisible = False
        self.holding_i = False
        self.holding_b = False
        self.holding_y = False
        self.holding_tab = False
        self.window_mode = False
        self.showing_properties_window = False

        self.current_layer = "0"

        #Block rotation (for spikes)
        self.rotation = 0

        self.selecting_dest_pos = False
        self.return_to_level = 0
        self.waiting_for_click_release = False
        self.transition_edit_pos = None

        self.clicking = False
        self.right_clicking = False
        self.shift = False
        self.ongrid = True

        # New variable for scrolling the map list
        self.map_list_scroll = 0

        # Font for UI
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        self.current_category = 0
        self.current_category_name = []

        self.save_action()

    # --- UNDO/REDO METHODS --- #
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

    # --- --- --- --- --- --- --- --- #
    def get_environment(self, level):
        file_id = self.level_manager.get_file_id(level)

        for environment in self.environments:
            if file_id in self.environments[environment]:
                return environment
        if len(self.environments) > 0:
            return list(self.environments.keys())[0]
        return "green_cave"

    def render_environment_selection_window(self):
        # Create a centered window
        window_size = (300, 200)
        window_x = (self.screen_width - window_size[0]) // 2
        window_y = (self.screen_height - window_size[1]) // 2

        self.env_window = pygame.Surface(window_size)
        self.env_window.fill((50, 50, 50))
        pygame.draw.rect(self.env_window, (255, 255, 255), (0, 0, window_size[0], window_size[1]), 2)

        title = self.font.render("Select Environment", True, (255, 255, 255))
        self.env_window.blit(title, ((window_size[0] - title.get_width()) // 2, 10))

        mpos = pygame.mouse.get_pos()
        mpos_rel = (mpos[0] - window_x, mpos[1] - window_y)

        # List available environments
        btn_height = 30
        gap = 10
        start_y = 50

        for i, env_name in enumerate(self.environments.keys()):
            y_pos = start_y + (btn_height + gap) * i

            # Draw Button
            btn = Button(20, y_pos, window_size[0] - 40, btn_height, self.clicking)
            btn.draw(self.env_window, (70, 70, 100), mpos_rel)

            text = self.font.render(env_name, True, (255, 255, 255))
            self.env_window.blit(text, (30, y_pos + 5))

            if btn.pressed(mpos_rel):
                # CREATE NEW MAP LOGIC
                # 1. Calculate a unique file ID (so we don't overwrite existing files until save)
                new_file_id = self.level_manager.get_next_file_id()

                # 2. Add to active maps
                self.active_maps.append(new_file_id)

                # 3. Update Environments (In memory)
                self.environments[env_name].append(new_file_id)

                # 4. Switch to new level (This creates the file)
                new_level_index = len(self.active_maps) - 1
                self.level_manager.change_level(new_level_index)

                self.selecting_environment_mode = False

        # Draw Cancel Button at bottom
        cancel_y = window_size[1] - 40
        cancel_btn = Button(20, cancel_y, window_size[0] - 40, 30, self.clicking)
        cancel_btn.draw(self.env_window, (150, 50, 50), mpos_rel)
        cancel_txt = self.font.render("Cancel", True, (255, 255, 255))
        self.env_window.blit(cancel_txt, ((window_size[0] - cancel_txt.get_width()) // 2, cancel_y + 5))

        if cancel_btn.pressed(mpos_rel):
            self.selecting_environment_mode = False

        self.screen.blit(self.env_window, (window_x, window_y))

    def sizeofmaps(self):
        return len(self.active_maps)

    # New method to centralize level changing logic

    def render_sidebar(self):
        # LOGIC
        if self.category_changed and not self.clicking:
            self.category_changed = False

        # Offset mouse for sidebar interaction
        mpos = (pygame.mouse.get_pos()[0] - (self.screen.get_size()[0] - SIDEBAR_WIDTH), pygame.mouse.get_pos()[1])

        # SIDEBAR BACKGROUND
        self.sidebar = pygame.Surface((SIDEBAR_WIDTH, self.screen_height))
        self.sidebar.fill((40, 40, 40))

        # --- MAP NAVIGATION COLUMN (Right side of sidebar) ---
        map_col_width = 40
        pygame.draw.rect(self.sidebar, (30, 30, 30),
                         (SIDEBAR_WIDTH - map_col_width, 0, map_col_width, self.screen_height))

        # Get total number of maps
        total_maps = self.sizeofmaps()

        # Button settings
        btn_size = 30
        gap = 5
        start_y = 10 - self.map_list_scroll

        # 1. Render Existing Map Buttons
        for i in range(total_maps):
            y_pos = start_y + (btn_size + gap) * i

            # Only draw if visible
            if -btn_size < y_pos < self.screen_height:
                # Highlight current level
                color = (0, 200, 100) if i == self.level else (60, 60, 60)

                map_btn = Button(SIDEBAR_WIDTH - map_col_width + 5, y_pos, btn_size, btn_size, self.clicking)
                map_btn.draw(self.sidebar, color, mpos)

                # Draw Number
                num_surf = self.small_font.render(str(i), True, (255, 255, 255))
                self.sidebar.blit(num_surf, (SIDEBAR_WIDTH - map_col_width + 5 + (btn_size - num_surf.get_width()) // 2,
                                             y_pos + (btn_size - num_surf.get_height()) // 2))

                if map_btn.pressed(mpos) and i != self.level:
                    self.level_manager.change_level(i)

        # 2. Render "+" Button (Create new map)
        tool_y = start_y + (btn_size + gap) * total_maps
        if -btn_size < tool_y < self.screen_height:
            # 2. Render "+" Button (Create new map)
            add_btn = Button(SIDEBAR_WIDTH - map_col_width + 5, tool_y, btn_size, btn_size, self.clicking)
            add_btn.draw(self.sidebar, (80, 80, 150), mpos)
            plus_surf = self.small_font.render("+", True, (255, 255, 255))
            self.sidebar.blit(plus_surf, (SIDEBAR_WIDTH - map_col_width + 5 + (btn_size - plus_surf.get_width()) // 2,
                                          tool_y + (btn_size - plus_surf.get_height()) // 2))

            if add_btn.pressed(mpos):
                self.default_bg = self.screen.copy()
                self.selecting_environment_mode = True  # Trigger the popup

            # 3. Render "-" Button (Delete current map)
            # Draw it below the + button
            del_y = tool_y + btn_size + gap
            del_btn = Button(SIDEBAR_WIDTH - map_col_width + 5, del_y, btn_size, btn_size, self.clicking)
            del_btn.draw(self.sidebar, (150, 50, 50), mpos)
            minus_surf = self.small_font.render("-", True, (255, 255, 255))
            self.sidebar.blit(minus_surf, (SIDEBAR_WIDTH - map_col_width + 5 + (btn_size - minus_surf.get_width()) // 2,
                                           del_y + (btn_size - minus_surf.get_height()) // 2))

            if del_btn.pressed(mpos):
                self.level_manager.delete_current_map()

        # Separator Line between Tile selector and Map selector
        pygame.draw.line(self.sidebar, (0, 0, 0), (SIDEBAR_WIDTH - map_col_width, 0),
                         (SIDEBAR_WIDTH - map_col_width, self.screen_height))

        # --- CATEGORY HEADER (Shifted left to not overlap map nav) ---
        avail_width = SIDEBAR_WIDTH - map_col_width

        next_category = Button(avail_width - 30, 5, 24, 24, self.clicking)
        previous_category = Button(10, 5, 24, 24, self.clicking)

        if not self.category_changed:
            if next_category.pressed(mpos):
                self.current_category = (self.current_category + 1) % len(self.categories.keys())
                self.category_changed = True
            if previous_category.pressed(mpos):
                self.current_category = (self.current_category - 1) % len(self.categories.keys())
                self.category_changed = True
            self.current_category_name = list(self.categories.keys())[self.current_category]

        category_text = self.font.render(self.current_category_name, True, (255, 255, 255))
        # Center text in available space
        self.sidebar.blit(category_text, ((avail_width - category_text.get_width()) / 2, 10))

        next_category.draw(self.sidebar, (50, 50, 50), mpos)
        previous_category.draw(self.sidebar, (50, 50, 50), mpos)

        pygame.draw.line(self.sidebar, (0, 0, 0), (10, 30), (avail_width - 10, 30))

        # --- TILE ELEMENTS ---
        pos = [10, 50]
        for element in self.categories[self.current_category_name]:
            # Check if we are running out of vertical space
            if pos[1] > self.screen_height - 60: break

            category_text = self.small_font.render(element if self.current_category_name != "Entities" else str(
                self.categories["Entities"].index(element)), True, (255, 255, 255))

            # Adjusted width for button
            button = Button(pos[0], pos[1] - 5, avail_width - 20, 34, self.clicking)
            button.draw(self.sidebar, (30, 30, 30), mpos)

            self.sidebar.blit(category_text, (pos[0] + 34, pos[1] + 5))
            self.sidebar.blit(
                pygame.transform.scale(self.assets[element][0] if self.current_category_name != "Entities" else element,
                                       (24, 24)), pos)

            if button.pressed(mpos):
                if self.current_category_name != "Entities":
                    self.tile_group = self.tile_list.index(element)
                    self.tile_variant = 0
                else:
                    self.tile_group = 0
                    self.tile_variant = self.categories["Entities"].index(element)
            pos[1] += 40

    def move_visual_to(self, pos):
        scale_x = 960 / (self.screen.get_size()[0] - SIDEBAR_WIDTH)
        scale_y = 576 / (self.screen.get_size()[1])
        self.scroll[0] = pos[0] * 16 - ((self.screen_width - SIDEBAR_WIDTH) * scale_x) // (
                2 * int(RENDER_SCALE * self.zoom))
        self.scroll[1] = pos[1] * 16 - self.screen_height * scale_y // (2 * int(RENDER_SCALE * self.zoom))

    def render_underbar(self):
        mpos = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1] - (self.screen.get_size()[1] - UNDERBAR_HEIGHT))

        self.underbar = pygame.Surface((self.screen.get_size()[0] - SIDEBAR_WIDTH, UNDERBAR_HEIGHT))
        self.underbar.fill((35, 35, 35))

        category_text = self.font.render(self.current_infos_tile_category, True, (255, 255, 255))
        category_button = Button(20, 10, 100, 20, self.clicking)


        infos_tiles = []
        for tile_pos in self.tilemap.tilemap[self.current_layer]:
            tile = self.tilemap.tilemap[self.current_layer][tile_pos]
            if "infos_type" in tile:
                infos_tiles.append(tile)


        r = c = 0
        cell_width = 150
        cell_h_offset = 15
        cell_height = 40
        cell_v_offset = 50
        for info_tile in infos_tiles:
            if self.get_infos_tile_category(info_tile) == self.current_infos_tile_category or self.current_infos_tile_category == "All":
                act_button = Button(cell_h_offset + (cell_width + cell_h_offset) * c,
                                    cell_v_offset + (cell_height + 10) * r, cell_width, cell_height, self.clicking)

                if self.waiting_for_click_release or self.selecting_infos_tile_category:
                    act_button.activated = False

                act_button.draw(self.underbar, (60, 60, 60), mpos)

                info_name = self.small_font.render("pos" + ":", True, (255, 255, 255))
                info_value = self.small_font.render(str(info_tile["pos"]), True, (255, 255, 255))
                self.underbar.blit(info_name, (
                    20 + (cell_width + cell_h_offset) * c, cell_v_offset + 5 + (cell_height + 10) * r))
                self.underbar.blit(info_value, (
                    20 + (cell_width + cell_h_offset) * c + info_name.get_width() + 2,
                    cell_v_offset + 5 + (cell_height + 10) * r))
                c += 1

                if cell_h_offset + (cell_width + cell_h_offset) * c + cell_width > self.underbar.get_width():
                    c = 0
                    r += 1



                if act_button.pressed(mpos) and act_button.activated:
                    self.move_visual_to(info_tile["pos"])

        category_button.draw(self.underbar, (50, 50, 50), mpos)
        self.underbar.blit(category_text, ((140 - category_text.get_width()) / 2, 13))

        if category_button.pressed(mpos):
            self.selecting_infos_tile_category = True

        categories = ["All"]
        categories += list(self.infos_per_type_per_category.keys())
        categories.remove(self.current_infos_tile_category)

        if self.selecting_infos_tile_category:
            for tile_category in categories:
                    c_text = self.font.render(tile_category, True, (255, 255, 255))
                    c_button = Button(20, 10 + 20 * (categories.index(tile_category) + 1), 100, 20, self.clicking)
                    c_button.draw(self.underbar, (50, 50, 50), mpos)
                    self.underbar.blit(c_text,
                                       ((140 - c_text.get_width()) / 2, 13 + 20 * (categories.index(tile_category) + 1)))
                    if c_button.pressed(mpos):
                        self.current_infos_tile_category = tile_category
                        self.selecting_infos_tile_category = False
                        self.waiting_for_click_release = True


    def set_window_mode(self):
        if not self.window_mode:
            self.default_bg = self.screen.copy()
            self.window_mode = True

    def update_window_mode_bg(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))

        scaled_bg = pygame.transform.scale(self.default_bg, self.screen.get_size())
        self.screen.blit(scaled_bg, (0, 0))
        self.screen.blit(overlay, (0, 0))

    def setup_edit_window(self, tile_category, tile):
        self.set_window_mode()
        self.edited_tile = tile
        self.edited_tile_category = tile_category
        if "infos_type" in tile:
            self.edited_type = tile["infos_type"]
        self.showing_properties_window = True
        self.clicking = False

    def update_and_render_info_window(self):
        self.properties_window = pygame.Surface((280, 250))
        self.properties_window.fill((35, 35, 35))
        window_pos = ((self.screen_width - self.properties_window.get_width()) / 2,
                      (self.screen_height - self.properties_window.get_height()) / 2)
        mpos = (pygame.mouse.get_pos()[0] - window_pos[0], pygame.mouse.get_pos()[1] - window_pos[1])

        cell_h_offset = 20
        cell_v_offset = 70
        row_offset = 30
        info_r = 0


        different_types = self.infos_per_type_per_category[self.edited_tile_category].copy()
        current_type = self.edited_type
        if current_type is not None:
            infos = {"infos_type": self.edited_type}
            infos.update(different_types[current_type])
        else:
            infos = {"infos_type"}


        # Render Position (Read only)
        pos_txt = self.font.render("pos" + ":", True, (255, 255, 255))
        pos_val = self.font.render(str(self.edited_tile["pos"]), True, (255, 255, 255))
        self.properties_window.blit(pos_txt, (
            self.properties_window.get_width() - pos_val.get_width() - pos_txt.get_width() - 12, 10))
        self.properties_window.blit(pos_val, (self.properties_window.get_width() - pos_val.get_width() - 10, 10))

        for info in infos:
            info_name = self.font.render(info + ":", True, (255, 255, 255))

            # Determine text color (Red if editing)
            txt_color = (255, 50, 50) if self.edited_info == info else (255, 255, 255)

            # Display value
            if self.edited_info == info:
                if info == "infos_type":
                    val_str = self.edited_type
                else:
                    val_str = self.edited_value
            else:
                if info == "infos_type":
                    val_str = "" if self.edited_type is None else self.edited_type

                elif info in self.edited_tile:
                    val_str = self.edited_tile[self.edited_info]
                else:
                    if infos[info] == int:
                        val_str = str(0)
                    elif infos[info] == list[int]:
                        val_str = "[ , ]"
                    else:
                        val_str = ""

            info_value = self.font.render(val_str, True, txt_color)

            value_rect = Button(cell_h_offset + info_name.get_width() + 2,
                                cell_v_offset + 5 + row_offset * info_r,
                                max(info_value.get_width(), 9), info_value.get_height(), self.clicking)

            # --- LOGIC FOR CLICKING A FIELD ---
            if value_rect.pressed(mpos) and not self.edited_info:

                # Type selection logic
                # Checks if it is changing type, if it does, loop doesn't go forward (stops here)
                if info == "infos_type":
                    self.edited_info = "infos_type"

                # SPECIAL HANDLING FOR DEST_POS
                elif info == "dest_pos":
                    try:
                        target_map_id = int(self.edited_tile["destination"])
                        if target_map_id in self.active_maps:
                            self.return_to_level = self.level
                            self.transition_edit_pos = self.edited_tile["pos"]

                            target_index = self.active_maps.index(target_map_id)
                            self.level_manager.change_level(target_index)

                            self.selecting_dest_pos = True
                            self.waiting_for_click_release = True
                            self.window_mode = False
                            self.showing_properties_window = False
                            self.edited_tile = None

                            return  # <--- CRITICAL FIX: STOP RENDERING IMMEDIATELY

                        else:
                            print(f"Map ID {target_map_id} not found in active maps.")
                    except ValueError:
                        print("Invalid destination ID set.")

                # NORMAL TEXT EDITING FOR OTHER FIELDS
                else:
                    self.edited_info = info
                    print('modifing: ' + self.edited_info)
                    if self.edited_info in self.edited_tile:
                        self.edited_value = self.edited_tile[self.edited_info]
                    else:
                        if different_types[self.edited_type][info] in (int, str):
                            self.edited_value_type = different_types[self.edited_type][info]
                            self.edited_value = str(0) if self.edited_value_type == int else ""

                        # Special handling for list[int] type
                        elif different_types[self.edited_type][info] == list[int]:
                            self.edited_value = "[ , ]"



            if self.edited_info == "infos_type":
                type_r = 0
                available_types = list(different_types.keys())
                if self.edited_type:
                    available_types.remove(self.edited_type)
                for t in available_types:
                    type_name = self.font.render(t, True, (255, 255, 255))

                    type_rect = Button(62,
                                       75 + type_name.get_height() * (type_r+1),
                                       type_name.get_width(),
                                       type_name.get_height(),
                                       self.clicking)
                    type_rect.draw(self.properties_window, (0, 50, 200), mpos)
                    self.properties_window.blit(type_name, (
                        type_rect.x, type_rect.y))
                    if type_rect.pressed(mpos):
                        self.edited_type = t
                        self.edited_tile["infos_type"] = t
                        self.edited_info = None
                        break
                    type_r += 1


            if self.edited_info:
                value_rect.activated = False

            value_rect.draw(self.properties_window, (0, 50, 200), mpos)
            self.properties_window.blit(info_name, (
                cell_h_offset, cell_v_offset + 5 + row_offset * info_r))
            self.properties_window.blit(info_value, (cell_h_offset + info_name.get_width() + 2,
                                                     cell_v_offset + 5 + row_offset * info_r))

            # Draw Icon (Only if we still have a selected activator)
            if self.edited_tile:
                self.properties_window.blit(pygame.transform.scale(self.assets[self.edited_tile["type"]][0], (48, 48)), (5, 0))

            info_r += 1

    def load_edited_values(self):
        pass

    def save_edited_values(self):
        with open("data/activators.json", "r") as file:
            try:
                actions_data = json.load(file)
            except json.JSONDecodeError:
                actions_data = {}

        with open("data/activators.json", "w") as f:
            json.dump(actions_data, f, indent=4)

    def get_categories(self):
        self.categories["Blocks"] = [b for b in list(load_tiles(self.get_environment(self.level)).keys()) if
                                     "decor" not in b]
        self.categories["Decor"] = [d for d in list(load_tiles(self.get_environment(self.level)).keys()) if
                                    "decor" in d]
        self.categories["Doors"] = load_doors('editor', self.get_environment(self.level))
        self.categories["Activators"] = load_activators(self.get_environment(self.level))
        self.categories["Entities"] = self.base_assets["spawners"].copy()
        self.categories["Pickups"] = load_pickups()
        self.current_category = 0
        self.current_category_name = list(self.categories.keys())[self.current_category]

    def get_infos_tile_category(self, tile):
        for tile_category in self.infos_per_type_per_category:
            if tile_category.lower()[:-1] in tile["type"]:
                return tile_category

    def main_editor_logic(self):
        self.display.fill((0, 0, 0))

        current_sidebar_width = 0 if self.selecting_dest_pos else SIDEBAR_WIDTH


        self.scroll[0] += (self.movement[1] - self.movement[0]) * 8
        self.scroll[1] += (self.movement[3] - self.movement[2]) * 8
        render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

        self.tilemap.render(self.display, offset=render_scroll,
                            mask_opacity=80 if self.edit_properties_mode_on or self.edit_background_mode_on else 255, precise_layer=self.current_layer if not self.showing_all_layers else None)

        current_tile_img = self.assets[self.tile_list[self.tile_group]][self.tile_variant].copy()
        current_tile_img.set_alpha(100)

        # Calculate mouse position (only for main display area)
        mpos = pygame.mouse.get_pos()
        main_area_width = (self.screen_width - current_sidebar_width)
        main_area_height = (self.screen_height - UNDERBAR_HEIGHT if self.edit_properties_mode_on else self.screen_height)
        if mpos[0] < main_area_width and mpos[1] < main_area_height:  # Only if mouse is over main area
            # Scale mouse position to account for display scaling
            scale_x = 960 / (self.screen.get_size()[0] - current_sidebar_width)
            scale_y = 576 / (self.screen.get_size()[1])
            mpos_scaled = ((mpos[0] / RENDER_SCALE ) * scale_x * self.zoom,
                           (mpos[1] / RENDER_SCALE) * scale_y * self.zoom)
            tile_pos = (int((mpos_scaled[0] + self.scroll[0]) // self.tilemap.tile_size),
                        int((mpos_scaled[1] + self.scroll[1]) // self.tilemap.tile_size))
        else:
            # Default values if out of bounds to prevent crash
            tile_pos = (0, 0)
            mpos_scaled = (0, 0)

        mpos_in_mainarea = mpos[0] < main_area_width and mpos[1] < main_area_height

        if self.selecting_dest_pos:
            # 1. Draw Visuals
            overlay_text = self.font.render("SELECT DESTINATION POS", True, (255, 50, 50))
            self.display.blit(overlay_text, (self.display.get_width() // 2 - overlay_text.get_width() // 2, 10))
            pygame.draw.rect(self.display, (255, 0, 0),
                             (tile_pos[0] * 16 - self.scroll[0], tile_pos[1] * 16 - self.scroll[1], 16, 16), 1)

            # 2. Logic: Actual Selection (Only runs if lock is off)
            if not self.waiting_for_click_release and self.clicking and mpos_in_mainarea:
                selected_pos = list(tile_pos)

                self.level_manager.change_level(self.return_to_level)

                tile_loc = str(self.transition_edit_pos[0]) + ";" + str(self.transition_edit_pos[1])
                if tile_loc in self.tilemap.tilemap[self.current_layer]:
                    self.tilemap.tilemap[self.current_layer][tile_loc]["dest_pos"] = selected_pos
                    print(f"Updated dest_pos to {selected_pos}")

                self.selecting_dest_pos = False
                self.clicking = False
                self.save_action()

        if mpos_in_mainarea:
            if not self.window_mode:
                if not self.edit_properties_mode_on:
                    if self.ongrid:
                        if 'spike' in self.tile_list[self.tile_group]:
                            current_tile_img = pygame.transform.rotate(current_tile_img, self.rotation * -90)
                        self.display.blit(current_tile_img, (tile_pos[0] * self.tilemap.tile_size - self.scroll[0],
                                                             tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
                    else:
                        self.display.blit(current_tile_img, mpos_scaled)
                else:
                    tile_loc = str(tile_pos[0]) + ";" + str(tile_pos[1])
                    if tile_loc in self.tilemap.tilemap[self.current_layer]:
                        if "infos_type" in self.tilemap.tilemap[self.current_layer][tile_loc] and not self.clicking:
                            element = self.tilemap.tilemap[self.current_layer][tile_loc]["type"]
                            shining_image = \
                                self.assets[self.tile_list[self.tile_list.index(element)]][
                                    self.tilemap.tilemap[self.current_layer][tile_loc]["variant"]].copy()
                            shining_image.fill((255, 255, 255, 100), special_flags=pygame.BLEND_ADD)
                            self.display.blit(shining_image, (tile_pos[0] * self.tilemap.tile_size - self.scroll[0],
                                                              tile_pos[1] * self.tilemap.tile_size - self.scroll[
                                                                  1]))

        if self.selecting_dest_pos and self.clicking and not self.waiting_for_click_release and mpos_in_mainarea:
            selected_pos = list(tile_pos)

            # 1. Switch back to original level
            self.level_manager.change_level(self.return_to_level)

            # 2. Update the specific transition tile
            tile_loc = str(self.transition_edit_pos[0]) + ";" + str(self.transition_edit_pos[1])

            if tile_loc in self.tilemap.tilemap[self.current_layer]:
                self.tilemap.tilemap[self.current_layer][tile_loc]["dest_pos"] = selected_pos
                print(f"Updated dest_pos to {selected_pos}")
            else:
                print("Error: Original transition tile not found.")

            # 3. Reset State
            self.selecting_dest_pos = False
            self.clicking = False  # Prevent accidental placement on return
            self.save_action()

        if self.clicking and self.ongrid and mpos_in_mainarea:
            if not self.edit_background_mode_on:
                if not self.window_mode:
                    if not self.edit_properties_mode_on:
                        if self.tile_list[
                            self.tile_group] == "spawners" and self.tile_variant == 0 and self.tilemap.extract(
                                [("spawners", 0)], keep=True):
                            print("Player aspawner alredy placed in this map")

                        else:
                            t = self.tile_list[self.tile_group]
                            self.tilemap.tilemap[self.current_layer][str(tile_pos[0]) + ";" + str(tile_pos[1])] = {
                                'type': self.tile_list[self.tile_group],
                                'variant': self.tile_variant,
                                'pos': tile_pos}

                            tile = self.tilemap.tilemap[self.current_layer][str(tile_pos[0]) + ";" + str(tile_pos[1])]

                            if "spike" in t:
                                self.tilemap.tilemap[self.current_layer][str(tile_pos[0]) + ";" + str(tile_pos[1])]["rotation"] = self.rotation

                            elif "lever" in t:
                                tile_category = self.get_infos_tile_category(tile)
                                self.setup_edit_window(tile_category, tile)

                            '''
                            if self.tile_list[self.tile_group] in (d[0] for d in self.doors):
                                iD = int(input("Enter the door id: "))
                                while iD in self.doors_ids:
                                    print("id already used")
                                    iD = int(input("Enter the door id: "))
                                self.doors_ids.add(iD)
                                self.tilemap.tilemap[str(tile_pos[0]) + ";" + str(tile_pos[1])] = {
                                    'type': self.tile_list[self.tile_group],
                                    'variant': self.tile_variant,
                                    'pos': tile_pos,
                                    'id': iD}
                            '''

                    else:
                        tile_loc = str(tile_pos[0]) + ";" + str(tile_pos[1])
                        if tile_loc in self.tilemap.tilemap[self.current_layer]:
                            tile = self.tilemap.tilemap[self.current_layer][tile_loc]
                            tile_category = self.get_infos_tile_category(tile)
                            self.setup_edit_window(tile_category, tile)
                        '''
                        
                            if t in self.present_activators_types[self.current_activator_category]:
                                self.set_window_mode()
                                self.showing_properties_window = True
                                self.selected_activator_type = "Levers" if "lever" in t else "Buttons" if "button" in t else "Teleporters"
                                self.selected_activator = {"image": self.assets[t][0],
                                                           "infos": self.activators[self.selected_activator_type][
                                                               tile_loc]}
                                self.clicking = False
                            elif t == "transition":
                                self.set_window_mode()
                                self.showing_properties_window = True
                                self.selected_activator_type = "Transitions"
                                # Manual construction of info for transitions
                                self.selected_activator = {
                                    "image": self.assets[t][0],
                                    "infos": {
                                        "type": "transition",
                                        "destination": self.tilemap.tilemap[tile_loc].get('destination', 0),
                                        "dest_pos": self.tilemap.tilemap[tile_loc].get('dest_pos', [0, 0]),
                                        "pos": self.tilemap.tilemap[tile_loc]['pos']
                                    }
                                }
                                self.clicking = False
                            '''
            else:
                self.tilemap.background[str(tile_pos[0]) + ";" + str(tile_pos[1])] = {
                    'type': self.tile_list[self.tile_group],
                    'variant': self.tile_variant,
                    'pos': tile_pos}

        if self.right_clicking and mpos_in_mainarea:
            if not self.window_mode:
                if not self.edit_properties_mode_on:
                    tile_loc = str(tile_pos[0]) + ";" + str(tile_pos[1])
                    if not self.edit_background_mode_on:
                        if tile_loc in self.tilemap.tilemap[self.current_layer]:
                            del self.tilemap.tilemap[self.current_layer][tile_loc]


        if not self.edit_properties_mode_on:
            self.display.blit(current_tile_img, (5, 5))

        if not self.selecting_dest_pos:
            self.render_sidebar()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEWHEEL:
                mpos_wheel = pygame.mouse.get_pos()
                # If mouse is over the sidebar (specifically the map nav area)
                if mpos_wheel[0] > self.screen_width - current_sidebar_width:
                    self.map_list_scroll -= event.y * 20
                    # Clamp scrolling
                    self.map_list_scroll = max(0, self.map_list_scroll)

                if not self.window_mode:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_CTRL:
                        self.zoom -= 0.1*event.y
                        self.zoom = max(0.2, min(self.zoom, 8.0))
                        self.display = pygame.Surface((480 * self.zoom, 288 * self.zoom))


            if not self.window_mode :
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (1, 3):  # Left or Right click
                        self.temp_snapshot = self.create_snapshot()

                    if event.button == 1:
                        self.clicking = True
                        if not self.ongrid:
                            self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group],
                                                               'variant': self.tile_variant,
                                                               'pos': (
                                                                   mpos_scaled[0] + self.scroll[0],
                                                                   mpos_scaled[1] + self.scroll[1])})
                    if event.button == 3:
                        self.right_clicking = True
                    if not self.shift and self.tile_group:
                        if event.button == 4:
                            self.tile_variant = (self.tile_variant - 1) % len(
                                self.assets[self.tile_list[self.tile_group]])
                        if event.button == 5:
                            self.tile_variant = (self.tile_variant + 1) % len(
                                self.assets[self.tile_list[self.tile_group]])
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
                                self.tilemap.tilemap[self.current_layer], self.tilemap.tilemap[str(int(self.current_layer) - 1)]\
                                    = self.tilemap.tilemap[str(int(self.current_layer) - 1)], self.tilemap.tilemap[self.current_layer]
                                self.current_layer = str(int(self.current_layer) - 1)
                                print(f"Current layer moved to layer {self.current_layer}")
                        if event.key == pygame.K_UP:
                            if self.tilemap.tilemap[self.current_layer] == {} and str(int(self.current_layer) + 1) not in self.tilemap.tilemap:
                                print("This layer is the last layer, can't go up")
                            else:
                                self.tilemap.tilemap[self.current_layer], self.tilemap.tilemap[str(int(self.current_layer) + 1)]\
                                    = self.tilemap.tilemap[str(int(self.current_layer) + 1)], self.tilemap.tilemap[self.current_layer]
                                self.current_layer = str(int(self.current_layer) + 1)
                                print(f"Current layer moved to layer {self.current_layer}")

                    else:
                        if event.key == pygame.K_i and not self.holding_i:
                            self.edit_properties_mode_on = not self.edit_properties_mode_on
                            self.holding_i = True
                        if event.key == pygame.K_q:
                            self.movement[0] = True
                        if event.key == pygame.K_RIGHT:
                            self.level_manager.change_level((self.level + 1) % self.sizeofmaps())
                        if event.key == pygame.K_LEFT:
                            self.level_manager.change_level((self.level - 1) % self.sizeofmaps())
                        if event.key == pygame.K_DOWN:
                            if self.current_layer == "0":
                                print("Layer 0, can't make any new layer under this one")
                            else:
                                self.current_layer = str(int(self.current_layer) - 1)
                                print(f"Current layer : {self.current_layer}")
                            if self.current_layer not in self.tilemap.tilemap:
                                self.tilemap.tilemap[self.current_layer] = {}

                        if event.key == pygame.K_UP:
                            if int(self.current_layer)+1 == len(self.tilemap.tilemap.keys()) and self.tilemap.tilemap[self.current_layer] == {}:
                                print("This layer is empty, can't make any new layer")
                            else:
                                self.current_layer = str(int(self.current_layer) + 1)
                                print(f"Current layer : {self.current_layer}")

                            if self.current_layer not in self.tilemap.tilemap:
                                self.tilemap.tilemap[self.current_layer] = {}
                        if event.key == pygame.K_TAB and not self.holding_tab:
                            self.showing_all_layers = not self.showing_all_layers
                            self.holding_tab = True

                        if event.key == pygame.K_b and not self.holding_b:
                            self.edit_background_mode_on = not self.edit_background_mode_on
                            self.holding_b = True
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
                        if event.key == pygame.K_LSHIFT:
                            self.shift = True
                        if event.key == pygame.K_o:
                            self.level_manager.full_save()
                        if event.key == pygame.K_c:
                            print((tile_pos[0] * 16, tile_pos[1] * 16))
                        if event.key == pygame.K_r:
                            self.rotation = (self.rotation + 1)%4
                        # Make tiles invisible
                        if event.key == pygame.K_y and not self.holding_y:
                            self.make_background_invisible = not self.make_background_invisible
                            self.holding_y = True
                        if not self.edit_background_mode_on:
                            # Shortcut for placing camera setup
                            if event.key == pygame.K_k:
                                pass
                                self.save_action()
                            # Shortcut for placing transitions
                            if event.key == pygame.K_p:
                                dest = 0  # Default value
                                self.tilemap.tilemap[self.current_layer][str(tile_pos[0]) + ";" + str(tile_pos[1])] = {
                                    'type': "transition",
                                    'variant': self.tile_variant,
                                    'pos': tile_pos,
                                    'destination': dest,
                                    'dest_pos': [0, 0]}
                                self.save_action()
                            # Shortcut for placing checkpoints
                            if event.key == pygame.K_j:
                                self.tilemap.tilemap[self.current_layer][str(tile_pos[0]) + ";" + str(tile_pos[1])] = {
                                    'type': "checkpoint",
                                    'variant': 0,
                                    'pos': tile_pos,
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
                    if event.key == pygame.K_TAB :
                        self.holding_tab = False
                    if event.key == pygame.K_LSHIFT:
                        self.shift = False
            else:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.clicking = True
                    if event.button == 3:
                        self.right_clicking = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.edited_type:
                            infos = self.infos_per_type_per_category[self.edited_tile_category][self.edited_type]
                            if self.edited_info:
                                self.edited_info = ""
                            elif (info in self.edited_tile for info in infos):
                                self.window_mode = False
                                self.showing_properties_window = False
                                self.edited_tile = None
                                self.edited_tile_category = None
                                self.edited_type = None
                            else:
                                print("All the infos have to be filled!")
                        else:
                            print("All the infos have to be filled!")


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

            if event.type == pygame.VIDEORESIZE:
                # Update screen dimensions
                self.screen_width = max(event.w, 480 + SIDEBAR_WIDTH)  # Minimum width
                self.screen_height = max(event.h, 288 + UNDERBAR_HEIGHT)  # Minimum height
                self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)

        # Calculate main area dimensions for scaling
        main_area_width = self.screen_width - current_sidebar_width
        main_area_height = self.screen_height

        # Blit everything to screen
        if not self.window_mode:

            scaled_display = pygame.transform.scale(self.display, (main_area_width, main_area_height))

            self.screen.blit(scaled_display, (0, 0))
            self.screen.blit(self.sidebar, (main_area_width, 0))
            if self.edit_properties_mode_on and not self.selecting_dest_pos:
                self.render_underbar()
                self.screen.blit(self.underbar, (0, main_area_height - UNDERBAR_HEIGHT))
            if self.selecting_environment_mode:
                self.update_window_mode_bg()  # Darken background
                self.render_environment_selection_window()
        else:
            self.update_window_mode_bg()
            if self.showing_properties_window:
                self.update_and_render_info_window()
                self.screen.blit(self.properties_window,
                                 ((self.screen_width - self.properties_window.get_width()) / 2,
                                  (self.screen_height - self.properties_window.get_height()) / 2))


        pygame.display.update()
        self.clock.tick(60)

    def run(self):
        while True:
            self.main_editor_logic()

if __name__ == "__main__":
    Editor().run()