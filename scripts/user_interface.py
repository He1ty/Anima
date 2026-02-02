import time

import pygame as py
import sys
import numpy as np
import cv2
import os
import datetime
from scripts.sound import set_game_volume
from scripts.utils import load_images, load_image
from scripts.text import load_game_font
from scripts.saving import save_game, load_game, load_settings, save_settings

class Menu:

    def __init__(self, game): #Basic definitions: Keyboard layout,languages, volume, screen resolutions,buttons configurations
        self.game = game
        self.screen = game.screen
        self.original_background = None

        self.volume = 0.5
        self.languages = ["Français", "English", "Español"]
        self.selected_language = self.languages[1]

        self.keyboard_layout = "AZERTY"

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

    def update_settings_from_game(self):#Takes the saved settings to apply them to our keyboard and language(which is not graphycally working for the moment)
        self.volume = self.game.volume
        self.keyboard_layout = self.game.keyboard_layout
        if self.game.selected_language in self.languages:
            self.selected_language = self.game.selected_language

    def capture_background(self):#uses the screen.copy of utils to do a screenshot of the game
        self.original_background = self.screen.copy()

    def _get_centered_buttons(self, current_screen_size):#compute and return buttons like RESUME centered on the screen.Very boring to read but useful to resize the screen easily
        buttons = {}

        if self.options_visible:
            button_x = (current_screen_size[0] - self.BUTTON_WIDTH) // 2
            buttons["BACK"] = py.Rect(button_x, current_screen_size[1] - 90, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        else:
            button_x = (current_screen_size[0] - self.BUTTON_WIDTH) // 2

            total_button_height = self.BUTTON_HEIGHT * 3
            total_spacing = 20 * 4
            total_content_height = total_button_height + total_spacing

            start_y = (current_screen_size[1] - total_content_height) // 2

            top_image = load_image("Opera_senza_titolo 1.png")
            bottom_image = load_image("Opera_senza_titolo 2.png")

            top_image_x = (current_screen_size[0] - top_image.get_width()) // 2
            top_image_y = start_y - top_image.get_height() - 20

            buttons["RESUME"] = py.Rect(button_x, start_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
            buttons["OPTIONS"] = py.Rect(button_x, start_y + (self.BUTTON_HEIGHT + 20) * 1, self.BUTTON_WIDTH,
                                         self.BUTTON_HEIGHT)
            buttons["QUIT"] = py.Rect(button_x, start_y + (self.BUTTON_HEIGHT + 20) * 2, self.BUTTON_WIDTH,
                                      self.BUTTON_HEIGHT)

            bottom_image_x = (current_screen_size[0] - bottom_image.get_width()) // 2
            bottom_image_y = buttons["QUIT"].bottom + 10

            self.top_image = top_image
            self.bottom_image = bottom_image
            self.top_image_pos = (top_image_x, top_image_y)
            self.bottom_image_pos = (bottom_image_x, bottom_image_y)

        return buttons

    def _draw_buttons(self, buttons):#Also very long. The function does 3 things: Hover effect, display the "arrows" images at the sides of the buttons, and "blacken" the other buttons when the language menu is expanded
        if self.dropdown_expanded and self.options_visible:
            for text, rect in buttons.items():
                label = self.button_font.render(text, True, self.COLORS["dimmed"])
                text_width = label.get_width()
                text_height = label.get_height()
                text_x = rect.x + (rect.width - text_width) // 2
                text_y = rect.y + (rect.height - text_height) // 2
                self.screen.blit(label, (text_x, text_y))
            return

        mouse_pos = py.mouse.get_pos()
        for text, rect in buttons.items():
            label = self.button_font.render(text, True, self.COLORS["light_gray"])
            text_width = label.get_width()
            text_height = label.get_height()

            text_color = self.COLORS["light_gray"]

            if rect.collidepoint(mouse_pos):
                text_color = (255, 255, 255)

            text_x = rect.x + (rect.width - text_width) // 2
            text_y = rect.y + (rect.height - text_height) // 2

            label = self.button_font.render(text, True, text_color)
            self.screen.blit(label, (text_x, text_y))

            if rect.collidepoint(mouse_pos):
                image_x = text_x - self.hover_image.get_width() - 5
                image_y = rect.y + (rect.height - self.hover_image.get_height()) // 2
                self.screen.blit(self.hover_image, (image_x, image_y))

                image_x2 = text_x + text_width + 5
                image_y2 = rect.y + (rect.height - self.hover2_image.get_height()) // 2
                self.screen.blit(self.hover2_image, (image_x2, image_y2))

    def _draw_volume_control(self):#Draw the volume control option and the Hover effect
        if not self.options_visible:
            return 0

        if self.dropdown_expanded:
            return 0

        mouse_pos = py.mouse.get_pos()
        is_hovered = self.slider_rect.collidepoint(mouse_pos) or py.Rect(self.slider_rect.x - 10, self.slider_rect.y - 10,self.slider_rect.width + 20, self.slider_rect.height + 20).collidepoint(mouse_pos)

        vol_text = self.control_font.render("Volume:", True, self.COLORS["white"])
        self.screen.blit(vol_text, (self.slider_rect.x, self.slider_rect.centery - vol_text.get_height() // 2))

        slider_start_x = self.slider_rect.x + vol_text.get_width() + 20
        slider_width = self.slider_rect.width
        slider_y = self.slider_rect.centery

        self.slider_rect = py.Rect(slider_start_x, slider_y - 2, slider_width, 4)

        py.draw.rect(self.screen, self.COLORS["dark_gray"], self.slider_rect, border_radius=2)

        if is_hovered:
            highlight_rect = py.Rect(self.slider_rect.x - 5, self.slider_rect.y - 5,
                                     self.slider_rect.width + 10, self.slider_rect.height + 10)
            highlight_surface = py.Surface((highlight_rect.width, highlight_rect.height), py.SRCALPHA)
            py.draw.rect(highlight_surface, self.COLORS["highlight"],
                         (0, 0, highlight_rect.width, highlight_rect.height), border_radius=4)
            self.screen.blit(highlight_surface, (highlight_rect.x, highlight_rect.y))

        knob_x = self.slider_rect.x + int(self.volume * self.slider_rect.width)
        py.draw.circle(self.screen, self.COLORS["white"],
                       (knob_x, self.slider_rect.centery),
                       self.KNOB_RADIUS)

        percent_text = self.control_font.render(f"{int(self.volume * 100)}%", True, self.COLORS["white"])
        self.screen.blit(percent_text,
                         (self.slider_rect.right + 10, self.slider_rect.centery - percent_text.get_height() // 2))

        return knob_x

    def _draw_language_dropdown(self):#Display the current language. If expanded display three buttons. And hover effect over every one of these buttons
        if not self.options_visible:
            return []

        mouse_pos = py.mouse.get_pos()

        lang_title = self.control_font.render("Language:", True, self.COLORS["white"])
        self.screen.blit(lang_title, (self.dropdown_rect.x, self.dropdown_rect.centery - lang_title.get_height() // 2))

        dropdown_start_x = self.dropdown_rect.x + lang_title.get_width() + 20
        dropdown_width = self.dropdown_rect.width
        dropdown_y = self.dropdown_rect.y
        dropdown_height = self.dropdown_rect.height

        self.dropdown_rect = py.Rect(dropdown_start_x, dropdown_y, dropdown_width, dropdown_height)

        is_hovered = self.dropdown_rect.collidepoint(mouse_pos)

        if is_hovered:
            highlight_rect = py.Rect(self.dropdown_rect.x - 5, self.dropdown_rect.y - 5,
                                     self.dropdown_rect.width + 10, self.dropdown_rect.height + 10)
            highlight_surface = py.Surface((highlight_rect.width, highlight_rect.height), py.SRCALPHA)
            py.draw.rect(highlight_surface, self.COLORS["highlight"],
                         (0, 0, highlight_rect.width, highlight_rect.height), border_radius=4)
            self.screen.blit(highlight_surface, (highlight_rect.x, highlight_rect.y))

        py.draw.rect(self.screen, (70, 70, 70), self.dropdown_rect, border_radius=4)

        lang_text = self.control_font.render(self.selected_language, True, self.COLORS["white"])
        text_x = self.dropdown_rect.x + (self.dropdown_rect.width - lang_text.get_width()) // 2
        text_y = self.dropdown_rect.centery - lang_text.get_height() // 2
        self.screen.blit(lang_text, (text_x, text_y))

        arrow_points = [
            (self.dropdown_rect.right - 15, self.dropdown_rect.centery - 3),
            (self.dropdown_rect.right - 5, self.dropdown_rect.centery - 3),
            (self.dropdown_rect.right - 10, self.dropdown_rect.centery + 5)
        ]
        py.draw.polygon(self.screen, self.COLORS["white"], arrow_points)

        option_rects = []
        if self.dropdown_expanded:
            total_height = len(self.languages) * self.dropdown_rect.height
            dropdown_y = self.dropdown_rect.y + self.dropdown_rect.height

            py.draw.rect(self.screen, (50, 50, 50),
                         (self.dropdown_rect.x, dropdown_y, self.dropdown_rect.width, total_height),
                         border_radius=4)

            option_rects = []

            for i, lang in enumerate(self.languages):
                option_rect = py.Rect(
                    self.dropdown_rect.x,
                    dropdown_y + i * self.dropdown_rect.height,
                    self.dropdown_rect.width,
                    self.dropdown_rect.height
                )
                option_rects.append(option_rect)

                is_option_hovered = option_rect.collidepoint(mouse_pos)

                if is_option_hovered:
                    py.draw.rect(self.screen, (80, 80, 80), option_rect, border_radius=4)
                    option_text = self.control_font.render(lang, True, (255, 255, 255))
                else:
                    option_text = self.control_font.render(lang, True, self.COLORS["white"])

                text_x = option_rect.x + (option_rect.width - option_text.get_width()) // 2
                text_y = option_rect.centery - option_text.get_height() // 2
                self.screen.blit(option_text, (text_x, text_y))

        return option_rects

    def _draw_keyboard_button(self):#Display the current keyboard layout. Only AZERTY and QWERTY posible. Most of the function is, like the other draw options, a ton of lines to make it slightly better looking
        if not self.options_visible:
            return False

        if self.dropdown_expanded:
            return False

        mouse_pos = py.mouse.get_pos()

        keyboard_title = self.control_font.render("Keyboard Layout:", True, self.COLORS["white"])
        self.screen.blit(keyboard_title, (self.keyboard_button_rect.x,
                                          self.keyboard_button_rect.centery - keyboard_title.get_height() // 2))

        button_start_x = self.keyboard_button_rect.x + keyboard_title.get_width() + 20
        button_width = self.keyboard_button_rect.width
        button_y = self.keyboard_button_rect.y
        button_height = self.keyboard_button_rect.height

        self.keyboard_button_rect = py.Rect(button_start_x, button_y, button_width, button_height)

        is_hovered = self.keyboard_button_rect.collidepoint(mouse_pos)

        if is_hovered:
            highlight_rect = py.Rect(self.keyboard_button_rect.x - 5, self.keyboard_button_rect.y - 5,
                                     self.keyboard_button_rect.width + 10, self.keyboard_button_rect.height + 10)
            highlight_surface = py.Surface((highlight_rect.width, highlight_rect.height), py.SRCALPHA)
            py.draw.rect(highlight_surface, self.COLORS["highlight"],
                         (0, 0, highlight_rect.width, highlight_rect.height), border_radius=4)
            self.screen.blit(highlight_surface, (highlight_rect.x, highlight_rect.y))

        keyboard_bg = py.Surface((button_width, button_height), py.SRCALPHA)
        py.draw.rect(keyboard_bg, (70, 70, 70, 200), (0, 0, button_width, button_height), border_radius=4)
        self.screen.blit(keyboard_bg, (self.keyboard_button_rect.x, self.keyboard_button_rect.y))

        button_text = self.keyboard_font.render(self.keyboard_layout, True, self.COLORS["white"])
        text_x = self.keyboard_button_rect.x + (self.keyboard_button_rect.width - button_text.get_width()) // 2
        text_y = self.keyboard_button_rect.centery - button_text.get_height() // 2
        self.screen.blit(button_text, (text_x, text_y))

        return is_hovered

    def _handle_button_click(self, buttons, mouse_pos):#Here, to detect if a button is clicked we do not use the coordinates but the text displayed on it. It is easier
        if self.dropdown_expanded and self.options_visible:
            return True

        for text, rect in buttons.items():
            if rect.collidepoint(mouse_pos):
                if text == "RESUME":
                    return False
                elif text == "OPTIONS":
                    self.options_visible = True
                    return True
                elif text == "QUIT":
                    self.game.menu_time += time.time() - self.menu_time_start
                    self.game.save_system.update_playtime(self.game.current_slot)
                    py.quit()
                    sys.exit()
                elif text == "BACK":
                    self.options_visible = False
                    save_settings(self.game)
                    if self.game.state == "START_SCREEN":
                        return False
                    return True
        return True

    def _handle_volume_click(self, knob_x, mouse_pos):#the listle animation of changing the side of the cursor to make it more lively
        if not self.options_visible or self.dropdown_expanded:
            return False

        knob_area = py.Rect(
            knob_x - self.KNOB_RADIUS,
            self.slider_rect.y - self.KNOB_RADIUS,
            self.KNOB_RADIUS * 2,
            self.KNOB_RADIUS * 2
        )

        if knob_area.collidepoint(mouse_pos) or self.slider_rect.collidepoint(mouse_pos):
            if self.slider_rect.collidepoint(mouse_pos):
                volume = (mouse_pos[0] - self.slider_rect.x) / self.slider_rect.width
                volume = max(0, min(1, volume))
                set_game_volume(self.game, volume)
            return True
        return False

    def _handle_language_click(self, option_rects, mouse_pos):#just many other functions to diplay, when clicked the language menu
        if not self.options_visible:
            return

        if self.dropdown_rect.collidepoint(mouse_pos):
            self.dropdown_expanded = not self.dropdown_expanded
        elif self.dropdown_expanded:
            for i, option_rect in enumerate(option_rects):
                if option_rect.collidepoint(mouse_pos):
                    self.selected_language = self.languages[i]
                    self.dropdown_expanded = False
                    break
            else:
                self.dropdown_expanded = False

    def _handle_keyboard_click(self, mouse_pos):#Updated to it's other state when clicked
        if not self.options_visible or self.dropdown_expanded:
            return False

        if self.keyboard_button_rect.collidepoint(mouse_pos):
            self.keyboard_layout = "QWERTY" if self.keyboard_layout == "AZERTY" else "AZERTY"

            self.game.keyboard_layout = self.keyboard_layout.lower()  # Convertir en minuscules pour correspondre à get_key_map

            return True

        return False

    def _handle_volume_drag(self, mouse_x):#Simply,if the volume is clicked update the volume bar with the x coordinates of the user's mouse
        if not self.options_visible or self.dropdown_expanded:
            return

        constrained_x = max(self.slider_rect.left, min(mouse_x, self.slider_rect.right))

        self.volume = (constrained_x - self.slider_rect.x) / self.slider_rect.width
        self.volume = max(0, min(1, self.volume))
        set_game_volume(self.game, self.volume)

    def _update_options_positions(self, current_screen_size):#keep in mind that we always have to modify the buttons size and positions when the screen is resized
        control_x = (current_screen_size[0] - 300) // 2
        panel_y = 50

        control_spacing = 60

        self.slider_rect = py.Rect(control_x, panel_y + 100, 200, 5)
        self.dropdown_rect = py.Rect(control_x, panel_y + 100 + control_spacing, 200, 30)
        self.keyboard_button_rect = py.Rect(control_x, panel_y + 100 + control_spacing * 2, 200, 40)

    def _draw_options_panel(self, current_screen_size):#drax the buttons and option in the option Panel mostly using the previous function
        if not self.options_visible:
            return

        self._update_options_positions(current_screen_size)

        options_title_color = self.COLORS["dimmed"] if self.dropdown_expanded else self.COLORS["white"]
        options_title = self.button_font.render("OPTIONS", True, options_title_color)
        self.screen.blit(options_title, (
            (current_screen_size[0] - options_title.get_width()) // 2,
            50
        ))

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

    def menu_display(self): #when called: Display the main menu with it's buttons, monitor keyboard and mouse input (keyboard means escape key but it looks cooler), and thirdly displaythe background and optio npanel if needed
        self.capture_background()
        if self.game.state == "PLAYING":
            save_game(self.game, self.game.current_slot)
        self.menu_time_start = time.time()
        running = True
        while running:
            current_screen_size = self.screen.get_size()

            if self.original_background is not None:
                scaled_bg = py.transform.scale(self.original_background, current_screen_size)
                self.screen.blit(scaled_bg, (0, 0))
            else:
                self.screen.fill(self.COLORS["black"])

            overlay = py.Surface(current_screen_size, py.SRCALPHA)
            overlay.fill(self.COLORS["overlay"])
            self.screen.blit(overlay, (0, 0))

            if self.options_visible:
                self._draw_options_panel(current_screen_size)

            buttons = self._get_centered_buttons(current_screen_size)

            if not self.options_visible:
                if hasattr(self, 'bottom_image'):
                    self.screen.blit(self.top_image, self.bottom_image_pos)
                if hasattr(self, 'top_image'):
                    self.screen.blit(self.bottom_image, self.top_image_pos)

            self._draw_buttons(buttons)

            knob_x = self._draw_volume_control()
            self._draw_keyboard_button()
            option_rects = self._draw_language_dropdown()

            py.display.flip()

            for event in py.event.get():
                if event.type == py.QUIT:
                    py.quit()
                    sys.exit()

                elif event.type == py.VIDEORESIZE:
                    self.screen = py.display.set_mode((event.w, event.h), py.RESIZABLE)

                elif event.type == py.KEYDOWN:
                    if event.key == py.K_ESCAPE:
                        if self.dropdown_expanded:
                            self.dropdown_expanded = False
                        elif self.options_visible:
                            self.options_visible = False
                        else:
                            running = False

                elif event.type == py.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos

                    if self.dropdown_expanded and self.options_visible:
                        self._handle_language_click(option_rects, mouse_pos)
                    else:
                        running = self._handle_button_click(buttons, mouse_pos)
                        if self.options_visible:
                            self.dragging_volume = self._handle_volume_click(knob_x, mouse_pos)
                            self._handle_language_click(option_rects, mouse_pos)
                            self._handle_keyboard_click(mouse_pos)

                elif event.type == py.MOUSEBUTTONUP:
                    self.dragging_volume = False

                elif event.type == py.MOUSEMOTION and self.dragging_volume and not self.dropdown_expanded:
                    self._handle_volume_drag(event.pos[0])

        if not running:
            self.game.menu_time += time.time() - self.menu_time_start

    def profile_selection_menu(self):
        """
        Displays a 3-slot selection menu.
        Handles loading existing saves or starting new games.
        Returns True if a game starts/loads, False if BACK is pressed.
        """
        # 1. Setup background (darken current screen)
        current_screen = self.screen.copy()
        overlay = py.Surface(self.screen.get_size(), py.SRCALPHA)
        overlay.fill((0, 0, 0, 230))  # Very dark overlay like the reference image

        # 2. Fetch Save Data
        saves = self.game.save_system.list_saves()
        used_slots = {save["slot"]: save for save in saves}

        # 3. Layout Configuration
        screen_w, screen_h = self.screen.get_size()
        center_x = screen_w // 2

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
            # Draw base layers
            self.screen.blit(current_screen, (0, 0))
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
                                    if load_game(self.game, slot_id):
                                        return True  # Game loaded successfully
                                else:
                                    # START NEW GAME
                                    self.game.level = 0
                                    self.game.load_level(self.game.default_level, transition_effect=False)
                                    self.game.player_hp = 100
                                    # Crucial: Tell the game which slot is currently active for future saves
                                    self.game.current_slot = slot_id
                                    # Optional: Autosave immediately so the slot isn't empty next time
                                    # save_game(self.game, slot_id)
                                    return True  # New game started

                    # Check Back button click
                    if back_rect.collidepoint(event.pos):
                        running = False  # Exit menu, return to title screen video

        return False  # Back was pressed


def start_menu(game):
    py.init()
    load_settings(game)
    if py.display.get_window_size() == (960, 576):
        size = (1000, 600)
    else:
        size = py.display.get_window_size()
    screen = py.display.set_mode(size, py.RESIZABLE)
    # Increase font size for better visibility on buttons
    font = py.font.Font(None, 24)
    font.set_italic(True)

    cap = cv2.VideoCapture("assets/images/start_video.mp4")
    running = True

    # We will store the user's choice here
    action = None

    while running:
        # 1. Define Button Rectangles (x, y, width, height)
        # Centered horizontally at x=400 (since screen width is 1000, center is 500, button width 200)
        width = 200
        height = 60
        x = screen.get_width() / 2 - width / 2
        y = screen.get_height() * 21 / 32
        play_rect = py.Rect(x, y, width, height)
        settings_rect = py.Rect(x, y + height, width, height)
        quit_rect = py.Rect(x, y + 2 * height, width, height)

        ret, frame = cap.read()
        if not ret:
            # Restart video loop
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # --- Video Processing ---
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (screen.get_width(), screen.get_height()))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = py.surfarray.make_surface(frame)
        screen.blit(frame, (0, 0))

        # --- Draw Buttons ---
        mouse_pos = py.mouse.get_pos()

        # List of buttons to iterate through: (Rectangle, Text Label, Return Value)
        buttons = [
            (play_rect, "Play", "play"),
            (settings_rect, "Settings", "settings"),
            (quit_rect, "Quit", "quit")
        ]

        for rect, label, _ in buttons:
            # Check if mouse is hovering over the button
            if rect.collidepoint(mouse_pos):
                color = (50, 50, 50)  # Lighter grey on hover
            else:
                color = (255, 255, 255)  # Dark grey default


            # Draw text centered in the button
            text_surf = font.render(label, True, color)
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)

        # --- Event Handling ---
        for event in py.event.get():
            if event.type == py.QUIT:
                action = "quit"
                running = False

            elif event.type == py.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check which button was clicked
                    if play_rect.collidepoint(event.pos):
                        action = "play"
                        running = False
                    elif settings_rect.collidepoint(event.pos):
                        action = "settings"
                        running = False
                    elif quit_rect.collidepoint(event.pos):
                        action = "quit"
                        running = False

        py.display.flip()
        # Reduced wait time slightly for smoother mouse movement (approx 30 FPS)
        py.time.wait(30)

    cap.release()
    # py.quit() # Optional: keep this commented if you want to keep the window open for the game
    return action

