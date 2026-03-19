import pygame
import datetime

from scripts.utils import load_image, random_color
class SimpleButton:
    def __init__(self, label:str, font:pygame.font.Font, pos_center:tuple[int,int], text_color:tuple[int,int,int], button_color:tuple[int,int,int]):
        self.default_pos = pos_center
        self.label = label
        self.text_surf = font.render(label, True, text_color)
        self.rect = pygame.Rect(0, 0, self.text_surf.get_width()+20, self.text_surf.get_height()+12)
        self.rect.center = self.default_pos
        self.activated = False
        self.font = font
        self.text_color = text_color
        self.button_color = button_color
        self.activated = False

    def draw(self, screen):
        overlay = pygame.Surface(self.rect.size)
        overlay.fill(self.button_color)
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom),2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom),(self.rect.left, self.rect.bottom), 2)
            screen.blit(overlay, (self.rect.x + 1, self.rect.y + 1))
        else:
            pygame.draw.line(screen,(96,96,96),(self.rect.x,self.rect.y),(self.rect.x,self.rect.bottom),2)
            pygame.draw.line(screen,(96,96,96),(self.rect.x,self.rect.y),(self.rect.right,self.rect.top),2)
            pygame.draw.line(screen,(40,40,40),(self.rect.right,self.rect.y),(self.rect.right,self.rect.bottom),2)
            pygame.draw.line(screen,(40,40,40),(self.rect.right,self.rect.bottom),(self.rect.left,self.rect.bottom),2)
            screen.blit(overlay, self.rect)

        self.text_surf = self.font.render(self.label, True, self.text_color)
        # Draw the text
        screen.blit(self.text_surf, (self.rect.x + (self.rect.width - self.text_surf.get_width())/2, self.rect.y + (self.rect.height - self.text_surf.get_height())/2))

    def is_selected(self, event, offset=None):
        if event.type == pygame.MOUSEMOTION:
            if offset is None:
                if self.rect.collidepoint(event.pos):
                    return True
            else:
                if self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def is_clicked(self, event, offset=None):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if offset is None:
                if event.button == 1 and self.rect.collidepoint(event.pos):
                    return True
            else:
                if event.button == 1 and self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def handle_event(self,event, offset=None):
        if event:
            return self.is_clicked(event,offset)

class EditorButton:

    def __init__(self, label:str, img:pygame.Surface, pos_center:tuple[int,int]|tuple[float,float],width:int|float,height:int|float, bg_color:tuple[int,int,int], img_ratio:int|float=None,resize=None):
        self.rect = pygame.Rect(0,0,width,height)
        self.default_pos = pos_center
        self.rect.center = self.default_pos
        self.img = img
        if resize:
            self.img = pygame.transform.scale(self.img, (width * resize, height * resize))
        if img_ratio:
            self.img = pygame.transform.scale_by(self.img,img_ratio)
        self.img_rect = self.img.get_rect(center=self.rect.center)
        self.bg_color = bg_color
        self.hover = False
        self.label = label
        self.activated = False

    def draw(self, screen):
        # Draw 3D effect
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom),2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom),(self.rect.left, self.rect.bottom), 2)
            self.img_rect.center = (self.default_pos[0]+1, self.default_pos[1]+1)


        else:
            pygame.draw.line(screen,(96,96,96),(self.rect.x,self.rect.y),(self.rect.x,self.rect.bottom),2)
            pygame.draw.line(screen,(96,96,96),(self.rect.x,self.rect.y),(self.rect.right,self.rect.top),2)
            pygame.draw.line(screen,(40,40,40),(self.rect.right,self.rect.y),(self.rect.right,self.rect.bottom),2)
            pygame.draw.line(screen,(40,40,40),(self.rect.right,self.rect.bottom),(self.rect.left,self.rect.bottom),2)
            self.img_rect.center = self.default_pos

        screen.blit(self.img, self.img_rect)

    def is_selected(self, event, offset=None):
        if event.type == pygame.MOUSEMOTION:
            if offset is None:
                if self.rect.collidepoint(event.pos):
                    return True
            else:
                if self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def is_clicked(self, event, offset=None):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if offset is None:
                if event.button == 1 and self.rect.collidepoint(event.pos):
                    return True
            else:
                if event.button == 1 and self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def handle_event(self,event, offset=None):
        self.hover = self.is_selected(event,offset)
        return self.is_clicked(event,offset)


