import pygame

import json
import math

from pygame import BLEND_ADD, BLEND_MAX, BLEND_RGBA_MULT, BLEND_RGBA_SUB, BLEND_RGBA_ADD

from scripts.utils import round_up
from scripts.pickup import pickups_render_and_update

AUTOTILE_MAP = {
    tuple(sorted([(1, 0), (0, 1)])): 0,
    tuple(sorted([(1, 0), (0, 1), (-1, 0)])): 1,
    tuple(sorted([(-1, 0), (0, 1)])): 2,
    tuple(sorted([(-1, 0), (0, -1), (0, 1)])): 3,
    tuple(sorted([(-1, 0), (0, -1)])): 4,
    tuple(sorted([(-1, 0), (0, -1), (1, 0)])): 5,
    tuple(sorted([(1, 0), (0, -1)])): 6,
    tuple(sorted([(1, 0), (0, -1), (0, 1)])): 7,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, 1), (1, -1), (-1, -1), (-1, 1)])): 8,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, -1), (-1, -1), (-1, 1)])): 9,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, 1), (1, -1), (-1, -1)])): 10,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, 1), (-1, -1)])): 11,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, 1), (-1, -1), (-1, 1)])): 12,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, 1), (1, -1), (-1, 1)])): 13,
    tuple(sorted([(1, 0), (-1, 0), (0, -1), (0, 1), (1, -1), (-1, 1)])): 14,
}

PHYSICS_TILES = {'purpur_rock', 'stone', 'vine','mossy_stone', 'gray_mossy_stone', 'blue_grass', 'mossy_stone_gluy'}
TRANSPARENT_TILES = {'vine_transp':[0,1,2], 'vine_transp_back':[0,1,2], 'dark_vine':[0,1,2],'hanging_vine':[0,1,2]}
AUTOTILE_TYPES = {'spikes', 'purpur_spikes', 'gluy_spikes', 'purpur_rock', 'grass', 'stone', 'mossy_stone', 'blue_grass', 'spike_roots', 'gray_mossy_stone', 'hollow_stone', 'mossy_stone_gluy', 'dark_hollow_stone', 'purpur_stone'}
AUTOTILE_COMPATIBILITY = {'purpur_spikes':["spikes"], "spikes":["purpur_spikes"] ,'mossy_stone': ["mossy_stone_gluy"], 'mossy_stone_gluy': ["mossy_stone"]}
PLAYER_LAYER = "2"

