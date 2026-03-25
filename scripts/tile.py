class Tile:
    def __init__(self, pos, t_type, variant, rotation):
        self.pos = pos
        self.type = t_type
        self.variant = variant
        self.rotation = rotation
        self.group = None