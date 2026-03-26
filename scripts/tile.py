import copy

class Tile:

    __slots__ = ["pos", "type", "variant", "rotation", "group"]
    def __init__(self, pos, t_type, variant, rotation):
        self.pos = pos
        self.type = t_type
        self.variant = variant
        self.rotation = rotation
        self.group = None

    def copy(self):
        return copy.deepcopy(self)