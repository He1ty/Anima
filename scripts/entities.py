import time
from typing import override

import pygame
import random
import math


class DamageBlock:
    def __init__(self, game_instance, pos):
        # Initialize a block that damages the player on contact
        self.pos = pos
        self.game = game_instance
        self.circle_hitbox = False

    def rect(self):
        # Return collision rectangle

        if 0:
            self.circle_hitbox = True
            r = pygame.Rect(self.pos[0], self.pos[1],
                            self.image.get_width(), self.image.get_height())
            r = r.inflate(-4, -4)

            return r

class Spike(DamageBlock):

    def __init__(self, game_instance, pos, tile):
        super().__init__(game_instance, pos)
        tile_id, variant, rotation, flip_x, flip_y = game_instance.tilemap.tile_manager.unpack_tile(tile)
        image = game_instance.tilemap.tile_manager.tiles[tile_id].images[variant]
        image = pygame.transform.rotate(image, rotation * -90)
        image = pygame.transform.flip(image, flip_x, flip_y)
        self.rotation = rotation
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.image = image

    @override
    def rect(self):
        width = 10
        height = 5
        angle = ((self.rotation - 1) % 4) * math.pi / 2
        if ((self.rotation - 1) % 4) % 2 == 0:
            width, height = height, width
            pos = (self.pos[0] + (self.image.get_width() - width) / 2 - math.cos(angle) * (
                    self.image.get_width() - width) / 2, self.pos[1] + (self.image.get_height() - height) / 2
                   )
        else:
            pos = (self.pos[0] + (self.image.get_width() - width) / 2,
                   self.pos[1] + ((self.image.get_height() - height) / 2) - math.sin(angle) * (
                               self.image.get_height() - height) / 2
                   )

        r = pygame.Rect(pos[0], pos[1],
                        width, height)

        return r

    def update(self):
        if not self.game.player.noclip:
            if not self.circle_hitbox:
                if self.game.player.collide_with(self.rect(), static_rect=True):
                    kill_player(self.game)
            else:
                dx = self.game.player.pos[0] - self.pos[0]
                dy = self.game.player.pos[1] - self.pos[1]
                distance = math.sqrt(dx ** 2 + dy ** 2)
                if distance < (
                        self.game.player.size[0] / 2 + self.image.get_width() / 2) and self.game.player.collide_with(
                        self.rect(), static_rect=True):
                    kill_player(self.game)

    def render(self, surf, offset=(0, 0)):
        img = self.image

        surf.blit(img, (self.pos[0] - offset[0], self.pos[1] - offset[1]))
        if self.game.show_spikes_hitboxes:
            r = self.rect()
            if self.circle_hitbox:
                xq = r.right - (r.right - r.x) / 2 != r.centerx
                yq = r.bottom - (r.bottom - r.y) / 2 != r.centery

                pygame.draw.circle(surf, (255, 0, 255),
                                   (r.centerx - offset[0] + 1 * xq, r.centery - offset[1] + 1 * yq), r.width / 2)
            else:
                pygame.draw.rect(surf, (255, 0, 255), pygame.Rect(r.x - offset[0], r.y - offset[1],
                                                                  r.width, r.height))




