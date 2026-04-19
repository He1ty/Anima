import pygame

from scripts.entities import Spike


class FakeTilesGroup:

    def __init__(self, game_instance, group):
        self.game = game_instance
        self.group = {}
        for fake_tile_loc in group:
            tile = group[fake_tile_loc][0]
            layer = group[fake_tile_loc][1]
            if type(tile) != int:
                self.group[fake_tile_loc] = {"tile": tile, "pos": tile.pos, "img": tile.image, "layer": layer}
                continue
            pos = [float(val)*game_instance.tile_size for val in fake_tile_loc.split(";")]
            tile_id, variant, rotation, flip_x, flip_y = self.game.tilemap.tile_manager.unpack_tile(tile)
            img = self.game.tilemap.tile_manager.tiles[tile_id].images[variant]
            img = pygame.transform.rotate(img, rotation * -90)
            img = pygame.transform.flip(img, flip_x, flip_y)
            self.group[fake_tile_loc] = {"tile": tile, "pos": pos, "img": img, "layer": layer}
        self.opacity = 255

    def handle_tile_remove(self, tile):
        if isinstance(tile, Spike):
            self.game.spikes.remove(tile)


    def update(self):
        for fake_tile_loc in self.group:
            fake_tile = self.group[fake_tile_loc]
            fake_tile_pos = fake_tile["pos"]
            layer = fake_tile["layer"]

            rect = pygame.Rect(fake_tile_pos[0], fake_tile_pos[1], self.game.tile_size, self.game.tile_size)
            if self.game.player.collide_with(rect, static_rect=True):
                self.game.fake_tiles_colliding_group = self

        if self.game.fake_tiles_colliding_group == self:
            self.opacity = max(0, self.opacity - 30)

        if self.opacity == 0:
            self.game.fake_tiles.remove(self)
            for fake_tile_loc in self.group:
                self.handle_tile_remove(self.group[fake_tile_loc]["tile"])

    def render(self, surf, offset=(0, 0)):
        for fake_tile_loc in self.group:
            pos = self.group[fake_tile_loc]["pos"]
            img = self.group[fake_tile_loc]["img"]
            img.fill((255, 255, 255, self.opacity), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(img, (pos[0] - offset[0], pos[1] - offset[1]))
