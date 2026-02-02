import json
import os
import time
import pygame as py

# Removed Boss import to match the new main script
from scripts.entities import DistanceEnemy, Enemy, Throwable
from scripts.sound import set_game_volume
from scripts.activators import Activator
from scripts.doors import Door


class Save:
    def __init__(self, game):
        self.game = game
        self.save_folder = "saves"
        self.ensure_save_folder_exists()

    def ensure_save_folder_exists(self):
        """Creates the save directory if it doesn't exist."""
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)

    def update_playtime(self, slot=1):
        save_path = os.path.join(self.save_folder, f"save_{slot}.json")

        if not os.path.exists(save_path):
            print(f"No save found in {save_path}")
            return False

        try:
            with open(save_path, 'r') as save_file:
                save_data = json.load(save_file)
            print("With menu time", time.time() - self.game.start_time + self.game.playtime)
            print("Without menu time: ", time.time() - self.game.start_time + self.game.playtime - self.game.menu_time)
            save_data["playtime"] = time.time() - self.game.start_time + self.game.playtime - self.game.menu_time

        except Exception as e:
            print(f"Error while loading the save: {e}")
            import traceback
            traceback.print_exc()
            return False

        try:
            with open(save_path, 'w') as save_file:
                json.dump(save_data, save_file, indent=4)
            print(f"Game saved successfully to {save_path}")
            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

    def save_game(self, slot=1):
        """
        Serializes current game state to a JSON file.
        Iterates through charged levels to save persistent changes (dead enemies, opened doors).
        """
        # Base structure
        save_data = {
            "player": {
                "position": self.game.spawn_point["pos"].copy(),
                "spawn_point": self.game.spawn_point,
            },
            "level": self.game.level,
            "timestamp": time.time(),
            "playtime": time.time() - self.game.start_time + self.game.playtime - self.game.menu_time,
        }

        py.image.save(self.game.screen, f"saves/slot_{slot}_thumb.png")

        # --- Save Persistent Level Data ---
        # We only save data for levels that the player has visited ("charged")

        # Write to file
        save_path = os.path.join(self.save_folder, f"save_{slot}.json")
        try:
            with open(save_path, 'w') as save_file:
                json.dump(save_data, save_file, indent=4)
            print(f"Game saved successfully to {save_path}")
            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

    def load_game(self, slot=1):
        """
        Loads the game state from JSON.
        Restores player position, settings, and reconstructs objects for visited levels.
        """
        save_path = os.path.join(self.save_folder, f"save_{slot}.json")

        if not os.path.exists(save_path):
            print(f"No save found in {save_path}")
            return False

        try:
            with open(save_path, 'r') as save_file:
                save_data = json.load(save_file)

            # --- Restore Core Game State ---
            level = save_data.get("level", 0)
            self.game.level = level
            self.game.current_slot = slot
            # --- Finalize Load ---
            # Set scroll to player position
            if "player" in save_data and "position" in save_data["player"]:
                self.game.scroll = list(save_data["player"]["position"])
            # Load the actual map tiles and background
            self.game.load_level(level, transition_effect=False)

            # Override player stats with saved stats
            if "player" in save_data:
                if "position" in save_data["player"]:
                    self.game.player.pos = save_data["player"]["position"]
                    self.game.scroll = [self.game.player.pos[0] - self.game.display.get_width()/2, self.game.player.pos[1] - self.game.display.get_height()]
                if "spawn_point" in save_data["player"]:
                    self.game.spawn_point = save_data["player"]["spawn_point"]
            self.game.playtime = save_data["playtime"]

            print(f"Game loaded successfully from {save_path}")
            return True

        except Exception as e:
            print(f"Error while loading the save: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_saves(self):
        """Returns a summary of all save files in the save folder."""
        saves = []
        for file in os.listdir(self.save_folder):
            if file.startswith("save_") and file.endswith(".json"):
                save_path = os.path.join(self.save_folder, file)
                try:
                    with open(save_path, 'r') as save_file:
                        save_data = json.load(save_file)

                    slot = int(file.split('_')[1].split('.')[0])
                    from datetime import datetime
                    save_date = datetime.fromtimestamp(save_data["timestamp"]).strftime("%Y-%m-%d")
                    level = save_data.get("level", 0)

                    save_info = {
                        "slot": slot,
                        "date": save_date,
                        "level": level,
                        "keyboard_layout": save_data.get("settings", {}).get("keyboard_layout", "unknown"),
                        "playtime": save_data.get("playtime", 0)
                    }

                    saves.append(save_info)
                except Exception as e:
                    print(f"Error reading save file {file}: {e}")
        return saves

    def delete_save(self, slot=1):
        save_path = os.path.join(self.save_folder, f"save_{slot}.json")
        if os.path.exists(save_path):
            os.remove(save_path)
            print(f"Save {slot} deleted")
            return True
        else:
            print(f"No save found in the slot {slot}")
            return False

    def get_latest_save(self):
        saves = self.list_saves()
        if not saves:
            return None
        saves.sort(key=lambda x: x["date"], reverse=True)
        return saves[0]["slot"]

    def save_settings(self):

        save_data = {
                "volume": self.game.volume,
                "keyboard_layout": self.game.keyboard_layout,
                "language": self.game.selected_language
            }

        save_path = os.path.join(self.save_folder, f"settings.json")
        try:
            with open(save_path, 'w') as save_file:
                json.dump(save_data, save_file, indent=4)
            print(f"Game saved successfully to {save_path}")
            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

    def load_settings(self):
        save_path = os.path.join(self.save_folder, f"settings.json")

        if not os.path.exists(save_path):
            print(f"No save found in {save_path}")
            return False

        try:
            with open(save_path, 'r') as save_file:
                save_data = json.load(save_file)

            # --- Restore Settings ---
            volume = save_data.get("volume", 0.5)
            set_game_volume(self.game, volume)
            self.game.keyboard_layout = save_data.get("keyboard_layout")
            self.game.selected_language = save_data.get("language", "English")
            if hasattr(self.game, "menu"):
                self.game.menu.update_settings_from_game()
        except Exception as e:
            print(f"Error while loading the save: {e}")
            import traceback
            traceback.print_exc()
            return False



# --- Global Helpers ---
def save_game(game, slot=1):
    if hasattr(game, 'save_system'):
        return game.save_system.save_game(slot)
    return False

def save_settings(game):
    if hasattr(game, 'save_system'):
        return game.save_system.save_settings()
    return False

def load_settings(game):
    if hasattr(game, 'save_system'):
        return game.save_system.load_settings()
    return False


def load_game(game, slot=1):
    if hasattr(game, 'save_system'):
        return game.save_system.load_game(slot)
    return False