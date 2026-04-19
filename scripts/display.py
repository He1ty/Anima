import pygame
import random

class Shader:

    def __init__(self, game):
        self.game = game
        self.display = game.display

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
        player_screen_x = self.game.player.rect.centerx - render_scroll[0]
        player_screen_y = self.game.player.rect.centery - render_scroll[1]

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
        level_info = self.game.light_infos[self.game.level_id]
        self.game.darkness_level = level_info["darkness_level"]

        self.game.player_light["radius"] = level_info["light_radius"]
        self.game.light_mask = pygame.Surface((self.game.light_radius * 2, self.game.light_radius * 2), pygame.SRCALPHA)
        self.create_light_mask(self.game.light_radius)

    def register_light_emitting_object(self, obj, properties=None):
        """Register an object as a light source"""
        if not hasattr(obj, "light_properties") and properties:
            obj.light_properties = properties
        self.game.light_emitting_objects.append(obj)

    def apply_chromatic_aberration(self, offset_x, offset_y):
        """
        Takes a surface and returns a new surface with chromatic aberration applied.
        """
        self.display = self.game.display
        width, height = self.display.get_size()

        # 2. Create copies for the Red, Green, and Blue channels
        r_surf = self.display.copy()
        g_surf = self.display.copy()
        b_surf = self.display.copy()

        # 3. Isolate the channels using BLEND_RGB_MULT
        # This multiplies the pixels by the given color.
        # E.g., multiplying by pure red (255,0,0) removes all green and blue.
        r_surf.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
        g_surf.fill((0, 255, 0), special_flags=pygame.BLEND_RGB_MULT)
        b_surf.fill((0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)

        # 4. Create a black final surface to compose the channels back together
        final_surf = pygame.Surface((width, height))

        # 5. Blit them together using BLEND_RGB_ADD to reconstruct the original colors
        # Offset the Red channel positively, and the Blue channel negatively
        final_surf.blit(r_surf, (offset_x, offset_y), special_flags=pygame.BLEND_RGB_ADD)
        final_surf.blit(g_surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)  # Green stays centered
        final_surf.blit(b_surf, (-offset_x, -offset_y), special_flags=pygame.BLEND_RGB_ADD)

        self.game.display = final_surf

def display_bg(surf, img, pos):
    n = pos[0]//img.get_width()
    if pos[0] - n*img.get_width() > 0:
        surf.blit(img, (pos[0] - n* img.get_width(), pos[1]))
        surf.blit(img, (pos[0] - (n+1)*img.get_width() - 1, pos[1]))

    elif pos[0] + n*img.get_width() < 0:
        surf.blit(img, (pos[0] + (n+1)*img.get_width(), pos[1]))
        surf.blit(img, (pos[0] + n* img.get_width(), pos[1]))
        
def display_level_bg(game, map_id):
    environment = str(map_id)
    if environment in game.assets:
        pygame.draw.rect(game.display, (0, 0, 0), game.display.get_rect())
        game.assets[environment].update()
        game.display.blit(pygame.transform.scale(game.assets[environment].img(), game.display.get_size()), (0, 0))
        fog_surface = pygame.Surface(game.display.get_size(), pygame.SRCALPHA)
        fog_surface.fill((0, 0, 0, 190))
        game.display.blit(fog_surface, (0, 0))
    else:
        game.display.blit(pygame.transform.scale(game.assets[f'{2}/0'], game.display.get_size()) , (0, 0))
        display_bg(game.display, pygame.transform.scale(game.assets[f'{2}/1'], game.display.get_size()), (game.scroll[0]/20, 0))
        game.display.blit(pygame.transform.scale(game.assets[f'{2}/2'], game.display.get_size()), (0, 0))
        fog_surface = pygame.Surface(game.display.get_size(), pygame.SRCALPHA)
        fog_surface.fill((0,0,0,100))
        game.display.blit(fog_surface, (0, 0))

def draw_cutscene_border(surf, color=(0, 0, 0), width=20, opacity=255):

    border_surface = pygame.Surface(surf.get_size(), pygame.SRCALPHA)

    # Draw top border
    pygame.draw.rect(border_surface, (*color, opacity), (0, 0, surf.get_width(), width))

    # Draw bottom border
    pygame.draw.rect(border_surface, (*color, opacity),
                     (0, surf.get_height() - width, surf.get_width(), width))

    # Blit the border onto the screen
    surf.blit(border_surface, (0, 0))

def check_screen(game):
    if game.fullscreen:
        game.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME | pygame.DOUBLEBUF, vsync=game.vsync_on)
    else:
        game.screen = pygame.display.set_mode((game.SCREEN_WIDTH, game.SCREEN_HEIGHT),vsync=game.vsync_on)

    game.menu.reload_menu()

def toggle_fullscreen(game):
    game.fullscreen = not game.fullscreen
    check_screen(game)



