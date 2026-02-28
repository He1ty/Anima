import pygame
import time

from scripts.saving import save_game


class Pickup:

    def __init__(self, game, pos, pickup_type):
        self.pos = pos
        self.initial_pos = pos.copy()
        self.type = pickup_type
        self.game = game
        self.state = "idle"
        self.animation = self.game.assets[self.type+"/"+self.state].copy()
        self.size = self.animation.images[0].get_size()
        self.taking_time = 0
        self.animations_duration = {
            "doubledashball":
                            {"idle": 8,
                             "taking": 1,
                             "taken": 4,
                             "appearing": 3},
            "soul":
                    {"idle": 5,
                 "taking": 3},

                                    }
        self.recharging_per_type = {
                                        "doubledashball": 3,

                                    }
        if self.type in self.recharging_per_type:
            self.recharging_time = self.recharging_per_type[self.type]  # in seconds

    def update(self):

        if self.state == "idle":
            self.animation.img_duration = self.animations_duration[self.type][self.state]

            # Actions if player touches pickup
            if self.player_is_touching():
                if self.type == "doubledashball":
                    if self.game.player.dash_amt != 2:
                        self.game.player.dash_amt = 2
                        self.animation.frame = 0
                        self.state = "taking"

                # If player touches while dashing
                if self.game.player.dashtime_cur != 0:

                    if self.type == "soul":
                        pos = f"{self.initial_pos[0]};{self.initial_pos[1]}"
                        self.game.collected_souls.append(pos)
                        save_game(self.game, self.game.current_slot)

                    self.animation.frame = 0
                    self.state = "taking"
                    self.animation = self.game.assets[self.type + "/" + self.state].copy()


            # Avoid player movement
            if self.type == "soul":
                self.avoid_player()

        elif self.state == "taking":
            self.animation.img_duration = self.animations_duration[self.type][self.state]
            if self.animation.done:
                self.animation.done = False
                self.animation.frame = 0
                self.state = "taken"
                self.taking_time = time.time()
                self.animation = self.game.assets[self.type + "/" + self.state].copy()

        elif self.state == "taken":
            if "taken" in self.animations_duration[self.type]:
                self.animation.img_duration = self.animations_duration[self.type][self.state]
                if time.time() - self.taking_time >= self.recharging_time:
                    self.state = "appearing"
                    self.animation = self.game.assets[self.type + "/" + self.state].copy()
            else:
                self.game.pickups.remove(self)

        elif self.state == "appearing":
            self.animation.img_duration = self.animations_duration[self.type][self.state]
            if self.animation.done:
                self.animation.done = False
                self.animation.frame = 0
                self.state = "idle"
                self.animation = self.game.assets[self.type + "/" + self.state].copy()

        self.animation.update()

    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

    def initial_rect(self):
        return pygame.Rect(self.initial_pos[0], self.initial_pos[1], self.size[0], self.size[1])

    def avoid_player(self):
        comeback_speed = 0.1  # How fast it returns (0.0 to 1.0)
        avoid_radius = 15  # How close the player gets before it moves
        push_strength = 0.5  # How strongly it's pushed away

        # 1. Get the vector from the player to the object's initial (home) spot
        # (This is where the object "wants" to be)
        home_pos = pygame.Vector2(self.initial_pos)
        current_pos = pygame.Vector2(self.pos)
        player_pos = pygame.Vector2(self.game.player.pos)

        # 2. Return Force: Move back toward initial_pos
        # Lerp (Linear Interpolation) makes the return move smooth and slow down as it arrives
        target_pos = current_pos.lerp(home_pos, comeback_speed)

        # 3. Avoidance Force: If player is too close, push target_pos away
        dist_to_player = current_pos.distance_to(player_pos)

        if dist_to_player < avoid_radius:
            # Calculate direction AWAY from player
            # If distance is 0, use a default vector to avoid error
            push_dir = (current_pos - player_pos)
            if push_dir.length() == 0:
                push_dir = pygame.Vector2(1, 0)
            else:
                push_dir = push_dir.normalize()

            # How much to push? (Stronger when closer)
            push_magnitude = (avoid_radius - dist_to_player) * push_strength
            target_pos += push_dir * push_magnitude

        # 4. Apply the position
        self.pos[0], self.pos[1] = target_pos.x, target_pos.y

    def player_is_touching(self):
        return self.rect().colliderect(self.game.player.rect().inflate(0, 0))

    def render(self, surf, offset=(0, 0)): #display the animation
        surf.blit(self.animation.img(),
                  (self.pos[0] - offset[0], self.pos[1] - offset[1]))

def pickups_render_and_update(game, offset):
        for pickup in game.pickups:
            if game.tilemap.pos_visible(game.display, pickup.pos, offset, additional_offset=pickup.size):
                pickup.update()
                pickup.render(game.display, offset)
