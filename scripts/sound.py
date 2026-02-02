import pygame
import time
import os

def load_sounds(entity, sound_paths):#useful function to load sounds. And very useful for debugging when loading sounds

    for sound_key, path in sound_paths.items():
        if sound_key in entity.sounds and path:
            try:
                entity.sounds[sound_key] = pygame.mixer.Sound(path)
            except Exception as e:
                print(f"Erreur lors du chargement du son '{sound_key}': {e}")

def set_game_volume(game, volume):
    """Sets the master volume and updates the background music volume."""
    game.volume = max(0, min(1, volume))
    # Use pygame.mixer.music for background volume
    pygame.mixer.music.set_volume(game.volume)

def change_music(game, path):
    """Changes background music using the music module to prevent overlapping."""
    # Create tracker if it doesn't exist
    if not hasattr(game, 'current_music_path'):
        game.current_music_path = None

    # Only change if the path is different
    if game.current_music_path != path:
        try:
            # 1. Fade out the current music over 500ms
            pygame.mixer.music.fadeout(500)

            # 2. Load and play the new track
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(game.volume)
            pygame.mixer.music.play(loops=-1)

            # 3. Update the tracking variable
            game.current_music_path = path
        except Exception as e:
            print(f"Error changing music to {path}: {e}")
            game.current_music_path = None
