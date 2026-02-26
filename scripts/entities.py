import time
import pygame
import random
import math

from scripts.saving import load_game
from scripts.display import update_light


class PhysicsEntity:
    def __init__(self, game, e_type, pos, size):
        # Initialize a physics-based entity with position, size and movement properties
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}

        self.action = ''
        self.flip = False
        try:
            self.set_action('idle')
        except AttributeError:
            pass
        except KeyError:
            pass

        self.last_movement = [0, 0]

    def rect(self):
        # Return the collision rectangle for this entity
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

    def set_action(self, action):
        # Change the animation action for this entity
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()

    def update(self, tilemap, movement=(0, 0)):
        # Update entity position, handle collisions with environment and apply physics
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}

        frame_movement = (movement[0] + self.velocity[0], movement[1] + self.velocity[1])

        self.pos[0] += frame_movement[0]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos, self.size) + self.game.doors_rects:
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0:
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                if frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x

        self.pos[1] += frame_movement[1]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_under(self.pos, self.size) + self.game.doors_rects:
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                self.pos[1] = entity_rect.y
        for rect in tilemap.physics_rects_around(self.pos, self.size):
            if entity_rect.colliderect(rect):
                if frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
            self.pos[1] = entity_rect.y

        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True

        self.last_movement = movement

        self.velocity[1] = min(5, self.velocity[1] + 0.1)

        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0

        self.animation.update()

    def render(self, surf, offset=(0, 0)):
        # Draw the entity on the screen with proper orientation
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False),
                  (self.pos[0] - offset[0], self.pos[1] - offset[1]))


