import json
import os
import time
from typing import SupportsFloat

import pygame as py

from scripts.display import check_screen


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
                # noinspection PyTypeChecker
                json.dump(save_data, save_file, indent=4)
            print(f"Playtime saved successfully to {save_path}")
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
                "current_checkpoint": self.game.current_checkpoint,
            },
            "camera": {
                "scroll_limits":self.game.spawn_point["scroll_limits"],
                "center":self.game.spawn_point["camera_center"],
                "cameras": self.game.spawn_point["cameras"]
            },
            "collected_souls": self.game.collected_souls,
            "doors": [],
            "activators":{},
            "level": self.game.level,
            "timestamp": time.time(),
            "playtime": time.time() - self.game.start_time + self.game.playtime - self.game.menu_time,
        }

        #Only the opened doors' and activated activators' ids are saved in save_data
        if hasattr(self.game, "doors"):
            for door in self.game.doors:
                if door.opened:
                    save_data["doors"].append(str(door.id))

        if hasattr(self.game, "activators"):
            for activator in self.game.activators:
                if activator.state == 1 and not activator.activated:
                    if activator.type in save_data["activators"]:
                        save_data["activators"][activator.type].append(activator.id)
                    else:
                        save_data["activators"][activator.type] = [activator.id]


        py.image.save(self.game.screen, f"saves/slot_{slot}_thumb.png")

        # --- Save Persistent Level Data ---
        # We only save data for levels that the player has visited ("charged")

        # Write to file
        save_path = os.path.join(self.save_folder, f"save_{slot}.json")
        try:
            with open(save_path, 'w') as save_file:
                # noinspection PyTypeChecker
                json.dump(save_data, save_file, indent=4)
            print(f"Game saved successfully to {save_path}")
            return True
        except Exception as e:
            print(f"Error saving game: {e}")
            return False

    def get_current_save(self, slot=1):
        save_path = os.path.join(self.save_folder, f"save_{slot}.json")

        if not os.path.exists(save_path):
            print(f"(get_current_save() function) : No save found in {save_path}")
            return False

        try:
            with open(save_path, 'r') as save_file:
                save_data = json.load(save_file)

        except Exception as e:
            print(f"Error while loading the save: {e}")
            import traceback
            traceback.print_exc()
            return False

        return save_data

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

            #Update players infos
            if "player" in save_data:
                if "position" in save_data["player"]:
                    self.game.player.pos = save_data["player"]["position"]
                if "spawn_point" in save_data["player"]:
                    self.game.spawn_point = save_data["player"]["spawn_point"]
                if "current_checkpoint" in save_data["player"]:
                    self.game.current_checkpoint = save_data["player"]["current_checkpoint"]

            if "camera" in save_data:
                if "scroll_limits" in save_data["camera"]:
                    self.game.scroll_limits = save_data["camera"]["scroll_limits"]
                if "center" in save_data["camera"]:
                    self.game.camera_center = save_data["camera"]["center"]

            if "collected_souls" in save_data:
               self.game.collected_souls = save_data["collected_souls"]

            if "playtime" in save_data:
               self.game.playtime = save_data["playtime"]

            #Load level
            self.game.load_level(level, transition_effect=False)

            #Update doors and activators state
            if "doors" in save_data:
                for door in self.game.doors:
                    if door.id in save_data["doors"]:
                        door.opened = True

            if "activators" in save_data:
                for activator in self.game.activators:
                    if activator.type in save_data["activators"]:
                        if activator.id in save_data["activators"][activator.type]:
                            activator.state = 1
                            activator.activated = False

            if "camera" in save_data:
                if "cameras" in save_data["camera"]:
                    for camera in self.game.camera_setup:
                        if str(camera.initial_state) in save_data["camera"]["cameras"]:
                            camera.scroll_limits = save_data["camera"]["cameras"][str(camera.initial_state)]["scroll_limits"]
                            if "center" in save_data["camera"]["cameras"][str(camera.initial_state)]:
                                camera.center = save_data["camera"]["cameras"][str(camera.initial_state)]["center"]

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
                "music_volume": self.game.music_sound_manager.volume,
                "SE_volume": self.game.sound_effect_manager.volume,
                "keyboard_layout": self.game.keyboard_layout,
                "language": self.game.selected_language,
                "fullscreen": self.game.fullscreen,
                "v-sync": self.game.vsync_on,
                "brightness": self.game.brightness,
                "debug_mode": self.game.debug_mode,
            }

        save_path = os.path.join(self.save_folder, f"settings.json")

        try:
            with open(save_path, 'w') as save_file:
                # noinspection PyTypeChecker
                json.dump(save_data, save_file, indent=4)
            print(f"Settings saved successfully to {save_path}")
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
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
            music_volume = save_data.get("music_volume", 0.5)
            self.game.music_sound_manager.set_volume(music_volume)
            se_volume = save_data.get("SE_volume", 0.5)
            self.game.sound_effect_manager.set_volume(se_volume)
            self.game.keyboard_layout = save_data.get("keyboard_layout")
            self.game.selected_language = save_data.get("language", "English")
            self.game.fullscreen = save_data.get("fullscreen", True)
            self.game.vsync_on = save_data.get("vsync_on", True)
            self.game.brightness = save_data.get("brightness", 0.5)
            self.game.debug_mode = save_data.get("debug_mode", False)

            check_screen(self.game)
            if hasattr(self.game, "menu"):
                self.game.menu.update_settings_categories()
                self.game.menu.init_buttons()
        except Exception as e:
            print(f"Error while loading the save: {e}")
            import traceback
            traceback.print_exc()
            return False
