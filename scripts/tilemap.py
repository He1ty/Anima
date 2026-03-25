import pygame

import json
import math
import copy

from pygame import BLEND_ADD, BLEND_MAX, BLEND_RGBA_MULT, BLEND_RGBA_SUB, BLEND_RGBA_ADD

from scripts.utils import round_up
from scripts.tile import Tile
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

PHYSICS_TILES = {'whiter_blocks', 'white_blocks', 'purpur_rock', 'vine','mossy_stone', 'gray_mossy_stone', 'mossy_stone_gluy'}
TRANSPARENT_TILES = {'vine_transp':[0,1,2], 'vine_transp_back':[0,1,2], 'dark_vine':[0,1,2],'hanging_vine':[0,1,2]}
AUTOTILE_TYPES = {'whiter_blocks', 'red_spikes', 'white_blocks', 'spikes', 'purpur_spikes', 'gluy_spikes', 'purpur_rock', 'grass', 'stone', 'mossy_stone', 'blue_grass', 'spike_roots', 'gray_mossy_stone', 'hollow_stone', 'mossy_stone_gluy', 'dark_hollow_stone', 'purpur_stone'}
AUTOTILE_COMPATIBILITY = {'purpur_spikes':["spikes"], "spikes":["purpur_spikes"] ,'mossy_stone': ["mossy_stone_gluy"], 'mossy_stone_gluy': ["mossy_stone"]}