class Enemy(PhysicsEntity):
    def __init__(self, game, enemy_type, pos, size, hp, attack_info):
        # Initialize an enemy entity with behavior and combat stats
        super().__init__(game, 'enemy', pos, size)

        self.walking = 0
        self.enemy_type = enemy_type

        self.attack_distance = attack_info["attack_distance"]
        self.vision_distance = 100
        self.is_attacking = False
        self.is_chasing = False
        self.mono_direction_attack_check = False
        self.player_x = self.game.player.rect().centerx
        self.enemy_x = self.rect().centerx
        self.enemy_y = self.rect().centery
        self.last_attack_time = 0
        self.attack_dmg = attack_info["attack_dmg"]
        self.attack_time = attack_info["attack_time"]
        self.first_attack_time = 0
        self.is_dealing_damage = False
        self.hp = hp
        self.hit = False
        self.stunned = False
        self.last_stun_time = 0
        self.is_attacked = False
        self.knockback_dir = [0, 0]
        self.animation = self.game.assets[self.enemy_type + '/idle'].copy()

    def update(self, tilemap, movement=(0, 0)):
        # Update enemy behavior, AI and combat state
        self.player_x = self.game.player.rect().centerx
        self.enemy_x = self.rect().centerx
        self.is_attacked = (self.game.attacking
                            and self.distance_with_player() <= self.game.player_attack_dist
                            and self.player_looking_at_entity()
                            and not self.is_attacked)

        if self.hp <= 0:
            self.animation.update()
            return

        if self.is_attacked and not self.hit:
            self.is_attacking = True
            self.is_chasing = True
            if time.time() - self.game.player_last_attack_time >= self.game.player_attack_time:
                deal_dmg(self.game, 'player', self)
                self.stunned = True
                self.hit = True
                self.last_stun_time = time.time()

        if not self.game.holding_attack and (
                not ("attack" in self.game.player.action) or self.game.player.animation.done):
            self.hit = False

        self.update_attack()

        # Handle stun state first
        if self.stunned:
            self.is_chasing = False
            self.is_attacking = False

            # Calculate time since stun started
            stun_elapsed = time.time() - self.last_stun_time
            stun_duration = 0.5

            if stun_elapsed >= stun_duration:
                self.stunned = False
                self.is_attacking = True
                self.is_chasing = True

            else:
                # Add stun animation/movement here
                movement = deal_knockback(self.game.player, self, 1)
                super().update(tilemap, movement=movement)
                self.flip = self.player_x < self.enemy_x
                self.animations(movement)
                return  # Skip the rest of the normal update logic
        self.knockback_dir = [0, 0]

        # Regular (non-stunned) behavior continues below
        if self.walking:
            if tilemap.solid_check((self.rect().centerx + (-7 if self.flip else 7), self.pos[1] + 23)):
                if self.collisions['right'] or self.collisions['left']:
                    self.flip = not self.flip
                else:
                    movement = (movement[0] - 0.5 if self.flip else 0.5, movement[1])
                self.walking = max(0, self.walking - 1)
            else:
                self.flip = not self.flip
                self.is_attacking = False
                self.is_chasing = False

        elif not (self.is_attacking or self.is_chasing):
            rand = random.random()
            if rand < 0.01:
                self.walking = random.randint(30, 120)

        if self.distance_with_player() <= self.vision_distance:
            if tilemap.solid_check((self.rect().centerx + (-7 if self.flip else 7), self.pos[1] + 23)):
                if (self.check_if_player_close(self.vision_distance, not self.is_chasing)
                        or (not self.game.player.is_on_floor() and self.is_chasing)):
                    if self.check_if_player_close(self.vision_distance, not self.is_chasing):
                        if self.player_x < self.enemy_x:
                            self.flip = True
                        elif self.player_x > self.enemy_x:
                            self.flip = False
                    if not self.is_attacking:
                        self.is_chasing = True
                        movement = (movement[0] - 1 if self.flip else 1, movement[1])
                else:
                    self.is_chasing = False

                if self.check_if_player_close(self.attack_distance, self.mono_direction_attack_check) or (
                        not self.game.player.is_on_floor() and self.is_attacking):
                    self.walking = 0
                    self.is_attacking = True
                    self.is_chasing = True
            else:
                self.flip = not self.flip
                self.is_attacking = False
                self.is_chasing = False

        if self.distance_with_player() > self.attack_distance and self.is_attacking:
            self.is_attacking = False

        if self.distance_with_player() > self.vision_distance and self.is_chasing:
            self.is_chasing = False

        super().update(tilemap, movement=movement)
        self.animations(movement)

    def set_action(self, action):
        # Set the enemy's animation based on its current action
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.enemy_type + '/' + self.action].copy()

    def update_attack(self):
        # Handle enemy attack logic and timing
        if self.is_attacking and not self.stunned:
            if time.time() - self.first_attack_time >= self.attack_time / 5:
                deal_dmg(self.game, self, 'player', self.attack_dmg, self.attack_time)
                self.is_dealing_damage = False
        elif not self.is_attacking:
            self.last_attack_time = 0
            self.first_attack_time = time.time()

    def check_if_player_close(self, vision_distance, mono_direction=True):
        # Check if the player is within detection distance and line of sight
        if (not (self.game.tilemap.between_check(self.game.player.pos, self.pos))
                and self.game.player.pos[1] + self.game.player.size[1] == int(self.pos[1] + self.size[1])):
            if abs(self.player_x - self.enemy_x) <= vision_distance:
                if mono_direction:
                    if self.flip and self.player_x < self.enemy_x:
                        return True
                    if not self.flip and self.player_x > self.enemy_x:
                        return True
                else:
                    return True
        return False

    def distance_with_player(self):
        # Calculate the distance between enemy and player
        relative_player_pos = 1 if self.player_x > self.enemy_x else -1
        if self.pos[0] < self.player_x < self.pos[0] + self.size[0]:
            return True
        return math.sqrt((self.enemy_x + relative_player_pos * self.size[0] / 2 - self.player_x) ** 2 + (
                (self.pos[1] + self.size[1]) - (self.game.player.pos[1] + self.game.player.size[1])) ** 2)

    def player_looking_at_entity(self):
        # Check if the player is facing the enemy
        if (not (self.game.tilemap.between_check(self.game.player.pos, self.pos))
                and self.game.player.pos[1] <= self.pos[1] + self.size[1]):
            if self.pos[0] + self.size[0] >= self.player_x >= self.pos[0]:
                return True
            elif self.game.player.last_direction == 1:
                return self.enemy_x > self.player_x
            elif self.game.player.last_direction == -1:
                return self.enemy_x < self.player_x

    def render(self, surf, offset=(0, 0)):
        # Draw the enemy on screen with proper orientation
        if self.game.e_info[self.enemy_type]["left/right"]:
            surf.blit(self.animation.img(), (self.pos[0] - offset[0], self.pos[1] - offset[1]))
        else:
            surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False),
                      (self.pos[0] - offset[0], self.pos[1] - offset[1]))

    def animations(self, movement):
        # Set appropriate animation based on enemy state
        animation_running = False

        if self.stunned:
            self.set_action("hit")
            animation_running = True

        if self.is_attacking and not animation_running and not self.stunned:
            if self.action != "attack":
                self.set_action("attack")
            animation_running = True

        if not self.is_attacking and not animation_running:
            if movement[0] != 0:
                if self.game.e_info[self.enemy_type]["left/right"]:
                    if self.flip:
                        self.set_action("run/left")
                    else:
                        self.set_action("run/right")
                else:
                    self.set_action("run")
            else:
                self.set_action("idle")