class Tilemap:
    def __init__(self, game, tile_size = 16):
        self.game = game
        self.tile_size = tile_size
        self.tilemap = {}
        self.offgrid_tiles = {}
        self.show_collisions = False
        self.fake_tile_opacity = 255
        self.fake_tile_groups = []
        self.fake_tile_colliding_group = []

    def extract(self, id_pairs, keep=False, layers=()):
        """dict, bool -> list
        extract a list of all elements in the map which are of type id_pairs[n][0] and variant id_pairs[n][1],
        where 0 <= n < len(id_pairs)"""
        matches = []
        for loc in self.offgrid_tiles.copy():
            tile = self.offgrid_tiles[loc]
            if (tile['type'], tile['variant']) in id_pairs:
                matches.append(tile.copy())
                if not keep:
                    del self.offgrid_tiles[loc]

        for layer in (layers if layers else self.tilemap):
            for loc in self.tilemap[layer].copy():
                tile = self.tilemap[layer][loc]
                if "variant" in tile:
                    check = (tile['type'], tile["variant"]) in id_pairs
                else:
                    check = (tile['type'] in id_pairs)
                if check:
                    matches.append(tile.copy())
                    matches[-1]['pos'] = list(matches[-1]['pos']).copy()
                    matches[-1]['pos'][0] *= self.tile_size
                    matches[-1]['pos'][1] *= self.tile_size
                    if not keep:
                        del self.tilemap[layer][loc]

        return matches

    def neighbor_offset(self, size):
        offset = []
        tiles_x = round_up(size[0]/self.tile_size) + 1
        tiles_y = round_up(size[1]/self.tile_size) + 1
        for x in range(-1, tiles_x):
            for y in range(-1, tiles_y):
                offset.append((x, y))
        return offset

    def between_check(self,p_pos,e_pos):
        y = e_pos[1]
        x_min, x_max = int(min(p_pos[0], e_pos[0])),int(max(p_pos[0], e_pos[0]))
        for x in range(x_min, x_max+1):
            if self.solid_check((x,y)):
                return True
        return False

    def under_offset(self, size, gravity_dir):
        u_offset = []
        tiles_x = round_up(size[0] / self.tile_size) + 1
        tiles_y = round_up(size[1] / self.tile_size) + gravity_dir
        r = range(tiles_y - 1, tiles_y)
        for x in range(-1, tiles_x):
            for y in r:
                u_offset.append((x, y))
        return u_offset

    def tiles_around(self, pos, size):
        tiles = []
        tile_loc = (int((pos[0]+size[0]/2) // self.tile_size), int((pos[1]+size[0]/2) // self.tile_size))
        for offset in self.neighbor_offset(size):
            check_loc = str(tile_loc[0] + offset[0]) + ';' + str(tile_loc[1] + offset[1])
            if self.show_collisions:
                pygame.draw.rect(self.game.display, (255, 0, 255),
                                 ((tile_loc[0] + offset[0]) * self.tile_size - int(self.game.scroll[0]),
                                  (tile_loc[1] + offset[1]) * self.tile_size - int(self.game.scroll[1]),
                                  16,
                                  16))
            for layer in self.tilemap:
                if check_loc in self.tilemap[layer]:
                    tiles.append(self.tilemap[layer][check_loc])
        return tiles

    def tiles_under(self, pos, size, gravity_dir):
        u_tiles = []
        u_tile_loc = (int((pos[0] + size[0]/2) // self.tile_size), int((pos[1] + size[0]/2) // self.tile_size))
        for offset in self.under_offset(size, gravity_dir):
            check_loc = str(u_tile_loc[0] + offset[0]) + ';' + str(u_tile_loc[1] + offset[1])
            if self.show_collisions:
                pygame.draw.rect(self.game.display, (0, 0, 255),
                                ((u_tile_loc[0] + offset[0]) * self.tile_size - int(self.game.scroll[0]),
                                  (u_tile_loc[1] + offset[1]) * self.tile_size - int(self.game.scroll[1]),
                                  16,
                                  16))
            for layer in self.tilemap:
                if check_loc in self.tilemap[layer]:
                    u_tiles.append(self.tilemap[layer][check_loc])
        return u_tiles

    def render_tiles_under(self, pos, size, gravity_dir):
        u_tile_loc = (int((pos[0] + size[0] / 2) // self.tile_size), int((pos[1] + size[0]/2) // self.tile_size))
        for offset in self.under_offset(size, gravity_dir):
            pygame.draw.rect(self.game.display, (0, 0, 255),
                                 ((u_tile_loc[0] + offset[0]) * self.tile_size - int(self.game.scroll[0]),
                                  (u_tile_loc[1] + offset[1]) * self.tile_size - int(self.game.scroll[1]),
                                  16,
                                  16))

    def save(self, path):
        f = open(path, 'w')

        json.dump({'tilemap': self.tilemap,
                        'offgrid':self.offgrid_tiles,
                   'tilesize': self.tile_size},
                  f, indent=1)
        f.close()

    def load(self, path):
        f = open(path, 'r')
        map_data = json.load(f)
        f.close()

        self.tilemap = map_data['tilemap']
        self.offgrid_tiles = map_data['offgrid']
        self.tile_size = map_data['tilesize']

    def autotile(self):
        for layer in self.tilemap:
            for loc in self.tilemap[layer]:
                tile = self.tilemap[layer][loc]
                neighbors = set()
                corner_additional_shifts = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
                for shift in [(1, 0), (-1, 0), (0, -1), (0, 1)] + corner_additional_shifts:
                    check_loc = str(tile['pos'][0] + shift[0]) + ";" + str(tile['pos'][1] + shift[1])
                    if check_loc in self.tilemap[layer]:
                        if self.tilemap[layer][check_loc]['type'] == tile['type'] or (tile["type"] in AUTOTILE_COMPATIBILITY and
                                                                                      self.tilemap[layer][check_loc]["type"] in AUTOTILE_COMPATIBILITY[tile['type']]):
                            neighbors.add(shift)
                neighbors = sorted(neighbors)

                a_map = AUTOTILE_MAP
                if "rotation" in tile:
                    angle = -(tile["rotation"] - 1)*math.pi/2
                    a_map = {
                        tuple(sorted([(int(math.sin(angle)), int(math.cos(angle)))])): 0,
                        tuple(sorted([(int(math.sin(angle)), int(math.cos(angle))), (int(-math.sin(angle)), int(-math.cos(angle)))])): 1,
                        tuple(sorted([(int((-math.sin(angle))), int(-math.cos(angle)))])): 2,
                    }

                if tuple(neighbors) not in a_map:
                    for s in corner_additional_shifts:
                        if s in neighbors:
                            neighbors.remove(s)

                neighbors = tuple(sorted(neighbors))

                if (tile['type'] in AUTOTILE_TYPES) and (neighbors in a_map):
                    if "rotation" in tile:
                        tile['variant'] = a_map[neighbors]
                    else:
                        new_variant = a_map[neighbors]
                        if new_variant < len(self.game.assets[tile["type"]]):
                            tile['variant'] = new_variant

    def solid_check(self, pos, transparent_check=True):
        tile_loc = str(int(pos[0] // self.tile_size)) + ";" + str(int(pos[1] // self.tile_size))
        for layer in self.tilemap:
            if tile_loc in self.tilemap[layer]:
                tile = self.tilemap[layer][tile_loc]
                if tile["type"] in PHYSICS_TILES:
                    return self.tilemap[layer][tile_loc]
                elif transparent_check and tile['type'] in set(TRANSPARENT_TILES.keys()) and tile['variant'] in TRANSPARENT_TILES[tile['type']]:
                    return self.tilemap[layer][tile_loc]

    def physics_rects_around(self, pos, size):
        rects = []
        for tile in self.tiles_around(pos, size):
            if tile['type'] in PHYSICS_TILES:
                rects.append(pygame.Rect(tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size, self.tile_size, self.tile_size))
        return rects

    def physics_rects_under(self, pos, size, gravity_dir):
        u_rects = []
        for tile in self.tiles_under(pos, size, gravity_dir):
            if tile['type'] in PHYSICS_TILES:
                u_rects.append(pygame.Rect(tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size, self.tile_size, self.tile_size))
            elif tile['type'] in set(TRANSPARENT_TILES.keys()) and tile['variant'] in TRANSPARENT_TILES[tile['type']]:
                if not self.game.player.collide_with_passable_blocks: #System in order to make collision with passable blocks more clean (bigger vertical collision offset)
                    if pos[1] + size[1] <= tile["pos"][1]*self.tile_size:
                        self.game.player.collide_with_passable_blocks = True
                if gravity_dir == 1 and self.game.player.collide_with_passable_blocks:
                    u_rects.append(pygame.Rect(tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size, self.tile_size,self.tile_size))
        return u_rects

    def get_type_from_rect(self, rect):
        for layer in self.tilemap:
            for tile in self.tilemap[layer]:
                if str(rect.x//self.tile_size) + ";" + str(rect.y//self.tile_size) == tile:
                    return self.tilemap[layer][tile]["type"]

    def get_variant_from_rect(self, rect):
        for layer in self.tilemap:
            for tile in self.tilemap[layer]:
                if str(rect.x//self.tile_size) + ";" + str(rect.y//self.tile_size) == tile:
                    return self.tilemap[layer][tile]["variant"]

    def pos_visible(self, surf, pos, offset = (0, 0), additional_offset=(0, 0)):
           return (offset[0] - additional_offset[0] <= pos[0] <= offset[0] + additional_offset[0] + surf.get_width() and
                   offset[1] - additional_offset[1] <= pos[1] <= offset[1] + additional_offset[1] + surf.get_height())

    def get_same_type_connected_tiles(self, tile, layer):
        connected_tiles = [tile]
        offsets = [(0,1), (0,-1), (1,0), (-1,0)]
        for t in connected_tiles:
            for offset in offsets:
                check_loc = f"{t["pos"][0] + offset[0]};{t["pos"][1] + offset[1]}"
                if check_loc in self.tilemap[layer]:
                    checked_tile = self.tilemap[layer][check_loc].copy()
                    if checked_tile["type"] != tile["type"]:
                        continue
                    if checked_tile not in connected_tiles:
                        connected_tiles.append(checked_tile)

        return connected_tiles

    def fake_tile_colliding_with_player(self, tile):
        r = pygame.Rect(tile["pos"][0]*self.tile_size, tile["pos"][1]*self.tile_size, self.tile_size, self.tile_size)
        return self.game.player.rect().colliderect(r)

    def render(self, surf, offset = (0, 0), mask_opacity=255, exception=(), precise_layer = None, with_player = True):

        tiles_opacity = mask_opacity

        for layer in self.tilemap:

            if precise_layer is not None:
                if layer != precise_layer:
                    tiles_opacity = 80
                else:
                    tiles_opacity = 255

            if with_player:
                if layer == PLAYER_LAYER:
                    pickups_render_and_update(self.game, offset=offset)
                    self.game.player.render(surf, offset=offset)
                if layer == self.game.FAKE_TILES_LAYER:
                    self.game.fake_tiles_render(offset=offset)
                    continue

            for x in range(offset[0] // self.tile_size, (offset[0] + surf.get_width()) // self.tile_size + 1):
                for y in range(offset[1] // self.tile_size, (offset[1] + surf.get_height()) // self.tile_size + 1):
                    loc = str(x) + ";" + str(y)
                    if loc in self.tilemap[layer]:
                        tile = self.tilemap[layer][loc]
                        if tile["type"] in self.game.assets:
                            img = self.game.assets[tile['type']][tile['variant']].copy()
                            img.fill((255, 255, 255, 255 if tile['type'] in exception else tiles_opacity), special_flags=BLEND_RGBA_MULT)

                            if 'rotation' in tile:
                                img = pygame.transform.rotate(img, tile['rotation'] * -90)

                            surf.blit(img, (
                                tile['pos'][0] * self.tile_size - offset[0], tile['pos'][1] * self.tile_size - offset[1]))

            if layer == "2" and with_player and self.show_collisions:
                self.render_tiles_under(self.game.player.pos, self.game.player.size, 1)

        for pos in self.offgrid_tiles.copy():
            tile = self.offgrid_tiles[pos]
            img = self.game.assets[tile['type']][tile['variant']].copy()
            img.fill((255, 255, 255, 255 if tile['type'] in exception else tiles_opacity), special_flags=BLEND_RGBA_MULT)
            surf.blit(self.game.assets[tile['type']][tile['variant']], (tile['pos'][0] - offset[0], tile['pos'][1] - offset[1]))