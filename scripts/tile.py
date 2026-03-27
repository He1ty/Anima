import json
import os

from scripts.utils import load_tiles, Animation


class TileManager:

    PHYSICS_TILES = {'whiter_blocks', 'white_blocks', 'purpur_rock', 'vine', 'mossy_stone', 'gray_mossy_stone',
                     'mossy_stone_gluy'}

    PASSABLE_TILES = {'vine_transp': [0, 1, 2], 'vine_transp_back': [0, 1, 2], 'dark_vine': [0, 1, 2],
                         'hanging_vine': [0, 1, 2]}

    ID_MASK = 0xFFFF
    VAR_OFFSET = 16
    ROT_OFFSET = 20
    FLIP_H_BIT = 22
    FLIP_V_BIT = 23

    def __init__(self):
        self.manifest_path = "data/tiles_registry.json"
        self.registry = self.load_registry()
        self.tiles_images = load_tiles()
        self.sync_folder()
        self.tiles = {}
        for tile_type in self.tiles_images:
            t_id = self.get_id(tile_type)
            images = self.tiles_images[tile_type]
            solid = tile_type in self.PHYSICS_TILES
            passable = tile_type in self.PASSABLE_TILES
            self.tiles[t_id] = Tile(tile_type, images, solid, passable)


    def load_registry(self):
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                # On convertit les clés string du JSON en int
                return {int(k): v for k, v in json.load(f).items()}
        return {}

    def sync_folder(self):
        existing_files = list(self.registry.values())
        next_id = max(self.registry.keys(), default=0)

        for tile_type in self.tiles_images:
            if tile_type not in existing_files:
                self.registry[next_id] = tile_type
                next_id += 1

        # Sauvegarde le registre mis à jour
        with open(self.manifest_path, 'w') as f:
            json.dump(self.registry, f, indent=4)

    def get_id(self, t):
        for t_id in self.registry:
            if t == self.registry[t_id]:
                return t_id

    def get_tile_img(self, t_id, variant):
        images = self.tiles[t_id].images.copy()
        if isinstance(images, Animation):
            img = images.img()
        else:
            img = images[variant].copy()
        return img

    def pack_tile(self, tile_id, variant, rotation=0, flip_h=False, flip_v=False):
        """Combine les propriétés dans un seul entier."""

        value = tile_id & self.ID_MASK  # On s'assure que l'ID tient sur 16 bits
        value |= (variant & 0xF) << self.VAR_OFFSET # On place la variant (4 bits)
        value |= (rotation & 0x3) << self.ROT_OFFSET  # On place la rotation (2 bits)
        if flip_h: value |= (1 << self.FLIP_H_BIT)  # On active le bit de miroir H
        if flip_v: value |= (1 << self.FLIP_V_BIT)  # On active le bit de miroir V
        return value

    def unpack_tile(self, value):
        """Extrait les propriétés d'un entier."""
        tile_id = value & self.ID_MASK
        variant = (value >> self.VAR_OFFSET) & 0xF
        rotation = (value >> self.ROT_OFFSET) & 0x3
        flip_h = bool((value >> self.FLIP_H_BIT) & 1)
        flip_v = bool((value >> self.FLIP_V_BIT) & 1)
        return tile_id, variant, rotation, flip_h, flip_v


class Tile:
    __slots__ = ["type", "images", "solid", "passable", "group"]
    def __init__(self, t_type, images, solid, passable, group=None):
        self.type = t_type
        self.images = images
        self.solid = solid
        self.passable = passable
        self.group = group