class DistanceEnemy(Enemy):
    def __init__(self, game, enemy_type, pos, size, hp, attack_info):
        # Initialize a ranged enemy that can fire projectiles
        super().__init__(game, enemy_type, pos, size, hp, attack_info)
        self.projectile_sent = False
        self.mono_direction_attack_check = True

    def update_attack(self):
        # Handle ranged attack logic and create projectiles
        if self.is_attacking and not self.stunned:
            if time.time() - self.first_attack_time >= self.attack_time / 5:
                if time.time() - self.last_attack_time >= self.attack_time:
                    self.last_attack_time = time.time()
                    self.game.projectiles.append({"type": self.enemy_type + "_projectile",
                                                  "pos": self.pos.copy(),
                                                  "direction": [-1 if self.flip else 1, 0],
                                                  "timer": 0,
                                                  "dmg": 10})
                    self.is_dealing_damage = True
                self.is_dealing_damage = False
        elif not self.is_attacking:
            self.last_attack_time = 0
            self.first_attack_time = time.time()

class Throwable(PhysicsEntity):
    def __init__(self, game, o_type, pos, size):
        # Initialize an object that can be picked up and thrown
        super().__init__(game, o_type, pos, size)
        self.action = ''
        self.flip = False
        try:
            self.set_action('intact')
        except AttributeError:
            pass
        self.grabbed = False
        self.grabbing_entity = None

    def update(self, tilemap, movement=(0, 0)):
        # Update physics for throwable objects, handle grabbing state
        if not self.grabbed:
            self.game.player_grabbing = False

            # Call parent update (handles physics and movement)
            super().update(tilemap, movement=(0, 0))

            # Check if we've collided with something (implement based on your collision system)
            # If we hit something horizontally, stop horizontal movement
            if self.collisions["left"] or self.collisions["right"] or self.collisions["down"] or self.collisions["up"]:
                self.velocity[0] = 0
            # We keep vertical velocity for gravity effects

        else:
            self.game.player_grabbing = True
            self.pos = [
                self.grabbing_entity.rect().centerx + 5 if self.grabbing_entity.last_direction == 1 else self.grabbing_entity.rect().centerx - 15,
                self.grabbing_entity.rect().centery - 10]

    def can_interact(self, player_rect, interaction_distance=2):
        # Check if player is close enough to interact with this object
        can_interact = self.rect().colliderect(player_rect.inflate(interaction_distance, interaction_distance))
        return can_interact

    def grab(self, entity):
        # Player grabs this object
        self.grabbed = True
        self.grabbing_entity = entity

    def launch(self, direction, strength):
        # Throw the object in a specific direction with given strength
        # Release from grabbed state
        self.grabbed = False

        # Calculate magnitude of the direction vector
        magnitude = math.sqrt(direction[0] ** 2 + direction[1] ** 2)

        # Avoid division by zero
        if magnitude > 0:
            # Normalize and multiply by strength
            normalized_x = direction[0] / magnitude
            normalized_y = direction[1] / magnitude

            # Set velocity based on strength and direction
            self.velocity[0] = normalized_x * strength
            self.velocity[1] = normalized_y * strength
        else:
            # If direction vector is zero, just throw upward
            self.velocity[0] = 0
            self.velocity[1] = -strength

    def rect(self):
        # Return collision rectangle
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

