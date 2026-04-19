import pygame


class SinkingGroup:
    DOWN_SPEED = 0.2 #pixels per frame
    UP_SPEED = 0.4
    BOTTOM_LIMIT = 8 #pixels under initial position

    def __init__(self, game_instance, group):
        self.game = game_instance
        self.group = {}
        for tile_loc in group:
            tile = group[tile_loc][0]
            layer = group[tile_loc][1]
            if type(tile) != int:
                self.group[tile_loc] = {"tile": tile, "pos": tile.pos, "img": tile.image, "layer": layer}
                continue
            pos = [float(val)*game_instance.tile_size for val in tile_loc.split(";")]
            tile_id, variant, rotation, flip_x, flip_y = self.game.tilemap.tile_manager.unpack_tile(tile)
            img = self.game.tilemap.tile_manager.tiles[tile_id].images[variant]
            img = pygame.transform.rotate(img, rotation * -90)
            img = pygame.transform.flip(img, flip_x, flip_y)
            self.group[tile_loc] = {"tile": tile, "pos": pos, "img": img, "layer": layer}

            rect = pygame.Rect(int(pos[0]), int(pos[1]), self.game.tile_size, self.game.tile_size)
            self.game.sinking_rects.append(rect)

        self.down_speed_cur = 0
        self.up_speed_cur = 0


    def update(self, dt):
        no_more_collision = True
        for tile_loc in self.group:
            tile = self.group[tile_loc]
            tile_pos = tile["pos"]
            tile_type = type(tile["tile"])
            shifted_rect = pygame.Rect(int(tile_pos[0]), int(tile_pos[1] - 1), self.game.tile_size, self.game.tile_size)

            if tile_type != int:
                continue
            if self.game.player.collide_with(shifted_rect, static_rect=True, rotating_rect=False):
                self.game.sinking_colliding_group = self
                no_more_collision = False
                break

        if self.game.sinking_colliding_group == self:
            total_delta = 0
            if self.down_speed_cur == 0:
                for tile_loc in self.group:
                    tile = self.group[tile_loc]
                    tile_pos = tile["pos"]
                    tile_type = type(tile["tile"])
                    initial_y = [float(val) * self.game.tile_size for val in tile_loc.split(";")][1]

                    old_y = tile["pos"][1]
                    new_y = min(tile["pos"][1] + 1, initial_y + self.BOTTOM_LIMIT)
                    delta = new_y - old_y
                    total_delta = delta  # same for all tiles in the group

                    if tile_type == int:
                        rect = pygame.Rect(int(tile_pos[0]), int(tile_pos[1]), self.game.tile_size, self.game.tile_size)
                        self.game.sinking_rects.remove(rect)
                    tile["pos"][1] = new_y
                    if tile_type == int:
                        rect = pygame.Rect(int(tile["pos"][0]), int(tile["pos"][1]), self.game.tile_size, self.game.tile_size)
                        self.game.sinking_rects.append(rect)
                self.down_speed_cur = 1 / self.DOWN_SPEED

                # Push the player down with the block so there's no gap
                if total_delta > 0:
                    self.game.player.pos[1] += 1

            self.down_speed_cur = max(0, self.down_speed_cur - dt)

        if no_more_collision and self.game.sinking_colliding_group == self:
            self.game.sinking_colliding_group = None

        if no_more_collision:
            if self.up_speed_cur == 0:
                for tile_loc in self.group:
                    tile = self.group[tile_loc]
                    tile_pos = tile["pos"]
                    tile_type = type(tile["tile"])

                    initial_y = [float(val) * self.game.tile_size for val in tile_loc.split(";")][1]

                    if tile_type == int:
                        rect = pygame.Rect(int(tile_pos[0]), int(tile_pos[1]), self.game.tile_size, self.game.tile_size)
                        self.game.sinking_rects.remove(rect)
                    tile["pos"][1] = max(tile["pos"][1] - self.UP_SPEED, initial_y)
                    if tile_type == int:
                        rect = pygame.Rect(int(tile["pos"][0]), int(tile["pos"][1]), self.game.tile_size,
                                           self.game.tile_size)
                        self.game.sinking_rects.append(rect)
                self.up_speed_cur = 1 / self.UP_SPEED

            self.up_speed_cur = max(0, self.up_speed_cur - dt)

    def render(self, surf, offset=(0, 0)):
        for tile_loc in self.group:
            pos = self.group[tile_loc]["pos"]
            img = self.group[tile_loc]["img"]
            #rect = pygame.Rect(pos[0] - offset[0], pos[1] - offset[1], self.game.tile_size, self.game.tile_size)
            #pygame.draw.rect(surf, (255, 255, 255), rect)
            surf.blit(img, (round(pos[0]) - offset[0], round(pos[1]) - offset[1]))