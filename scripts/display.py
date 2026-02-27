import pygame
import random
import time

class Shader:

    def __init__(self, game):
        self.game = game

    def generate_fog(self, surface, color=(220, 230, 240), opacity=40):
        fog_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        fog_surface.fill((*color, opacity))
        surface.blit(fog_surface, (0, 0))

    def create_light_mask(self, radius, color=(255, 255, 255), intensity=255, edge_softness=50, flicker=False):
        actual_radius = radius
        if flicker and random.random() < 0.3:
            flicker_factor = 0.85 + random.random() * 0.3
            actual_radius = int(radius * flicker_factor)
            intensity = int(intensity * flicker_factor)

        light_mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        center = (radius, radius)

        steps = min(actual_radius, 100)

        for i in range(steps):
            r = actual_radius - (i * actual_radius / steps)

            # Calculate alpha based on distance from edge
            distance_factor = i / steps
            # Use a non-linear function for smoother falloff
            alpha = int(intensity * (distance_factor ** 0.8))  # Exponent < 1 creates a softer gradient

            # Apply color with calculated alpha
            light_color = color + (alpha,)
            pygame.draw.circle(light_mask, light_color, center, r)

        # Optional: Apply a small Gaussian blur if pygame has this capability
        # This would require an external library like pygame.transform.smoothscale
        # or implementing a custom blur function

        return light_mask

    def apply_lighting(self, render_scroll):
        """Apply darkness effect with player and other light sources"""
        # Create a surface for darkness
        darkness = pygame.Surface(self.game.display.get_size(), pygame.SRCALPHA)
        darkness.fill((0, 0, 0, self.game.darkness_level))  # Semi-transparent black

        # Create and apply player light
        player_props = self.game.player_light
        player_light = self.create_light_mask(
            player_props["radius"],
            player_props["color"],
            player_props["intensity"],
            player_props["edge_softness"],
            player_props["flicker"]
        )

        # Calculate player position on screen
        player_screen_x = self.game.player.rect().centerx - render_scroll[0]
        player_screen_y = self.game.player.rect().centery - render_scroll[1]

        # Position for the light mask
        light_x = player_screen_x - player_props["radius"]
        light_y = player_screen_y - player_props["radius"]

        # Apply the player light mask to the darkness surface
        darkness.blit(player_light, (light_x, light_y), special_flags=pygame.BLEND_RGBA_SUB)

        # Process light-emitting tiles
        for light_tile in self.game.light_emitting_tiles:
            # Get position and properties
            pos = light_tile["pos"]
            light_type = light_tile.get("type", "torch")
            properties = self.game.light_properties[light_type]

            # Calculate screen position
            tile_screen_x = pos[0] - render_scroll[0]
            tile_screen_y = pos[1] - render_scroll[1]

            # Check if the light is visible on screen (with buffer)
            buffer = properties["radius"] * 2
            if (-buffer <= tile_screen_x <= self.game.display.get_width() + buffer and
                    -buffer <= tile_screen_y <= self.game.display.get_height() + buffer):
                # Create light mask for this tile
                tile_light = self.create_light_mask(
                    properties["radius"],
                    properties["color"],
                    properties["intensity"],
                    properties["edge_softness"],
                    properties["flicker"]
                )

                # Apply light
                light_pos = (tile_screen_x - properties["radius"], tile_screen_y - properties["radius"])
                darkness.blit(tile_light, light_pos, special_flags=pygame.BLEND_RGBA_SUB)

        # Process light-emitting objects (enemies, items, etc.)
        for light_obj in self.game.light_emitting_objects:
            if hasattr(light_obj, "pos") and hasattr(light_obj, "light_properties"):
                props = light_obj.light_properties

                # Calculate screen position
                obj_screen_x = light_obj.pos[0] - render_scroll[0]
                obj_screen_y = light_obj.pos[1] - render_scroll[1]

                # Create light mask for this object
                obj_light = self.create_light_mask(
                    props.get("radius", 80),
                    props.get("color", (255, 255, 255)),
                    props.get("intensity", 200),
                    props.get("edge_softness", 30),
                    props.get("flicker", False)
                )

                # Apply light
                light_pos = (obj_screen_x - props["radius"], obj_screen_y - props["radius"])
                darkness.blit(obj_light, light_pos, special_flags=pygame.BLEND_RGBA_SUB)

        # Apply the darkness to the display
        self.game.display.blit(darkness, (0, 0))

    def register_light_emitting_tile(self, pos, light_type="torch"):
        """Register a new light-emitting tile at the given position"""
        if light_type in self.game.light_properties:
            self.game.light_emitting_tiles.append({
                "pos": pos,
                "type": light_type
            })

    def display_level_fg(self, map_id):
        if map_id in (0, 1, 2):
            self.generate_fog(self.game.display, color=(83, 48, 99), opacity=0)
        if map_id == 3:
            self.generate_fog(self.game.display, color=(28, 50, 73), opacity=90)

    def update_light(self):
        level_info = self.game.light_infos[self.game.level]
        self.game.darkness_level = level_info["darkness_level"]

        self.game.player_light["radius"] = level_info["light_radius"]
        self.game.light_mask = pygame.Surface((self.game.light_radius * 2, self.game.light_radius * 2), pygame.SRCALPHA)
        self.create_light_mask(self.game.light_radius)

    def register_light_emitting_object(self, obj, properties=None):
        """Register an object as a light source"""
        if not hasattr(obj, "light_properties") and properties:
            obj.light_properties = properties
        self.game.light_emitting_objects.append(obj)

