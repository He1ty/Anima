import pygame

class CheckPoint:
    def __init__(self, game_instance, pos, tile):

        self.game = game_instance
        tile_id, variant, rotation, flip_x, flip_y = game_instance.tilemap.tile_manager.unpack_tile(tile)
        animation = game_instance.tilemap.tile_manager.tiles[tile_id].images

        self.pos = pos.copy()
        self.state = "deactivated"

        self.flip_x = flip_x
        self.flip_y = flip_y
        self.rotation = rotation
        self.animation = animation.copy()

    @property
    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.animation.img().get_width(), self.animation.img().get_height())

    def update(self):
        if self.game.player.collide_with(self.rect, static_rect=True) and self.game.current_checkpoint != self:
            self.state = "activated"
            self.game.current_checkpoint = self
            if self.game.spawn_point["pos"] == self.game.current_checkpoint.pos:
                return
            self.game.spawn_point = {"pos": self.game.current_checkpoint.pos, "level": self.game.level}
            self.game.save_game(self.game.current_slot)

        if self.game.current_checkpoint != self:
            self.state = "deactivated"

        self.animation.animation = self.state
        self.animation.update()

    def render(self, offset=(0, 0)):
        img = pygame.transform.rotate(self.animation.img(), self.rotation* -90 )
        img = pygame.transform.flip(img, self.flip_x, self.flip_y)

        self.game.display.blit(img, (self.pos[0] - offset[0], self.pos[1] - offset[1]))