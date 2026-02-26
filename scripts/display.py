import pygame
import random
import time

def generate_fog(surface, color=(220, 230, 240), opacity=40):
    fog_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    fog_surface.fill((*color, opacity))
    surface.blit(fog_surface, (0, 0))
    
def create_light_mask(radius, color=(255, 255, 255), intensity=255, edge_softness=50, flicker=False):
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

def apply_lighting(game, render_scroll):
    """Apply darkness effect with player and other light sources"""
    # Create a surface for darkness
    darkness = pygame.Surface(game.display.get_size(), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, game.darkness_level))  # Semi-transparent black

    # Create and apply player light
    player_props = game.player_light
    player_light = create_light_mask(
        player_props["radius"],
        player_props["color"],
        player_props["intensity"],
        player_props["edge_softness"],
        player_props["flicker"]
    )

    # Calculate player position on screen
    player_screen_x = game.player.rect().centerx - render_scroll[0]
    player_screen_y = game.player.rect().centery - render_scroll[1]

    # Position for the light mask
    light_x = player_screen_x - player_props["radius"]
    light_y = player_screen_y - player_props["radius"]

    # Apply the player light mask to the darkness surface
    darkness.blit(player_light, (light_x, light_y), special_flags=pygame.BLEND_RGBA_SUB)

    # Process light-emitting tiles
    for light_tile in game.light_emitting_tiles:
        # Get position and properties
        pos = light_tile["pos"]
        light_type = light_tile.get("type", "torch")
        properties = game.light_properties[light_type]

        # Calculate screen position
        tile_screen_x = pos[0] - render_scroll[0]
        tile_screen_y = pos[1] - render_scroll[1]

        # Check if the light is visible on screen (with buffer)
        buffer = properties["radius"] * 2
        if (-buffer <= tile_screen_x <= game.display.get_width() + buffer and
                -buffer <= tile_screen_y <= game.display.get_height() + buffer):
            # Create light mask for this tile
            tile_light = create_light_mask(
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
    for light_obj in game.light_emitting_objects:
        if hasattr(light_obj, "pos") and hasattr(light_obj, "light_properties"):
            props = light_obj.light_properties

            # Calculate screen position
            obj_screen_x = light_obj.pos[0] - render_scroll[0]
            obj_screen_y = light_obj.pos[1] - render_scroll[1]

            # Create light mask for this object
            obj_light = create_light_mask(
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
    game.display.blit(darkness, (0, 0))

def register_light_emitting_tile(game, pos, light_type="torch"):
    """Register a new light-emitting tile at the given position"""
    if light_type in game.light_properties:
        game.light_emitting_tiles.append({
            "pos": pos,
            "type": light_type
        })

def register_light_emitting_object(game, obj, properties=None):
        """Register an object as a light source"""
        if not hasattr(obj, "light_properties") and properties:
            obj.light_properties = properties
        game.light_emitting_objects.append(obj)

def draw_cutscene_border(surf, color=(0, 0, 0), width=20, opacity=255):

        border_surface = pygame.Surface(surf.get_size(), pygame.SRCALPHA)

        # Draw top border
        pygame.draw.rect(border_surface, (*color, opacity), (0, 0, surf.get_width(), width))

        # Draw bottom border
        pygame.draw.rect(border_surface, (*color, opacity),
                         (0, surf.get_height() - width, surf.get_width(), width))


        # Blit the border onto the screen
        surf.blit(border_surface, (0, 0))

def move_visual(game, duration, pos):
    game.moving_visual = True
    game.visual_pos = pos
    game.visual_movement_duration = duration
    game.visual_start_time = time.time()

def update_camera(game):
        current_time = time.time()

        if game.moving_visual:
            elapsed_time = current_time - game.visual_start_time
            if elapsed_time < game.visual_movement_duration:
                game.scroll[0] += (game.visual_pos[0] - game.display.get_width() / 2 - game.scroll[0]) / 20
                game.scroll[1] += (game.visual_pos[1] - game.display.get_height() / 2 - game.scroll[1]) / 20
            else:
                game.moving_visual = False

        else:
            target_x = (game.player.rect().centerx if game.camera_center is None else game.camera_center[0]) - game.display.get_width() / 2
            target_y = (game.player.rect().centery if game.camera_center is None else game.camera_center[1]) - game.display.get_height() / 2

            level_limits = game.scroll_limits

            if level_limits["x"]:
                min_x, max_x = level_limits["x"]
                max_x -= game.display.get_width()
                target_x = max(min_x, min(target_x, max_x))

            if level_limits["y"]:
                min_y, max_y = level_limits["y"]
                max_y -= game.display.get_height()
                target_y = max(min_y, min(target_y, max_y))

            game.scroll[0] += (target_x - game.scroll[0]) / 20
            game.scroll[1] += (target_y - game.scroll[1]) / 20
            
def draw_health_bar(game, max_hearts=5):
    display_hp = max(10, game.player_hp) if game.player_hp > 0 else 0

    full_hearts = display_hp // 20
    half_heart = 1 if display_hp % 20 >= 10 else 0

    start_x = 20
    start_y = 20
    heart_spacing = 22

    for i in range(full_hearts):
        game.display.blit(game.assets['full_heart'], (start_x + (i * heart_spacing), start_y))

    if half_heart:
        game.display.blit(game.assets['half_heart'], (start_x + (full_hearts * heart_spacing), start_y))

    empty_hearts = max_hearts - full_hearts - half_heart
    for i in range(empty_hearts):
        pos = start_x + ((full_hearts + half_heart + i) * heart_spacing)
        game.display.blit(game.assets['empty_heart'], (pos, start_y))
        
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
    if map_id in (3,4):
        game.display.blit(pygame.transform.scale(game.assets['blue_cave/0'], game.display.get_size()), (0, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/1'], game.display.get_size()), (-game.scroll[0] / 10, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/2'], game.display.get_size()), (-game.scroll[0] / 30, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/3'], game.display.get_size()), (game.scroll[0] / 30, 0))
        display_bg(game.display, pygame.transform.scale(game.assets['blue_cave/4'], game.display.get_size()), (game.scroll[0] / 50, 0))

def draw_boss_health_bar(game, boss):
    if not game.bosses or boss.hp <= 0:
        return

    bar_width = 200
    bar_height = 6
    border_thickness = 1
    border_radius = 3

    bar_x = (game.display.get_width() - bar_width) // 2
    bar_y = 25

    health_percentage = max(0, boss.hp / boss.max_hp)
    current_bar_width = int(bar_width * health_percentage)

    border_color = (30, 30, 30)
    bg_color = (60, 60, 60)
    health_color = (133, 6, 6)

    shadow_offset = 2
    pygame.draw.rect(
        game.display,
        (20, 20, 20),
        (bar_x - border_thickness + shadow_offset,
         bar_y - border_thickness + shadow_offset,
         bar_width + (border_thickness * 2),
         bar_height + (border_thickness * 2)),
        0,
        border_radius + border_thickness
    )

    pygame.draw.rect(game.display,border_color,(bar_x - border_thickness,bar_y - border_thickness,bar_width + (border_thickness * 2),bar_height + (border_thickness * 2)),0, border_radius + border_thickness)

    pygame.draw.rect(game.display,bg_color,(bar_x, bar_y, bar_width, bar_height),0,border_radius)

    if current_bar_width > 0:
        right_radius = border_radius if current_bar_width >= border_radius * 2 else 0
        pygame.draw.rect(game.display,health_color,(bar_x, bar_y, current_bar_width, bar_height),0,border_radius, right_radius, border_radius, right_radius)

    if current_bar_width > 5:
        highlight_height = max(2, bar_height // 3)
        highlight_width = current_bar_width - 4
        pygame.draw.rect(game.display,(220, 60, 60),  (bar_x + 2, bar_y + 1, highlight_width, highlight_height),0,border_radius // 2)


    try:
        font = pygame.font.SysFont("Arial", 15)
    except:
        font = pygame.font.Font(None, 26)

    boss_name = boss.enemy_type if hasattr(boss, 'enemy_type') else "Wrath"

    text_surface = font.render(boss_name, True, (255, 255, 255))
    text_rect = text_surface.get_rect(centerx=bar_x + bar_width // 2, bottom=bar_y - 4)

    shadow_surface = font.render(boss_name, True, (0, 0, 0))
    shadow_rect = shadow_surface.get_rect(centerx=text_rect.centerx + 1, centery=text_rect.centery + 1)

    game.display.blit(shadow_surface, shadow_rect)
    game.display.blit(text_surface, text_rect)

def display_level_fg(game, map_id):
    if map_id in (0,1,2):
        generate_fog(game.display, color=(83, 48, 99), opacity=10)
    if map_id == 3:
        generate_fog(game.display, color=(28, 50, 73), opacity=90)
        
def update_light(game):
    level_info = game.light_infos[game.level]
    game.darkness_level = level_info["darkness_level"]

    game.player_light["radius"] = level_info["light_radius"]
    game.light_mask = pygame.Surface((game.light_radius * 2, game.light_radius * 2), pygame.SRCALPHA)
    create_light_mask(game.light_radius)

def screen_shake(game, strenght):
    game.screenshake = max(strenght, game.screenshake)

def toggle_fullscreen(game):
    game.fullscreen = not game.fullscreen

    if game.fullscreen:
        game.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.NOFRAME, vsync=1)
    else:
        game.screen = pygame.display.set_mode((1000, 600), pygame.RESIZABLE)
    game.menu.init_buttons()

        