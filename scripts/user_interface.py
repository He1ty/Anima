import time

import pygame
import pygame as py
import sys
import numpy as np
import cv2

from scripts.button import MenuButton, DiscreteSlider, ToggleSwitch, ArrowSelector,SaveSlotUI
from scripts.display import  check_screen
from scripts.keybind_menu import ControlsMenu
from scripts.utils import load_images, load_image, Animation
from scripts.text import load_game_font

class Menu:
    # --- State Management --- #
    TITLE_STATE = "START_SCREEN"
    PAUSE_STATE = "PAUSE"
    OPTION_STATE = "SETTINGS"
    AUDIO_SETTING_STATE = "AUDIO_SETTINGS"
    VIDEO_SETTING_STATE = "VIDEO_SETTINGS"
    GAME_SETTING_STATE = "GAME_SETTINGS"
    KEYBOARD_STATE = "KEYBOARD_SETTINGS"
    PROFILE_SELECTION_STATE = "PROFILE_SELECTION"


    def __init__(self, game):
        """
        Basic definitions: Keyboard layout,languages, volume, screen resolutions,buttons configurations
        """
        self.game = game
        self.screen = game.screen
        self.SW, self.SH = self.screen.get_size()
        self.menu_state = self.TITLE_STATE
        self.previous_state = None

        self.original_background = None

        self.cap = cv2.VideoCapture("assets/images/start_video.mp4")

        self.volume = 0.5

        self.BUTTON_WIDTH = self.SW / 5
        self.BUTTON_HEIGHT = self.SH / 12

        py.font.init()
        self.control_font = load_game_font(size=24)
        self.keyboard_font = load_game_font(size=20)
        self.title_font = load_game_font(size=int(self.SH*0.07))
        self.button_font = load_game_font(size=int(self.SH*0.06))


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
                                                "current": self.game.master_volume
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
                                                "current": self.game.master_volume
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
                self.thumbs[i+1] = load_image("entities/player/idle/0.png")
            except FileNotFoundError:
                self.thumbs[i+1] = None

        self.COLORS = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "light_gray": (220, 220, 220),
            "medium_gray": (200, 200, 200),
            "dark_gray": (160, 160, 160),
            "highlight": (255, 255, 255, 50),
            "overlay": (0, 0, 0),
            "dimmed": (255, 255, 255, 80)
        }

        self.title_buttons = []
        self.title_buttons_labels = ["PLAY","SETTINGS","QUIT"]
        self.title_command_nb = 0

        self.profile_selection_slots = []
        self.profile_command_nb = 0
        self.delete_command_nb = 0
        self.delete_slot_id = None

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

        self.controls_menu = None
        self.controls_command_nb = 0

        self.is_souls_collected = False
        self.souls_collected_timer = 0

        self.init_buttons()

        # --- Souls Animation --- #
        self.souls_animation = Animation(load_images('pickups/soul/idle'),5,True)
        self.souls_pos = []
        self.souls_end_pos = [self.SH/12, self.SH/12]
        self.souls_start_size = [4 * self.SH / 75, 4 * self.SH / 75]
        self.nb_souls_pos = [self.SH/12 +self.SW*0.04, self.SH/12]

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
        self.profile_selection_slots = []


        button_x = 3*self.SW /4

        # TITLE SCREEN BUTTONS
        start_title_btn_y = (self.SH / 2)
        button_y = start_title_btn_y

        for label in self.title_buttons_labels:
            button = MenuButton(self,label,self.button_font,(button_x,button_y),self.COLORS['white'])
            button_y += self.BUTTON_HEIGHT
            self.title_buttons.append(button)

        button_x = self.SW / 2


        #  OPTION BUTTONS
        start_option_btn_y = (self.SH - (len(self.option_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_option_btn_y

        for label in self.option_buttons_labels:
            button = MenuButton(self,label, self.button_font, (button_x, button_y), self.COLORS['white'])
            button_y += self.BUTTON_HEIGHT
            self.option_buttons.append(button)

        button_y = self.SH - self.SH*0.18
        back_btn = MenuButton(self,"BACK", self.button_font, (button_x, button_y), self.COLORS['white'])
        self.option_buttons.append(back_btn)

        #  PAUSE BUTTONS
        start_pause_btn_y =(self.SH - (len(self.pause_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_pause_btn_y
        for label in self.pause_buttons_labels:
            button = MenuButton(self,label, self.button_font, (button_x, button_y), self.COLORS['white'])
            button_y += self.BUTTON_HEIGHT
            self.pause_buttons.append(button)

        #  AUDIO SETTINGS BUTTON

        button_x = self.SW / 8
        start_audio_btn_y = (self.SH - (len(self.audio_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_audio_btn_y
        for label in self.audio_buttons_labels:
            value = self.settings_categories["AUDIO"][label]["current"]
            button = DiscreteSlider(self,self.SW * 0.64 -button_x,button_y,self.SW*0.3,self.SH/60,10,font=self.button_font,text=label+":",textx= button_x)
            button_y += self.BUTTON_HEIGHT
            button.set_normalized_value(float(value))
            self.audio_buttons.append(button)
        self.audio_buttons.append(back_btn)

        # VIDEO SETTINGS BUTTON

        button_x = self.SW / 8

        start_video_btn = (self.SH - (len(self.video_buttons_labels) * self.BUTTON_HEIGHT) ) / 2
        button_y = start_video_btn

        for label in self.video_buttons_labels:

            button = None
            value = self.settings_categories["VIDEO"][label]["current"]
            match self.settings_categories["VIDEO"][label]["type"]:
                case "drag":
                    button = DiscreteSlider(self,self.SW * 0.64 -button_x,button_y,self.SW*0.3,self.SH/60,10,font=self.button_font,text=label+":",textx= button_x)
                    button.set_normalized_value(float(value))
                case "switch":
                    button = ToggleSwitch(self,self.SW * 0.94-button_x ,button_y,width=int(self.SW*0.06),height=int(self.SH/20),font=self.button_font,text=label+":",textx= button_x)
                    button.set_state(bool(value))
            button_y += self.BUTTON_HEIGHT
            self.video_buttons.append(button)
        self.video_buttons.append(back_btn)

        # GAME SETTINGS BUTTON
        button_x = self.SW / 8
        start_video_btn = (self.SH - (len(self.game_buttons_labels) * self.BUTTON_HEIGHT)) / 2
        button_y = start_video_btn

        for label in self.game_buttons_labels:

            button = None
            value = self.settings_categories["GAME"][label]["current"]
            match self.settings_categories["GAME"][label]["type"]:
                case "drag":
                    button = DiscreteSlider(self,self.SW * 0.64 -button_x,button_y,
                                            self.SW*0.3,self.SH/60,10,font=self.button_font,
                                            text=label+":",textx= button_x)
                    button.set_normalized_value(float(value))
                case "switch":
                    button = ToggleSwitch(self,self.SW * 0.94-button_x ,button_y,width=int(self.SW*0.06),
                                          height=int(self.SH/20),font=self.button_font,text=label+":",
                                          textx= button_x)
                    button.set_state(bool(value))
                case "multiple_choices":
                    button = ArrowSelector(self,self.SW * 0.64,button_y, self.SW * 0.2,self.SH/15,self.button_font,
                                           self.settings_categories["GAME"][label]["choices"],text=label + ":", textx=button_x,text_color2=(255,255,255))
                    button.set_selected(str(value))
            button_y += self.BUTTON_HEIGHT
            self.game_buttons.append(button)
        self.game_buttons.append(back_btn)

        # PROFILE SELECTION SLOTS
        saves = self.game.save_system.list_saves()
        used_slots = {save["slot"]: save for save in saves}

        slot_width = self.SW * 0.7
        slot_height = (11*self.SH)/60
        start_y = (4*self.SH)/15
        slot_x = (self.SW - slot_width) / 2

        fonts = {
            "number": load_game_font(size=int(self.SH*0.08)),
            "text": load_game_font(size=int(self.SH*0.05)),
            "detail": load_game_font(size=int(self.SH*0.03)),
        }
        fonts["number"].set_bold(True)

        for i in range(1, 4):
            slot = SaveSlotUI(self,
                slot_id=i,
                x=slot_x,
                y=start_y + (i - 1) * slot_height,
                width=slot_width,
                height=slot_height,
                fonts=fonts,
                colors=self.COLORS,
            )
            save_data = used_slots.get(i, None)
            thumb = self.thumbs.get(i, None) if hasattr(self, "thumbs") else None
            slot.update_data(save_data=save_data, thumbnail=thumb)
            self.profile_selection_slots.append(slot)
        self.profile_selection_slots.append(back_btn)

        self.controls_menu = ControlsMenu(self,
            screen=self.screen,
            game=self.game,
            title_font=self.title_font,  # même police que les autres menus
            button_font=self.button_font
        )

    def reload_menu(self):
        self.screen = self.game.screen
        self.SW, self.SH = self.screen.get_size()
        self.title_font = load_game_font(size=int(self.SH * 0.07))
        self.button_font = load_game_font(size=int(self.SH * 0.06))
        self.BUTTON_WIDTH = self.SW / 5
        self.BUTTON_HEIGHT = self.SH / 12
        self.souls_end_pos = [self.SH * 0.1, self.SH * 0.1]
        self.souls_start_size = [4 * self.SH / 75, 4 * self.SH / 75]
        self.nb_souls_pos = [self.SH * 0.1+self.SW*0.04, self.SH * 0.1]
        self.save_current_button_states()
        self.init_buttons()

    def draw(self):
        match self.menu_state:
            case self.TITLE_STATE:
                self.draw_title_menu()
            case self.OPTION_STATE:
                self.draw_option_menu()
            case self.AUDIO_SETTING_STATE:
                self.draw_audio_settings_menu()
            case self.VIDEO_SETTING_STATE:
                self.draw_video_settings_menu()
            case self.GAME_SETTING_STATE:
                self.draw_game_settings_menu()
            case self.KEYBOARD_STATE:
                self.draw_keyboard_settings_menu()
            case self.PROFILE_SELECTION_STATE:
                self.draw_profile_selection_menu()
            case self.PAUSE_STATE:
                self.draw_pause_menu()


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
                                                "current": self.game.master_volume
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

    def draw_delete_confirm_popup(self, confirm_delete_id, text_font):
        """Draws the delete confirmation popup. Returns (yes_btn_rect, no_btn_rect)."""
        current_screen_size = self.screen.get_size()
        center_x = self.SW // 2

        popup_rect = py.Rect(center_x - int(self.SW/5), self.SH // 2 - self.SH//6, self.SW*0.4, self.SH//3)
        py.draw.rect(self.screen, (20, 20, 20), popup_rect)
        py.draw.rect(self.screen, self.COLORS["white"], popup_rect, 2)

        msg = text_font.render(f"DELETE PROFILE {confirm_delete_id}?", True, self.COLORS["white"])
        self.screen.blit(msg, (center_x - msg.get_width() // 2, popup_rect.top + 40))

        yes_btn = py.Rect(center_x - self.SW*0.12, popup_rect.bottom - self.SH/10, self.SW/10, self.SH/15)
        no_btn = py.Rect(center_x + self.SW*0.02, popup_rect.bottom - self.SH/10, self.SW/10, self.SH/15)

        yes_color = (150,0,0) if self.delete_command_nb == 1 else (100,0,0)
        no_color = (100,100,100) if self.delete_command_nb == 0 else (50,50,50)

        py.draw.rect(self.screen, yes_color, yes_btn)
        py.draw.rect(self.screen, no_color, no_btn)

        yes_txt = text_font.render("YES", True, (255, 255, 255))
        no_txt = text_font.render("NO", True, (255, 255, 255))
        self.screen.blit(yes_txt, (yes_btn.centerx - yes_txt.get_width() // 2, yes_btn.centery - self.SH/40))
        self.screen.blit(no_txt, (no_btn.centerx - no_txt.get_width() // 2, no_btn.centery - self.SH/40))

        return yes_btn, no_btn

    def draw_profile_selection_menu(self):
        """
        Draws the profile selection menu on the screen.
        :return:
        """
        current_screen_size = self.screen.get_size()
        if self.previous_state == self.TITLE_STATE:
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
        options_title = self.title_font.render("SELECT PROFILE", True, options_title_color)
        self.screen.blit(options_title, options_title.get_rect(center=(self.SW / 2, 50)))


        if self.delete_slot_id is not None:
            self.draw_delete_confirm_popup(self.delete_slot_id, self.profile_selection_slots[0].text_font)
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT and self.delete_command_nb == 1:
                        self.delete_command_nb = 0
                    if event.key == pygame.K_LEFT and self.delete_command_nb == 0:
                        self.delete_command_nb = 1
                    if event.key == pygame.K_RETURN:
                        match self.delete_command_nb:
                            case 0:
                                self.delete_slot_id = None
                                self.delete_command_nb = 0
                            case 1:
                                # CALL DELETE LOGIC
                                self.delete_save_data(self.delete_slot_id)
                                # Refresh data
                                saves = self.game.save_system.list_saves()
                                used_slots = {save["slot"]: save for save in saves}
                                save_data = used_slots.get(self.delete_slot_id, None)
                                self.profile_selection_slots[self.delete_slot_id-1].update_data(save_data=save_data)
                                self.delete_slot_id = None
                                self.delete_command_nb = 0
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            if event.type == pygame.KEYDOWN:
                self.profile_command_nb = self.handle_key_input(event, self.profile_command_nb, len(self.profile_selection_slots)-1)
                if event.key == pygame.K_ESCAPE:
                    self.menu_state = self.TITLE_STATE
                    self.profile_command_nb = 0
            for slots in self.profile_selection_slots:
                action = slots.handle_event(event)
                match action:
                    case True:
                        self.menu_state = self.TITLE_STATE
                        self.profile_command_nb = 0
                    case "LOAD":
                        if self.game.load_game(slots.slot_id):
                            self.souls_collected_timer = 0
                            self.is_souls_collected = False
                            self.game.state = self.game.PLAYING_STATE
                            self.profile_command_nb = 0
                            self.game.play_music(f"level_{self.game.level}")
                            pygame.mouse.set_visible(False)
                    case "START":
                        # START NEW GAME
                        self.souls_collected_timer = 0
                        self.is_souls_collected = False
                        self.game.level = 0
                        self.game.load_level(self.game.default_level, transition_effect=False)
                        # Crucial: Tell the game which slot is currently active for future saves
                        self.game.current_slot = slots.slot_id
                        self.game.state = self.game.PLAYING_STATE
                        self.game.play_music(f"level_{self.game.level}")
                        pygame.mouse.set_visible(False)
                    case "DELETE":
                        self.delete_slot_id = slots.slot_id
        for i, slot in enumerate(self.profile_selection_slots):
            if i == self.profile_command_nb:
                slot.start_hover_effect()
            else:
                slot.end_hover_effect()
            slot.draw(self.screen)

    def draw_option_menu(self):

        current_screen_size = self.screen.get_size()
        if self.previous_state == self.TITLE_STATE:
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
        options_title = self.title_font.render("OPTIONS", True, options_title_color)
        self.screen.blit(options_title, options_title.get_rect(center=(self.SW / 2, 50)))
        top_image = load_image("ui/Opera_senza_titolo 2.png",size=(self.SW*0.16,self.SH*0.08))
        bottom_image = load_image("ui/Opera_senza_titolo 1.png",size=(self.SW*0.16,self.SH*0.08))
        image_x = (self.SW - top_image.get_width()) // 2
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

        for event in py.event.get():
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.option_command_nb = 0
                    self.game.save_settings()
                    self.menu_state = self.previous_state
                    self.previous_state = "SETTINGS"

            self.option_command_nb = self.handle_key_input(event,self.option_command_nb,len(self.option_buttons)-1)
            for button in self.option_buttons:

                if button.handle_event(event):
                    match button.text:
                        case "BACK":
                                self.option_command_nb = 0
                                self.game.save_settings()
                                self.menu_state = self.previous_state
                                self.previous_state = "SETTINGS"
                        case "AUDIO":
                                self.menu_state = self.AUDIO_SETTING_STATE
                        case "VIDEO":
                            self.menu_state = self.VIDEO_SETTING_STATE
                        case "GAME":
                            self.menu_state = self.GAME_SETTING_STATE
                        case "KEYBOARD":
                            self.menu_state = self.KEYBOARD_STATE
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
        if self.previous_state == self.TITLE_STATE:
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

        game_title_color = self.COLORS["white"]
        game_title = self.title_font.render("GAME", True, game_title_color)
        self.screen.blit(game_title, game_title.get_rect(center=(self.SW / 2, 50)))

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
                    self.menu_state = self.OPTION_STATE
            self.game_command_nb = self.handle_key_input(event,self.game_command_nb,len(self.game_buttons)-1)
            for button in self.game_buttons:
                match button.text:
                    case "LANGUAGE:":
                        self.game.selected_language = button.get_selected()
                    case "DEBUG MODE:":
                        self.game.debug_mode = button.get_state()
                if button.handle_event(event) and isinstance(button,MenuButton):
                    self.game_command_nb = 0
                    self.menu_state = self.OPTION_STATE

    def draw_audio_settings_menu(self):
        current_screen_size = self.screen.get_size()
        if self.previous_state == self.TITLE_STATE:
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
        audio_title = self.title_font.render("AUDIO", True, audio_title_color)
        self.screen.blit(audio_title, audio_title.get_rect(center=(self.SW / 2, 50)))

        for i, button in enumerate(self.audio_buttons):
            if i == self.audio_command_nb:
                button.start_hover_effect()
            else:
                button.end_hover_effect()
            button.draw(self.screen)

        for event in py.event.get():
            for i,button in enumerate(self.audio_buttons):
                if button.handle_event(event):
                    self.menu_state = self.OPTION_STATE
                    self.audio_command_nb = 0
                match button.text:
                    case "MUSIC:":
                        self.game.update_music_volume(button.get_normalized())
                    case "SOUND EFFECTS:":
                        self.game.update_sound_effect_volume(button.get_normalized())
                    case "MAIN SOUND:":
                        self.game.update_master_volume(button.get_normalized())

            self.audio_command_nb = self.handle_key_input(event, self.audio_command_nb, len(self.audio_buttons) -1)
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.audio_command_nb = 0
                    self.menu_state = self.OPTION_STATE

    def draw_video_settings_menu(self):
        current_screen_size = self.screen.get_size()
        if self.previous_state == self.TITLE_STATE:
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

        video_title_color = self.COLORS["white"]
        video_title = self.title_font.render("VIDEO", True, video_title_color)
        self.screen.blit(video_title, video_title.get_rect(center=(self.SW / 2, 50)))
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
                        self.menu_state = self.OPTION_STATE
                if button.text == "BRIGHTNESS:":
                    self.game.brightness = button.get_normalized()
            self.video_command_nb = self.handle_key_input(event, self.video_command_nb, len(self.video_buttons) - 1)
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.video_command_nb = 0
                    self.menu_state = self.OPTION_STATE

    def draw_keyboard_settings_menu(self):
        self.draw_title_screen_background_animation()
        self.controls_menu.draw_controls_menu()
        for event in pygame.event.get():
            result = self.controls_menu.handle_event(event)
            if result == "back":
                self.controls_command_nb = 0
                self.controls_menu.scroll_y = 0
                self.controls_menu.target_scroll = 0
                self.menu_state = self.OPTION_STATE
        self.controls_menu.draw_controls_menu()

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

        top_image = load_image("ui/Opera_senza_titolo 2.png",size=(self.SW*0.16,self.SH*0.08))
        bottom_image = load_image("ui/Opera_senza_titolo 1.png",size=(self.SW*0.16,self.SH*0.08))
        image_x = (self.SW - top_image.get_width()) // 2
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

        for event in py.event.get():
            if event.type == py.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.pause_command_nb = 0
                    self.game.state = self.game.PLAYING_STATE
                    self.previous_state = self.PAUSE_STATE

            self.pause_command_nb = self.handle_key_input(event, self.pause_command_nb, len(self.pause_buttons) - 1)
            for button in self.pause_buttons:
                if button.handle_event(event):
                    match button.text:
                        case "RESUME":
                                self.pause_command_nb = 0
                                self.game.state = self.game.PLAYING_STATE
                                self.previous_state = self.PAUSE_STATE
                        case "SETTINGS":
                            self.menu_state = self.OPTION_STATE
                            self.previous_state = self.PAUSE_STATE
                        case "SAVE AND QUIT":
                            self.game.save_system.update_playtime(self.game.current_slot)
                            self.game.save_game( self.game.current_slot)
                            settings_categories = self.save_current_button_states()
                            self.game.__init__(full_setup=False)
                            self.settings_categories = settings_categories
                            self.init_buttons()
                            self.menu_state = self.TITLE_STATE
                            self.previous_state = self.PAUSE_STATE
                            self.game.music_sound_manager.play(name="title_screen",loops=-1)

    def draw_title_menu(self):
        #self.draw_title_screen_background_animation()

        current_screen_size = self.screen.get_size()
        overlay = py.Surface(current_screen_size, py.SRCALPHA)
        overlay.fill(self.COLORS["overlay"])
        self.screen.blit(overlay, (0, 0))

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
                            self.previous_state = self.TITLE_STATE
                            self.menu_state = self.PROFILE_SELECTION_STATE
                        case "SETTINGS":
                            self.previous_state = self.TITLE_STATE
                            self.menu_state = self.OPTION_STATE
                        case "QUIT":
                            self.cap.release()
                            pygame.quit()
                            sys.exit()

    def draw_player_souls(self):
        if not self.is_souls_collected:
            return



        self.souls_animation.update()

        # --- Progression normalisée (0.0 → 1.0) ---
        duration = 120
        t = self.souls_collected_timer / duration  # 0.0 à 1.0

        nb_souls = self.button_font.render(f"x{self.game.nb_souls-1}",True,self.COLORS["white"])if self.souls_collected_timer <duration/2 else self.button_font.render(f"x{self.game.nb_souls}",True,self.COLORS["white"])
        self.screen.blit(nb_souls,nb_souls.get_rect(center=self.nb_souls_pos))

        # --- Easing : ease-in (accélère vers la fin) ---
        t_eased = t ** 2  # ou t ** 3 pour plus prononcé

        # --- Interpolation position ---
        start_pos = self.souls_pos
        end_pos = self.souls_end_pos

        self.souls_pos[0] = start_pos[0] + (end_pos[0] - start_pos[0]) * t_eased
        self.souls_pos[1] = start_pos[1] + (end_pos[1] - start_pos[1]) * t_eased

        # --- Interpolation taille (rétrécit en approchant) ---
        start_size = self.souls_start_size  # ex: [60, 60]
        end_size = [20, 20]

        current_w = int(start_size[0] + (end_size[0] - start_size[0]) * t_eased)
        current_h = int(start_size[1] + (end_size[1] - start_size[1]) * t_eased)

        # --- Fade out progressif ---
        alpha = int(255 * (1 - t_eased))

        # --- Rendu ---
        souls_icon = pygame.transform.scale(self.souls_animation.img(), (current_w, current_h))
        souls_icon.set_alpha(alpha)

        soul_rect = souls_icon.get_rect(centerx=int(self.souls_pos[0]), centery=int(self.souls_pos[1]))
        self.screen.blit(souls_icon, soul_rect)

        # --- Timer ---
        self.souls_collected_timer += 1
        if self.souls_collected_timer >= duration:
            self.souls_collected_timer = 0
            self.is_souls_collected = False

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