class Tilemap:
    def __init__(self, game, tile_size = 16):
        self.game = game
        self.tile_size = tile_size
        self.tilemap = {}
        self.offgrid_tiles = {}
        self.layers = {"player":["0"],
                       "activators":[],
                       "fake_tiles":[]}
        self.selection_groups = {}
        self.tag_groups = {}
        self.show_collisions = False
        self.render_filters = {}

    def extract(self, id_pairs, keep=False, layers=()):
        """dict, bool -> list
        extract a list of all elements in the map which are of type id_pairs[n][0] and variant id_pairs[n][1],
        where 0 <= n < len(id_pairs)"""
        matches = []

        for layer in (layers if layers else self.tilemap):
            for loc in self.tilemap[layer].copy():
                tile = self.tilemap[layer][loc]
                if "variant" in tile:
                    check = (tile.type, tile.variant) in id_pairs
                else:
                    check = (tile.type in id_pairs)
                if check:
                    matches.append(tile.copy())
                    matches[-1].pos = list(matches[-1].pos).copy()
                    matches[-1].pos[0] *= self.tile_size
                    matches[-1].pos[1] *= self.tile_size
                    if not keep:
                        del self.tilemap[layer][loc]

            if layer in self.offgrid_tiles:
                for loc in self.offgrid_tiles[layer].copy():
                    tile = self.offgrid_tiles[layer][loc]
                    if (tile.type, tile.variant) in id_pairs:
                        matches.append(tile.copy())
                        if not keep:
                            del self.offgrid_tiles[layer][loc]

        return matches
    
    def remove_tile(self, pos, layer):
        if layer in self.tilemap:
            if pos in self.tilemap[layer]:
                del self.tilemap[layer][pos]
        if layer in self.offgrid_tiles:
            if pos in self.offgrid_tiles[layer]:
                del self.offgrid_tiles[layer][pos]
            

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
        tile_loc = (int((pos[0]+size[0]/2) // self.tile_size), int((pos[1]+size[1]/2) // self.tile_size))
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
        u_tile_loc = (int((pos[0] + size[0]/2) // self.tile_size), int((pos[1] + size[1]/2) // self.tile_size))
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
        tilemap = {}
        offgrid = {}
        for layer in self.tilemap:
            tilemap[layer] = {}
            for tile_loc in self.tilemap[layer]:
                tile = self.tilemap[layer][tile_loc]
                tilemap[layer][tile_loc] = {
                    "type": tile.type,
                    "variant": tile.variant,
                    "pos": tile.pos,
                    "rotation": tile.rotation,
                }
                
        for layer in self.offgrid_tiles:
            offgrid[layer] = {}
            for tile_loc in self.offgrid_tiles[layer]:
                tile = self.offgrid_tiles[layer][tile_loc]
                offgrid[layer][tile_loc] = {
                    "type": tile.type,
                    "variant": tile.variant,
                    "pos": tile.pos,
                    "rotation": tile.rotation,
                }

        json.dump({'tilemap': tilemap,
                        'offgrid': offgrid,
                   'tag_groups': self.tag_groups,
                   'selection_groups': self.selection_groups,
                   'layers': self.layers,
                   'tilesize': self.tile_size},
                  f, indent=1)
        f.close()

    def load(self, path):
        f = open(path, 'r')
        map_data = json.load(f)
        f.close()

        if "tilemap" in map_data:
            self.tilemap = {}
            for layer in map_data["tilemap"]:
                self.tilemap[layer] = {}
                for tile_loc in map_data["tilemap"][layer]:
                    tile_infos = map_data["tilemap"][layer][tile_loc]
                    self.tilemap[layer][tile_loc] = Tile(tile_infos["pos"],tile_infos["type"], tile_infos["variant"],
                                                         tile_infos["rotation"] if "rotation" in tile_infos else 0)

        if "offgrid" in map_data:
            self.offgrid_tiles = {}
            for layer in map_data["offgrid"]:
                self.offgrid_tiles[layer] = {}
                for tile_loc in map_data["offgrid"][layer]:
                    tile_infos = map_data["offgrid"][layer][tile_loc]
                    self.offgrid_tiles[layer][tile_loc] = Tile(tile_infos["pos"],tile_infos["type"], tile_infos["variant"],
                                                         tile_infos["rotation"] if "rotation" in tile_infos else 0)
        if "tag_groups" in map_data:
            for group_id in map_data["tag_groups"]:
                for tile_loc, tile_layer in map_data["tag_groups"][group_id]["tiles"]:
                    self.tilemap[tile_layer][tile_loc].group = group_id
            self.tag_groups = map_data["tag_groups"]
            
        if "selection_groups" in map_data:
            self.selection_groups = map_data['selection_groups']
        self.layers = map_data["layers"]
        self.tile_size = map_data['tilesize']

    def get_rotated_autotile_map(self, angle):
        # Helper to rotate a single coordinate pair based on your sin/cos logic
        # We use round() before int() to avoid floating point errors (e.g., 0.999 becoming 0)
        def rot(x, y):
            rx = x * math.cos(angle) - y * math.sin(angle)
            ry = x * math.sin(angle) + y * math.cos(angle)
            return int(round(rx)), int(round(ry))

        return {
            # 2 Neighbors (Corners)
            tuple(sorted([rot(1, 0), rot(0, 1)])): 0,
            tuple(sorted([rot(-1, 0), rot(0, 1)])): 2,
            tuple(sorted([rot(-1, 0), rot(0, -1)])): 4,
            tuple(sorted([rot(1, 0), rot(0, -1)])): 6,

            # 3 Neighbors (T-junctions)
            tuple(sorted([rot(1, 0), rot(0, 1), rot(-1, 0)])): 1,
            tuple(sorted([rot(-1, 0), rot(0, -1), rot(0, 1)])): 3,
            tuple(sorted([rot(-1, 0), rot(0, -1), rot(1, 0)])): 5,
            tuple(sorted([rot(1, 0), rot(0, -1), rot(0, 1)])): 7,

            # 8 Neighbors (Center / Full)
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, 1), rot(1, -1), rot(-1, -1), rot(-1, 1)])): 8,

            # 7 Neighbors (One corner missing)
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, -1), rot(-1, -1), rot(-1, 1)])): 9,
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, 1), rot(1, -1), rot(-1, -1)])): 10,
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, 1), rot(-1, -1), rot(-1, 1)])): 12,
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, 1), rot(1, -1), rot(-1, 1)])): 13,

            # 6 Neighbors (Two corners missing)
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, 1), rot(-1, -1)])): 11,
            tuple(sorted([rot(1, 0), rot(-1, 0), rot(0, -1), rot(0, 1),
                          rot(1, -1), rot(-1, 1)])): 14,
        }

    def autotile(self):
        for layer in self.tilemap:
            for loc in self.tilemap[layer]:
                tile = self.tilemap[layer][loc]
                neighbors = set()
                corner_additional_shifts = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
                for shift in [(1, 0), (-1, 0), (0, -1), (0, 1)] + corner_additional_shifts:
                    check_loc = str(tile.pos[0] + shift[0]) + ";" + str(tile.pos[1] + shift[1])
                    if check_loc in self.tilemap[layer]:
                        if self.tilemap[layer][check_loc].type == tile.type or (tile.type in AUTOTILE_COMPATIBILITY and
                                                                                      self.tilemap[layer][check_loc].type in AUTOTILE_COMPATIBILITY[tile.type]):
                            neighbors.add(shift)
                neighbors = sorted(neighbors)

                angle = -(tile.rotation - 1) * math.pi / 2
                a_map = self.get_rotated_autotile_map(angle)

                if tuple(neighbors) not in a_map:
                    for s in corner_additional_shifts:
                        if s in neighbors:
                            neighbors.remove(s)

                neighbors = tuple(sorted(neighbors))

                if (tile.type in AUTOTILE_TYPES) and (neighbors in a_map):
                    tile.variant = a_map[neighbors]

    def copy(self, new_game):
        tilemap_copy = Tilemap(new_game, self.tile_size)
        tilemap_copy.tilemap = copy.deepcopy(self.tilemap)
        tilemap_copy.offgrid_tiles = copy.deepcopy(self.offgrid_tiles)
        tilemap_copy.layers = copy.deepcopy(self.layers)
        tilemap_copy.selection_groups = copy.deepcopy((self.selection_groups))
        tilemap_copy.tag_groups = copy.deepcopy(self.tag_groups)

        return tilemap_copy

    def solid_check(self, pos, transparent_check=True):
        tile_loc = str(int(pos[0] // self.tile_size)) + ";" + str(int(pos[1] // self.tile_size))
        for layer in self.tilemap:
            if tile_loc in self.tilemap[layer]:
                tile = self.tilemap[layer][tile_loc]
                if tile.type in PHYSICS_TILES:
                    return self.tilemap[layer][tile_loc]
                elif transparent_check and tile.type in set(TRANSPARENT_TILES.keys()) and tile.variant in TRANSPARENT_TILES[tile.type]:
                    return self.tilemap[layer][tile_loc]

    def transparent_tile_check(self, tile, hitbox: pygame.Rect, gravity_dir):
        u_rects = []
        pos, size = hitbox.topleft, hitbox.size
        if tile.type in set(TRANSPARENT_TILES.keys()) and tile.variant in TRANSPARENT_TILES[tile.type]:
            if not self.game.player.collide_with_passable_blocks:  # System in order to make collision with passable blocks more clean (bigger vertical collision offset)
                print(pos[1] + size[1], tile.pos[1] * self.tile_size)
                if pos[1] + size[1] <= tile.pos[1] * self.tile_size:
                    self.game.player.collide_with_passable_blocks = True
            if gravity_dir == 1 and self.game.player.collide_with_passable_blocks:
                u_rects.append(
                    pygame.Rect(tile.pos[0] * self.tile_size, tile.pos[1] * self.tile_size, self.tile_size,
                                self.tile_size))
        return u_rects

    def physics_rects_around(self, hitbox: pygame.Rect):
        pos, size = hitbox.topleft, hitbox.size
        rects = []
        for tile in self.tiles_around(pos, size):
            if tile.type in PHYSICS_TILES:
                rects.append(pygame.Rect(tile.pos[0] * self.tile_size, tile.pos[1] * self.tile_size, self.tile_size, self.tile_size))
        return rects

    def physics_rects_under(self, hitbox: pygame.Rect, gravity_dir):
        u_rects = []
        pos, size = hitbox.topleft, hitbox.size
        for tile in self.tiles_under(pos, size, gravity_dir):
            if tile.type in PHYSICS_TILES:
                u_rects.append(pygame.Rect(tile.pos[0] * self.tile_size, tile.pos[1] * self.tile_size, self.tile_size, self.tile_size))
            else:
                u_rects += self.transparent_tile_check(tile, hitbox, gravity_dir)
        return u_rects

    def get_type_from_rect(self, rect):
        for layer in self.tilemap:
            for tile in self.tilemap[layer]:
                if str(rect.x//self.tile_size) + ";" + str(rect.y//self.tile_size) == tile:
                    return self.tilemap[layer][tile].type

    def get_variant_from_rect(self, rect):
        for layer in self.tilemap:
            for tile in self.tilemap[layer]:
                if str(rect.x//self.tile_size) + ";" + str(rect.y//self.tile_size) == tile:
                    return self.tilemap[layer][tile].variant

    def pos_visible(self, surf, pos, offset = (0, 0), additional_offset=(0, 0)):
           return (offset[0] - additional_offset[0] <= pos[0] <= offset[0] + additional_offset[0] + surf.get_width() and
                   offset[1] - additional_offset[1] <= pos[1] <= offset[1] + additional_offset[1] + surf.get_height())

    def get_same_type_connected_tiles(self, tile, layers):
        connected_tiles = [tile]
        offsets = [(0,1), (0,-1), (1,0), (-1,0)]
        layer_detected = False
        for layer in layers:
            for t in connected_tiles:
                for offset in offsets:
                    check_loc = f"{t.pos[0] + offset[0]};{t.pos[1] + offset[1]}"
                    if check_loc in self.tilemap[layer]:
                        layer_detected = True
                        checked_tile = self.tilemap[layer][check_loc].copy()
                        if checked_tile.type != tile.type:
                            continue
                        if checked_tile not in connected_tiles:
                            connected_tiles.append(checked_tile)
            if layer_detected:
                break

        return connected_tiles

    def fake_tile_colliding_with_player(self, tile):
        r = pygame.Rect(tile.pos[0]*self.tile_size, tile.pos[1]*self.tile_size, self.tile_size, self.tile_size)
        return self.game.player.rect().colliderect(r)

    def set_render_filter(self, tiles, filter_instance : int|tuple[int, int, int]|tuple[int, int, int, int]):
        for tile in tiles:
            if tile not in self.render_filters:
                if type(filter_instance) is int:
                    self.render_filters[tile] = {"opacity": filter_instance}
                elif type(filter_instance) is tuple:
                    self.render_filters[tile] = {"color": filter_instance}


    def render(self, surf, offset = (0, 0), precise_layer = None, with_player = True):

        for layer in self.tilemap:

            if precise_layer is not None:
                if layer != precise_layer:
                    tiles_opacity = 80
                else:
                    tiles_opacity = 255
            else:
                tiles_opacity = 255
            if with_player:
                if layer in self.layers["player"]:
                    pickups_render_and_update(self.game, offset=offset)
                    self.game.player.render(surf, offset=offset)
                if layer in self.layers["fake_tiles"]:
                    self.game.fake_tiles_render(offset=offset)
                    continue

            for x in range(offset[0] // self.tile_size, (offset[0] + surf.get_width()) // self.tile_size + 1):
                for y in range(offset[1] // self.tile_size, (offset[1] + surf.get_height()) // self.tile_size + 1):
                    loc = str(x) + ";" + str(y)
                    if loc in self.tilemap[layer]:
                        tile = self.tilemap[layer][loc]
                        if tile.type in self.game.assets:
                            img = self.game.assets[tile.type][tile.variant].copy()
                            mask = (255, 255, 255, tiles_opacity)

                            if loc in self.render_filters:
                                if list(self.render_filters[loc].keys())[0] == "opacity":
                                    mask = (255, 255, 255, self.render_filters[loc]["opacity"])
                                    img.fill(mask, special_flags=BLEND_RGBA_MULT)
                                elif list(self.render_filters[loc].keys())[0] == "color":
                                    mask = self.render_filters[loc]["color"]
                                    img = pygame.transform.grayscale(img)
                                    highlight = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                                    highlight.fill(mask)

                                    # Blit it onto your image
                                    img.blit(highlight, (0, 0))
                            else:
                                img.fill(mask, special_flags=BLEND_RGBA_MULT)

                            img = pygame.transform.rotate(img, tile.rotation * -90)

                            surf.blit(img, (
                                tile.pos[0] * self.tile_size - offset[0], tile.pos[1] * self.tile_size - offset[1]))
                        else:
                            pass
                            #print(f"{tile.type} not in assets")

            if layer in self.offgrid_tiles:
                for pos in self.offgrid_tiles.copy()[layer]:
                    tile = self.offgrid_tiles[layer][pos]
                    img = self.game.assets[tile.type][tile.variant].copy()
                    mask = (255, 255, 255, tiles_opacity)
                    if pos in self.render_filters:
                        if list(self.render_filters[pos].keys())[0] == "opacity":
                            mask = (255, 255, 255, self.render_filters[pos]["opacity"])
                            img.fill(mask, special_flags=BLEND_RGBA_MULT)

                        elif list(self.render_filters[pos].keys())[0] == "color":
                            mask = self.render_filters[pos]["color"]
                            img = pygame.transform.grayscale(img)
                            highlight = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                            highlight.fill(mask)

                            # Blit it onto your image
                            img.blit(highlight, (0, 0))
                    else:
                        img.fill(mask, special_flags=BLEND_RGBA_MULT)

                    surf.blit(img,
                              (tile.pos[0] - offset[0], tile.pos[1] - offset[1]))


            if layer == "2" and with_player and self.show_collisions:
                self.render_tiles_under(self.game.player.pos, self.game.player.size, 1)

