import sys

from scripts.checkpoint import CheckPoint
# --- Game Script Imports ---
# These modules handle specific game logic like physics, entities, and UI.
from scripts.entities import *
from scripts.utils import *
from scripts.tilemap import Tilemap
from scripts.physics import Player
from scripts.particle import update_particles, particle_render
from scripts.activators import *
from scripts.user_interface import Menu
from scripts.saving import Save
from scripts.doors import Door, doors_render_and_update
from scripts.display import *
from scripts.camera import Camera
from scripts.text import load_game_texts, update_bottom_text
from scripts.sound import Sound
from scripts.pickup import Pickup

class LevelManager:
    def __init__(self, game):
        self.game = game
        self.first_level_id = 1
        game.level_id = self.first_level_id

    def update_map(self, level_id):
        self.game.tilemap.load(f"data/maps/{level_id:03d}.json")
        self.game.tilemap.tile_size = self.game.tile_size

    def load_level(self, level_id):
        self.update_map(level_id)

        self.game.levers = []
        self.game.doors = []
        self.game.spikes = []
        self.game.fake_tiles = []
        self.game.pickups = []
        self.game.leaf_spawners = []
        self.game.camera_zones = []
        for group_id in self.game.tilemap.tag_groups:
            group = self.game.tilemap.tag_groups[group_id]
            group_tags = group["tags"]
            match group_tags:
                case _ if "lever" in group_tags:
                    tag = group_tags["lever"]
                    for tile_loc, tile_layer in group["tiles"]:
                        self.game.tilemap.extract(tile_loc, tile_layer)
                        #self.game.levers.append(Lever(group_id, tile_pos, tag["target_group"]))
                        pass
                case _ if "door" in group_tags:
                    pass
                case _ if "spike" in group_tags:
                    for tile_loc, tile_layer in group["tiles"]:
                        tile = self.game.tilemap.extract(tile_loc, tile_layer)
                        tile_id, variant, rotation, flip_x, flip_y = self.game.tilemap.tile_manager.unpack_tile(tile)
                        image = self.game.tilemap.tile_manager.tiles[tile_id].images[variant]
                        pos = [float(val)*self.game.tile_size for val in tile_loc.split(";")]
                        self.game.spikes.append(Spike(self.game, pos, image, rotation))
                case _ if "fake_tile" in group_tags:
                    pass
                case _ if "checkpoint" in group_tags:
                    for tile_loc, tile_layer in group["tiles"]:
                        tile = self.game.tilemap.extract(tile_loc, tile_layer)
                        tile_id, variant, rotation, flip_x, flip_y = self.game.tilemap.tile_manager.unpack_tile(tile)
                        animation = self.game.tilemap.tile_manager.tiles[tile_id].images
                        pos = [float(val) * self.game.tile_size for val in tile_loc.split(";")]
                        self.game.checkpoints.append(CheckPoint(self.game, pos, animation))


            # Set scroll on player spawn position at the very start (before any save), it updates later in load_game function in saving.py

        for zone in self.game.tilemap.camera_zones:
            self.game.camera_zones.append([int(val) for val in zone.split(";")])

        target_x = self.game.player.rect.centerx  - self.game.display.get_width() / 2
        target_y = self.game.player.rect.centery  - self.game.display.get_height() / 2

        self.game.scroll = [target_x, target_y]

        # Reset VFX and interaction pools
        self.game.cutscene = False
        self.game.particles = []
        self.game.sparks = []
        self.game.transition = -30
        self.game.max_falling_depth = 50000000000
        self.game.shader.update_light()

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

        self.level_manager = LevelManager(self)
        self._init_display()
        self._init_assets()
        self.tilemap = Tilemap(self, self.tile_size)
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
        path = 'data/environments.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.environments = json.load(f)

        self.level = f"{self.level_id:03d}"
        self.tile_size = 16
        self.b_info = {
            "1": {"animated": True, "img_dur": 6, "loop": True, "path": f"environments/white_space/images/backgrounds"},
            "2": {"animated": False, "path": f"environments/green_cave/images/backgrounds"},
        }
        self.assets = {}
        self.assets.update(load_player())
        self.assets.update(load_backgrounds(self.b_info))
        self.assets.update(load_particles())

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
        self.camera_zones = []
        self.scroll_limits = {}
        self.screenshake = 0
        self.scroll = [0.0, 0.0]
        self.scroll_limits = {"x": [-5000, 5000], "y": [-5000, 5000]}

        # Player
        self.player = Player(self, self.tilemap, (100, 0), (16, 16))
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
        }

        # Activators / interactables
        self.activators = []
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

    def _camera_borders_check(self):
        for zone in self.camera_zones:
            left, right, top, bottom = zone[0], zone[0] + zone[2], zone[1], zone[1] + zone[3]
            if left <= self.player.pos[0] < right and top <= self.player.pos[1] < bottom:
                self.scroll_limits = {"x": [left, right], "y": [top, bottom]}
                return



    def toggle_hitboxes(self):
        self.player.show_hitbox = not self.player.show_hitbox
        self.show_spikes_hitboxes = not self.show_spikes_hitboxes
        #self.tilemap.show_collisions = not self.tilemap.show_collisions

    def set_keymap(self,bindings: dict):
        for cat in bindings:
            for bind in bindings[cat]:
                if bind.lower() == "show hitbox":
                    self.key_map["key_hitbox"] = bindings[cat][bind]
                elif bind.lower() == "no clip":
                    self.key_map["key_noclip"] = bindings[cat][bind]
                else:
                    self.key_map[f"key_{bind.lower()}"] = bindings[cat][bind]

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
            if (self.player.rect.left <= transition.pos[0] <= self.player.rect.right <= transition.pos[0] + self.tile_size and
                    self.player.rect.bottom >= transition.pos[1] >= self.player.rect.top):
                self.level_id = 2
                self.level = f"{self.level_id:03d}"
                self.scroll_limits = self.scroll_limits_per_level[str(self.level_id)]
                delattr(self, "fake_tile_groups")
                self.level_manager.load_level(self.level_id)
                self.player.pos = [8 * self.tile_size, 5 * self.tile_size]

    def _render_checkpoints(self, render_scroll):
        for checkpoint in self.checkpoints:
            checkpoint.render(render_scroll)



    def _update_spikes(self):
        if hasattr(self, "spikes"):
            for spike in self.spikes:
                spike.update()

    def _update_checkpoints(self):
        for checkpoint in self.checkpoints:
            checkpoint.update()



    def _render_spikes(self, render_scroll):
        if hasattr(self, "spikes"):
            for spike in self.spikes:
                spike.render(self.display, render_scroll)



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
                img = self.assets[fake_tile.type][fake_tile.variant].copy()
                img.fill((255, 255, 255, opacity),special_flags=pygame.BLEND_RGBA_MULT)

                self.display.blit(img, (
                    fake_tile.pos[0]*self.tile_size - offset[0], fake_tile.pos[1]*self.tile_size - offset[1]))

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
        self._camera_borders_check()
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

        self._update_spikes()
        self._update_checkpoints()


        self._render_spikes(render_scroll)
        self._render_checkpoints(render_scroll)





        doors_render_and_update(self, render_scroll)
        render_activators(self, render_scroll)
        #self.spike_hitbox_update(render_scroll)
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