class DamageBlock:
    def __init__(self, game, pos, size, hitbox_type='', rotation=0):
        # Initialize a block that damages the player on contact
        self.pos = pos
        self.size = size
        self.last_attack_time = 0
        self.game = game
        self.type = hitbox_type
        self.rotation = (rotation - 1) % 4
        self.circle_hitbox = False

    def rect(self):
        # Return collision rectangle

        if self.type == 'spike':
            width = 8
            height = 5
            angle = self.rotation*math.pi/2
            if self.rotation % 2 == 0:
                width, height = height, width
                pos = (self.pos[0] + (self.size.get_width() - width) / 2 - math.cos(angle) * (
                            self.size.get_width() - width) / 2, self.pos[1] + (self.size.get_height() - height) / 2
                       )
            else:
                pos = (self.pos[0] + (self.size.get_width() - width) / 2,
                       self.pos[1] + ((self.size.get_height() - height) / 2) - math.sin(angle) * (self.size.get_height() - height) / 2
                       )

            r = pygame.Rect(pos[0], pos[1],
                            width, height)

        elif self.type == 'spike_block':
            self.circle_hitbox = True
            r = pygame.Rect(self.pos[0], self.pos[1],
                            self.size.get_width(), self.size.get_height())
            r = r.inflate(-4, -4)

        return r

    def render(self, surf, circle, offset=(0, 0)):
        # Draw the damage block on screen
        r = self.rect()
        if circle:
            xq = r.right - (r.right - r.x) / 2 != r.centerx
            yq = r.bottom - (r.bottom - r.y) / 2 != r.centery

            pygame.draw.circle(surf, (255, 0, 255),(r.centerx - offset[0] + 1*xq, r.centery - offset[1] + 1*yq), r.width/2)
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
        "Language is a subset of humanity": "Benoît Tailhades, Ingenio Magno, "
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

    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                print("dead")
                return
        clock.tick(30)


def kill_player(game, screen, spawn_pos, spawn_level, animation=True, transition=True):
    # Handle player death, respawn them at the proper position
    game.cutscene = False
    if animation:
        death_animation(screen)
    pickups = game.pickups
    load_game(game, game.current_slot)
    game.pickups = pickups
    game.transition = -30
    game.player.dash_amt = 1
    game.player.velocity = [0, 0]
    game.player.dashtime_cur = 0



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
    for o in game.throwable:
        if not o.grabbed and not game.player_grabbing:
            if o.can_interact(game.player.rect()):
                o.grab(game.player)
                return
        elif o.grabbed:
            o.launch([game.player.last_direction, -1], 3.2)
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

def death_handling(game):
    if game.player.pos[1] > game.max_falling_depth or game.player_hp <= 0:
        kill_player(game, game.screen, game.spawn_point["pos"], game.spawn_point["level"])
        for key in game.dict_kb.keys():
            game.dict_kb[key] = 0
        game.player_hp = 100