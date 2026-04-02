
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
            target_x = self.game.player.rect().centerx - self.game.display.get_width() / 2
            target_y = self.game.player.rect().centery - self.game.display.get_height() / 2

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