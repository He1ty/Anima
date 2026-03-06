import time
import pygame
import json
import os


def load_game_font(size=36):
    """
    This function tries to load a font for the game, falling back to alternatives if the primary font fails
    :param size:
    :return:
    """

    try:
        return pygame.font.SysFont('Times New Roman', size, bold=True)
    except Exception:
        try:
            times_path = os.path.join(os.path.dirname(__file__), 'fonts', 'TimesNewRoman-Bold.ttf')
            if os.path.exists(times_path):
                return pygame.font.Font(times_path, size)
        except Exception:
            pass

    FALLBACK_FONTS = [
        'DejaVuSans-Bold.ttf',
        'FreeMono.ttf',
        'LiberationMono-Bold.ttf'
    ]

    for fallback in FALLBACK_FONTS:
        try:
            path = os.path.join(os.path.dirname(__file__), 'fonts', fallback)
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        except Exception:
            pass

    return pygame.font.SysFont('serif', size, bold=True)


def load_game_texts():
    # This function loads game text content from a JSON file
    try:
        with open("data/texts.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading texts: {e}")
        return {}


def display_bottom_text(game, text_key, duration=2.0, color=(255, 255, 255)):
    """Display text at the bottom of the screen"""
    level_str = str(game.level)
    if level_str in game.game_texts and text_key in game.game_texts[level_str]:
        text = game.game_texts[level_str][text_key]
        game.bottom_text = {
            'text': text,
            'color': color,
            'end_time': time.time() + duration,
            'opacity': 255
        }
    else:
        print(f"Text not found: level {level_str}, key {text_key}")


def update_bottom_text(game):
    """Update and render the bottom text display"""
    if not hasattr(game, 'bottom_text') or game.bottom_text is None:
        return

    current_time = time.time()
    remaining_time = game.bottom_text['end_time'] - current_time

    # Fade out in the last 0.5 seconds
    if remaining_time < 0.5 and remaining_time > 0:
        game.bottom_text['opacity'] = int(255 * (remaining_time / 0.5))

    # Remove text if time is up
    if remaining_time <= 0:
        game.bottom_text = None
        return

    # Render the text
    try:
        font = load_game_font(size=16)
    except:
        font = pygame.font.Font(None, 20)

    text_surface = font.render(game.bottom_text['text'], True, game.bottom_text['color'])
    text_surface.set_alpha(game.bottom_text['opacity'])

    # Create shadow for better readability
    shadow_surface = font.render(game.bottom_text['text'], True, (0, 0, 0))
    shadow_surface.set_alpha(game.bottom_text['opacity'] * 0.7)

    # Position at bottom center of screen
    screen_width = game.display.get_width()
    screen_height = game.display.get_height()

    text_rect = text_surface.get_rect(center=(screen_width // 2, screen_height - 30))
    shadow_rect = shadow_surface.get_rect(center=(screen_width // 2 + 2, screen_height - 28))

    # Draw background box for better visibility
    padding = 10
    box_rect = pygame.Rect(
        text_rect.left - padding,
        text_rect.top - padding,
        text_rect.width + padding * 2,
        text_rect.height + padding * 2
    )

    # Semi-transparent background
    background = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
    background.fill((0, 0, 0, int(180 * (game.bottom_text['opacity'] / 255))))
    game.display.blit(background, box_rect.topleft)

    # Draw the text
    game.display.blit(shadow_surface, shadow_rect)
    game.display.blit(text_surface, text_rect)