def display_bg(surf, img, pos):
    n = pos[0]//img.get_width()
    if pos[0] - n*img.get_width() > 0:
        surf.blit(img, (pos[0] - n* img.get_width(), pos[1]))
        surf.blit(img, (pos[0] - (n+1)*img.get_width() - 1, pos[1]))

    elif pos[0] + n*img.get_width() < 0:
        surf.blit(img, (pos[0] + (n+1)*img.get_width(), pos[1]))
        surf.blit(img, (pos[0] + n* img.get_width(), pos[1]))
        
def display_level_bg(game, map_id):
    if map_id in (0, 1, 2):
        game.display.blit(game.assets['green_cave/0'], (0, 0))
        display_bg(game.display, game.assets['green_cave/1'], (game.scroll[0]/20, 0))
        game.display.blit(game.assets['green_cave/2'], (0, 0))
        fog_surface = pygame.Surface(game.display.get_size(), pygame.SRCALPHA)
        fog_surface.fill((0,0,0,100))
        game.display.blit(fog_surface, (0, 0))


    if map_id in (3,4):
        game.display.blit(pygame.transform.scale(game.assets['blue_cave/0'], game.display.get_size()), (0, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/1'], game.display.get_size()), (-game.scroll[0] / 10, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/2'], game.display.get_size()), (-game.scroll[0] / 30, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/3'], game.display.get_size()), (game.scroll[0] / 30, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/4'], game.display.get_size()), (game.scroll[0] / 50, 0))

def draw_cutscene_border(surf, color=(0, 0, 0), width=20, opacity=255):

    border_surface = pygame.Surface(surf.get_size(), pygame.SRCALPHA)

    # Draw top border
    pygame.draw.rect(border_surface, (*color, opacity), (0, 0, surf.get_width(), width))

    # Draw bottom border
    pygame.draw.rect(border_surface, (*color, opacity),
                     (0, surf.get_height() - width, surf.get_width(), width))

    # Blit the border onto the screen
    surf.blit(border_surface, (0, 0))

def toggle_fullscreen(game):
    game.fullscreen = not game.fullscreen

    if game.fullscreen:
        game.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME, vsync=1)
    else:
        game.screen = pygame.display.set_mode((1000, 600), pygame.RESIZABLE)
    game.menu.init_buttons()

        