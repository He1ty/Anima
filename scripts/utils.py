import random

import pygame
import os



BASE_IMG_PATH = "assets/"
ANIMATED_CATEGORIES = {"doors", "pickups", "checkpoint", "animated_blocks"}

def load_image(path, size=None):#Takes a path and load the coresponding image. Can resize the image if size given
    img = pygame.image.load(BASE_IMG_PATH + path).convert_alpha()
    img.set_colorkey((0, 0, 0))
    if size:
        img = pygame.transform.scale(img, size)  # Resize image if size is provided
    return img

def load_images(path, tile_size=None):
    """
    Sort in alpha order every image of a given file. Will be used for animations or image variants
    :param path:
    :param tile_size:
    :return:
    """
    images = []
    if type(tile_size) is not tuple and tile_size:
        tile_size = (tile_size, tile_size)
    for img_name in sorted(os.listdir(BASE_IMG_PATH + path)):
        images.append(load_image(path + '/' + img_name, (tile_size[0], tile_size[1]) if tile_size else None))
    return images

def load_animations(path, tile_size=None):
    animations = {}
    for animation in os.listdir(f"{BASE_IMG_PATH}{path}"):
        animations[animation] = load_images(f"{path}/{animation}")
    return animations


def load_tileset(image_path, tile_width, tile_height, spiral_order=False, size=None):
    """
    Slices a tileset image into a list of individual surfaces.
    """
    # Load the master sheet
    sheet = pygame.image.load(image_path).convert_alpha()
    sheet_width, sheet_height = sheet.get_size()

    tiles = []

    # Iterate through the sheet by tile dimensions
    for y in range(0, sheet_height, tile_height):
        for x in range(0, sheet_width, tile_width):
            # Define the rectangular area of the tile
            rect = pygame.Rect(x, y, tile_width, tile_height)

            # Extract the subsurface and store it
            tile = sheet.subsurface(rect)
            if size:
                tile = pygame.transform.scale(tile, size)
            tiles.append(tile)

    if spiral_order:
        if len(tiles) > 3:
            tmp = tiles.copy()
            transformation = {7: 3, 8: 4, 3: 5, 4: 8, 5: 7}
            for i in transformation:
                try:
                    tiles[i] = tmp[transformation[i]]
                except IndexError:
                    pass

    return tiles

def round_up(x): #pretty basic
    return int(x) + 1 if x % 1 != 0 and x > 0 else int(x)

def load_tiles():
    tiles = {}
    for environment in os.listdir(f"{BASE_IMG_PATH}environments"):
        path = f"{BASE_IMG_PATH}environments/{environment}/images/tiles"
        for category in sorted(os.listdir(path)):
            for tile in sorted(os.listdir(f"{path}/{category}")):
                if category in ANIMATED_CATEGORIES:
                    tiles[tile] = Animation(
                        load_animations(f"environments/{environment}/images/tiles/{category}/{tile}"))
                else:
                    images = load_images(f"environments/{environment}/images/tiles/{category}/{tile}")
                    if "tileset.png" in os.listdir(f'{path}/{category}/{tile}'):
                        tiles[tile] = load_tileset(image_path=f"{path}/{category}/{tile}/tileset.png",
                                                   tile_width=16, tile_height=16, spiral_order=True)
                    else:
                        tiles[tile] = images
    return tiles

def load_editor_tiles():
    categories = {}
    for environment in os.listdir(f"{BASE_IMG_PATH}environments"):
        path = f"{BASE_IMG_PATH}environments/{environment}/images/tiles"
        categories[environment] = {}
        for category in sorted(os.listdir(path)):
            category_name = category.capitalize()
            category_tiles = {category_name:{}}
            for tile in sorted(os.listdir(f"{path}/{category}")):
                if category in ANIMATED_CATEGORIES:
                    category_tiles[category_name][tile] = [Animation(
                        load_animations(f"environments/{environment}/images/tiles/{category}/{tile}")).img()]
                else:
                    images = load_images(f"environments/{environment}/images/tiles/{category}/{tile}")
                    if "tileset.png" in os.listdir(f'{path}/{category}/{tile}'):
                        category_tiles[category_name][tile] = load_tileset(image_path=f"{path}/{category}/{tile}/tileset.png",
                                                   tile_width=16, tile_height=16, spiral_order=True)
                    else:
                        category_tiles[category_name][tile] = images
            categories[environment].update(category_tiles)

    return categories

def load_player():
    return {'player/idle': Animation(load_animations(f'player/animations'), img_dur=12)}

def load_particles():
    tiles = {}
    for environment in sorted(os.listdir(f"{BASE_IMG_PATH}environments/")):
        if "particles" in sorted(os.listdir(f"{BASE_IMG_PATH}environments/{environment}/images/")):
            for particle in sorted(os.listdir(f"{BASE_IMG_PATH}environments/{environment}/images/particles")):
                tiles[f"particle/{particle}"] = Animation(load_images(f'environments/{environment}/images/particles/leaf'), loop=5)

    return tiles

def load_backgrounds(b_info):
    tiles = {}
    for map_id in b_info:
        path = b_info[map_id]["path"]

        if b_info[map_id]["animated"]:
            tiles[map_id] = Animation(load_animations(path), img_dur=b_info[map_id]["img_dur"], loop=b_info[map_id]["loop"])
            continue
        for bg in sorted(os.listdir(f"{BASE_IMG_PATH}{path}")):
                tiles[map_id + "/" + bg[:-4]] = load_image(f"{path}/{bg}",
                                                           (480, 300))

    return tiles

def create_rect_alpha(color, rect, alpha):
    """
    surface : surface where we draw the rectangle (ex: screen)
    color   : (R, G, B)
    rect    : (x, y, width, height)
    alpha   : opacity between 0 et 255
    """

    shape_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    shape_surf.fill((color[0], color[1], color[2], alpha))
    return shape_surf

def key_name(keycode: int) -> str:
    if keycode is None:
        return ""
    name = pygame.key.name(keycode)
    return name.upper() if len(name) == 1 else name.capitalize()

def build_items(bindings: dict) -> list:
    """Liste plate : ('cat', nom) ou ('bind', cat, action)"""
    items = []
    for cat, actions in bindings.items():
        items.append(("cat", cat))
        for action in actions:
            items.append(("bind", cat, action))
    return items

def random_color():
    return (random.randrange(0, 255, 1),
            random.randrange(0, 255, 1),
            random.randrange(0, 255, 1))

def sign(n):
    return n/abs(n)

class Animation:
    def __init__(self, images, img_dur = 5, loop = -1):
        self.images = images
        self.animation = next(iter(images))
        self.loop = loop
        self.img_duration = img_dur
        self.done = False
        self.frame = 0

    def copy(self): #will be very useful for the screen.copy when displaying the menu
        return Animation(self.images, self.img_duration, self.loop)

    def update(self):
        if self.loop > 0:
            self.frame = (self.frame + 1) % (self.img_duration * len(self.images[self.animation]))
            self.loop -= (1/int(self.img_duration * len(self.images[self.animation])))
        elif self.loop < 0:
            self.frame = (self.frame + 1) % (self.img_duration * len(self.images[self.animation]))
        else:
            self.frame = min(self.frame + 1, self.img_duration * len(self.images[self.animation]) - 1)
            if self.frame >= self.img_duration * len(self.images[self.animation]) - 1:
                self.done = True

    def img(self):
        return self.images[self.animation][int(self.frame / self.img_duration)].copy()





