import pygame
import os
from PIL import Image



BASE_IMG_PATH = "assets/images/"

def load_image(path, size=None):#Takes a path and load the coresponding image. Can resize the image if size given
    img = pygame.image.load(BASE_IMG_PATH + path).convert_alpha()
    img.set_colorkey((0, 0, 0))
    if size:
        img = pygame.transform.scale(img, size)  # Resize image if size is provided
    return img

def load_images(path, tile_size=None):#Sort in alpha order every images of a given file. Will be used for animations or image variants
    images = []
    if type(tile_size) is not tuple and tile_size:
        tile_size = (tile_size, tile_size)
    for img_name in sorted(os.listdir(BASE_IMG_PATH + path)):
        images.append(load_image(path + '/' + img_name, (tile_size[0], tile_size[1]) if tile_size else None))
    return images

def pil_to_pygame(pil_image):
    # Get the image dimensions and raw pixel data
    mode = pil_image.mode
    size = pil_image.size
    data = pil_image.tobytes()

    # Create the Pygame surface from the raw string data
    surface = pygame.image.fromstring(data, size, mode)

    # .convert_alpha() optimizes the surface for Pygame rendering
    return surface.convert_alpha()

def slice_tileset_to_memory(image_path, tile_width, tile_height):
    tiles = []  # This list will hold all our image objects

    try:
        # Open the source image
        img = Image.open(image_path)
        img_width, img_height = img.size

        # Calculate the number of columns and rows
        columns = img_width // tile_width
        rows = img_height // tile_height

        # Loop through the grid
        for row in range(rows):
            for col in range(columns):
                # Calculate the bounding box for the current tile
                left = col * tile_width
                upper = row * tile_height
                right = left + tile_width
                lower = upper + tile_height

                # Crop the image using the bounding box
                bounding_box = (left, upper, right, lower)
                tile = img.crop(bounding_box)

                # Add the tile object to our list instead of saving it
                tiles.append(pil_to_pygame(tile))

        if len(tiles) > 3:
            tmp = tiles.copy()
            transformation = {7:3, 8:4, 3:5, 4:8, 5:7}
            for i in transformation:
                try:
                    tiles[i] = tmp[transformation[i]]
                except IndexError:
                    pass

        #print(f"Successfully sliced {len(tiles)} tiles into memory.")
        return tiles

    except FileNotFoundError:
        print(f"Error: The file {image_path} was not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def round_up(x):#pretty basic
    return int(x) + 1 if x % 1 != 0 and x > 0 else int(x)

def load_tiles(env=None):#load every tiles (graphic components) coresponding to a given environement
    tiles = {}
    for environment in sorted(os.listdir(BASE_IMG_PATH + 'tiles')) if env is None else [env]:
        for tile in sorted(os.listdir(BASE_IMG_PATH + 'tiles/' + environment)):
            images = load_images('tiles/' + environment + '/' + tile)
            if "tileset.png" in os.listdir(f'{BASE_IMG_PATH}/tiles/{environment}/{tile}'):
                tiles[tile] = slice_tileset_to_memory(image_path=f'{BASE_IMG_PATH}/tiles/{environment}/{tile}/tileset.png', tile_width=16, tile_height=16)
            else:
                tiles[tile] = images
    return tiles

def load_entities(e_info):#load every info on every entities
    tiles = {}
    for ent in sorted(os.listdir(BASE_IMG_PATH + 'entities/')):
        if ent != "player":
            for tile in sorted(os.listdir(BASE_IMG_PATH + 'entities/' + ent)):
                for animation in sorted(os.listdir(BASE_IMG_PATH + 'entities/' + ent + '/' + tile)):
                    if animation in e_info[tile]["left/right"]:
                        for direction in sorted(os.listdir(BASE_IMG_PATH + 'entities/' + ent + '/' + tile + '/' + animation)):
                            tiles[tile + '/' + animation + '/' + direction] = Animation(load_images('entities/' + ent + '/' +
                                                                                                    tile + '/' +
                                                                                                    animation + '/' +
                                                                                                    direction, e_info[tile]["size"]),
                                                                                        img_dur=e_info[tile]["img_dur"][animation],
                                                                                        loop=e_info[tile]["loop"][animation])
                    else:
                        tiles[tile+'/'+animation] = Animation(load_images('entities/' + ent + '/' + tile + '/' + animation, e_info[tile]["size"]),
                                                              img_dur=e_info[tile]["img_dur"][animation],
                                                              loop=e_info[tile]["loop"][animation])
    return tiles

def load_player():
    return {'player/idle': Animation(load_images('entities/player/idle', (16,16)), img_dur=12)}

def load_doors(d_info, env=None):
    tiles = {}
    for environment in sorted(os.listdir(BASE_IMG_PATH + 'doors/')) if env is None else [env]:
        for door in sorted(os.listdir(BASE_IMG_PATH + 'doors/' + environment)):
            if d_info == 'editor':
                tiles[door] = load_images('doors/' + environment + '/' + door + "/closed")
            else:
                for animation in sorted(os.listdir(BASE_IMG_PATH + 'doors/' + environment + '/' + door)):
                    tiles[door + '/' + animation] = Animation(
                        load_images('doors/' + environment + '/' + door + '/' + animation,
                                    d_info[door]["size"]),
                        img_dur=d_info[door]["img_dur"] if animation in ("closing","opening") else 1,
                        loop=False)
    return tiles

def load_activators(env=None):
    tiles = {}
    for activator in sorted(os.listdir(BASE_IMG_PATH + 'activators/')):
        for environment in sorted(os.listdir(BASE_IMG_PATH + 'activators/' + activator)) if env is None else [env]:
            try:
                tiles[environment + "_" + activator[:-1]] = load_images('activators/' + activator + '/' + environment)
            except FileNotFoundError:
                pass
    return tiles

def load_pickups(one_image=False):
    pickups = {}
    for pickup in sorted(os.listdir(BASE_IMG_PATH + 'pickups')):
        if not one_image:
            for animation in sorted(os.listdir(BASE_IMG_PATH + 'pickups/' + pickup)):
                pickups[f"{pickup}/{animation}"] = Animation(load_images(f'pickups/{pickup}/{animation}'), loop = animation in ("idle", "taken"))
        else:
            pickups[pickup] = load_images(f'pickups/{pickup}/idle')
    return pickups

def load_backgrounds(b_info):
    tiles = {}
    for environment in sorted(os.listdir(BASE_IMG_PATH + 'backgrounds/')):
        for bg in sorted(os.listdir(BASE_IMG_PATH + 'backgrounds/' + environment)):
            tiles[environment + "/" + bg[:-4]] = load_image('backgrounds/' + environment + "/" + bg,
                                                       b_info[str(environment + "/" + bg[:-4])]["size"] if str(environment + "/" + bg[:-4]) in b_info else None)
    return tiles

class Animation:
    def __init__(self, images, img_dur = 5, loop = True):
        self.images = images
        self.loop = loop
        self.img_duration = img_dur
        self.done = False
        self.frame = 0

    def copy(self): #will be very useful for the screen.copy when displaying the menu
        return Animation(self.images, self.img_duration, self.loop)

    def update(self):
        if self.loop > 0:
            self.frame = (self.frame + 1) % (self.img_duration * len(self.images))
            if type(self.loop) in (int, float):
                self.loop -= (1/int(self.img_duration * len(self.images)))

        else:
            self.frame = min(self.frame + 1, self.img_duration * len(self.images) - 1)
            if self.frame >= self.img_duration * len(self.images) - 1:
                self.done = True

    def img(self):
        return self.images[int(self.frame / self.img_duration)]



