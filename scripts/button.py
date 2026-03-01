import pygame

from scripts.utils import load_image


class EditButton:

    def __init__(self, left, top, width, height, clicking,text=None,hover=False,):
        self.x = left
        self.y = top
        self.width = width
        self.height = height
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.clicking = clicking
        self.activated = True

    def pressed(self, mpos):
        if self.clicking and self.rect.collidepoint(mpos):
            return True
        return False

    def draw(self, surf, color, mpos):
        if self.rect.collidepoint(mpos) and not self.pressed(mpos) and self.activated:
            color = (0, 0, 0)
        pygame.draw.rect(surf, color, self.rect)

class MenuButton:
    def __init__(self, text:str, font:pygame.font.Font, pos_center:tuple[int,int], text_color:tuple[int,int,int]):
        self.text_surf = font.render(text, True, text_color)
        self.text = text
        self.font = font
        self.rect = self.text_surf.get_rect(center=pos_center)
        self.text_color = text_color
        self.hover = False
        self.hover_image = load_image("Opera_senza_titolo.png")
        self.hover2_image = pygame.transform.flip(load_image("Opera_senza_titolo.png"), True, False)


    def draw(self, screen):
        if self.hover:
            self.text_surf = self.font.render(self.text, True, self.text_color)
            image_x = self.rect.x - self.hover_image.get_width() - 5
            image_y = self.rect.y + (self.rect.height - self.hover_image.get_height()) // 2
            screen.blit(self.hover_image, (image_x, image_y))

            image_x2 = self.rect.x + self.rect.width + 5
            image_y2 = self.rect.y + (self.rect.height - self.hover2_image.get_height()) // 2
            screen.blit(self.hover2_image, (image_x2, image_y2))
        else:
            self.text_surf = self.font.render(self.text, True, self.text_color)
        # Draw the text
        screen.blit(self.text_surf, self.rect)

    def is_clicked(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return True
            return False

    def is_selected(self, event):
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def handle_event(self,event):
        if self.hover:
            return self.is_clicked(event)
        return None

    def start_hover_effect(self):
        self.hover = True
    def end_hover_effect(self):
        self.hover = False

class DiscreteSlider:
    def __init__(self, x, y, width, height, steps,
                 active_color=(255, 255, 255),
                 inactive_color=(180, 180, 180),
                 knob_color=(255, 255, 255),
                 border_radius=8,
                 selector_image=None,
                 font=None,
                 text=None,
                 textx=None):

        self.rect = pygame.Rect(x, y, width, height)

        self.steps = steps
        self.value = 0  # valeur actuelle (0 → steps)

        self.active_color = active_color
        self.inactive_color = inactive_color
        self.knob_color = knob_color
        self.border_radius = border_radius

        self.selector_image = selector_image
        if selector_image:
            self.image_rect = self.selector_image.get_rect()
            self.image_rect.height = 2 * height
            self.image_rect.width = 2 * height
        else:
            self.image_rect = None

        self.font = font
        self.nb_text_surf = font.render(str(self.value), True, active_color) if self.font else None
        self.nb_text_rect = self.nb_text_surf.get_rect(
            center=(self.rect.x + self.rect.width + 50, self.rect.centery)) if self.nb_text_surf else None
        self.text = text
        self.textx = textx
        self.text_surf = font.render(text, True, active_color) if self.text else None
        self.text_rect = self.text_surf.get_rect(centery=self.rect.centery, x=textx) if self.text_surf else None

        self.hover = False
        self.hover_image_left = pygame.image.load('assets/images/Opera_senza_titolo.png')
        self.hover_image_right = pygame.transform.flip(self.hover_image_left, True, False)
        self.hover_image_width = self.hover_image_right.get_width()
        self.dragging = False

        self.rects = [self.rect]
        if self.image_rect is not None: self.rects.append(self.image_rect)
        if self.text_rect is not None: self.rects.append(self.text_rect)
        if self.nb_text_rect is not None: self.rects.append(self.nb_text_rect)




    def draw(self, surface):

        # Label
        if self.text is not None:
            surface.blit(self.text_surf, self.text_rect)

        # Background Bar
        pygame.draw.rect(surface, self.inactive_color,
                         self.rect, border_radius=self.border_radius)

        # Active width with respect to the value
        if self.value > 0:
            step_width = self.rect.width / self.steps
            active_width = step_width * self.value

            active_rect = pygame.Rect(
                self.rect.x,
                self.rect.y,
                active_width,
                self.rect.height
            )

            pygame.draw.rect(surface, self.active_color,
                             active_rect, border_radius=self.border_radius)

        # Selector button
        if self.value > 0:
            knob_x = self.rect.x + (self.rect.width / self.steps) * self.value
        else:
            knob_x = self.rect.x
        if self.selector_image is None:
            pygame.draw.circle(surface,
                               self.knob_color,
                               (int(knob_x), self.rect.centery),
                               self.rect.height)
        else:
            self.image_rect = self.selector_image.get_rect(center=(int(knob_x), self.rect.centery))
            surface.blit(self.selector_image,
                         self.image_rect)

        # Display the value
        if self.font is not None:
            surface.blit(self.nb_text_surf, self.nb_text_rect)

        if self.hover:
            surface.blit(self.hover_image_left,
                         self.hover_image_left.get_rect(
                             x=self.text_rect.x - self.hover_image_width if self.text_rect.x else self.rect.x - self.hover_image_width,
                             centery=self.rect.centery))
            surface.blit(self.hover_image_right, self.hover_image_right.get_rect(
                x=self.nb_text_rect.x + self.nb_text_rect.width if self.nb_text_rect.x else self.rect.x + self.rect.width,
                centery=self.rect.centery
            ))


    def handle_event(self, event):
        self._update_value(event)
        if self.hover:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    if self.value > 0:
                        self.value -= 1
                if event.key == pygame.K_RIGHT:
                    if self.value < self.steps:
                        self.value += 1
        return None

    def _update_value(self, mouse_x):
        #
        # # Clamp mouse
        # mouse_x = max(self.rect.x, min(mouse_x, self.rect.right))
        #
        # # Relative Position
        # relative_x = mouse_x - self.rect.x
        # ratio = relative_x / self.rect.width
        #
        # # Convertion in discrete step
        # self.value = round(ratio * self.steps)
        if self.font is not None:
            self.nb_text_surf = self.font.render(str(self.value), True, self.active_color)

    # -------------------------
    def get_value(self):
        return self.value

    def get_normalized(self)->float:
        return self.value / self.steps

    def start_hover_effect(self):
        self.hover = True

    def end_hover_effect(self):
        self.hover = False

    def set_normalized_value(self, value):
        self.value = int(value*self.steps)

class ToggleSwitch:
    def __init__(self, x, y, width=60, height=30,
                 bg_on=(255, 255, 255),
                 bg_off=(180, 180, 180),
                 circle_color=(100, 100, 100),
                 font=None,
                 text=None,
                 textx=None):

        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height

        self.bg_on = bg_on
        self.bg_off = bg_off
        self.circle_color = circle_color

        self.state = False  # OFF par défaut

        self.circle_radius = height // 2 - 3
        self.padding = 3

        self.text = text
        self.textx = textx
        self.font = font
        self.text_surf = font.render(self.text, True, bg_on) if font is not None else None
        self.text_rect = self.text_surf.get_rect(x=textx ,centery=self.rect.centery) if self.text_surf is not None else None

        self.hover = False
        self.hover_image_left = pygame.image.load('assets/images/Opera_senza_titolo.png')
        self.hover_image_right = pygame.transform.flip(self.hover_image_left, True, False)
        self.hover_image_width = self.hover_image_right.get_width()

        self.selected = False
        self.rects = [self.rect]
        if self.text_rect is not None:self.rects.append(self.text_rect)
    def draw(self, surface):
        #Label
        if self.font is not None:
            surface.blit(self.text_surf, self.text_rect)
        # Fond
        bg_color = self.bg_on if self.state else self.bg_off
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=self.height // 2)

        # Position du cercle
        if self.state:
            circle_x = self.rect.right - self.circle_radius - self.padding
        else:
            circle_x = self.rect.left + self.circle_radius + self.padding

        circle_y = self.rect.centery

        pygame.draw.circle(surface, self.circle_color, (circle_x, circle_y), self.circle_radius)

        if self.hover:
            surface.blit(self.hover_image_left,self.hover_image_right.get_rect(
                x=self.text_rect.x - self.hover_image_width if self.text_rect else self.rect.x - self.hover_image_width,
                centery=self.rect.centery
            ))
            surface.blit(self.hover_image_right,self.hover_image_left.get_rect(
                x=self.rect.x + self.rect.width,
                centery=self.rect.centery
            ))

    def handle_event(self, event):
        if self.hover:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.state = not self.state
                    return True

    def get_state(self):
        return self.state

    def set_state(self, value: bool):
        self.state = value

    def start_hover_effect(self):
        self.hover = True
    def end_hover_effect(self):
        self.hover = False

class ArrowSelector:
    def __init__(self, x, y, width, height, font, options,
                 bg_color=(180, 180, 180),
                 arrow_color=(255, 255, 255),
                 text_color1=(0, 0, 0),
                 text=None,
                 textx=None,
                 text_color2=None):


        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.options = options
        self.index = 0

        self.bg_color = bg_color
        self.arrow_color = arrow_color
        self.text_color = text_color1

        # Zones flèches
        self.arrow_width = height
        self.left_rect = pygame.Rect(x-40, y, self.arrow_width, height)
        self.right_rect = pygame.Rect(x + width + 40 - self.arrow_width, y,
                                      self.arrow_width, height)

        # Zone texte centrale
        self.center_rect = pygame.Rect(
            x + self.arrow_width,
            y,
            width - 2 * self.arrow_width,
            height
        )

        #Label
        self.text = text
        self.textx = textx
        self.text_color2 = text_color2
        self.text_surf = font.render(self.text, True, self.text_color2) if self.text else None
        self.text_rect = self.text_surf.get_rect(x=textx,centery=self.rect.centery) if self.text_surf else None

        # Hover effect
        self.hover = True
        self.hover_image_left = pygame.image.load('assets/images/Opera_senza_titolo.png')
        self.hover_image_right = pygame.transform.flip(self.hover_image_left, True, False)
        self.hover_image_width = self.hover_image_right.get_width()

    # -------------------------
    # Dessin
    # -------------------------
    def draw(self, surface):

        # Fond central
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=6)

        # Texte actuel
        current_text = self.options[self.index]
        text_surface = self.font.render(current_text, True, self.text_color)
        surface.blit(text_surface, text_surface.get_rect(center=self.center_rect.center))

        # Flèche gauche
        pygame.draw.polygon(surface, self.arrow_color, [
            (self.left_rect.centerx + 5, self.left_rect.centery - 8),
            (self.left_rect.centerx - 5, self.left_rect.centery),
            (self.left_rect.centerx + 5, self.left_rect.centery + 8)
        ])

        # Flèche droite
        pygame.draw.polygon(surface, self.arrow_color, [
            (self.right_rect.centerx - 5, self.right_rect.centery - 8),
            (self.right_rect.centerx + 5, self.right_rect.centery),
            (self.right_rect.centerx - 5, self.right_rect.centery + 8)
        ])

        if self.text:
            surface.blit(self.text_surf,self.text_rect)
        if self.hover:
            surface.blit(self.hover_image_left,self.hover_image_left.get_rect(
                x =self.text_rect.x - self.hover_image_width,
                centery = self.rect.centery
            ))

            surface.blit(self.hover_image_right,self.hover_image_right.get_rect(
                x = self.right_rect.right,
                centery = self.rect.centery
            ))




    # -------------------------
    # Gestion événements
    # -------------------------
    def handle_event(self, event):
        if self.hover:
            if event.type == pygame.KEYDOWN:

                # Flèche gauche
                if event.key == pygame.K_LEFT:
                    self.index = (self.index - 1) % len(self.options)
                    return self.get_selected()

                # Flèche droite
                if event.key == pygame.K_RIGHT:
                    self.index = (self.index + 1) % len(self.options)
                    return self.get_selected()

        return None

    # -------------------------
    def get_selected(self):
        return self.options[self.index]

    def set_selected(self, value):
        if value in self.options:
            self.index = self.options.index(value)

    def start_hover_effect(self):
        self.hover = True
    def end_hover_effect(self):
        self.hover = False