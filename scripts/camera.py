
import pygame
import time

class Camera:

    def __init__(self, game):
        self.game = game

    def move_visual(self, duration, pos):
        self.game.moving_visual = True
        self.game.visual_pos = pos
        self.game.visual_movement_duration = duration
        self.game.visual_start_time = time.time()

    def update_camera(self):
        current_time = time.time()

        if self.game.moving_visual:
            elapsed_time = current_time - self.game.visual_start_time
            if elapsed_time < self.game.visual_movement_duration:
                self.game.scroll[0] += (self.game.visual_pos[0] - self.game.display.get_width() / 2 - self.game.scroll[0]) / 20
                self.game.scroll[1] += (self.game.visual_pos[1] - self.game.display.get_height() / 2 - self.game.scroll[1]) / 20
            else:
                self.game.moving_visual = False

        else:
            target_x = (self.game.player.rect().centerx if self.game.camera_center is None else self.game.camera_center[
                0]) - self.game.display.get_width() / 2
            target_y = (self.game.player.rect().centery if self.game.camera_center is None else self.game.camera_center[
                1]) - self.game.display.get_height() / 2

            level_limits = self.game.scroll_limits

            if level_limits["x"]:
                min_x, max_x = level_limits["x"]
                max_x -= self.game.display.get_width()
                target_x = max(min_x, min(target_x, max_x))

            if level_limits["y"]:
                min_y, max_y = level_limits["y"]
                max_y -= self.game.display.get_height()
                target_y = max(min_y, min(target_y, max_y))

            self.game.scroll[0] += (target_x - self.game.scroll[0]) / 20
            self.game.scroll[1] += (target_y - self.game.scroll[1]) / 20

    def screen_shake(self, strenght):
        self.game.screenshake = max(strenght, self.game.screenshake)

class CameraSetup:
    def __init__(self, game, camera):
        self.game = game
        self.type = camera["infos_type"]
        self.scroll_limits = {"x":[int(x) for x in camera["x_limits"].split(";")],
                              "y":[int(y) for y in camera["y_limits"].split(";")]}
        self.size = [int(s) for s in camera["size"].split(";")]
        self.pos = camera["pos"]
        self.rect = pygame.Rect(self.pos[0], self.pos[1], self.size[0]*self.game.tile_size, self.size[1]*self.game.tile_size)
        if "center" in camera:
            self.center = [int(coordinate) for coordinate in camera["center"].split(";")]
        self.previous_infos = {}

        self.activated = True
        self.player_entry_side = None
        self.initial_state = {"x":[int(x) for x in camera["x_limits"].split(";")],
                              "y":[int(y) for y in camera["y_limits"].split(";")]}

    def get_player_entry_side(self):
        player_rect = self.game.player.rect()


        if self.is_colliding(player_rect) and self.player_entry_side is None:
            #If player is on same camera_setup y level
            if player_rect.bottom <= self.rect.bottom and player_rect.top >= self.rect.top:
                if player_rect.left < self.rect.left <= player_rect.right:
                    self.player_entry_side = "left"
                elif player_rect.right > self.rect.right >= player_rect.left:
                    self.player_entry_side = "right"
            #Else
            elif (player_rect.bottom <= self.rect.bottom and player_rect.top <= self.rect.top) or (player_rect.top >= self.rect.top and player_rect.bottom >= self.rect.bottom) :
                if player_rect.top < self.rect.top <= player_rect.bottom:
                    self.player_entry_side = "top"
                elif player_rect.bottom > self.rect.bottom >= player_rect.top:
                    self.player_entry_side = "bottom"
        elif self.has_passed():
            self.player_entry_side = None

    def is_colliding(self, player_rect, interaction_distance = -1):  # Check if the player can "touch" the lever.
        is_colliding = self.rect.colliderect(player_rect.inflate(interaction_distance, interaction_distance))
        return is_colliding

    def has_passed(self):
        player_rect = self.game.player.rect()
        if self.player_entry_side == "top" and player_rect.top > self.rect.bottom:
            return True
        if self.player_entry_side == "bottom" and player_rect.bottom < self.rect.top:
            return True
        if self.player_entry_side == "right" and player_rect.right < self.rect.left:
            return True
        if self.player_entry_side == "left" and player_rect.left > self.rect.right:
            return True

    def update(self):
        if self.has_passed():
            self.player_entry_side = None
            #First of, save previous "room" camera settings
            self.previous_infos["scroll_limits"] = self.game.scroll_limits.copy()
            if self.game.camera_center is not None:
                self.previous_infos["center"] = self.game.camera_center

            self.game.scroll_limits = self.scroll_limits
            if hasattr(self, "center"):
                self.game.camera_center = self.center
            else:
                self.game.camera_center = None
            self.scroll_limits = self.previous_infos["scroll_limits"]
            if hasattr(self, "center"):
                self.center = self.previous_infos["center"]
            self.activated = False
        else:
            self.activated = True


        self.get_player_entry_side()