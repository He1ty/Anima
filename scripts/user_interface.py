import time

import pygame
import pygame as py
import sys
import numpy as np
import cv2
import os
import datetime

from scripts.button import MenuButton, DiscreteSlider, ToggleSwitch, ArrowSelector
from scripts.display import toggle_fullscreen, check_screen
from scripts.utils import load_images, load_image
from scripts.text import load_game_font

class Menu:

    def __init__(self, game): #Basic definitions: Keyboard layout,languages, volume, screen resolutions,buttons configurations
        self.game = game
        self.screen = game.screen
        self.original_background = None

        self.cap = cv2.VideoCapture("assets/images/start_video.mp4")

        self.volume = 0.5

        self.dropdown_expanded = False
        self.dragging_volume = False
        self.options_visible = False

        self.BUTTON_WIDTH = 200
        self.BUTTON_HEIGHT = 50
        self.KNOB_RADIUS = 8

        self.slider_rect = py.Rect(50, 100, 200, 5)
        self.dropdown_rect = py.Rect(50, 150, 200, 30)
        self.keyboard_button_rect = py.Rect(50, 250, 200, 40)

        py.font.init()
        self.control_font = load_game_font(size=24)
        self.keyboard_font = load_game_font(size=20)
        self.button_font = load_game_font(size=36)
        self.hover_image = load_image("Opera_senza_titolo.png")
        self.hover2_image = py.transform.flip(load_image("Opera_senza_titolo.png"), True, False)

        self.button_font.set_bold(True)

        self.settings_categories = {
                                    "GAME" :
                                        {"LANGUAGE":
                                             {
                                                 "type": "multiple_choices",
                                                 "choices": self.game.languages,
                                                 "current": self.game.selected_language
                                             },
                                        "DEBUG MODE":
                                            {
                                            "type":"switch",
                                            "current": self.game.debug_mode
                                            }
                                        },

                                    "AUDIO":
                                        {"MAIN SOUND":
                                            {
                                                "type": "drag",
                                                "current": self.volume
                                            },
                                        "MUSIC":
                                            {
                                                "type": "drag",
                                                "current": self.game.music_sound_manager.volume
                                            },
                                        "SOUND EFFECTS":
                                            {
                                                "type": "drag",
                                                "current": self.game.sound_effect_manager.volume
                                            },
                                        "UI SOUNDS":
                                            {
                                                "type": "drag",
                                                "current": self.volume
                                            }
                                        },

                                    "VIDEO":
                                        {"FULL SCREEN":
                                             {"type" : "switch",
                                              "current": self.game.fullscreen},
                                        "V-SYNC" :
                                             {
                                                 "type" : "switch",
                                                 "current" : self.game.vsync_on
                                             },
                                        "BRIGHTNESS" :
                                             {
                                                 "type": "drag",
                                                 "current": self.game.brightness
                                             }
                                        },

                                    "KEYBOARD":
                                        {"Layout":
                                             {
                                                 "type":"multiple_choices",
                                                 "choices": ["AZERTY", "QWERTY"],
                                                 "current" : self.game.keyboard_layout
                                             },
                                        "Binds":
                                            {
                                                "type":"binds"
                                            }
                                         }
                                    }

        self.thumbs = {}
        for i in range(3):
            try:
                self.thumbs[i+1] = py.image.load(f"saves/slot_{i+1}_thumb.png")
            except FileNotFoundError:
                self.thumbs[i+1] = None

        self.COLORS = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "light_gray": (220, 220, 220),
            "medium_gray": (200, 200, 200),
            "dark_gray": (160, 160, 160),
            "highlight": (255, 255, 255, 50),
            "overlay": (0, 0, 0, 200),
            "dimmed": (255, 255, 255, 80)
        }

        self.title_buttons = []
        self.title_buttons_labels = ["PLAY","SETTINGS","QUIT"]
        self.title_command_nb = 0

        self.option_buttons = []
        self.option_buttons_labels = ["GAME","VIDEO","AUDIO","KEYBOARD"]
        self.option_command_nb = 0

        self.pause_buttons = []
        self.pause_buttons_labels = ["RESUME","SETTINGS","SAVE AND QUIT"]
        self.pause_command_nb = 0

        self.audio_buttons = []
        self.audio_buttons_labels = self.settings_categories["AUDIO"].keys()
        self.audio_command_nb = 0

        self.video_buttons = []
        self.video_buttons_labels = self.settings_categories["VIDEO"].keys()
        self.video_command_nb = 0

        self.game_buttons = []
        self.game_buttons_labels = self.settings_categories["GAME"].keys()
        self.game_command_nb = 0

        self.init_buttons()

    def init_buttons(self):
        """
        Initialize all the buttons for all the different menu ( Pause , Settings, etc. )
        """
        # We clear the current button list
        self.title_buttons = []
        self.option_buttons = []
        self.pause_buttons = []
        self.audio_buttons = []
        self.video_buttons = []
        self.game_buttons = []

        current_screen_size = self.screen.get_size()

        button_x = 3*current_screen_size[0] /4

        # TITLE SCREEN BUTTONS
        start_title_btn_y = (current_screen_size[1] / 2)
        button_y = start_title_btn_y

        for label in self.title_buttons_labels:
            button = MenuButton(label,self.button_font,(button_x,button_y),self.COLORS['white'])
            button_y += self.BUTTON_HEIGHT
            self.title_buttons.append(button)

        button_x = (current_screen_size[0]) / 2


        #  OPTION BUTTONS
        start_option_btn_y = (current_screen_size[1] - (len(self.option_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_option_btn_y

        for label in self.option_buttons_labels:
            button = MenuButton(label, self.button_font, (button_x, button_y), self.COLORS['white'])
            button_y += self.BUTTON_HEIGHT
            self.option_buttons.append(button)

        button_y = current_screen_size[1] - 90
        print(self.video_buttons)

        back_btn = MenuButton("BACK", self.button_font, (button_x, button_y), self.COLORS['white'])
        print(self.video_buttons)
        self.option_buttons.append(back_btn)

        #  PAUSE BUTTONS
        start_pause_btn_y =(current_screen_size[1] - (len(self.pause_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_pause_btn_y
        for label in self.pause_buttons_labels:
            button = MenuButton(label, self.button_font, (button_x, button_y), self.COLORS['white'])
            button_y += self.BUTTON_HEIGHT
            self.pause_buttons.append(button)

        #  AUDIO SETTINGS BUTTON

        button_x = (current_screen_size[0]) / 8
        start_audio_btn_y = (current_screen_size[1] - (len(self.audio_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_audio_btn_y
        for label in self.audio_buttons_labels:
            value = self.settings_categories["AUDIO"][label]["current"]
            button = DiscreteSlider(current_screen_size[0]-button_x-current_screen_size[0]*0.3-60,button_y,current_screen_size[0]*0.3,10,10,font=self.button_font,text=label+":",textx= button_x)
            button_y += self.BUTTON_HEIGHT
            button.set_normalized_value(float(value))
            self.audio_buttons.append(button)
        self.audio_buttons.append(back_btn)

        # VIDEO SETTINGS BUTTON

        button_x = (current_screen_size[0]) / 8

        start_video_btn = (current_screen_size[1] - (len(self.video_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_video_btn

        for label in self.video_buttons_labels:

            button = None
            value = self.settings_categories["VIDEO"][label]["current"]
            match self.settings_categories["VIDEO"][label]["type"]:
                case "drag":
                    button = DiscreteSlider(current_screen_size[0]-button_x-current_screen_size[0]*0.3-60,button_y,current_screen_size[0]*0.3,10,10,font=self.button_font,text=label+":",textx= button_x)
                    button.set_normalized_value(float(value))
                case "switch":
                    button = ToggleSwitch(current_screen_size[0]-button_x-60 ,button_y,font=self.button_font,text=label+":",textx= button_x)
                    button.set_state(bool(value))
            button_y += self.BUTTON_HEIGHT
            self.video_buttons.append(button)
        self.video_buttons.append(back_btn)

        # GAME SETTINGS BUTTON
        button_x = (current_screen_size[0]) / 8
        start_video_btn = (current_screen_size[1] - (len(self.game_buttons_labels) * self.BUTTON_HEIGHT)) / 2
        button_y = start_video_btn

        for label in self.game_buttons_labels:

            button = None
            value = self.settings_categories["GAME"][label]["current"]
            match self.settings_categories["GAME"][label]["type"]:
                case "drag":
                    button = DiscreteSlider(current_screen_size[0] - button_x - current_screen_size[0] * 0.3 - 60,
                                            button_y, current_screen_size[0] * 0.3, 10, 10, font=self.button_font,
                                            text=label + ":", textx=button_x)
                    button.set_normalized_value(float(value))
                case "switch":
                    button = ToggleSwitch(current_screen_size[0] - button_x - 60, button_y, font=self.button_font,
                                          text=label + ":", textx=button_x)
                    button.set_state(bool(value))
                case "multiple_choices":
                    button = ArrowSelector(current_screen_size[0] - current_screen_size[0] / 8 - current_screen_size[0] * 0.2 - 35,
                                           button_y, current_screen_size[0] * 0.2,40,self.button_font,
                                           self.settings_categories["GAME"][label]["choices"],text=label + ":", textx=button_x,text_color2=(255,255,255))
                    button.set_selected(str(value))
            button_y += self.BUTTON_HEIGHT
            self.game_buttons.append(button)
        self.game_buttons.append(back_btn)

    def save_current_button_states(self):
        """Update the dictionary with the current button state."""

        # SAVING AUDIO BUTTONS VALUES
        for label, button in zip(self.audio_buttons_labels, self.audio_buttons):
            self.settings_categories["AUDIO"][label]["current"] = button.get_normalized()

        # SAVING VIDEO BUTTONS VALUES
        for label, button in zip(self.video_buttons_labels, self.video_buttons):
            btn_type = self.settings_categories["VIDEO"][label]["type"]
            if btn_type == "drag":
                self.settings_categories["VIDEO"][label]["current"] = button.get_normalized()
            elif btn_type == "switch":
                self.settings_categories["VIDEO"][label]["current"] = button.get_state()

        # SAVING GAME BUTTONS VALUES
        for label, button in zip(self.game_buttons_labels, self.game_buttons):
            btn_type = self.settings_categories["GAME"][label]["type"]
            if btn_type == "drag":
                self.settings_categories["GAME"][label]["current"] = button.get_normalized()
            elif btn_type == "switch":
                self.settings_categories["GAME"][label]["current"] = button.get_state()
            elif btn_type == "multiple_choices":
                self.settings_categories["GAME"][label]["current"] = button.get_selected()

        return self.settings_categories

    def update_settings_categories(self):
        self.settings_categories = {
                                    "GAME" :
                                        {"LANGUAGE":
                                             {
                                                 "type": "multiple_choices",
                                                 "choices": self.game.languages,
                                                 "current": self.game.selected_language
                                             },
                                        "DEBUG MODE":
                                            {
                                            "type":"switch",
                                            "current": self.game.debug_mode
                                            }
                                        },

                                    "AUDIO":
                                        {"MAIN SOUND":
                                            {
                                                "type": "drag",
                                                "current": self.volume
                                            },
                                        "MUSIC":
                                            {
                                                "type": "drag",
                                                "current": self.game.music_sound_manager.volume
                                            },
                                        "SOUND EFFECTS":
                                            {
                                                "type": "drag",
                                                "current": self.game.sound_effect_manager.volume
                                            },
                                        "UI SOUNDS":
                                            {
                                                "type": "drag",
                                                "current": self.volume
                                            }
                                        },

                                    "VIDEO":
                                        {"FULL SCREEN":
                                             {"type" : "switch",
                                              "current": self.game.fullscreen},
                                        "V-SYNC" :
                                             {
                                                 "type" : "switch",
                                                 "current" : self.game.vsync_on
                                             },
                                        "BRIGHTNESS" :
                                             {
                                                 "type": "drag",
                                                 "current": self.game.brightness
                                             }
                                        },

                                    "KEYBOARD":
                                        {"Layout":
                                             {
                                                 "type":"multiple_choices",
                                                 "choices": ["AZERTY", "QWERTY"],
                                                 "current" : self.game.keyboard_layout
                                             },
                                        "Binds":
                                            {
                                                "type":"binds"
                                            }
                                         }
                                    }

    def handle_key_input(self,event,command_nb : int,max_index : int):

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                if command_nb == 0:
                    command_nb = 0
                else:
                    command_nb -= 1
            if event.key == pygame.K_DOWN:
                if command_nb == max_index:
                    command_nb = max_index
                else:
                    command_nb += 1

        return command_nb

    def update_settings_from_game(self):
        """
        Takes the saved settings to apply them to our keyboard and language (which is not graphically working for the moment)
        """
        self.volume = self.game.volume
        self.keyboard_layout = self.game.keyboard_layout.upper()
        if self.game.selected_language in self.languages:
            self.selected_language = self.game.selected_language

    def capture_background(self):
        """
        Uses the screen.copy of utils to do a screenshot of the game
        :return:
        """
        self.original_background = self.screen.copy()

    def delete_save_data(self, slot_id):
        """Deletes the JSON file and the associated thumbnail."""
        import os

        # 1. Path to your save files (Adjust based on your SaveSystem)
        save_path = f"saves/save_{slot_id}.json"
        thumb_path = f"saves/slot_{slot_id}_thumb.png"

        try:
            if os.path.exists(save_path):
                os.remove(save_path)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
                # Also clear from memory so it doesn't show up again
                self.thumbs[slot_id] = None
            print(f"Slot {slot_id} deleted successfully.")
        except Exception as e:
            print(f"Error deleting save: {e}")

    def profile_selection_menu(self):
        """
        Displays a 3-slot selection menu.
        Handles loading existing saves or starting new games.
        Returns True if a game starts/loads, False if BACK is pressed.
        """
        # 1. Setup background (darken current screen)
        current_screen = self.screen.copy()
        overlay = py.Surface(py.display.get_window_size(), py.SRCALPHA)
        overlay.fill((0, 0, 0, 230))  # Very dark overlay like the reference image

        # 2. Fetch Save Data
        saves = self.game.save_system.list_saves()
        used_slots = {save["slot"]: save for save in saves}


        slot_width = 800  # Wide slots
        slot_height = 110  # Height between dividers
        start_y = 160  # Where the first slot begins

        # Fonts (You might want a larger/more ornate font for the slot numbers)
        number_font = load_game_font(size=48)
        text_font = load_game_font(size=30)
        detail_font = load_game_font(size=22)
        number_font.set_bold(True)

        confirm_delete_id = None  # Tracks which slot is being asked for deletion
        running = True
        while running:

            # 3. Layout Configuration
            screen_w, screen_h = py.display.get_window_size()
            center_x = screen_w // 2
            overlay = py.Surface(py.display.get_window_size(), py.SRCALPHA)
            overlay.fill((0, 0, 0, 230))

            # Draw base layers
            self.screen.blit(py.transform.scale(current_screen, py.display.get_window_size()), (0, 0))
            self.screen.blit(overlay, (0, 0))
            mouse_pos = py.mouse.get_pos()

            # --- DRAW TITLE ---
            # Draw ornate separators above/below title (Placeholders for images)
            py.draw.line(self.screen, self.COLORS["white"], (center_x - 150, 60), (center_x + 150, 60), 2)
            title = self.button_font.render("SELECT PROFILE", True, self.COLORS["white"])
            self.screen.blit(title, (center_x - title.get_width() // 2, 70))
            py.draw.line(self.screen, self.COLORS["white"], (center_x - 150, 120), (center_x + 150, 120), 2)

            # --- DRAW SLOTS ---
            slot_rects = {}
            delete_rects = {}  # Stores locations of the 'X' buttons
            current_y = start_y

            for i in range(1, 4):  # Adjusted to 1-4 for Hollow Knight style
                slot_rect = py.Rect(center_x - slot_width // 2, current_y, slot_width, slot_height)
                slot_rects[i] = slot_rect
                is_hovered = slot_rect.collidepoint(mouse_pos)

                line_color = self.COLORS["white"] if is_hovered else (100, 100, 100)
                text_color = self.COLORS["white"] if is_hovered else (200, 200, 200)

                # Top Line
                py.draw.line(self.screen, line_color, (slot_rect.left, slot_rect.top), (slot_rect.right, slot_rect.top),
                             2)

                # --- Draw Slot Content ---
                # 1. Slot Number
                num_txt = number_font.render(f"{i}.", True, text_color)
                self.screen.blit(num_txt, (slot_rect.left + 20, slot_rect.centery - num_txt.get_height() // 2))

                # 2. IMAGE PREVIEW (The Box)
                # This creates a dark frame where the screenshot will live
                img_rect = py.Rect(slot_rect.left + 80, slot_rect.top + 10, 160, 90)
                py.draw.rect(self.screen, (30, 30, 30), img_rect)  # Background box
                py.draw.rect(self.screen, line_color, img_rect, 1)  # Border

                if i in used_slots:
                    save_data = used_slots[i]
                    # --- PREVIEW IMAGE LOGIC ---
                    if self.thumbs[i]:
                        img = py.transform.scale(self.thumbs[i], img_rect.size)
                        img.set_alpha(128)
                        self.screen.blit(img, img_rect.topleft)


                    # 3. Level Name (Large Text)
                    lvl_name = save_data.get('level_name', 'Unknown Region').upper()
                    lvl_txt = text_font.render(lvl_name, True, text_color)
                    self.screen.blit(lvl_txt, (img_rect.right + 30, slot_rect.top + 20))

                    # 4. Playtime and Date (Smaller Details)
                    # Convert seconds to HH:MM:SS format
                    play_seconds = save_data.get('playtime', 0)
                    time_str = str(datetime.timedelta(seconds=int(play_seconds)))

                    # Draw Sub-details
                    details = f"TIME: {time_str}    |    SAVED: {save_data['date']}"
                    detail_txt = detail_font.render(details, True, (150, 150, 150))
                    self.screen.blit(detail_txt, (img_rect.right + 30, slot_rect.top + 60))


                    # Position it on the far right of the slot
                    del_x_rect = py.Rect(slot_rect.right - 50, slot_rect.centery - 15, 30, 30)
                    delete_rects[i] = del_x_rect

                    is_del_hovered = del_x_rect.collidepoint(mouse_pos)
                    del_color = (255, 50, 50) if is_del_hovered else (150, 50, 50)

                    # Draw a simple 'X'
                    py.draw.line(self.screen, del_color, (del_x_rect.left, del_x_rect.top),
                                 (del_x_rect.right, del_x_rect.bottom), 3)
                    py.draw.line(self.screen, del_color, (del_x_rect.right, del_x_rect.top),
                                 (del_x_rect.left, del_x_rect.bottom), 3)

                else:
                    # EMPTY SLOT
                    ng_txt = text_font.render("NEW GAME", True, (100, 100, 100) if not is_hovered else (255, 255, 255))
                    self.screen.blit(ng_txt, (img_rect.right + 30, slot_rect.centery - ng_txt.get_height() // 2))


                current_y += slot_height

            # --- CONFIRMATION OVERLAY ---
            if confirm_delete_id is not None:
                # Draw a small popup box in the center
                popup_rect = py.Rect(center_x - 200, screen_h // 2 - 100, 400, 200)
                py.draw.rect(self.screen, (20, 20, 20), popup_rect)
                py.draw.rect(self.screen, self.COLORS["white"], popup_rect, 2)

                msg = text_font.render(f"DELETE PROFILE {confirm_delete_id}?", True, self.COLORS["white"])
                self.screen.blit(msg, (center_x - msg.get_width() // 2, popup_rect.top + 40))

                # Buttons for Yes / No
                yes_btn = py.Rect(center_x - 120, popup_rect.bottom - 60, 100, 40)
                no_btn = py.Rect(center_x + 20, popup_rect.bottom - 60, 100, 40)

                # Draw buttons (Hover logic omitted for brevity, but same as others)
                py.draw.rect(self.screen, (100, 0, 0), yes_btn)
                py.draw.rect(self.screen, (50, 50, 50), no_btn)
                yes_txt = text_font.render("YES", True, (255, 255, 255))
                no_txt = text_font.render("NO", True, (255, 255, 255))

                self.screen.blit(yes_txt,
                                 (yes_btn.centerx - yes_txt.get_width()/2, yes_btn.centery - 15))
                self.screen.blit(no_txt,
                                 (no_btn.centerx - no_txt.get_width()/2, no_btn.centery - 15))

            # --- DRAW BACK BUTTON ---
            back_rect = py.Rect(center_x - 60, screen_h - 80, 120, 40)
            is_back_hovered = back_rect.collidepoint(mouse_pos)
            back_color = self.COLORS["white"] if is_back_hovered else self.COLORS["light_gray"]
            back_txt = self.control_font.render("BACK", True, back_color)
            self.screen.blit(back_txt, (
                back_rect.centerx - back_txt.get_width() // 2, back_rect.centery - back_txt.get_height() // 2))

            py.display.flip()

            # --- EVENT HANDLING ---
            for event in py.event.get():
                if event.type == py.QUIT:
                    py.quit()
                    sys.exit()
                elif event.type == py.MOUSEBUTTONDOWN:
                    # Check slot clicks
                    # 1. Handle Confirmation Popup First
                    if confirm_delete_id is not None:
                        if yes_btn.collidepoint(event.pos):
                            # CALL DELETE LOGIC
                            self.delete_save_data(confirm_delete_id)
                            # Refresh data
                            saves = self.game.save_system.list_saves()
                            used_slots = {save["slot"]: save for save in saves}
                            confirm_delete_id = None
                        elif no_btn.collidepoint(event.pos):
                            confirm_delete_id = None
                        continue  # Skip other clicks while popup is active

                    # 2. Check Delete Icon Clicks
                    for slot_id, d_rect in delete_rects.items():
                        if d_rect.collidepoint(event.pos):
                            confirm_delete_id = slot_id
                            break

                    # 3. Check Slot Clicks (Only if not clicking delete)
                    if confirm_delete_id is None:
                        for slot_id, rect in slot_rects.items():
                            if rect.collidepoint(event.pos):
                                if slot_id in used_slots:
                                    # LOAD EXISTING GAME
                                    if self.game.load_game(slot_id):
                                        return True  # Game loaded successfully
                                else:
                                    # START NEW GAME
                                    self.game.level = 0
                                    self.game.load_level(self.game.default_level, transition_effect=False)
                                    # Crucial: Tell the game which slot is currently active for future saves
                                    self.game.current_slot = slot_id
                                    # Optional: Autosave immediately so the slot isn't empty next time
                                    # save_game(self.game, slot_id)
                                    return True  # New game started

                    # Check Back button click
                    if back_rect.collidepoint(event.pos):
                        running = False  # Exit menu, return to title screen video

        return False  # Back was pressed

    def draw_option_menu(self):

        current_screen_size = self.screen.get_size()
        if self.game.previous_state == self.game.title_state:
            self.draw_title_screen_background_animation()
        else:
            if self.original_background is not None:
                scaled_bg = py.transform.scale(self.original_background, current_screen_size)
                self.screen.blit(scaled_bg, (0, 0))
            else:
                self.screen.fill(self.COLORS["black"])

        overlay = py.Surface(current_screen_size, py.SRCALPHA)
        overlay.fill(self.COLORS["overlay"])
        self.screen.blit(overlay, (0, 0))


        options_title_color = self.COLORS["white"]
        options_title = self.button_font.render("OPTIONS", True, options_title_color)
        self.screen.blit(options_title, options_title.get_rect(center=(current_screen_size[0] / 2, 50)))
        top_image = load_image("Opera_senza_titolo 2.png")
        bottom_image = load_image("Opera_senza_titolo 1.png")
        image_x = (current_screen_size[0] - top_image.get_width()) // 2
        top_image_y = self.option_buttons[0].rect.y - top_image.get_height() - 20
        bottom_image_y = self.option_buttons[-2].rect.y + self.BUTTON_HEIGHT + 10

        self.top_image = top_image
        self.bottom_image = bottom_image
        self.top_image_pos = (image_x, top_image_y)
        self.bottom_image_pos = (image_x, bottom_image_y)

        self.screen.blit(self.top_image, self.top_image_pos)
        self.screen.blit(self.bottom_image,self.bottom_image_pos)

        for i,button in enumerate(self.option_buttons):
            if i == self.option_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()
            button.draw(self.screen)
        py.display.flip()

        for event in py.event.get():
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.option_command_nb = 0
                    self.options_visible = False
                    self.game.save_settings()
                    self.game.state = self.game.previous_state
                    self.game.previous_state = "SETTINGS"

            self.option_command_nb = self.handle_key_input(event,self.option_command_nb,len(self.option_buttons)-1)
            for button in self.option_buttons:

                if button.handle_event(event):
                    match button.text:
                        case "BACK":
                                self.option_command_nb = 0
                                self.options_visible = False
                                self.game.save_settings()
                                self.game.state = self.game.previous_state
                                self.game.previous_state = "SETTINGS"
                        case "AUDIO":
                                self.game.state = self.game.audio_setting_state
                        case "VIDEO":
                            self.game.state = self.game.video_setting_state
                        case "GAME":
                            self.game.state = self.game.game_settings_state
        return

    def draw_title_screen_background_animation(self):
        ret, frame = self.cap.read()
        if not ret:
            # Restart video loop
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if not ret or frame is None:
            return  # sécurité absolue

        # --- Video Processing ---
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (self.screen.get_width(), self.screen.get_height()))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = py.surfarray.make_surface(frame)
        self.screen.blit(frame, (0, 0))
        py.time.wait(30)

    def draw_game_settings_menu(self):
        current_screen_size = self.screen.get_size()
        if self.game.previous_state == self.game.title_state:
            self.draw_title_screen_background_animation()
        else:
            if self.original_background is not None:
                scaled_bg = py.transform.scale(self.original_background, current_screen_size)
                self.screen.blit(scaled_bg, (0, 0))
            else:
                self.screen.fill(self.COLORS["black"])

        overlay = py.Surface(current_screen_size, py.SRCALPHA)
        overlay.fill(self.COLORS["overlay"])
        self.screen.blit(overlay, (0, 0))

        game_title_color = self.COLORS["dimmed"] if self.dropdown_expanded else self.COLORS["white"]
        game_title = self.button_font.render("GAME", True, game_title_color)
        self.screen.blit(game_title, game_title.get_rect(center=(current_screen_size[0] / 2, 50)))

        for i,button in enumerate(self.game_buttons):
            if i == self.game_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()
            button.draw(self.screen)

        for event in py.event.get():
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_command_nb = 0
                    self.game.state = self.game.option_state
            self.game_command_nb = self.handle_key_input(event,self.game_command_nb,len(self.game_buttons)-1)
            for button in self.game_buttons:
                match button.text:
                    case "LANGUAGE:":
                        self.game.selected_language = button.get_selected()
                    case "DEBUG MODE:":
                        self.game.debug_mode = button.get_state()
                if button.handle_event(event) and isinstance(button,MenuButton):
                    self.game_command_nb = 0
                    self.game.state = self.game.option_state


        py.display.flip()

    def draw_audio_settings_menu(self):
        current_screen_size = self.screen.get_size()
        if self.game.previous_state == self.game.title_state:
            self.draw_title_screen_background_animation()
        else:
            if self.original_background is not None:
                scaled_bg = py.transform.scale(self.original_background, current_screen_size)
                self.screen.blit(scaled_bg, (0, 0))
            else:
                self.screen.fill(self.COLORS["black"])

        overlay = py.Surface(current_screen_size, py.SRCALPHA)
        overlay.fill(self.COLORS["overlay"])
        self.screen.blit(overlay, (0, 0))
        audio_title_color =  self.COLORS["white"]
        audio_title = self.button_font.render("AUDIO", True, audio_title_color)
        self.screen.blit(audio_title, audio_title.get_rect(center=(current_screen_size[0] / 2, 50)))

        for i, button in enumerate(self.audio_buttons):
            if i == self.audio_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()
            button.draw(self.screen)

        for event in py.event.get():
            for i,button in enumerate(self.audio_buttons):
                if button.handle_event(event):
                    self.game.state = self.game.option_state
                    self.audio_command_nb = 0
                match button.text:
                    case "MUSIC:":
                        self.game.update_music_volume(button.get_normalized())
                    case "SOUND EFFECTS:":
                        self.game.update_sound_effect_volume(button.get_normalized())

            self.audio_command_nb = self.handle_key_input(event, self.audio_command_nb, len(self.audio_buttons) -1)
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.audio_command_nb = 0
                    self.game.state = self.game.option_state





        py.display.flip()

    def draw_video_settings_menu(self):
        current_screen_size = self.screen.get_size()
        if self.game.previous_state == self.game.title_state:
            self.draw_title_screen_background_animation()
        else:
            if self.original_background is not None:
                scaled_bg = py.transform.scale(self.original_background, current_screen_size)
                self.screen.blit(scaled_bg, (0, 0))
            else:
                self.screen.fill(self.COLORS["black"])

        overlay = py.Surface(current_screen_size, py.SRCALPHA)
        overlay.fill(self.COLORS["overlay"])
        self.screen.blit(overlay, (0, 0))

        video_title_color = self.COLORS["dimmed"] if self.dropdown_expanded else self.COLORS["white"]
        video_title = self.button_font.render("VIDEO", True, video_title_color)
        self.screen.blit(video_title, video_title.get_rect(center=(current_screen_size[0] / 2, 50)))

        for i, button in enumerate(self.video_buttons):
            if i == self.video_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()

            button.draw(self.screen)

        for event in py.event.get():
            for  i,button in enumerate(self.video_buttons):
                if button.handle_event(event):

                    match button.text:
                        case "FULL SCREEN:":
                            self.game.fullscreen = button.get_state()
                    check_screen(self.game)
                    if isinstance(button, MenuButton):
                        self.video_command_nb = 0
                        self.game.state = self.game.option_state
            self.video_command_nb = self.handle_key_input(event, self.video_command_nb, len(self.video_buttons) - 1)
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.video_command_nb = 0
                    self.game.state = self.game.option_state



        py.display.flip()

    def draw_keyboard_settings_menu(self):
        return

    def draw_pause_menu(self):
        current_screen_size = self.screen.get_size()
        if self.original_background is not None:
            scaled_bg = py.transform.scale(self.original_background, current_screen_size)
            self.screen.blit(scaled_bg, (0, 0))
        else:
            self.screen.fill(self.COLORS["black"])

        overlay = py.Surface(current_screen_size, py.SRCALPHA)
        overlay.fill(self.COLORS["overlay"])
        self.screen.blit(overlay, (0, 0))

        top_image = load_image("Opera_senza_titolo 2.png")
        bottom_image = load_image("Opera_senza_titolo 1.png")
        image_x = (current_screen_size[0] - top_image.get_width()) // 2
        top_image_y = self.pause_buttons[0].rect.y - top_image.get_height() - 20
        bottom_image_y = self.pause_buttons[-1].rect.y + self.BUTTON_HEIGHT + 10

        self.top_image = top_image
        self.bottom_image = bottom_image
        self.top_image_pos = (image_x, top_image_y)
        self.bottom_image_pos = (image_x, bottom_image_y)

        self.screen.blit(self.top_image, self.top_image_pos)
        self.screen.blit(self.bottom_image, self.bottom_image_pos)

        for i,button in enumerate(self.pause_buttons):
            if i == self.pause_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()
            button.draw(self.screen)
        py.display.flip()

        for event in py.event.get():
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.pause_command_nb = 0
                    self.game.state = "PLAYING"
                    self.game.previous_state = "PAUSE"

            self.pause_command_nb = self.handle_key_input(event, self.pause_command_nb, len(self.pause_buttons) - 1)
            for button in self.pause_buttons:
                if button.handle_event(event):
                    match button.text:
                        case "RESUME":
                                self.pause_command_nb = 0
                                self.game.state = "PLAYING"
                                self.game.previous_state = "PAUSE"
                        case "SETTINGS":
                            self.game.state = "SETTINGS"
                            self.game.previous_state = "PAUSE"
                        case "SAVE AND QUIT":
                            self.game.save_system.update_playtime(self.game.current_slot)
                            self.game.save_game( self.game.current_slot)
                            settings_categories = self.save_current_button_states()
                            self.game.__init__(full_setup=False)
                            self.settings_categories = settings_categories
                            self.init_buttons()
                            self.game.state = self.game.title_state
                            self.game.previous_state = self.game.pause_state
                            self.game.music_sound_manager.play(name="title_screen",loops=-1)

    def draw_title_menu(self):
        self.draw_title_screen_background_animation()

        for i,button in enumerate(self.title_buttons):
            if i == self.title_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()
            button.draw(self.screen)

        for event in pygame.event.get():
            self.title_command_nb = self.handle_key_input(event, self.title_command_nb, len(self.title_buttons) - 1)
            if event.type == pygame.QUIT:
                self.cap.release()
                pygame.quit()
                sys.exit()
            for button in self.title_buttons:
                if button.handle_event(event):
                    match button.text:
                        case "PLAY":
                            self.game.previous_state = self.game.title_state
                            self.game.state = self.game.profile_selection_state
                        case "SETTINGS":
                            self.game.previous_state = self.game.title_state
                            self.game.state = self.game.option_state
                        case "QUIT":
                            self.cap.release()
                            pygame.quit()
                            sys.exit()

    def update_setting_by_button(self,button,setting):
        """
        Update a settings with te value given by the button.
        :param button: The button object
        :param setting: The settings to be modified
        :return:
        """
        if isinstance(button,MenuButton):
            pass
        if isinstance(button, ToggleSwitch):
            setting = button.get_state()
        if isinstance(button, DiscreteSlider):
            setting = button.get_normalized()
        if isinstance(button,ArrowSelector):
            setting = button.get_selected()
        return setting