class Picklist:
    def __init__(self, labels: list[str], font: pygame.font.Font, pos_center: tuple[int, int],
                 text_color: tuple[int, int, int], button_color: tuple[int, int, int]):
        self.default_pos = pos_center
        self.labels = labels
        self.selected_label = self.labels[0]
        self.font = font
        self.text_color = text_color
        self.button_color = button_color
        self.activated = False

        # Calculate width based on the longest label so nothing gets cut off
        max_width = max([font.size(label)[0] for label in labels])
        height = font.get_height() + 12

        self.rect = pygame.Rect(0, 0, max_width + 20, height)
        self.rect.center = self.default_pos

    def get_option_rects(self):
        """Helper method to calculate the position of the dropdown choices."""
        option_rects = []
        # Exclude the currently selected label
        available_labels = [label for label in self.labels if label != self.selected_label]

        for i, label in enumerate(available_labels):
            # Place each option directly below the previous one
            opt_rect = pygame.Rect(self.rect.x, self.rect.y + (i + 1) * self.rect.height, self.rect.width,
                                   self.rect.height)
            option_rects.append((opt_rect, label))

        return option_rects

    def handle_event(self, event):
        """Handles mouse clicks and returns the selected label if changed."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left click
            if not self.activated:
                # If closed, check if the main button was clicked to open it
                if self.rect.collidepoint(event.pos):
                    self.activated = True
            else:

                # If open, check if an option was clicked
                for opt_rect, label in self.get_option_rects():
                    if opt_rect.collidepoint(event.pos):
                        self.selected_label = label
                        self.activated = False
                        return self.selected_label

                # If they clicked anywhere else (or on the main button again), close the menu
                self.activated = False

        return "All"

    def draw(self, screen):
        # 1. Always draw the main button
        pygame.draw.rect(screen, self.button_color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)  # Black outline

        text_surf = self.font.render(self.selected_label, True, self.text_color)
        screen.blit(text_surf, (self.rect.x + (self.rect.width - text_surf.get_width()) / 2,
                                self.rect.y + (self.rect.height - text_surf.get_height()) / 2))

        # 2. Draw the dropdown options if activated
        if self.activated:
            for opt_rect, label in self.get_option_rects():
                # Draw background and outline for each option
                pygame.draw.rect(screen, self.button_color, opt_rect)
                pygame.draw.rect(screen, (0, 0, 0), opt_rect, 1)  # Thin outline to separate choices

                # Draw text for each option
                opt_text = self.font.render(label, True, self.text_color)
                screen.blit(opt_text, (opt_rect.x + (opt_rect.width - opt_text.get_width()) / 2,
                                       opt_rect.y + (opt_rect.height - opt_text.get_height()) / 2))

class EnvironmentButton(EditorButton):

    def __init__(self, label: str, img: pygame.Surface, pos_center: tuple[int, int], width: int, height: int,
                 bg_color: tuple[int, int, int]):
        super().__init__(label, img, pos_center, width, height, bg_color, img_ratio=0)
        self.img = img
        self.img = pygame.transform.scale(self.img, (width*0.5, height*0.5))
        self.img_rect = self.img.get_rect(center=self.rect.center)

    def draw(self, screen):
        # Draw 3D effect
        img_cx, img_cy = self.rect.left + self.img.get_width()/2, self.rect.bottom - self.img.get_height()/2
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom),2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom),(self.rect.left, self.rect.bottom), 2)
            self.img_rect.center = (round(img_cx+1), round(img_cy+1))

        else:
            pygame.draw.line(screen,(96,96,96),(self.rect.x,self.rect.y),(self.rect.x,self.rect.bottom),2)
            pygame.draw.line(screen,(96,96,96),(self.rect.x,self.rect.y),(self.rect.right,self.rect.top),2)
            pygame.draw.line(screen,(40,40,40),(self.rect.right,self.rect.y),(self.rect.right,self.rect.bottom),2)
            pygame.draw.line(screen,(40,40,40),(self.rect.right,self.rect.bottom),(self.rect.left,self.rect.bottom),2)
            self.img_rect.center = (round(img_cx), round(img_cy))

        screen.blit(self.img, self.img_rect)

class LevelCarousel:

    def __init__(self, x, y, size, levels):

        self.center_rect = None
        self.left_rect = None
        self.right_rect = None
        self.x = x
        self.y = y

        self.levels = levels
        self.selected = 0

        self.big_size = size
        self.small_size = (size[0]*2/3, size[1]*2/3)

        self.spacing = 260 * size[0]/300

        self.delete_button = pygame.Rect(x - 70 * size[0]/300, y + 150 * size[1]/180, 140 * size[0]/300, 50 * size[1]/180)
        self.delete_button_selected = False

        self.offset = 0
        self.target_offset = 0
        self.anim_speed = 0.2
        self.animating = False

        self.delete_window_on = False
        self.yes_button = None
        self.no_button = None


    # -------------------------
    def draw_level(self, screen, img, rect, selected=False):

        pygame.draw.rect(screen, (40,40,40), rect)

        if img is not None:
            try:
                img = pygame.transform.scale(img, rect.size)
                screen.blit(img, rect)
            except TypeError:
                i = img
                img = pygame.Surface(rect.size)
                img.fill(((150*(i+1))%255, (30*i)%255, (30*i)%255))
                screen.blit(img, rect)

        else:
            # Empty slot
            font = pygame.font.SysFont(None, 80)
            txt = font.render("+", True, (200,200,200))
            screen.blit(txt, txt.get_rect(center=rect.center))

        if selected:
            pygame.draw.rect(screen, (255,255,255), rect, 3)

    # -------------------------
    def draw(self, screen):

        center_rect = pygame.Rect(0,0,*self.big_size)
        center_x = self.x - self.offset * self.spacing
        center_rect.center = (center_x, self.y)

        # LEFT
        if self.selected > 0:

            left_rect = pygame.Rect(0,0,*self.small_size)
            left_rect.center = (center_x - self.spacing, self.y)

            self.draw_level(screen,
                            self.levels[self.selected-1],
                            left_rect)

            self.left_rect = left_rect

        else:
            self.left_rect = None

        # CENTER
        self.draw_level(screen,
                        self.levels[self.selected],
                        center_rect,
                        True)

        self.center_rect = center_rect

        # RIGHT
        if self.selected < len(self.levels)-1:

            right_rect = pygame.Rect(0,0,*self.small_size)
            right_rect.center = (center_x + self.spacing, self.y)

            self.draw_level(screen,
                            self.levels[self.selected+1],
                            right_rect)

            self.right_rect = right_rect

        else:
            self.right_rect = None

        # DELETE BUTTON
        if self.levels[self.selected] is not None:
            pygame.draw.rect(screen, (220,40,40), self.delete_button, border_radius=10)

            font = pygame.font.SysFont(None, round(30*self.big_size[0]/300))
            txt = font.render("DELETE",True,(255,255,255))
            screen.blit(txt, txt.get_rect(center=self.delete_button.center))
            if self.delete_button_selected:
                pygame.draw.rect(screen, (255, 255, 255), self.delete_button, 3,border_radius=10)
        if self.delete_window_on:
            self.yes_button,self.no_button = self.draw_delete_popup(screen,self.selected,"DELETE THE LEVEL ")
    #--------------------------
    def draw_delete_popup(self,screen,confirm_delete_id,text):
        """Draws the delete confirmation popup. Returns (yes_btn_rect, no_btn_rect)."""
        text_font = pygame.font.SysFont(None, 30)
        SW,SH = screen.get_size()

        center_x = SW // 2

        popup_rect = pygame.Rect(center_x - int(SW / 5), SH // 2 - SH // 6, SW * 0.4, SH // 3)
        pygame.draw.rect(screen, (20, 20, 20), popup_rect)
        pygame.draw.rect(screen, (255,255,255), popup_rect, 2)

        msg = text_font.render(f"{text} {confirm_delete_id}?", True, (255,255,255))
        screen.blit(msg, (center_x - msg.get_width() // 2, popup_rect.top + 40))

        yes_btn = pygame.Rect(center_x - SW * 0.12, popup_rect.bottom - SH / 10, SW / 10, SH / 15)
        no_btn = pygame.Rect(center_x + SW * 0.02, popup_rect.bottom - SH / 10, SW / 10, SH / 15)

        yes_color = (150, 0, 0) #if self.delete_command_nb == 1 else (100, 0, 0)
        no_color = (100, 100, 100) #if self.delete_command_nb == 0 else (50, 50, 50)

        pygame.draw.rect(screen, yes_color, yes_btn)
        pygame.draw.rect(screen, no_color, no_btn)

        yes_txt = text_font.render("YES", True, (255, 255, 255))
        no_txt = text_font.render("NO", True, (255, 255, 255))
        screen.blit(yes_txt, (yes_btn.centerx - yes_txt.get_width() // 2, yes_btn.centery - SH / 40))
        screen.blit(no_txt, (no_btn.centerx - no_txt.get_width() // 2, no_btn.centery - SH / 40))

        return yes_btn, no_btn

    # -------------------------
    def handle_event(self,event):


        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.delete_window_on:
                if self.left_rect and self.left_rect.collidepoint(event.pos):

                    if not self.animating:
                        self.target_offset = -1
                        self.animating = True

                elif self.right_rect and self.right_rect.collidepoint(event.pos):

                    if not self.animating:
                        self.target_offset = 1
                        self.animating = True

                elif self.center_rect and self.center_rect.collidepoint(event.pos):

                    # ADD LEVEL if empty
                    if self.levels[self.selected] is None:
                        return "AddLevel"
                    else:
                        return "LoadLevel"


                elif self.delete_button.collidepoint(event.pos):
                    self.delete_window_on = True

            elif self.delete_window_on:
                if self.no_button and self.no_button.collidepoint(event.pos):
                    self.delete_window_on = False
                if self.yes_button and self.yes_button.collidepoint(event.pos):
                    if len(self.levels) > 1 and self.levels[self.selected] is not None:
                        self.delete_window_on = False
                        return "DeleteLevel"

        if event.type == pygame.KEYDOWN:
            if not self.delete_window_on:
                if event.key == pygame.K_DOWN:
                    self.delete_button_selected = True
                if event.key == pygame.K_UP:
                    self.delete_button_selected = False

                if not self.delete_button_selected:
                    if event.key == pygame.K_RIGHT and self.selected < len(self.levels)-1:
                        if not self.animating:
                            self.target_offset = 1
                            self.animating = True

                    if event.key == pygame.K_LEFT and self.selected > 0:
                        if not self.animating:
                            self.target_offset = -1
                            self.animating = True

                if event.key == pygame.K_RETURN:
                    if self.delete_button_selected:
                       self.delete_window_on = True


                    else:
                        if self.levels[self.selected] is None:
                            return "AddLevel"
                        else:
                            return "LoadLevel"

        return None

    # -------------------------
    def update(self):

        if self.animating:

            self.offset += (self.target_offset - self.offset) * self.anim_speed

            if abs(self.target_offset - self.offset) < 0.01:
                self.selected += int(self.target_offset)

                self.offset = 0
                self.target_offset = 0
                self.animating = False

class MenuButton:
    def __init__(self,menu, text:str, font:pygame.font.Font, pos_center:tuple[int,int], text_color:tuple[int,int,int]):
        self.menu=menu
        self.text_surf = font.render(text, True, text_color)
        self.text = text
        self.font = font
        self.rect = self.text_surf.get_rect(center=pos_center)
        self.text_color = text_color
        self.hover = False

        self.hover_image = load_image("ui/Opera_senza_titolo.png",size=(font.get_height()*4,font.get_height()*4))
        self.hover2_image = pygame.transform.flip(self.hover_image, True, False)

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
            if event.key == self.menu.game.key_map["key_select"]:
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
    def __init__(self,menu, x, y, width, height, steps,
                 active_color=(255, 255, 255),
                 inactive_color=(180, 180, 180),
                 knob_color=(255, 255, 255),
                 border_radius=8,
                 selector_image=None,
                 font=None,
                 text=None,
                 textx=None):
        self.menu = menu

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
            center=(self.rect.x + self.rect.width*1.16, self.rect.centery)) if self.nb_text_surf else None
        self.text = text
        self.textx = textx
        self.text_surf = font.render(text, True, active_color) if self.text else None
        self.text_rect = self.text_surf.get_rect(centery=self.rect.centery, x=textx) if self.text_surf else None

        self.hover = False
        self.hover_image_left = load_image('/ui/Opera_senza_titolo.png',size = (width*0.16,width*0.16))
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
        self._update_value()
        if self.hover:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    if self.value > 0:
                        self.value -= 1
                if event.key == pygame.K_RIGHT:
                    if self.value < self.steps:
                        self.value += 1
        return None

    def _update_value(self):
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
    def __init__(self,menu, x, y, width=60, height=30,
                 bg_on=(255, 255, 255),
                 bg_off=(180, 180, 180),
                 circle_color=(100, 100, 100),
                 font=None,
                 text=None,
                 textx=None):
        self.menu = menu

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
        self.hover_image_left = load_image('/ui/Opera_senza_titolo.png',size = (width*0.8,width*0.8))
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
                if event.key == self.menu.game.key_map["key_select"]:
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
    def __init__(self,menu, x, y, width, height, font, options,
                 bg_color=(180, 180, 180),
                 arrow_color=(255, 255, 255),
                 text_color1=(0, 0, 0),
                 text=None,
                 textx=None,
                 text_color2=None):
        self.menu = menu


        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.options = options
        self.index = 0

        self.bg_color = bg_color
        self.arrow_color = arrow_color
        self.text_color = text_color1

        # Zones flèches
        self.arrow_width = height
        self.left_rect = pygame.Rect(x-height, y, self.arrow_width, height)
        self.right_rect = pygame.Rect(x + width + height - self.arrow_width, y,
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
        self.hover_image_left = load_image('ui/Opera_senza_titolo.png',size = (width*0.24,width*0.24))
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
            (self.left_rect.centerx + int(self.arrow_width/8), self.left_rect.centery - int(self.arrow_width/5)),
            (self.left_rect.centerx - int(self.arrow_width/8), self.left_rect.centery),
            (self.left_rect.centerx + int(self.arrow_width/8), self.left_rect.centery + int(self.arrow_width/5))
        ])

        # Flèche droite
        pygame.draw.polygon(surface, self.arrow_color, [
            (self.right_rect.centerx - int(self.arrow_width/8), self.right_rect.centery - int(self.arrow_width/5)),
            (self.right_rect.centerx + int(self.arrow_width/8), self.right_rect.centery),
            (self.right_rect.centerx - int(self.arrow_width/8), self.right_rect.centery + int(self.arrow_width/5))
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

class SaveSlotUI:
    def __init__(self,menu, slot_id, x,y,width,height, fonts, colors):
        self.menu = menu

        self.slot_id = slot_id
        self.rect = pygame.Rect(x,y,4 * width / 5,height)
        self.width = self.rect.width
        self.height = self.rect.height

        self.number_font = fonts["number"]
        self.text_font = fonts["text"]
        self.detail_font = fonts["detail"]

        self.colors = colors

        self.souls_icon = load_image("ui/soul.png")
        self.death_icon = load_image("ui/skull.png")

        self.save_data = None
        self.thumbnail = None

        self.delete_rect = pygame.Rect(
            self.rect.right + width/35,
            self.rect.top,
            width/5,
            height/2
        )
        self.delete_rect.centery = self.rect.centery


        self.hover = False
        self.is_selected = False
        self.delete_hover = False

    def update_data(self, save_data=None, thumbnail=None):
        self.save_data = save_data
        self.thumbnail = thumbnail

    def draw(self, surface):

        line_color = self.colors["white"] if self.hover else (100, 100, 100)
        text_color = self.colors["white"] if self.hover else (200, 200, 200)

        pygame.draw.line(surface, line_color,
                     (self.rect.left, self.rect.top),
                     (self.rect.right, self.rect.top), 2)

        num_txt = self.number_font.render(f"{self.slot_id}.", True, text_color)
        surface.blit(num_txt, (
            self.rect.left + self.width / 28,
            self.rect.centery - num_txt.get_height() // 2
        ))



        if self.save_data:
            img_rect = pygame.Rect(self.rect.left + self.width / 7,
                               self.rect.top + self.width*0.026,
                               self.width / 7, self.width / 7)
            if self.thumbnail:
                img = pygame.transform.scale(self.thumbnail, img_rect.size)
                surface.blit(img, img_rect.topleft)

            right_margin = 30
            x_right = self.rect.right - right_margin

            level_name = self.save_data.get("level_name", "Unknown").upper()
            play_seconds = self.save_data.get("playtime", 0)
            time_str = str(datetime.timedelta(seconds=int(play_seconds)))
            date_str = self.save_data.get("date", "----")


            y_start = self.rect.top + 10
            spacing = 5

            lvl_txt = self.text_font.render(level_name, True, (220, 220, 220))
            lvl_rect  = lvl_txt.get_rect(x=x_right - lvl_txt.get_width(),y=y_start)
            time_txt = self.detail_font.render(time_str, True, (170, 170, 170))
            time_rect = time_txt.get_rect(x=x_right - time_txt.get_width(),y=lvl_rect.bottom + spacing)
            date_txt = self.detail_font.render(date_str, True, (150, 150, 150))
            date_rect = date_txt.get_rect(x=x_right - date_txt.get_width(),y=time_rect.bottom + spacing)



            surface.blit(lvl_txt,lvl_rect)

            surface.blit(time_txt,time_rect)

            surface.blit(date_txt,date_rect)
            del_color = (200, 0, 0) if self.delete_hover else (120, 0, 0)

            pygame.draw.rect(surface, del_color, self.delete_rect, border_radius=6)

            del_txt = self.detail_font.render("DELETE", True, (255, 255, 255))

            surface.blit(del_txt,
                         (self.delete_rect.centerx - del_txt.get_width() // 2,
                          self.delete_rect.centery - del_txt.get_height() // 2))

            deaths = self.save_data.get("death", 0)
            souls = self.save_data.get("souls", 0)

            stats_y = img_rect.bottom + 10
            icon_size = 32

            # Logo morts (carré rouge)
            death_icon = pygame.Rect(img_rect.right + 20,
                                 img_rect.top+5,
                                 icon_size,
                                 icon_size)
            surface.blit(pygame.transform.scale(self.death_icon, (icon_size, icon_size)), death_icon)

            # Texte
            death_txt = self.detail_font.render(f"{deaths}",True,(200, 200, 200))
            death_rect = death_txt.get_rect(x=death_icon.right + 5 ,centery = death_icon.centery)
            surface.blit(death_txt,death_rect)


            # Logo souls (carré bleu)
            soul_icon_rect = pygame.Rect(
                img_rect.right + 20,
                img_rect.bottom-icon_size-5,
                icon_size,
                icon_size
            )
            surface.blit(pygame.transform.scale(self.souls_icon,(icon_size,icon_size)), soul_icon_rect)

            # Texte
            souls_text = self.detail_font.render(f"{souls}",True,(200, 200, 200))
            souls_rect = souls_text.get_rect(x=soul_icon_rect.right + 5,centery = soul_icon_rect.centery)
            surface.blit(souls_text,souls_rect)

        else:
            ng_txt = self.text_font.render(
                "NEW GAME",
                True,
                (255, 255, 255) if self.hover else (120, 120, 120)
            )
            ng_rect = ng_txt.get_rect(centerx=self.rect.centerx,centery=self.rect.centery)
            surface.blit(ng_txt,ng_rect)

    def handle_event(self, event):
        if self.hover:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    self.delete_hover = True
                elif event.key == pygame.K_LEFT:
                    self.delete_hover = False
                if event.key == self.menu.game.key_map["key_select"]:
                    if self.save_data and self.delete_hover:
                        return "DELETE"

                    if self.save_data:
                        return "LOAD"
                    else:
                        return "START"
            return None
        else:
            self.delete_hover = False
            return None

    def update_delete_hover(self):
        if not self.hover:
            self.delete_hover = False

    def start_hover_effect(self):
        self.hover = True

    def end_hover_effect(self):
        self.hover = False

