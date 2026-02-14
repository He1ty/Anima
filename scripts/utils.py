import pygame
import os
import json



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

def round_up(x):#pretty basic
    return int(x) + 1 if x % 1 != 0 and x > 0 else int(x)

def load_tiles(env=None):#load every tiles (graphic components) coresponding to a given environement
    tiles = {}
    for environment in sorted(os.listdir(BASE_IMG_PATH + 'tiles')) if env is None else [env]:
        for tile in sorted(os.listdir(BASE_IMG_PATH + 'tiles/' + environment)):
            tiles[tile] = load_images('tiles/' + environment + '/' + tile)
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
                pickups[f"{pickup}/{animation}"] = Animation(load_images(f'pickups/{pickup}/{animation}'))
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



