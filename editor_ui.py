import os
import copy
import json
import shutil

from scripts.utils import load_image, create_rect_alpha
from scripts.button import EditorButton, LevelCarousel, EnvironmentButton, SimpleButton
from scripts.text import load_game_font
from scripts.utils import load_editor_tiles, load_tiles, load_images
from scripts.tilemap import Tilemap
import pygame

class LevelManager:

    def __init__(self, editor_instance):
        self.editor = editor_instance

    # Helper to get the actual File ID from the UI Level Index
    def get_file_id(self, ui_level):
        '''if 0 <= ui_level < len(self.editor.active_maps):
                    return self.editor.active_maps[ui_level]
                return 0'''
        return ui_level

    def get_next_file_id(self):
        # We look at actual files on disk to avoid conflicts
        existing_files = [int(f.split('.')[0]) for f in os.listdir('data/maps/') if f.endswith('.json')]
        # Also look at active maps in memory (in case we created one but haven't saved yet)
        all_ids = set(existing_files + self.editor.active_maps)
        if not all_ids:
            return 0
        return max(all_ids) + 1

    def delete_map(self, level):

        # 1. Remove the current File ID from our active list
        # We don't touch the file system yet!
        self.editor.environments[self.editor.get_environment(level)].remove(level)
        del self.editor.active_maps[level]

        # 2. Determine new level index
        # If we deleted the last map, go to the previous one
        if self.editor.level == level:
            if self.editor.level >= len(self.editor.active_maps):
                next_level = max(0, len(self.editor.active_maps) - 1)
                self.change_level(next_level)

        # 3. If list is empty, create a fresh map 0 immediately
        if len(self.editor.active_maps) == 0:
            self.editor.active_maps.append(0)
            self.editor.level = 0

    def map_data_reset(self):
        # Load new level (using new file ID)
        new_file_id = self.get_file_id(self.editor.level)
        try:
            self.editor.tilemap.load('data/maps/' + str(new_file_id) + '.json')
        except FileNotFoundError:
            # Create the file if it doesn't exist (e.g. new map)
            with open('data/maps/' + str(new_file_id) + '.json', 'w') as f:
                json.dump({'tilemap': {"0":{},
                                            "1":{},
                                            "2":{},
                                            "3":{},
                                            "4":{},
                                            "5":{},
                                            "6":{}},
                           'tilesize': 16, 'offgrid': {}}, f)
            self.editor.tilemap.load('data/maps/' + str(new_file_id) + '.json')

        # Reload assets
        self.editor.reload()

    def change_level(self, new_level):
        # Save current level (using current file ID)
        current_file_id = self.get_file_id(self.editor.level)
        if self.editor.tilemap.tilemap != {"0":{},
                                            "1":{},
                                            "2":{},
                                            "3":{},
                                            "4":{},
                                            "5":{},
                                            "6":{}}:
            self.editor.tilemap.save('data/maps/' + str(current_file_id) + '.json')

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
            return {"white_space":[0], "green_cave": [1], "blue_cave": []}

    def save_environments(self):
        with open('data/environments.json', 'w') as f:
            json.dump(self.editor.environments, f, indent=4)

    def full_save(self):
        # 1. Save current map state first
        current_file_id = self.get_file_id(self.editor.level)
        self.editor.tilemap.save('data/maps/' + str(current_file_id) + '.json')

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

        # LevelManager — doit être créé AVANT d'utiliser active_maps/environments
        self.level_manager = LevelManager(self)
        self.environments = self.level_manager.load_environments()
        self.active_maps = list(range(
            sum(1 for f in os.listdir('data/maps/') if f.endswith('.json'))
        ))

        self.tile_group = 0
        self.tile_variant = 0

        self.categories = load_editor_tiles(self.current_environment)
        self.assets = {}
        for tile in self.categories.values():
            self.assets.update(tile)
        self.assets.update({"spawners": load_images("player/spawner")})

        self.tile_type = next(iter(self.categories[next(iter(self.categories))]))

        self.showing_all_layers = False
        self.current_layer = "0"
        self.current_category = 0

        self.tilemap = Tilemap(self)

        try:
            self.tilemap.load('data/maps/' + str(self.level) + '.json')
        except FileNotFoundError:
            pass

        self.save_action()

        self.ui = UI(self)

    def get_environment(self, level):
        file_id = self.level_manager.get_file_id(level)
        for environment in self.environments:
            if file_id in self.environments[environment]:
                return environment
        if len(self.environments) > 0:
            return list(self.environments.keys())[0]
        return "white_space"

    def get_categories(self):
        self.categories = {}
        self.categories = load_editor_tiles(self.get_environment(self.level))
        self.current_category = 0

    def get_assets(self):
        self.assets = {}
        for tile in self.categories.values():
            self.assets.update(tile)
        self.assets.update({"spawners": load_images("player/spawner")})

    def save_action(self):
        snapshot = {'tilemap': copy.deepcopy(self.tilemap.tilemap)}
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(snapshot)
        self.history_index += 1
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1

    def sizeofmaps(self):
        return len(self.active_maps)

    def reload(self):
        self.scroll = [0, 0]
        self.get_categories()
        self.get_assets()

        self.history = []
        self.history_index = -1
        self.save_action()  # Save the initial state (Index 0)


    def main_editor_logic(self):
        self.display.fill((0, 0, 0))

        self.scroll[0] += (self.movement[1] - self.movement[0]) * 8
        self.scroll[1] += (self.movement[3] - self.movement[2]) * 8
        render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

        self.tilemap.render(self.display, offset=render_scroll,
                            precise_layer=self.current_layer if not self.showing_all_layers else None,
                            with_player=False)



        changing_size = False

        if self.display.get_size() != (int(480 * self.zoom), int(288 * self.zoom)):
            screenshot = self.screen.copy()
            self.display = pygame.Surface((480 * self.zoom, 288 * self.zoom))
            changing_size = True

        scaled_display = pygame.transform.scale(self.display, self.screen.get_size())

        self.screen.blit(scaled_display, (0, 0))

        if changing_size:
            # noinspection PyUnboundLocalVariable
            self.screen.blit(screenshot, (0, 0))
        self.ui.draw()


    def run(self):
        while True:
            self.main_editor_logic()
            self.clock.tick(60)
            pygame.display.update()