def blur(surface, span):
    # Apply a blur effect to a surface
    for i in range(span):
        surface = pygame.transform.smoothscale(surface, (surface.get_width() // 2, surface.get_height() // 2))
        surface = pygame.transform.smoothscale(surface, (surface.get_width() * 2, surface.get_height() * 2))
    return surface


def message_display(surface, message, auteur, font, couleur):
    # Show a message with author on the screen
    texte = font.render(message, True, couleur)
    auteur_texte = font.render(f"- {auteur}", True, couleur)

    surface_rect = surface.get_rect()
    texte_rect = texte.get_rect(center=(surface_rect.centerx, surface_rect.centery - 20))
    auteur_rect = auteur_texte.get_rect(center=(surface_rect.centerx, surface_rect.centery + 20))

    surface.blit(texte, texte_rect)
    surface.blit(auteur_texte, auteur_rect)


def death_animation(screen):
    # Display death animation with philosophical quotes
    clock = pygame.time.Clock()
    pygame.font.init()
    font = pygame.font.Font(None, 36)

    citations = {
        "Lingagu ligaligali wasa.": "Giannini Loic, Ingenio magno",
        "The darkest places in hell are reserved for those who maintain their neutrality intimes of moral crisis.": "Dante Alighieri, 'Il sommo Poeta'",
        "You cannot find peace by avoiding life": "Virginia Woolf, Writer ",
        "All men's souls are immortal, but the souls of the righteous are immortal and divine.": "Socrates, Founder of Philosophy",
        "The wounds of conscience are the voice of God within the soul.": "Saint Augustine, Founder of Theology",
        "True redemption is seized when you accept the future consequences of your past actions.": "Unknown (stoicism inspired)",
        "To die is nothing; but it is terrible not to live.": "Victor Hugo, 'l'homme siècle'",
        "Do not go gentle into that good night.": "Dylan Thomas, Writer",
        "Even the devil was once an angel.": "Thomas d'Aquinas(Attributed to him)",
        "Every saint has a past, and every sinner has a future.": "Oscar Wilde, Writer ",
        "We are each our own devil, and we make this world our hell.": "Oscar wilde, Writer ",
        "It is not death that a man should fear, but never beginning to live.": "Marcus Aurelius, Pontifex Maximus",
        "No man is lost while he still hopes.": "Miguel Cervantes, Lépante Soldier, Writer, Poet, SceneWriter",
        "Death is nothing, but to live defeated and without glory is to die every day.": "Napoléon Bonaparte, Emperor of Europe",
        "It is not death i am afraid of, It is not to have lived enough ": "Napoléon Bonaparte, Emperor of Europe",
        "Language is a subset of humanity": "Benoît Tailhades, Ingenio Magno, ",
        "Mon Avis :" :"Giannini Loic, Ingenio Magno"
    }

    message, auteur = random.choice(list(citations.items()))

    screen_copy = screen.copy()

    for blur_intensity in range(1, 6):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return

        blurred_screen = blur(screen_copy, blur_intensity)
        screen.blit(blurred_screen, (0, 0))
        message_display(screen, message, auteur, font, (255, 255, 255))
        pygame.display.flip()
        clock.tick(15)


def kill_player(game):
    game.player_dead = True
    game.death_counter += 1

def deal_dmg(game, source, target, att_dmg=5, att_time=1):
    # Handle damage dealing between entities
    current_time = time.time()
    if target == "player" and current_time - source.last_attack_time >= att_time:
        source.last_attack_time = time.time()
        game.player_hp -= att_dmg
        game.damage_flash_active = True
        source.is_dealing_damage = True
        game.damage_flash_end_time = pygame.time.get_ticks() + game.damage_flash_duration

    elif target != "player" and current_time - game.player_last_attack_time >= game.player_attack_time:
        game.player_last_attack_time = time.time()
        target.hp -= game.player_dmg


def deal_knockback(entity, target, strenght, knockback=None, stun_duration=0.5):
    # Apply knockback force to targets when hit
    stun_elapsed = time.time() - target.last_stun_time
    knockback_force = max(0, strenght * (1.0 - stun_elapsed / stun_duration))

    if not target.knockback_dir[0] and not target.knockback_dir[1] and knockback is None:
        target.knockback_dir[0] = 1 if entity.rect().centerx < target.rect().centerx else -1
        target.knockback_dir[1] = 0
    return target.knockback_dir[0] * knockback_force, target.knockback_dir[1] * knockback_force


def update_throwable_objects_action(game):
    # Handle interaction with throwable objects
    '''for o in game.throwable:
        if not o.grabbed and not game.player_grabbing:
            if o.can_interact(game.player.rect()):
                o.grab(game.player)
                return
        elif o.grabbed:
            o.launch([game.player.last_direction, -1], 3.2)
            return'''
    return


def attacking_update(game):
    # Update player attack state and handle attack direction
    game.attacking = ((game.dict_kb["key_attack"] == 1 and time.time() - game.player_last_attack_time >= 0.03)
                      or game.player.action in (
                      "attack/left", "attack/right")) and not game.player.is_stunned and not game.player_grabbing
    if game.attacking and game.player.action == "attack/right" and game.player.get_direction("x") == -1:
        game.attacking = False
        game.dict_kb["key_attack"] = 0
    elif game.attacking and game.player.action == "attack/left" and game.player.get_direction("x") == 1:
        game.attacking = False
        game.dict_kb["key_attack"] = 0

    if game.attacking and game.player.animation.done:
        game.dict_kb["key_attack"] = 0
        game.player_last_attack_time = time.time()

def death_handling(game, screen):
    if game.player_dead:
        # Handle player death, respawn them at the proper position
        game.cutscene = False
        death_animation(screen)
        nb_deaths = game.death_counter
        game.load_game(game.current_slot)
        game.death_counter = nb_deaths
        game.transition = -30
        game.player.dash_amt = 1
        game.player.velocity = [0, 0]
        game.player.dashtime_cur = 0
        for key in game.dict_kb.keys():
            game.dict_kb[key] = 0

        game.player_dead = False