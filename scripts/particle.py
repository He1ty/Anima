import random

class Particle:
    def __init__(self, game, p_type, pos, velocity=None, frame=0):
        if velocity is None:
            velocity = [0.0, 0.0]
        self.game = game
        self.type = p_type
        self.pos = list(pos)
        self.velocity = list(velocity)
        self.animation = self.game.assets['particle/' + p_type].copy()
        self.animation.frame = frame

    def update(self):
        kill = False
        if self.animation.done:
            kill = True

        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]

        self.animation.update()

        return kill

    def render(self, surf, offset=(0, 0)):
        img = self.animation.img()
        surf.blit(img, (self.pos[0] - offset[0] - img.get_width() // 2,
                        self.pos[1] - offset[1] - img.get_height() // 2))

def update_particles(game, render_scroll):
    for rect in game.leaf_spawners:
        if not game.tilemap.pos_visible(game.display, (rect.x, rect.y), offset=render_scroll, additional_offset=(100, 100)):
            continue
        if random.random() * 49999 < rect.width * rect.height:
            pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
            game.particles.append(Particle(game, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

def particle_render(game, render_scroll):
    for particle in game.particles[:]:
        if not game.tilemap.pos_visible(game.display, particle.pos, offset=render_scroll, additional_offset=(100, 100)):
            game.particles.remove(particle)
            continue
        if particle.update(): game.particles.remove(particle)
        particle.render(game.display, offset=render_scroll)