class UI:
    TOOLBAR_COLOR = (64,64,64)
    ASSETS_SECTION_COLOR = (32,32,32)
    PADDING = 5

    def __init__(self, editor):
        self.editor = editor
        self.editor_previous_tool = None
        self.screen = editor.screen
        self.screen_width, self.screen_height = self.screen.get_size()

        self.level_carousel = None

        self.title_font = load_game_font(24)
        self.buttons_font = load_game_font(18)

        self.state = "Editor"

        self.toolbar_width = self.screen_width * 5 / 96
        self.toolbar_default_width = self.screen_width * 5 / 96
        self.toolbar_buttons_width = self.toolbar_width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_width * (3 / 5)
        self.tools_buttons = []
        self.tools_buttons_labels = ["Brush", "Eraser", "Selection", "LevelSelector"]
        #self.tools_buttons_images = {tool: load_image(f"ui/{tool.lower()}.png") for tool in self.tools_buttons_labels}
        self.tools_buttons_images = {"Brush": load_image("ui/brush.png"),
                                     "Eraser": load_image("ui/eraser.png"),
                                     "Selection": load_image("ui/selection.png"),
                                     "LevelSelector": load_image("ui/skull.png")}

        self.assets_section_width = self.assets_section_default_width = self.screen_width * 20/96
        self.assets_section_height = self.screen_width * 25/96
        self.current_category = 0
        self.current_category_name = list(self.editor.categories.keys())[self.current_category]
        self.assets_section_buttons_width = self.assets_section_width * (1 / 8)
        self.assets_section_buttons_height = self.assets_section_width * (1 / 8)
        self.assets_section_buttons = []
        self.assets_section_buttons_labels = ["Previous", "Next"]
        self.assets_section_buttons_images = {"Previous": pygame.transform.flip(load_image("ui/next.png"), True, False),
                                              "Next": load_image("ui/next.png")}
        self.assets_button_width = self.assets_section_width * (1 / 10)
        self.assets_button_height = self.assets_section_width * (1 / 10)
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

        button_x, button_y = self.toolbar_width/2, self.toolbar_width/2
        for label in self.tools_buttons_labels:
            button = EditorButton(label, self.tools_buttons_images[label] ,
                                  (button_x, button_y),
                                  self.toolbar_buttons_width,
                                  self.toolbar_buttons_height,
                                  (64,64,64),
                                  self.screen_width/self.editor.SW)

            if label == self.tools_buttons_labels[-2]:
                button_y = self.screen_height - 1*self.toolbar_buttons_height
            else:
                button_y += self.toolbar_buttons_height + (self.PADDING/self.editor.SH)*self.screen_height
            self.tools_buttons.append(button)

        button_x, button_y = (30/self.editor.SW)*self.screen_width, (20/self.editor.SH)*self.screen_height
        for label in self.assets_section_buttons_labels:
            button = EditorButton(label, self.assets_section_buttons_images[label], (button_x, button_y), self.assets_section_buttons_width, self.assets_section_buttons_height, (24,24,24), self.screen_width/self.editor.SW)
            button_x = self.assets_section_width - button_x
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
                    self.screen_width - self.assets_section_width - 10 * self.screen_width / self.editor.SW):
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

    def init_assets_buttons(self, categories):
        self.assets_buttons = []

        initial_x = (20 / self.editor.SW) * self.screen_width

        button_x, button_y = initial_x, (60 / self.editor.SH) * self.screen_height
        for tile in categories[self.current_category_name]:
            img = categories[self.current_category_name][tile].copy()[0]
            button = EditorButton(tile, img, (button_x, button_y), self.assets_button_width, self.assets_button_height,
                                  (24, 24, 24), self.screen_width/self.editor.SW)
            if button_x + self.assets_button_width + self.PADDING > self.assets_section_width - self.assets_button_width:
                button_y = (button_y + self.assets_button_height + self.PADDING*self.screen_height/self.editor.SH %
                            self.screen_height)
                button_x = initial_x
            else:
                button_x = ((button_x + self.assets_button_width + self.PADDING*self.screen_width/self.editor.SW) %
                            (self.assets_section_width - self.assets_button_width))
            if button_x < initial_x:
                button_x = initial_x
            if button_y + self.assets_button_height/2 > self.assets_section_height:
                self.assets_section_height += self.assets_button_height + self.PADDING*self.screen_height/self.editor.SH
            self.assets_buttons.append(button)


    def render_toolbar(self):

        overlay = pygame.Surface((self.toolbar_width, self.screen_height))
        overlay.fill(self.TOOLBAR_COLOR)

        for button in self.tools_buttons:
            button.draw(overlay)
            if button.label == self.editor.current_tool:
                button.activated = True
            else:
                button.activated = False

        self.screen.blit(overlay, (self.screen_width - self.toolbar_width, 0))

    def render_assets_section(self, x, y):
        overlay = pygame.Surface((self.assets_section_width, self.assets_section_height))
        overlay.fill(self.ASSETS_SECTION_COLOR)

        category_text = self.title_font.render(self.current_category_name, True, (255, 255, 255))
        category_x = (self.assets_section_width - category_text.get_width())/2
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

        self.screen.blit(overlay, (x, y))

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
            self.toolbar_width = max(0, self.toolbar_width - 5)
            self.assets_section_width = max(0, self.assets_section_width - 20)
        else:
            self.toolbar_width = min(self.toolbar_default_width, self.toolbar_width + 5)
            self.assets_section_width = min(self.assets_section_default_width, self.assets_section_width + 20)


    def reload(self):
        self.screen_width, self.screen_height = self.editor.screen.get_size()

        self.title_font = load_game_font(int((24/self.editor.SH)*self.screen_height))
        self.buttons_font = load_game_font(int((18/self.editor.SH)*self.screen_height))

        self.toolbar_width = self.screen_width * 5/96
        self.toolbar_default_width = self.screen_width * 5/96
        self.toolbar_buttons_width = self.toolbar_width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_width * (3 / 5)

        self.assets_section_width = self.assets_section_default_width = self.screen_width * 20 / 96
        self.assets_section_height = self.screen_width * 25/96
        self.assets_section_buttons_width = self.assets_section_width * (1 / 8)
        self.assets_section_buttons_height = self.assets_section_width * (1 / 8)
        self.assets_button_width = self.assets_section_width * (1 / 10)
        self.assets_button_height = self.assets_section_width * (1 / 10)
        self.init_buttons()

    def reload_assets_section(self):
        self.current_category = 0
        self.current_category_name = list(self.editor.categories.keys())[self.current_category]
        self.init_assets_buttons(self.editor.categories)

    def draw(self):
        for event in pygame.event.get():
            self.handle_ui_event(event)


        self.check_closed()
        self.render_toolbar()
        match self.editor.current_tool:
            case "Brush":
                self.render_assets_section(self.screen_width - self.toolbar_width - self.assets_section_width,
                                   self.screen_height - self.assets_section_height)
            case "LevelSelector":
                if self.environment_selector_state:
                    self.render_environment_selector()
                else:
                    self.render_level_selector()


    def handle_ui_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.closing = not self.closing
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
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_width, 0)):
                self.editor_previous_tool = self.editor.current_tool
                self.editor.current_tool = button.label

    def handle_assets_section_event(self, event):
        for button in self.assets_section_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_width - self.assets_section_width,
                                                  self.screen_height - self.assets_section_height)):
                if button.label == "Next":
                    self.current_category = (self.current_category + 1) % len(self.editor.categories)
                elif button.label == "Previous":
                    self.current_category = (self.current_category - 1) % len(self.editor.categories)
                button.activated = True
                self.current_category_name = list(self.editor.categories.keys())[self.current_category]
                self.init_assets_buttons(self.editor.categories)
            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION and not button.is_selected(
                    event,
                    offset=(self.screen_width - self.toolbar_width - self.assets_section_width,
                            self.screen_height - self.assets_section_height)):
                button.activated = False
        for button in self.assets_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_width - self.assets_section_width,
                                                  self.screen_height - self.assets_section_height)):
                self.editor.tile_type = button.label
                self.editor.tile_variant = 0

    def handle_environment_selector_event(self, event):
        for button in self.environment_selector_buttons:
            if button.handle_event(event):
                self.selected_environment = button.label

        if self.environment_selector_confirmation_button.handle_event(event):
            self.level_carousel.levels[self.level_carousel.selected] = self.level_carousel.selected
            self.level_carousel.levels.append(None)

            self.editor.environments[self.selected_environment].append(self.level_carousel.selected)
            self.editor.level_manager.save_environments()
            self.editor.active_maps.append(self.level_carousel.selected)
            self.editor.level_manager.change_level(self.level_carousel.selected)

            self.reload_assets_section()
            self.editor.current_tool = self.editor_previous_tool
            self.environment_selector_state = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.environment_selector_state = False

    def handle_level_selector_event(self,event):
        level_selector_state = self.level_carousel.handle_event(event)
        match level_selector_state:
            case "AddLevel":
                self.environment_selector_state = True
            case "DeleteLevel":
                self.editor.level_manager.delete_map(self.level_carousel.selected)
                self.level_carousel.selected = max(0, self.level_carousel.selected - 1)
            case "LoadLevel":
                self.editor.level_manager.change_level(self.level_carousel.selected)
                self.editor.current_tool = self.editor_previous_tool
                self.reload_assets_section()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.editor.current_tool = self.editor_previous_tool


if __name__ == "__main__":
    editor = EditorSimulation()
    editor.run()