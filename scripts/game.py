import sys

# --- Game Script Imports ---
# These modules handle specific game logic like physics, entities, and UI.
from scripts.entities import *
from scripts.utils import *
from scripts.tilemap import Tilemap
from scripts.physics import PhysicsPlayer
from scripts.particle import update_particles, particle_render
from scripts.activators import *
from scripts.user_interface import Menu
from scripts.saving import Save
from scripts.doors import Door, doors_render_and_update
from scripts.display import *
from scripts.camera import CameraSetup, Camera
from scripts.text import load_game_texts, update_bottom_text
from scripts.sound import Sound
from scripts.pickup import Pickup


class Game:
    """
    The primary Engine class for 'Anima'.

    This class manages the core game loop, state transitions (menus to gameplay),
    asset loading, level streaming, and the rendering pipeline (lighting, particles, UI).
    """

    # --- State Management ---
    # Controls which 'loop' the game is currently running

    MENU_STATE = "MENU"
    PLAYING_STATE = "PLAYING"

    SCREEN_WIDTH = 960
    SCREEN_HEIGHT = 600

    def __init__(self):
        pygame.init()
        self._init_display()
        self._init_assets()
        self._init_sound()
        self._init_settings()
        self._init_runtime_state()
        self.menu = Menu(self)

    def _init_display(self):
        pygame.display.set_caption("Anima")
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        self.display = pygame.Surface((self.SCREEN_WIDTH / 2, self.SCREEN_HEIGHT / 2))
        self.clock = pygame.time.Clock()
        self.debug_mode = False
        try:
            icon = pygame.image.load("assets/images/ui/logo.png").convert_alpha()
            pygame.display.set_icon(pygame.transform.smoothscale(icon, (16, 16)))
        except FileNotFoundError:
            pass

    def _init_sound(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self.sound_running = True
        except Exception as e:
            print(f"Error initializing sound: {e}")
            self.sound_running = False

        self.master_volume = 1
        player_sfx = "assets/player/sounds/"
        self.music_sound_manager = Sound(self, {
            'title_screen': "assets/ui/sounds/Title-screen-ambient-music.wav",
            'level_1': f"assets/environments/{self.get_environment_by_id(1)}/sounds/map_1.wav",
            'level_2': f"assets/environments/{self.get_environment_by_id(2)}/sounds/map_2.wav",
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

    def _init_settings(self):
        self.save_system = Save(self)
        self.current_slot = None
        self.languages = ["Français", "English", "Español"]
        self.selected_language = self.languages[1]
        self.fullscreen = False
        self.vsync_on = False
        self.brightness = 0.5
        self.keyboard_layout = "AZERTY"
        self.key_map = {
            "key_up": pygame.K_z, "key_down": pygame.K_s,
            "key_left": pygame.K_q, "key_right": pygame.K_d,
            "key_jump": pygame.K_SPACE, "key_dash": pygame.K_g,
            "key_interact": pygame.K_e, "key_noclip": pygame.K_n,
            "key_hitbox": pygame.K_h, "key_select": pygame.K_RETURN,
        }

    def _init_assets(self):
        self.level_id = 1
        path = 'data/environments.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.environments = json.load(f)

        self.environment = self.get_environment_by_id(self.level_id)
        self.level = self.get_file_name(self.environment, self.level_id)
        self.default_level = self.level
        self.tile_size = 16
        self.b_info = {
            "white_space": {"animated": True, "img_dur": 6, "loop": True},
            "green_cave": {"animated": False},
            "blue_cave": {"animated": False},
        }
        self.assets = {}
        self.assets.update(load_tiles(self.environment))
        self.assets.update(load_player())
        self.assets.update(load_backgrounds(self.b_info, self.environment))
        self.assets.update(load_particles(self.environment))
        self.doors_id_pairs = []
        self.levers_id_pairs = []
        self.buttons_id_pairs = []
        self.tp_id_pairs = []
        self.tilemap = Tilemap(self, self.tile_size)

    def _init_runtime_state(self):
        """Everything that resets on reload(). Single source of truth."""
        # Input
        self.keybindings = {}
        self.dict_kb = {
            "key_right": 0, "key_left": 0, "key_up": 0, "key_down": 0,
            "key_jump": 0, "key_dash": 0, "key_noclip": 0,
        }

        # State machine
        self.state = self.MENU_STATE
        self.previous_state = None
        self.game_initialized = False
        self.current_mode = "default"

        # Camera
        self.camera = Camera(self)
        self.camera_center = None
        self.scroll_limits_per_level = {
            "1": {"x": (0, 0), "y": (-1230, 1233)},
            "2": {"x": (64, 624), "y": (-176, 144)},
        }
        self.scroll_limits = self.scroll_limits_per_level["1"]
        self.screenshake = 0
        self.scroll = [0.0, 0.0]

        # Player
        self.player = PhysicsPlayer(self, self.tilemap, (100, 0), (16, 16))
        self.player_dead = False
        self.death_counter = 0
        self.collected_souls = []
        self.nb_souls = 0
        self.checkpoints = []
        self.current_checkpoint = None
        self.active_checkpoint_anim = None
        self.sections = {0: (0, 1, 2)}
        self.spawn_point = {
            "pos": [100, 0],
            "level": self.level,
            "scroll_limits": {"x": (0, 0), "y": (-1230, 1233)},
            "camera_center": None,
            "cameras": {}
        }

        # Activators / interactables
        self.activators = []
        self.activators_actions = load_activators_actions(
            self.level, self.tilemap.layers["activators"]
        )
        self.spawners = {}
        self.spawner_pos = {}
        self.projectiles = []
        self.teleporting = False
        self.tp_id = None
        self.last_teleport_time = 0
        self.player_grabbing = False

        # Gameplay flow
        self.cutscene = False
        self.game_texts = load_game_texts()
        self.bottom_text = None
        self.attacking = False
        self.holding_attack = False
        self.transitions = []
        self.doors_rects = []

        # Lighting
        self._init_lighting()

        # VFX / combat
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

        # Timers
        self.playtime = 0
        self.menu_time = 0
        self.show_spikes_hitboxes = False

    def _init_lighting(self):
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
        self.light_mask = pygame.Surface(
            (self.light_radius * 2, self.light_radius * 2), pygame.SRCALPHA
        )

    def reload(self):
        self.previous_state = None
        self.state = self.MENU_STATE
        self._init_runtime_state()
        # Keep menu alive — just reset its music
        self.music_sound_manager.play(name="title_screen", loops=-1)

    def _handle_events(self):
        """Pure event polling. Returns False if game should quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            self._handle_keydown(event)
            self._handle_keyup(event)
            self._update_dict_kb(event)
        return True

    def _handle_keydown(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.menu.capture_background()
            self.state = self.MENU_STATE
            self.menu.menu_state = self.menu.PAUSE_STATE
            for key in self.dict_kb: self.dict_kb[key] = 0
        elif event.key == self.key_map["key_interact"]:
            update_throwable_objects_action(self)
            if not self.player_grabbing:
                update_activators_actions(self)
        elif event.key == pygame.K_F11:
            toggle_fullscreen(self)
        elif event.key == pygame.K_f and not self.holding_attack:
            self.dict_kb["key_attack"] = 1
            self.holding_attack = True
        elif event.key == self.key_map["key_hitbox"] and self.debug_mode:
            self.toggle_hitboxes()
        elif event.key == pygame.K_r:
            kill_player(self)

    def _handle_keyup(self, event):
        if event.type != pygame.KEYUP:
            return
        if event.key == pygame.K_f:
            self.dict_kb["key_attack"] = 0
            self.holding_attack = False

    def _update_dict_kb(self, event):
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return
        for key, mapped in self.key_map.items():
            if event.key == mapped:
                self.dict_kb[key] = 1 if event.type == pygame.KEYDOWN else 0

    def toggle_hitboxes(self):
        self.player.show_hitbox = not self.player.show_hitbox
        self.show_spikes_hitboxes = not self.show_spikes_hitboxes
        #self.tilemap.show_collisions = not self.tilemap.show_collisions

    def get_env_prefix(self, env_name):
        # Converts "green_cave" to "gc", "white_space" to "ws"
        return "".join([word[0] for word in env_name.split("_")])

    def get_file_name(self, env_name, map_id):
        prefix = self.get_env_prefix(env_name)
        return f"{prefix}{map_id:03d}.json"

    def get_environment_by_id(self, map_id, environments_dict=None):
        if environments_dict is None:
            environments_dict = self.environments
        for env, ids in environments_dict.items():
            if map_id in ids:
                return env
        return "white_space"

    def set_keymap(self,bindings: dict):
        for cat in bindings:
            for bind in bindings[cat]:
                if bind.lower() == "show hitbox":
                    self.key_map["key_hitbox"] = bindings[cat][bind]
                elif bind.lower() == "no clip":
                    self.key_map["key_noclip"] = bindings[cat][bind]
                else:
                    self.key_map[f"key_{bind.lower()}"] = bindings[cat][bind]

    def load_level(self, map_id, transition_effect=True):
        """
        Loads level data from a JSON file, extracts entities, and sets up level-specific logic.

        Args:
            map_id (int): The index of the level to load.
            :param map_id:
            :param transition_effect:
        """
        self.environment = self.get_environment_by_id(self.level_id)
        map_name = self.get_file_name(self.environment, map_id)
        self.assets = {}
        self.assets.update(load_tiles(self.environment))
        self.assets.update(load_player())
        self.assets.update(load_backgrounds(self.b_info, self.environment))
        self.assets.update(load_particles(self.environment))

        self.tilemap.load("data/maps/" + map_name)
        self.tilemap.tile_size = self.tile_size
        mult=0.5
        self.display = pygame.Surface((self.SCREEN_WIDTH*mult, self.SCREEN_HEIGHT*mult))
        self.light_emitting_tiles = []
        self.light_emitting_objects = []
        self.activators_actions = load_activators_actions(map_name, self.tilemap.layers["activators"])

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
        '''for door in self.tilemap.extract(self.doors_id_pairs):
            door_type = door["type"]
            speed = int(door["opening_time"])
            door_id = door["id"]
            self.doors.append(
                Door(self.d_info[door_type]["size"], door["pos"], door_type, door_id, False, speed, self))'''

        self.camera_setup = []
        for camera in self.tilemap.extract(["camera_setup"]):
            self.camera_setup.append(CameraSetup(self, camera))

        fake_tiles_id_pairs = []
        for tile in sorted(os.listdir(f"{BASE_IMG_PATH}environments/{self.environment}/images/tiles/blocks")):
            if "fake" in tile:
                for variant in range(len(self.assets[tile])):
                    fake_tiles_id_pairs.append((tile, variant))

        if not hasattr(self, "fake_tile_groups"):
            self.fake_tile_groups = []
            for fake_tile in self.tilemap.extract(fake_tiles_id_pairs, keep=True, layers=tuple(self.tilemap.layers["fake_tiles"])):
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
        self.tilemap.extract(fake_tiles_id_pairs, layers=tuple(self.tilemap.layers["fake_tiles"]))

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
        self.shader.update_light()

    def save_game(self, slot=1):
        if hasattr(self, 'save_system'):
            return self.save_system.save_game(slot)
        return False

    def save_settings(self):
        if hasattr(self, 'save_system'):
            return self.save_system.save_settings()
        return False

    def load_settings(self):
        if hasattr(self, 'save_system'):
            return self.save_system.load_settings()
        return False

    def load_game(self, slot=1):
        if hasattr(self, 'save_system'):
            return self.save_system.load_game(slot)
        return False

    def update_transitions(self):
        for transition in self.transitions:
            if (self.player.rect().left <= transition['pos'][0] <= self.player.rect().right <= transition['pos'][0] + self.tile_size and
                    self.player.rect().bottom >= transition['pos'][1] >= self.player.rect().top):
                self.level_id = int(transition["destination"])
                self.level = self.get_file_name(self.environment, self.level_id)
                self.scroll_limits = self.scroll_limits_per_level[str(self.level_id)]
                delattr(self, "fake_tile_groups")
                self.load_level(self.level_id, transition_effect=False)
                self.player.pos = [transition["dest_pos"][0] * self.tile_size, transition["dest_pos"][1] * self.tile_size]

    def checkpoints_render_and_update(self, render_scroll):
        for checkpoint in self.checkpoints:
            if not self.tilemap.pos_visible(self.display, checkpoint["pos"], render_scroll, additional_offset=(16, 16)):
                continue
            pos = checkpoint["pos"]

            if self.current_checkpoint == checkpoint:
                checkpoint["state"] = 1

                # 1. Only create the animation object if we haven't already!
                if self.active_checkpoint_anim is None:
                    self.active_checkpoint_anim = self.assets['simple_campfire/activated'].copy()
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
            img = self.assets['simple_campfire/deactivated'].img()
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
                self.save_game(self.current_slot)

    def update_camera_setup(self):
        for camera in self.camera_setup:
            camera.update()

    def spike_hitbox_update(self, render_scroll):
        for spike_hitbox in self.spikes:
            if not self.player.noclip:
                if not spike_hitbox.circle_hitbox:
                    if self.player.collide_with(spike_hitbox.rect(), static_rect=True):
                        kill_player(self)
                else:
                    dx = self.player.pos[0] - spike_hitbox.pos[0]
                    dy = self.player.pos[1] - spike_hitbox.pos[1]
                    distance = math.sqrt(dx ** 2 + dy ** 2)
                    if distance < (self.player.size[0]/2 + spike_hitbox.size.get_width()/2) and self.player.collide_with(spike_hitbox.rect(), static_rect=True):
                        kill_player(self)


            if self.show_spikes_hitboxes:
                spike_hitbox.render(self.display, spike_hitbox.circle_hitbox, offset=render_scroll)

    def fake_tiles_render(self, offset=(0, 0)):
        group_to_remove = None
        for group in self.fake_tile_groups:
            opacity = 255
            for fake_tile in group:
                if self.tilemap.fake_tile_colliding_with_player(fake_tile):
                    self.fake_tiles_colliding_group = group.copy()
                    break

            if group == self.fake_tiles_colliding_group:
                self.fake_tiles_opacity = max(0, self.fake_tiles_opacity - 30)
                opacity = self.fake_tiles_opacity
                if opacity == 0:
                    group_to_remove=self.fake_tiles_colliding_group

            for fake_tile in group:
                img = self.assets[fake_tile["type"]][fake_tile['variant']].copy()
                img.fill((255, 255, 255, opacity),special_flags=pygame.BLEND_RGBA_MULT)

                self.display.blit(img, (
                    fake_tile['pos'][0]*self.tile_size - offset[0], fake_tile['pos'][1]*self.tile_size - offset[1]))

        if group_to_remove:
            if group_to_remove in self.fake_tile_groups:
                self.fake_tile_groups.remove(group_to_remove)
            self.fake_tiles_opacity = 255
            self.fake_tiles_colliding_group = []

    def main_game_logic(self):
        raw_dt = self.clock.tick(60)
        dt = 1#min(raw_dt / (1000.0 / 60.0), 3.0)

        self._update_world(dt)
        self._render_world()
        self._render_ui()

        if not self._handle_events():
            pygame.quit()
            sys.exit()

    def _update_world(self, dt):
        self.update_camera_setup()
        self.camera.update_camera()
        self.player.physics_process(self.dict_kb, dt)
        self.update_transitions()
        if self.teleporting:
            update_teleporter(self, self.tp_id)
        self.player.disablePlayerInput = (
                self.cutscene or self.moving_visual or self.teleporting
        )
        if not self.game_initialized:
            self.start_time = time.time()

    def _render_world(self):
        render_scroll = (round(self.scroll[0]), round(self.scroll[1]))
        display_level_bg(self, self.level_id)
        self.tilemap.render(self.display, offset=render_scroll)
        self.checkpoints_render_and_update(render_scroll)
        doors_render_and_update(self, render_scroll)
        render_activators(self, render_scroll)
        self.spike_hitbox_update(render_scroll)
        update_particles(self, render_scroll)
        particle_render(self, render_scroll)
        self.shader.display_level_fg(self.level)
        self.shader.apply_lighting(render_scroll)

    def _render_ui(self):
        update_bottom_text(self)
        if self.cutscene:
            draw_cutscene_border(self.display)
        self._render_transition()
        self._render_screenshake()
        death_handling(self, self.screen)
        self._finalize_frame()

    def _render_transition(self):
        if self.transition < 0:
            self.transition += 2
        if self.transition:
            self.player.disablePlayerInput = True
            surf = pygame.Surface(self.display.get_size())
            pygame.draw.circle(surf, (255, 255, 255),
                               (self.display.get_width() // 2, self.display.get_height() // 2),
                               (30 - abs(self.transition)) * 8)
            surf.set_colorkey((255, 255, 255))
            self.display.blit(surf, (0, 0))
        else:
            self.player.disablePlayerInput = False

    def _render_screenshake(self):
        self.screenshake = max(0, self.screenshake - 1)
        offset = (
            random.random() * self.screenshake - self.screenshake / 2,
            random.random() * self.screenshake - self.screenshake / 2,
        )
        self.screen.blit(
            pygame.transform.scale(self.display, self.screen.get_size()), offset
        )

    def _finalize_frame(self):
        if not self.game_initialized:
            self.game_initialized = True
            if not os.path.exists(f"saves/save_{self.current_slot}.json"):
                self.save_game(self.current_slot)



    def run(self):
        """
        The main program entry point.
        This function implements a state machine to switch between the Intro, Profile Menu, and Gameplay.
        """
        self.play_music("title_screen")
        self.load_settings()
        pygame.mouse.set_visible(False)
        while True:
            match self.state:
                case self.MENU_STATE:
                    self.menu.draw()
                case self.PLAYING_STATE:
                    self.main_game_logic()
                    self.menu.draw_player_souls()
            self.apply_brightness()
            pygame.display.update()


    def apply_brightness(self):
        width, height = self.screen.get_size()
        overlay = pygame.Surface((width, height),pygame.SRCALPHA)

        if self.brightness < 0.5:
            alpha = int((0.5-self.brightness) *2* 200)
            overlay.fill((0,0,0,alpha))
        elif self.brightness > 0.5:
            alpha = int((self.brightness-0.5) *2* 50)
            overlay.fill((255,255,255,alpha))
        else:
            return
        self.screen.blit(overlay, (0, 0))

    def play_music(self, name):
        self.music_sound_manager.play(name=name, loops=-1)

    def play_se(self, name):
        self.sound_effect_manager.play(name=name)

    def update_music_volume(self, volume):
        self.music_sound_manager.volume = volume
        self.music_sound_manager.set_volume(self.music_sound_manager.volume)

    def update_sound_effect_volume(self, volume):
        self.sound_effect_manager.volume = volume
        self.sound_effect_manager.set_volume(self.sound_effect_manager.volume)

    def update_master_volume(self, volume):
        self.master_volume = volume
        self.sound_effect_manager.master_volume = self.master_volume
        self.music_sound_manager.master_volume = self.master_volume

