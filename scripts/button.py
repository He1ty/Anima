import pygame
import datetime
# --- Configuration ---
COLOR_BG = (30, 30, 30)
COLOR_PARENT = (50, 80, 200)
COLOR_CHILD = (200, 70, 70)
COLOR_TEXT_BG = (200, 200, 200)
COLOR_ACTIVE = (255, 255, 255)

from scripts.utils import load_image, random_color


class SimpleButton:
    """
    A basic labeled button with a retro 3D beveled border effect.
    Supports click detection and an activated (pressed) visual state.
    """

    def __init__(self, label: str, font: pygame.font.Font, pos_center: tuple[int, int],
                 text_color: tuple[int, int, int], button_color: tuple[int, int, int]):
        """
        Initialize the button with a label, font, center position, and colors.

        :param label: Text displayed on the button.
        :param font: Pygame font used to render the label.
        :param pos_center: (x, y) center position of the button on screen.
        :param text_color: RGB color of the label text.
        :param button_color: RGB background fill color of the button.
        """
        self.default_pos = pos_center
        self.label = label
        self.text_surf = font.render(label, True, text_color)
        self.rect = pygame.Rect(0, 0, self.text_surf.get_width() + 20, self.text_surf.get_height() + 12)
        self.rect.center = self.default_pos
        self.activated = False
        self.font = font
        self.text_color = text_color
        self.button_color = button_color
        self.activated = False

    def draw(self, screen: pygame.Surface):
        """
        Draw the button on the given surface.
        Renders a pressed appearance when activated, raised otherwise.

        :param screen: Target surface to draw on.
        """
        overlay = pygame.Surface(self.rect.size)
        overlay.fill(self.button_color)
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            screen.blit(overlay, (self.rect.x + 1, self.rect.y + 1))
        else:
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            screen.blit(overlay, self.rect)

        self.text_surf = self.font.render(self.label, True, self.text_color)
        screen.blit(self.text_surf, (self.rect.x + (self.rect.width - self.text_surf.get_width()) / 2,
                                     self.rect.y + (self.rect.height - self.text_surf.get_height()) / 2))

    def is_selected(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Return True if the mouse is hovering over the button.

        :param event: The Pygame event to check.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if the mouse position is inside the button rect.
        """
        if event.type == pygame.MOUSEMOTION:
            if offset is None:
                if self.rect.collidepoint(event.pos):
                    return True
            else:
                if self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def is_clicked(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Return True if the button was left-clicked.

        :param event: The Pygame event to check.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if a left mouse button down event occurred inside the rect.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if offset is None:
                if event.button == 1 and self.rect.collidepoint(event.pos):
                    return True
            else:
                if event.button == 1 and self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def handle_event(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Process an event and return True if the button was clicked.

        :param event: The Pygame event to process.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if clicked, False otherwise.
        """
        if event:
            return self.is_clicked(event, offset)


class EditorButton:
    """
    An icon-based button with a 3D beveled border effect used in the editor UI.
    Supports hover detection, click detection, and an activated (pressed) state.
    """

    def __init__(self, label: str, img: pygame.Surface, pos_center: tuple[int, int] | tuple[float, float],
                 width: int | float, height: int | float, bg_color: tuple[int, int, int],
                 img_ratio: int | float = None, resize=None):
        """
        Initialize the editor button with an image and layout parameters.

        :param label: Identifier label (not displayed, used for logic).
        :param img: Image surface displayed inside the button.
        :param pos_center: (x, y) center position of the button.
        :param width: Button width in pixels.
        :param height: Button height in pixels.
        :param bg_color: Background color drawn behind the image.
        :param img_ratio: Optional uniform scale factor applied to the image.
        :param resize: Optional factor to scale image relative to button size.
        """
        self.rect = pygame.Rect(0, 0, width, height)
        self.default_pos = pos_center
        self.rect.center = self.default_pos
        self.img = img
        if resize:
            self.img = pygame.transform.scale(self.img, (width * resize, height * resize))
        if img_ratio:
            self.img = pygame.transform.scale_by(self.img, img_ratio)
        self.img_rect = self.img.get_rect(center=self.rect.center)
        self.bg_color = bg_color
        self.hover = False
        self.label = label
        self.activated = False

    def draw(self, screen: pygame.Surface):
        """
        Draw the button with a beveled 3D border and the image centered inside.
        The image shifts by 1px when activated to simulate a press effect.

        :param screen: Target surface to draw on.
        """
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            self.img_rect.center = (self.default_pos[0] + 1, self.default_pos[1] + 1)
        else:
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            self.img_rect.center = self.default_pos

        screen.blit(self.img, self.img_rect)

    def is_selected(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Return True if the mouse is hovering over the button.

        :param event: The Pygame event to check.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if hovering.
        """
        if event.type == pygame.MOUSEMOTION:
            if offset is None:
                if self.rect.collidepoint(event.pos):
                    return True
            else:
                if self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def is_clicked(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Return True if the button was left-clicked.

        :param event: The Pygame event to check.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if a left mouse button down occurred inside the rect.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if offset is None:
                if event.button == 1 and self.rect.collidepoint(event.pos):
                    return True
            else:
                if event.button == 1 and self.rect.move(offset).collidepoint(event.pos):
                    return True
        return False

    def handle_event(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Process an event: update hover state and return True if clicked.

        :param event: The Pygame event to process.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if clicked.
        """
        self.hover = self.is_selected(event, offset)
        return self.is_clicked(event, offset)


class IconButton(EditorButton):
    """
    A circular icon button with hover highlight and optional toggle behavior.
    Inherits from EditorButton but replaces the bevel style with circular drawing.
    When inactive, the button is rendered semi-transparent.
    """

    ALPHA = 80

    def __init__(self, label: str, img: pygame.Surface, pos_center: tuple[int, int] | tuple[float, float],
                 width: float, height: float, bg_color: tuple[int, int, int], resize=None, toggle=False):
        """
        Initialize the icon button.

        :param label: Identifier label (not displayed).
        :param img: Icon image drawn inside the circular button.
        :param pos_center: (x, y) center position of the button.
        :param width: Button width (also used to compute circle radius).
        :param height: Button height.
        :param bg_color: Circle background color.
        :param resize: Optional factor to scale image relative to button size.
        :param toggle: If True, clicking toggles the hover/active state instead of a one-shot click.
        """
        super().__init__(label, img, pos_center, width, height, bg_color, resize)
        self.width = width
        self.height = height
        self.radius = width // 2

        if resize:
            self.img = pygame.transform.scale(self.img, (width * resize, height * resize))
        self.img_rect = self.img.get_rect(center=self.rect.center)

        self.hover_img = pygame.transform.scale_by(self.img, 1.2)
        self.hover_img_rect = self.hover_img.get_rect(center=self.rect.center)
        self.toggle = toggle
        self.activated = False

    def draw(self, screen: pygame.Surface):
        """
        Draw the circular icon button.
        Active state: full opacity with a white ring highlight on hover.
        Inactive state: semi-transparent circle.

        :param screen: Target surface to draw on.
        """
        self.img_rect = self.img.get_rect(center=self.rect.center)
        self.hover_img_rect = self.hover_img.get_rect(center=self.rect.center)
        if self.activated:
            self.img.set_alpha(255)
            if self.hover:
                pygame.draw.circle(screen, (255, 255, 255), self.rect.center, self.radius + 4)
                pygame.draw.circle(screen, self.bg_color, self.rect.center, self.radius + 2)
                screen.blit(self.hover_img, self.hover_img_rect)
            else:
                pygame.draw.circle(screen, (255, 255, 255), self.rect.center, self.radius + 2)
                pygame.draw.circle(screen, self.bg_color, self.rect.center, self.radius)
                screen.blit(self.img, self.img_rect)
        else:
            surf = pygame.Surface((self.width + 10, self.height + 10), pygame.SRCALPHA)
            surf.set_alpha(self.ALPHA)
            pygame.draw.circle(surf, (255, 255, 255), surf.get_rect().center, self.radius + 2)
            pygame.draw.circle(surf, self.bg_color, surf.get_rect().center, self.radius)
            surf.blit(self.img, self.img.get_rect(center=surf.get_rect().center))
            screen.blit(surf, surf.get_rect(center=self.rect.center))

    def is_clicked(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Handle click detection, with different behavior for toggle vs. standard mode.
        In standard mode: returns True on MOUSEBUTTONUP inside the rect after pressing.
        In toggle mode: returns the current hover state after toggling on click.

        :param event: The Pygame event to process.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if the button was activated.
        """
        if not self.toggle:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if offset is None:
                    if self.rect.collidepoint(event.pos):
                        self.hover = True
                else:
                    if self.rect.move(offset).collidepoint(event.pos):
                        self.hover = True
            if event.type == pygame.MOUSEMOTION and self.hover:
                if offset is None:
                    self.hover = self.rect.collidepoint(event.pos)
                else:
                    self.hover = self.rect.move(offset).collidepoint(event.pos)
            if event.type == pygame.MOUSEBUTTONUP:
                if offset is None:
                    if self.hover and self.rect.collidepoint(event.pos):
                        self.hover = False
                        return True
                else:
                    if self.hover and self.rect.move(offset).collidepoint(event.pos):
                        self.hover = False
                        return True
            return False
        else:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if offset is None:
                    if event.button == 1 and self.rect.collidepoint(event.pos):
                        self.hover = not self.hover
                else:
                    if event.button == 1 and self.rect.move(offset).collidepoint(event.pos):
                        self.hover = not self.hover
            return self.hover

    def is_selected(self, event: pygame.event.Event, offset=None):
        """Not used in IconButton. Hover is managed inside is_clicked."""
        pass

    def handle_event(self, event: pygame.event.Event, offset=None) -> bool:
        """
        Process an event. Only handles clicks when the button is activated.

        :param event: The Pygame event to process.
        :param offset: Optional (dx, dy) offset applied to the button rect.
        :return: True if clicked while activated.
        """
        if self.activated:
            return self.is_clicked(event, offset)
        return False


class TextButton(EditorButton):
    """
    An editor-style button that displays text instead of an image.
    Uses the same beveled 3D border as EditorButton.
    """

    def __init__(self, label: str, pos_center: tuple[int, int] | tuple[float, float],
                 width: float, height: float, font: pygame.font.Font, resize=None,
                 text_color=(255, 255, 255)):
        """
        Initialize the text button.

        :param label: Text displayed on the button.
        :param pos_center: (x, y) center position.
        :param width: Button width in pixels.
        :param height: Button height in pixels.
        :param font: Pygame font used to render the label.
        :param resize: Unused (inherited parameter).
        :param text_color: RGB color of the label text.
        """
        super().__init__(label, pygame.Surface((0, 0)), pos_center, width, height, resize)
        self.font = font
        self.text = self.font.render(label, True, text_color)
        self.text_rect = self.text.get_rect(center=self.rect.center)

    def draw(self, screen: pygame.Surface):
        """
        Draw the text button with a beveled 3D border.
        Text shifts 1px when activated to simulate a press.

        :param screen: Target surface to draw on.
        """
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            self.text_rect.center = (self.default_pos[0] + 1, self.default_pos[1] + 1)
        else:
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            self.text_rect.center = self.default_pos

        screen.blit(self.text, self.text_rect)


class ChildButton:
    """
    A child node inside a ParentButton tree.
    Can be expanded to reveal two text input fields: a variable name and a value.
    Closing a ChildButton does not affect its siblings.
    """

    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font, parent):
        """
        Initialize the child button with position, size, font, and a reference to its parent.

        :param x: Left position on screen.
        :param y: Top position on screen.
        :param width: Width of the toggle button (input fields use multiples of this).
        :param height: Height of the button row.
        :param font: Pygame font used for labels and text input rendering.
        :param parent: The ParentButton instance this child belongs to.
        """
        self.parent = parent
        self.rect = pygame.Rect(x, y, width, height)
        self.variable_input_rect = pygame.Rect(x + width, y, width * 5, height)
        self.variable_text_input = ""
        self.value_input_rect = pygame.Rect(self.variable_input_rect.right + 20, y, width * 5, height)
        self.value_text_input = ""
        self.variable_active = False
        self.value_active = False
        self.font = font
        self.is_expanded = False

    def handle_event(self, event: pygame.event.Event, offset=None):
        """
        Process mouse and keyboard events for this child.
        Clicking the toggle button expands/collapses the input fields.
        Typing updates the active input field (variable name or value).
        Returns "TOGGLE" when the expansion state changes.

        :param event: The Pygame event to process.
        :param offset: Optional (dx, dy) offset applied to rects.
        :return: "TOGGLE" if the expansion state changed, None otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if offset:
                if self.value_input_rect.move(offset).collidepoint(event.pos):
                    self.value_active = True
                else:
                    self.value_active = False
                if self.rect.move(offset).collidepoint(event.pos):
                    self.is_expanded = not self.is_expanded
                    if self.is_expanded:
                        self.variable_active = True
                    self.value_text_input = ""
                    self.variable_text_input = ""
                    return "TOGGLE"
            else:
                if self.value_input_rect.collidepoint(event.pos):
                    self.value_active = True
                else:
                    self.value_active = False
                if self.rect.collidepoint(event.pos):
                    self.is_expanded = not self.is_expanded
                    if self.is_expanded:
                        self.variable_active = True
                    self.value_text_input = ""
                    self.variable_text_input = ""
                    return "TOGGLE"

        if (self.variable_active or self.value_active) and event.type == pygame.KEYDOWN:
            if self.variable_active and event.key == pygame.K_RETURN:
                self.variable_active = False
            if event.key == pygame.K_BACKSPACE:
                if self.variable_active:
                    self.variable_text_input = self.variable_text_input[:-1]
                else:
                    self.value_text_input = self.value_text_input[:-1]
            elif event.unicode.isprintable():
                if self.variable_active:
                    self.variable_text_input += event.unicode
                else:
                    self.value_text_input += event.unicode

    def draw(self, surface: pygame.Surface, x: int, y: int):
        """
        Draw the child row at the given position.
        Shows a +/- toggle button; if expanded, shows two text input fields.

        :param surface: Target surface to draw on.
        :param x: Left position for this row.
        :param y: Top position for this row.
        """
        self.rect.topleft = (x, y)
        self.variable_input_rect.topleft = (x + self.rect.width * 1.3, y)
        self.value_input_rect.topleft = (self.variable_input_rect.right + self.rect.width // 2, y)

        pygame.draw.rect(surface, COLOR_CHILD, self.rect)
        symbole = "-" if self.is_expanded else "+"
        lbl = self.font.render(symbole, True, (255, 255, 255))
        surface.blit(lbl, lbl.get_rect(center=self.rect.center))
        if self.is_expanded:
            color = (255, 255, 255) if self.variable_active else COLOR_TEXT_BG
            color2 = (255, 255, 255) if self.value_active else COLOR_TEXT_BG
            pygame.draw.rect(surface, color, self.variable_input_rect)
            txt_surf = self.font.render(self.variable_text_input, True, (0, 0, 0))
            surface.blit(txt_surf, (self.variable_input_rect.x + 5, self.variable_input_rect.y + 5))
            pygame.draw.rect(surface, color2, self.value_input_rect)
            txt_surf = self.font.render(self.value_text_input, True, (0, 0, 0))
            surface.blit(txt_surf, (self.value_input_rect.x + 5, self.value_input_rect.y + 5))

    def reload(self, new_width: int, new_height: int, font: pygame.font.Font):
        """
        Resize the child button and update its input field rects and font.
        Called when the parent is resized (e.g. on window resize).

        :param new_width: New button width in pixels.
        :param new_height: New button height in pixels.
        :param font: Updated Pygame font to use.
        """
        self.font = font
        self.rect.width = new_width
        self.rect.height = new_height
        self.variable_input_rect = pygame.Rect(self.rect.x + new_width, self.rect.y, new_width * 5, new_height)
        self.value_input_rect = pygame.Rect(self.variable_input_rect.right + 20, self.rect.y, new_width * 5, new_height)


class ParentButton:
    """
    A parent node in a collapsible tree UI.
    When expanded, shows a text input field for the node name and a list of ChildButton rows.
    Closing this node only affects its own children; sibling ParentButtons are untouched.
    A new empty child is automatically added when the last existing child is expanded.
    """

    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font):
        """
        Initialize the parent button.

        :param x: Left position on screen.
        :param y: Top position on screen.
        :param width: Width of the toggle button.
        :param height: Height of the button row.
        :param font: Pygame font used for rendering labels and input text.
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.input_rect = pygame.Rect(x + width, y, width * 5, height)
        self.is_expanded = False
        self.active = False
        self.text_input = ""
        self.children = []
        self.next_Parent = None
        self.font = font

    def handle_event(self, event: pygame.event.Event, offset=None):
        """
        Process mouse and keyboard events for the parent and propagate to children.
        Clicking the toggle button expands/collapses the node and its children.
        When collapsing, all children are removed and the text input is cleared.
        A new child is automatically appended when the last child becomes expanded.

        :param event: The Pygame event to process.
        :param offset: Optional (dx, dy) offset applied to rects.
        :return: "TOGGLE" if the expansion state changed, None otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if offset:
                if self.rect.move(offset).collidepoint(event.pos):
                    self.is_expanded = not self.is_expanded
                    if self.is_expanded:
                        self.active = True
                        if len(self.children) == 0:
                            self.add_child()
                    else:
                        self.text_input = ""
                        for _ in self.children:
                            self.children = self.children[1:]
                    return "TOGGLE"
            else:
                if self.rect.collidepoint(event.pos):
                    self.is_expanded = not self.is_expanded
                    if self.is_expanded:
                        self.active = True
                        if len(self.children) == 0:
                            self.add_child()
                    else:
                        self.text_input = ""
                        for _ in self.children:
                            self.children = self.children[1:]
                    return "TOGGLE"

        if event.type == pygame.KEYDOWN:
            if self.active and event.key == pygame.K_RETURN:
                self.active = False

        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text_input = self.text_input[:-1]
            elif event.unicode.isprintable():
                self.text_input += event.unicode

        if self.is_expanded:
            for index, child in enumerate(self.children):
                result = child.handle_event(event, offset)
                if result == "TOGGLE" and not child.is_expanded:
                    if index != 0 or len(self.children) > 2:
                        self.children.remove(child)
                    elif len(self.children) <= 2:
                        self.children.remove(self.children[index + 1])
                if self.children[-1].is_expanded:
                    self.add_child()

    def add_child(self):
        """
        Append a new empty ChildButton to the children list.
        Position is calculated dynamically during draw.
        """
        self.children.append(ChildButton(0, 0, self.rect.width, self.rect.height, self.font, self))

    def get_total_height(self) -> int:
        """
        Calculate the total vertical space occupied by this parent and all its children.

        :return: Total height in pixels.
        """
        if not self.is_expanded:
            return self.rect.height
        return self.rect.height * 1.3 + (len(self.children) * self.rect.height * 1.3)

    def draw(self, surface: pygame.Surface, x: int, y: int):
        """
        Draw the parent node and, if expanded, its text input and all children.

        :param surface: Target surface to draw on.
        :param x: Left position for this row.
        :param y: Top position for this row.
        """
        self.rect.topleft = (x, y)
        self.input_rect.topleft = (x + self.rect.width * 1.5, y)

        pygame.draw.rect(surface, COLOR_PARENT, self.rect)
        symbol = "-" if self.is_expanded else "+"
        lbl = self.font.render(symbol, True, (255, 255, 255))
        surface.blit(lbl, lbl.get_rect(center=self.rect.center))

        if self.is_expanded:
            color = (255, 255, 255) if self.active else COLOR_TEXT_BG
            pygame.draw.rect(surface, color, self.input_rect)
            txt_surf = self.font.render(self.text_input, True, (0, 0, 0))
            surface.blit(txt_surf, (self.input_rect.x + 5, self.input_rect.y + 5))

        if self.is_expanded:
            for i, child in enumerate(self.children):
                child_y = y + self.rect.height * 1.3 + (i * self.rect.height * 1.3)
                child.draw(surface, self.input_rect.x, child_y)

    def reload(self, new_width: int, new_height: int, font: pygame.font.Font):
        """
        Resize the parent button and propagate the resize to all children.

        :param new_width: New button width in pixels.
        :param new_height: New button height in pixels.
        :param font: Updated Pygame font to use.
        """
        self.font = font
        self.rect.width = new_width
        self.rect.height = new_height
        self.input_rect = pygame.Rect(self.rect.x + new_width, self.rect.y, new_width * 5, new_height)
        for child in self.children:
            child.reload(new_width, new_height, font)


class NumberStepper:
    """
    A UI component to select a non-negative integer via arrow buttons or direct text input.
    Consists of a minus button, a text input area, and a plus button laid out horizontally.
    """

    COLOR_BTN = (70, 70, 70)
    COLOR_TEXT_BG = (255, 255, 255)
    COLOR_ACTIVE = (200, 230, 255)
    COLOR_ARROW = (100, 100, 100)

    def __init__(self, x: int, y: int, width: int = 120, height: int = 30, start_val: int = 0,font=None):
        """
        Initialize the number stepper.

        :param x: Left position on screen.
        :param y: Top position on screen.
        :param width: Total width of the component in pixels.
        :param height: Height of the component in pixels (also used as arrow button width).
        :param start_val: Initial integer value (must be >= 0).
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.value = start_val
        self.active = False
        self.font = pygame.font.SysFont(None, 24) if font is None else font

        self.minus_rect = pygame.Rect(x, y, height, height)
        self.plus_rect = pygame.Rect(x + width - height, y, height, height)
        self.input_rect = pygame.Rect(x + height, y, width - 2 * height, height)

        self.temp_text = str(start_val)

    def handle_event(self, event: pygame.event.Event,offset=None):
        """
        Process mouse and keyboard events.
        Minus/plus buttons decrement/increment the value.
        Clicking the input area enables text typing mode.
        Pressing Enter or clicking away validates and commits the typed value.

        :param event: The Pygame event to process.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not offset:
                if self.minus_rect.collidepoint(event.pos) and self.value > 0:
                    self.value -= 1
                    self.temp_text = str(self.value)
                    self.active = False
                elif self.plus_rect.collidepoint(event.pos):
                    self.value += 1
                    self.temp_text = str(self.value)
                    self.active = False
                elif self.input_rect.collidepoint(event.pos):
                    self.active = True
                    self.temp_text = ""
                else:
                    self.active = False
                    self._validate_input()
            else:
                if self.minus_rect.move(offset).collidepoint(event.pos) and self.value > 0:
                    self.value -= 1
                    self.temp_text = str(self.value)
                    self.active = False
                elif self.plus_rect.move(offset).collidepoint(event.pos):
                    self.value += 1
                    self.temp_text = str(self.value)
                    self.active = False
                elif self.input_rect.move(offset).collidepoint(event.pos):
                    self.active = True
                    self.temp_text = ""
                else:
                    self.active = False
                    self._validate_input()

        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.active = False
                self._validate_input()
            elif event.key == pygame.K_BACKSPACE:
                self.temp_text = self.temp_text[:-1]
            elif event.unicode.isdigit() or (event.unicode == "-" and len(self.temp_text) == 0):
                self.temp_text += event.unicode

    def _validate_input(self):
        """
        Convert the temporary string buffer to an integer and store it as the value.
        Resets the buffer to the current value string if conversion fails or result is negative.
        """
        try:
            value = int(self.temp_text)
            if value >= 0:
                self.value = value
        except ValueError:
            self.temp_text = str(self.value)

    def draw(self, surface: pygame.Surface):
        """
        Draw the number stepper: background, text input area, minus button, and plus button.

        :param surface: Target surface to draw on.
        """
        pygame.draw.rect(surface, (50, 50, 50), self.rect)

        bg_color = COLOR_ACTIVE if self.active else COLOR_TEXT_BG
        pygame.draw.rect(surface, bg_color, self.input_rect)

        display_text = self.temp_text if self.active else str(self.value)
        txt_surf = self.font.render(display_text, True, (0, 0, 0))
        txt_rect = txt_surf.get_rect(center=self.input_rect.center)
        surface.blit(txt_surf, txt_rect)

        pygame.draw.rect(surface, self.COLOR_ARROW, self.minus_rect)
        m_txt = self.font.render("-", True, (255, 255, 255))
        surface.blit(m_txt, m_txt.get_rect(center=self.minus_rect.center))

        pygame.draw.rect(surface, self.COLOR_ARROW, self.plus_rect)
        p_txt = self.font.render("+", True, (255, 255, 255))
        surface.blit(p_txt, p_txt.get_rect(center=self.plus_rect.center))

    def reload(self,x,y,width,height,font):
        self.rect = pygame.Rect(x,y , width, height)
        self.minus_rect = pygame.Rect(x, y, height, height)
        self.plus_rect = pygame.Rect(x + width - height, y, height, height)
        self.input_rect = pygame.Rect(x + height, y, width - 2 * height, height)
        self.font = font


class Dropdown:
    """
    A dropdown selector widget that shows a list of options when clicked.
    Displays the currently selected option with a small arrow indicator.
    """

    def __init__(self, x: int, y: int, font: pygame.font.Font, options: list[str],
                 main_color=(180, 180, 180, 0),
                 hover_color=(200, 200, 200),
                 text_color=(0, 0, 0)):
        """
        Initialize the dropdown with a list of string options.

        :param x: Left position on screen.
        :param y: Top position on screen.
        :param font: Pygame font used to render option text.
        :param options: List of selectable string options. First entry is the default.
        :param main_color: RGBA background color of the main button and non-hovered options.
        :param hover_color: RGB color of the hovered option background.
        :param text_color: RGB color used for all text.
        """
        self.font = font
        self.options = options
        self.selected = options[0]

        selected_rect = font.render(self.selected, True, text_color)
        self.rect = pygame.Rect(x, y, selected_rect.get_width() + 50, selected_rect.get_height())

        self.main_color = main_color
        self.hover_color = hover_color
        self.text_color = text_color

        self.expanded = False
        self.hovered_option = -1

    def draw(self, surface: pygame.Surface):
        """
        Draw the dropdown button and, if expanded, the list of options below it.

        :param surface: Target surface to draw on.
        """
        pygame.draw.rect(surface, self.main_color, self.rect, border_radius=5)
        text = self.font.render(self.selected, True, self.text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))

        pygame.draw.polygon(surface, self.text_color, [
            (self.rect.right - 20, self.rect.centery - 5),
            (self.rect.right - 10, self.rect.centery - 5),
            (self.rect.right - 15, self.rect.centery + 5)
        ])

        if self.expanded:
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y + (i + 1) * self.rect.height,
                    self.rect.width,
                    self.rect.height
                )
                color = self.hover_color if i == self.hovered_option else self.main_color
                pygame.draw.rect(surface, color, option_rect)
                text = self.font.render(option, True, self.text_color)
                surface.blit(text, text.get_rect(center=option_rect.center))

    def handle_event(self, event: pygame.event.Event) -> str:
        """
        Process mouse events to expand/collapse the list and select an option.
        Returns the selected option string when a new selection is made,
        or "All" as a default when no selection change occurs.

        :param event: The Pygame event to process.
        :return: The newly selected option string, or "All" if no change.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
            elif self.expanded:
                for i in range(len(self.options)):
                    option_rect = pygame.Rect(
                        self.rect.x,
                        self.rect.y + (i + 1) * self.rect.height,
                        self.rect.width,
                        self.rect.height
                    )
                    if option_rect.collidepoint(event.pos):
                        self.selected = self.options[i]
                        self.expanded = False
                        return self.selected
                self.expanded = False

        elif event.type == pygame.MOUSEMOTION:
            if self.expanded:
                self.hovered_option = -1
                for i in range(len(self.options)):
                    option_rect = pygame.Rect(
                        self.rect.x,
                        self.rect.y + (i + 1) * self.rect.height,
                        self.rect.width,
                        self.rect.height
                    )
                    if option_rect.collidepoint(event.pos):
                        self.hovered_option = i

        return "All"

    def get_selected(self) -> str:
        """
        Return the currently selected option.

        :return: Selected option string.
        """
        return self.selected


class EnvironmentButton(EditorButton):
    """
    An editor button variant that scales and positions its icon in the lower-left area
    of the button rect, rather than centered. Used for environment-type tools.
    """

    def __init__(self, label: str, img: pygame.Surface, pos_center: tuple[int, int],
                 width: int, height: int, bg_color: tuple[int, int, int]):
        """
        Initialize the environment button.
        The image is scaled to 50% of the button dimensions.

        :param label: Identifier label (not displayed).
        :param img: Icon image to display.
        :param pos_center: (x, y) center position of the button.
        :param width: Button width in pixels.
        :param height: Button height in pixels.
        :param bg_color: Background color (passed to EditorButton).
        """
        super().__init__(label, img, pos_center, width, height, bg_color, img_ratio=0)
        self.img = img
        self.img = pygame.transform.scale(self.img, (width * 0.5, height * 0.5))
        self.img_rect = self.img.get_rect(center=self.rect.center)

    def draw(self, screen: pygame.Surface):
        """
        Draw the button with a 3D bevel and the icon anchored to the lower-left of the rect.
        The image shifts 1px when activated to simulate a press.

        :param screen: Target surface to draw on.
        """
        img_cx = self.rect.left + self.img.get_width() / 2
        img_cy = self.rect.bottom - self.img.get_height() / 2
        if self.activated:
            pygame.draw.line(screen, (40, 40, 40), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40,), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            self.img_rect.center = (round(img_cx + 1), round(img_cy + 1))
        else:
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.x, self.rect.bottom), 2)
            pygame.draw.line(screen, (96, 96, 96), (self.rect.x, self.rect.y), (self.rect.right, self.rect.top), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.y), (self.rect.right, self.rect.bottom), 2)
            pygame.draw.line(screen, (40, 40, 40), (self.rect.right, self.rect.bottom), (self.rect.left, self.rect.bottom), 2)
            self.img_rect.center = (round(img_cx), round(img_cy))

        screen.blit(self.img, self.img_rect)


class LevelCarousel:
    """
    A horizontally scrolling carousel to browse, select, add, and delete levels.
    Displays the selected level large in the center with neighboring levels smaller on the sides.
    Supports animated sliding transitions and a delete confirmation popup.
    """

    def __init__(self, x: int, y: int, size: tuple, levels: list):
        """
        Initialize the carousel with a center position, card size, and level list.

        :param x: Horizontal center of the carousel on screen.
        :param y: Vertical center of the carousel on screen.
        :param size: (width, height) of the center (selected) level card.
        :param levels: List of level data (surfaces or None for empty slots).
        """
        self.center_rect = None
        self.left_rect = None
        self.right_rect = None
        self.x = x
        self.y = y

        self.levels = levels
        self.selected = 0

        self.big_size = size
        self.small_size = (size[0] * 2 / 3, size[1] * 2 / 3)
        self.spacing = 260 * size[0] / 300

        self.delete_button = pygame.Rect(x - 70 * size[0] / 300, y + 150 * size[1] / 180,
                                         140 * size[0] / 300, 50 * size[1] / 180)
        self.delete_button_selected = False

        self.offset = 0
        self.target_offset = 0
        self.anim_speed = 0.2
        self.animating = False

        self.delete_window_on = False
        self.yes_button = None
        self.no_button = None

    def draw_level(self, screen: pygame.Surface, img, rect: pygame.Rect, selected: bool = False):
        """
        Draw a single level card at the given rect.
        If the level has an image, it is scaled to fill the rect.
        If the slot is empty (img is None), a '+' placeholder is drawn.
        A white border is drawn around the selected card.

        :param screen: Target surface to draw on.
        :param img: Level thumbnail surface, an integer index for placeholder color, or None.
        :param rect: Destination rect to draw the card into.
        :param selected: If True, draws a white selection border around the card.
        """
        pygame.draw.rect(screen, (40, 40, 40), rect)

        if img is not None:
            try:
                img = pygame.transform.scale(img, rect.size)
                screen.blit(img, rect)
            except TypeError:
                i = img
                img = pygame.Surface(rect.size)
                img.fill(((150 * (i + 1)) % 255, (30 * i) % 255, (30 * i) % 255))
                screen.blit(img, rect)
        else:
            font = pygame.font.SysFont(None, 80)
            txt = font.render("+", True, (200, 200, 200))
            screen.blit(txt, txt.get_rect(center=rect.center))

        if selected:
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)

    def draw(self, screen: pygame.Surface):
        """
        Draw the full carousel: left neighbor, center (selected), right neighbor,
        the delete button, and the delete confirmation popup if active.

        :param screen: Target surface to draw on.
        """
        center_rect = pygame.Rect(0, 0, *self.big_size)
        center_x = self.x - self.offset * self.spacing
        center_rect.center = (center_x, self.y)

        if self.selected > 0:
            left_rect = pygame.Rect(0, 0, *self.small_size)
            left_rect.center = (center_x - self.spacing, self.y)
            self.draw_level(screen, self.levels[self.selected - 1], left_rect)
            self.left_rect = left_rect
        else:
            self.left_rect = None

        self.draw_level(screen, self.levels[self.selected], center_rect, True)
        self.center_rect = center_rect

        if self.selected < len(self.levels) - 1:
            right_rect = pygame.Rect(0, 0, *self.small_size)
            right_rect.center = (center_x + self.spacing, self.y)
            self.draw_level(screen, self.levels[self.selected + 1], right_rect)
            self.right_rect = right_rect
        else:
            self.right_rect = None

        if self.levels[self.selected] is not None:
            pygame.draw.rect(screen, (220, 40, 40), self.delete_button, border_radius=10)
            font = pygame.font.SysFont(None, round(30 * self.big_size[0] / 300))
            txt = font.render("DELETE", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=self.delete_button.center))
            if self.delete_button_selected:
                pygame.draw.rect(screen, (255, 255, 255), self.delete_button, 3, border_radius=10)

        if self.delete_window_on:
            self.yes_button, self.no_button = self.draw_delete_popup(screen, self.selected, "DELETE THE LEVEL ")

    def draw_delete_popup(self, screen: pygame.Surface, confirm_delete_id: int, text: str):
        """
        Draw a centered confirmation popup with YES and NO buttons.

        :param screen: Target surface to draw on.
        :param confirm_delete_id: Level index shown in the confirmation message.
        :param text: Prefix text for the confirmation message.
        :return: Tuple (yes_btn_rect, no_btn_rect) for click detection.
        """
        text_font = pygame.font.SysFont(None, 30)
        SW, SH = screen.get_size()
        center_x = SW // 2

        popup_rect = pygame.Rect(center_x - int(SW / 5), SH // 2 - SH // 6, SW * 0.4, SH // 3)
        pygame.draw.rect(screen, (20, 20, 20), popup_rect)
        pygame.draw.rect(screen, (255, 255, 255), popup_rect, 2)

        msg = text_font.render(f"{text} {confirm_delete_id}?", True, (255, 255, 255))
        screen.blit(msg, (center_x - msg.get_width() // 2, popup_rect.top + 40))

        yes_btn = pygame.Rect(center_x - SW * 0.12, popup_rect.bottom - SH / 10, SW / 10, SH / 15)
        no_btn = pygame.Rect(center_x + SW * 0.02, popup_rect.bottom - SH / 10, SW / 10, SH / 15)

        pygame.draw.rect(screen, (150, 0, 0), yes_btn)
        pygame.draw.rect(screen, (100, 100, 100), no_btn)

        yes_txt = text_font.render("YES", True, (255, 255, 255))
        no_txt = text_font.render("NO", True, (255, 255, 255))
        screen.blit(yes_txt, (yes_btn.centerx - yes_txt.get_width() // 2, yes_btn.centery - SH / 40))
        screen.blit(no_txt, (no_btn.centerx - no_txt.get_width() // 2, no_btn.centery - SH / 40))

        return yes_btn, no_btn

    def handle_event(self, event: pygame.event.Event):
        """
        Process mouse and keyboard events for the carousel.
        Clicking left/right neighbor cards starts a sliding animation.
        Clicking the center card returns "AddLevel" or "LoadLevel".
        Keyboard arrows navigate between cards; Enter confirms selection.
        Deletion flow opens the popup and returns "DeleteLevel" on confirmation.

        :param event: The Pygame event to process.
        :return: Action string ("AddLevel", "LoadLevel", "DeleteLevel") or None.
        """
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
                    if event.key == pygame.K_RIGHT and self.selected < len(self.levels) - 1:
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

    def update(self):
        """
        Advance the sliding animation each frame.
        Once the offset is close enough to the target, snap to the new selection
        and reset the animation state.
        """
        if self.animating:
            self.offset += (self.target_offset - self.offset) * self.anim_speed
            if abs(self.target_offset - self.offset) < 0.01:
                self.selected += int(self.target_offset)
                self.offset = 0
                self.target_offset = 0
                self.animating = False


class MenuButton:
    """
    A text-based menu button that shows decorative hover images on either side when focused.
    Navigation is keyboard-driven; the button activates via the game's configured select key.
    """

    def __init__(self, menu, text: str, font: pygame.font.Font, pos_center: tuple[int, int],
                 text_color: tuple[int, int, int]):
        """
        Initialize the menu button.

        :param menu: Reference to the parent menu object (used to access game key bindings).
        :param text: Label string displayed for this button.
        :param font: Pygame font used to render the text.
        :param pos_center: (x, y) center position of the text on screen.
        :param text_color: RGB color of the button text.
        """
        self.menu = menu
        self.text_surf = font.render(text, True, text_color)
        self.text = text
        self.font = font
        self.rect = self.text_surf.get_rect(center=pos_center)
        self.text_color = text_color
        self.hover = False
        self.hover_image = load_image("ui/Opera_senza_titolo.png", size=(font.get_height() * 4, font.get_height() * 4))
        self.hover2_image = pygame.transform.flip(self.hover_image, True, False)

    def draw(self, screen: pygame.Surface):
        """
        Draw the button text, and if hovered, the decorative images flanking the label.

        :param screen: Target surface to draw on.
        """
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
        screen.blit(self.text_surf, self.rect)

    def is_clicked(self, event: pygame.event.Event) -> bool:
        """
        Return True if the game's select key was pressed while this button is focused.

        :param event: The Pygame event to check.
        :return: True if the select key was pressed.
        """
        if event.type == pygame.KEYDOWN:
            if event.key == self.menu.game.key_map["key_select"]:
                return True
            return False

    def handle_event(self, event: pygame.event.Event):
        """
        Process an event; only acts when the button is hovered.

        :param event: The Pygame event to process.
        :return: True if activated, None otherwise.
        """
        if self.hover:
            return self.is_clicked(event)
        return None

    def start_hover_effect(self):
        """Enable the hover state, showing decorative flanking images."""
        self.hover = True

    def end_hover_effect(self):
        """Disable the hover state, hiding decorative flanking images."""
        self.hover = False


class DiscreteSlider:
    """
    A horizontal slider with a fixed number of discrete steps.
    Supports keyboard navigation when hovered and displays a hover indicator.
    Can show an optional label to the left and the current step value to the right.
    """

    def __init__(self, menu, x: int, y: int, width: int, height: int, steps: int,
                 active_color=(255, 255, 255), inactive_color=(180, 180, 180),
                 knob_color=(255, 255, 255), border_radius=8,
                 selector_image=None, font=None, text=None, textx=None):
        """
        Initialize the discrete slider.

        :param menu: Reference to the parent menu (used for key map access).
        :param x: Left position of the slider track.
        :param y: Top position of the slider track.
        :param width: Width of the slider track in pixels.
        :param height: Height of the slider track in pixels.
        :param steps: Total number of discrete steps (value range: 0 to steps).
        :param active_color: Color of the filled (active) portion of the track.
        :param inactive_color: Color of the unfilled (inactive) portion of the track.
        :param knob_color: Color of the circular knob (if no selector_image).
        :param border_radius: Corner radius for the track rectangle.
        :param selector_image: Optional surface used as the knob image.
        :param font: Optional font for rendering the numeric value and label.
        :param text: Optional label string displayed to the left of the slider.
        :param textx: X position of the label text.
        """
        self.menu = menu
        self.rect = pygame.Rect(x, y, width, height)
        self.steps = steps
        self.value = 0

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
            center=(self.rect.x + self.rect.width * 1.16, self.rect.centery)) if self.nb_text_surf else None
        self.text = text
        self.textx = textx
        self.text_surf = font.render(text, True, active_color) if self.text else None
        self.text_rect = self.text_surf.get_rect(centery=self.rect.centery, x=textx) if self.text_surf else None

        self.hover = False
        self.hover_image_left = load_image('/ui/Opera_senza_titolo.png', size=(width * 0.16, width * 0.16))
        self.hover_image_right = pygame.transform.flip(self.hover_image_left, True, False)
        self.hover_image_width = self.hover_image_right.get_width()
        self.dragging = False

        self.rects = [self.rect]
        if self.image_rect is not None: self.rects.append(self.image_rect)
        if self.text_rect is not None: self.rects.append(self.text_rect)
        if self.nb_text_rect is not None: self.rects.append(self.nb_text_rect)

    def draw(self, surface: pygame.Surface):
        """
        Draw the slider track, active fill, knob, optional label, numeric value,
        and hover indicator images.

        :param surface: Target surface to draw on.
        """
        if self.text is not None:
            surface.blit(self.text_surf, self.text_rect)

        pygame.draw.rect(surface, self.inactive_color, self.rect, border_radius=self.border_radius)

        if self.value > 0:
            step_width = self.rect.width / self.steps
            active_width = step_width * self.value
            active_rect = pygame.Rect(self.rect.x, self.rect.y, active_width, self.rect.height)
            pygame.draw.rect(surface, self.active_color, active_rect, border_radius=self.border_radius)

        if self.value > 0:
            knob_x = self.rect.x + (self.rect.width / self.steps) * self.value
        else:
            knob_x = self.rect.x

        if self.selector_image is None:
            pygame.draw.circle(surface, self.knob_color, (int(knob_x), self.rect.centery), self.rect.height)
        else:
            self.image_rect = self.selector_image.get_rect(center=(int(knob_x), self.rect.centery))
            surface.blit(self.selector_image, self.image_rect)

        if self.font is not None:
            surface.blit(self.nb_text_surf, self.nb_text_rect)

        if self.hover:
            surface.blit(self.hover_image_left, self.hover_image_left.get_rect(
                x=self.text_rect.x - self.hover_image_width if self.text_rect.x else self.rect.x - self.hover_image_width,
                centery=self.rect.centery))
            surface.blit(self.hover_image_right, self.hover_image_right.get_rect(
                x=self.nb_text_rect.x + self.nb_text_rect.width if self.nb_text_rect.x else self.rect.x + self.rect.width,
                centery=self.rect.centery))

    def handle_event(self, event: pygame.event.Event):
        """
        Process keyboard events to increment or decrement the value when hovered.
        Also refreshes the displayed numeric text surface.

        :param event: The Pygame event to process.
        :return: Always None.
        """
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
        """Refresh the numeric text surface to reflect the current value."""
        if self.font is not None:
            self.nb_text_surf = self.font.render(str(self.value), True, self.active_color)

    def get_value(self) -> int:
        """
        Return the current discrete step value.

        :return: Current value (0 to steps).
        """
        return self.value

    def get_normalized(self) -> float:
        """
        Return the current value normalized to the [0.0, 1.0] range.

        :return: Normalized float value.
        """
        return self.value / self.steps

    def start_hover_effect(self):
        """Enable the hover state, showing flanking indicator images."""
        self.hover = True

    def end_hover_effect(self):
        """Disable the hover state, hiding flanking indicator images."""
        self.hover = False

    def set_normalized_value(self, value: float):
        """
        Set the slider value from a normalized float in [0.0, 1.0].

        :param value: Normalized value to convert and apply.
        """
        self.value = int(value * self.steps)


class ToggleSwitch:
    """
    A toggle switch UI element (ON/OFF) styled as a sliding pill.
    Supports keyboard activation when hovered and an optional label to the left.
    """

    def __init__(self, menu, x: int, y: int, width: int = 60, height: int = 30,
                 bg_on=(255, 255, 255), bg_off=(180, 180, 180),
                 circle_color=(100, 100, 100),
                 font=None, text=None, textx=None):
        """
        Initialize the toggle switch.

        :param menu: Reference to the parent menu (used for key map access).
        :param x: Left position of the switch rect.
        :param y: Top position of the switch rect.
        :param width: Width of the pill-shaped switch.
        :param height: Height of the pill-shaped switch.
        :param bg_on: Background color when the switch is ON.
        :param bg_off: Background color when the switch is OFF.
        :param circle_color: Color of the sliding circle indicator.
        :param font: Optional font for rendering the label.
        :param text: Optional label string displayed to the left.
        :param textx: X position of the label text.
        """
        self.menu = menu
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height

        self.bg_on = bg_on
        self.bg_off = bg_off
        self.circle_color = circle_color

        self.state = False
        self.circle_radius = height // 2 - 3
        self.padding = 3

        self.text = text
        self.textx = textx
        self.font = font
        self.text_surf = font.render(self.text, True, bg_on) if font is not None else None
        self.text_rect = self.text_surf.get_rect(x=textx, centery=self.rect.centery) if self.text_surf is not None else None

        self.hover = False
        self.hover_image_left = load_image('/ui/Opera_senza_titolo.png', size=(width * 0.8, width * 0.8))
        self.hover_image_right = pygame.transform.flip(self.hover_image_left, True, False)
        self.hover_image_width = self.hover_image_right.get_width()

        self.selected = False
        self.rects = [self.rect]
        if self.text_rect is not None:
            self.rects.append(self.text_rect)

    def draw(self, surface: pygame.Surface):
        """
        Draw the toggle switch with its current ON/OFF state and optional label.
        Also draws hover indicator images when hovered.

        :param surface: Target surface to draw on.
        """
        if self.font is not None:
            surface.blit(self.text_surf, self.text_rect)

        bg_color = self.bg_on if self.state else self.bg_off
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=self.height // 2)

        if self.state:
            circle_x = self.rect.right - self.circle_radius - self.padding
        else:
            circle_x = self.rect.left + self.circle_radius + self.padding

        pygame.draw.circle(surface, self.circle_color, (circle_x, self.rect.centery), self.circle_radius)

        if self.hover:
            surface.blit(self.hover_image_left, self.hover_image_right.get_rect(
                x=self.text_rect.x - self.hover_image_width if self.text_rect else self.rect.x - self.hover_image_width,
                centery=self.rect.centery))
            surface.blit(self.hover_image_right, self.hover_image_left.get_rect(
                x=self.rect.x + self.rect.width, centery=self.rect.centery))

    def handle_event(self, event: pygame.event.Event):
        """
        Process keyboard events to toggle the state when hovered and select key is pressed.

        :param event: The Pygame event to process.
        :return: True if the state was toggled, None otherwise.
        """
        if self.hover:
            if event.type == pygame.KEYDOWN:
                if event.key == self.menu.game.key_map["key_select"]:
                    self.state = not self.state
                    return True

    def get_state(self) -> bool:
        """
        Return the current ON/OFF state.

        :return: True if ON, False if OFF.
        """
        return self.state

    def set_state(self, value: bool):
        """
        Programmatically set the switch state.

        :param value: True for ON, False for OFF.
        """
        self.state = value

    def start_hover_effect(self):
        """Enable the hover state, showing flanking indicator images."""
        self.hover = True

    def end_hover_effect(self):
        """Disable the hover state, hiding flanking indicator images."""
        self.hover = False


class ArrowSelector:
    """
    A horizontal option selector with left/right arrow buttons.
    Cycles through a list of string options using keyboard navigation when hovered.
    Displays an optional label to the left of the selector.
    """

    def __init__(self, menu, x: int, y: int, width: int, height: int, font: pygame.font.Font,
                 options: list[str], bg_color=(180, 180, 180), arrow_color=(255, 255, 255),
                 text_color1=(0, 0, 0), text=None, textx=None, text_color2=None):
        """
        Initialize the arrow selector.

        :param menu: Reference to the parent menu.
        :param x: Left position of the central selector rect.
        :param y: Top position of the selector.
        :param width: Width of the central option display area.
        :param height: Height of the component (also used as arrow width).
        :param font: Pygame font for rendering the current option and label.
        :param options: List of selectable string options.
        :param bg_color: Background color of the central display area.
        :param arrow_color: Color of the arrow polygons.
        :param text_color1: Text color of the current option.
        :param text: Optional label string shown to the left.
        :param textx: X position of the label text.
        :param text_color2: Text color of the optional label.
        """
        self.menu = menu
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.options = options
        self.index = 0

        self.bg_color = bg_color
        self.arrow_color = arrow_color
        self.text_color = text_color1

        self.arrow_width = height
        self.left_rect = pygame.Rect(x - height, y, self.arrow_width, height)
        self.right_rect = pygame.Rect(x + width + height - self.arrow_width, y, self.arrow_width, height)
        self.center_rect = pygame.Rect(x + self.arrow_width, y, width - 2 * self.arrow_width, height)

        self.text = text
        self.textx = textx
        self.text_color2 = text_color2
        self.text_surf = font.render(self.text, True, self.text_color2) if self.text else None
        self.text_rect = self.text_surf.get_rect(x=textx, centery=self.rect.centery) if self.text_surf else None

        self.hover = True
        self.hover_image_left = load_image('ui/Opera_senza_titolo.png', size=(width * 0.24, width * 0.24))
        self.hover_image_right = pygame.transform.flip(self.hover_image_left, True, False)
        self.hover_image_width = self.hover_image_right.get_width()

    def draw(self, surface: pygame.Surface):
        """
        Draw the central option display, left/right arrow triangles, optional label,
        and hover indicator images.

        :param surface: Target surface to draw on.
        """
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=6)

        current_text = self.options[self.index]
        text_surface = self.font.render(current_text, True, self.text_color)
        surface.blit(text_surface, text_surface.get_rect(center=self.center_rect.center))

        pygame.draw.polygon(surface, self.arrow_color, [
            (self.left_rect.centerx + int(self.arrow_width / 8), self.left_rect.centery - int(self.arrow_width / 5)),
            (self.left_rect.centerx - int(self.arrow_width / 8), self.left_rect.centery),
            (self.left_rect.centerx + int(self.arrow_width / 8), self.left_rect.centery + int(self.arrow_width / 5))
        ])
        pygame.draw.polygon(surface, self.arrow_color, [
            (self.right_rect.centerx - int(self.arrow_width / 8), self.right_rect.centery - int(self.arrow_width / 5)),
            (self.right_rect.centerx + int(self.arrow_width / 8), self.right_rect.centery),
            (self.right_rect.centerx - int(self.arrow_width / 8), self.right_rect.centery + int(self.arrow_width / 5))
        ])

        if self.text:
            surface.blit(self.text_surf, self.text_rect)

        if self.hover:
            surface.blit(self.hover_image_left, self.hover_image_left.get_rect(
                x=self.text_rect.x - self.hover_image_width,
                centery=self.rect.centery))
            surface.blit(self.hover_image_right, self.hover_image_right.get_rect(
                x=self.right_rect.right,
                centery=self.rect.centery))

    def handle_event(self, event: pygame.event.Event):
        """
        Process keyboard events to cycle through options when hovered.
        Left arrow decrements the index, right arrow increments it (wraps around).

        :param event: The Pygame event to process.
        :return: The newly selected option string, or None if no change.
        """
        if self.hover:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.index = (self.index - 1) % len(self.options)
                    return self.get_selected()
                if event.key == pygame.K_RIGHT:
                    self.index = (self.index + 1) % len(self.options)
                    return self.get_selected()
        return None

    def get_selected(self) -> str:
        """
        Return the currently selected option string.

        :return: Selected option.
        """
        return self.options[self.index]

    def set_selected(self, value: str):
        """
        Set the current selection by value, if it exists in the options list.

        :param value: Option string to select.
        """
        if value in self.options:
            self.index = self.options.index(value)

    def start_hover_effect(self):
        """Enable the hover state, showing flanking indicator images."""
        self.hover = True

    def end_hover_effect(self):
        """Disable the hover state, hiding flanking indicator images."""
        self.hover = False


class SaveSlotUI:
    """
    A UI row representing a single save slot in the save/load menu.
    Displays save metadata (level name, playtime, date, deaths, souls) and a thumbnail.
    If the slot is empty, shows a "NEW GAME" prompt.
    Supports keyboard navigation for selection and deletion.
    """

    def __init__(self, menu, slot_id: int, x: int, y: int, width: int, height: int,
                 fonts: dict, colors: dict):
        """
        Initialize the save slot UI.

        :param menu: Reference to the parent menu (used for key map access).
        :param slot_id: Slot number displayed as a label (e.g. 1, 2, 3).
        :param x: Left position of the slot rect.
        :param y: Top position of the slot rect.
        :param width: Full reference width (slot rect uses 4/5 of this).
        :param height: Height of the slot row.
        :param fonts: Dict with keys "number", "text", "detail" mapping to Pygame fonts.
        :param colors: Dict with at least a "white" key mapping to an RGB tuple.
        """
        self.menu = menu
        self.slot_id = slot_id
        self.rect = pygame.Rect(x, y, 4 * width / 5, height)
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
            self.rect.right + width / 35,
            self.rect.top,
            width / 5,
            height / 2
        )
        self.delete_rect.centery = self.rect.centery

        self.hover = False
        self.is_selected = False
        self.delete_hover = False

    def update_data(self, save_data=None, thumbnail=None):
        """
        Update the slot's save data and thumbnail.

        :param save_data: Dict containing save info (level_name, playtime, date, death, souls).
        :param thumbnail: Optional pygame.Surface used as the save thumbnail image.
        """
        self.save_data = save_data
        self.thumbnail = thumbnail

    def draw(self, surface: pygame.Surface):
        """
        Draw the save slot row.
        If the slot has data, renders the thumbnail, stats, and delete button.
        If empty, renders the "NEW GAME" prompt.

        :param surface: Target surface to draw on.
        """
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
                                   self.rect.top + self.width * 0.026,
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
            lvl_rect = lvl_txt.get_rect(x=x_right - lvl_txt.get_width(), y=y_start)
            time_txt = self.detail_font.render(time_str, True, (170, 170, 170))
            time_rect = time_txt.get_rect(x=x_right - time_txt.get_width(), y=lvl_rect.bottom + spacing)
            date_txt = self.detail_font.render(date_str, True, (150, 150, 150))
            date_rect = date_txt.get_rect(x=x_right - date_txt.get_width(), y=time_rect.bottom + spacing)

            surface.blit(lvl_txt, lvl_rect)
            surface.blit(time_txt, time_rect)
            surface.blit(date_txt, date_rect)

            del_color = (200, 0, 0) if self.delete_hover else (120, 0, 0)
            pygame.draw.rect(surface, del_color, self.delete_rect, border_radius=6)
            del_txt = self.detail_font.render("DELETE", True, (255, 255, 255))
            surface.blit(del_txt, (
                self.delete_rect.centerx - del_txt.get_width() // 2,
                self.delete_rect.centery - del_txt.get_height() // 2))

            deaths = self.save_data.get("death", 0)
            souls = self.save_data.get("souls", 0)
            icon_size = 32

            death_icon = pygame.Rect(img_rect.right + 20, img_rect.top + 5, icon_size, icon_size)
            surface.blit(pygame.transform.scale(self.death_icon, (icon_size, icon_size)), death_icon)
            death_txt = self.detail_font.render(f"{deaths}", True, (200, 200, 200))
            death_rect = death_txt.get_rect(x=death_icon.right + 5, centery=death_icon.centery)
            surface.blit(death_txt, death_rect)

            soul_icon_rect = pygame.Rect(img_rect.right + 20, img_rect.bottom - icon_size - 5, icon_size, icon_size)
            surface.blit(pygame.transform.scale(self.souls_icon, (icon_size, icon_size)), soul_icon_rect)
            souls_text = self.detail_font.render(f"{souls}", True, (200, 200, 200))
            souls_rect = souls_text.get_rect(x=soul_icon_rect.right + 5, centery=soul_icon_rect.centery)
            surface.blit(souls_text, souls_rect)

        else:
            ng_txt = self.text_font.render(
                "NEW GAME", True,
                (255, 255, 255) if self.hover else (120, 120, 120))
            ng_rect = ng_txt.get_rect(centerx=self.rect.centerx, centery=self.rect.centery)
            surface.blit(ng_txt, ng_rect)

    def handle_event(self, event: pygame.event.Event):
        """
        Process keyboard input for slot selection and deletion when hovered.
        Right arrow focuses the delete button; left arrow unfocuses it.
        Select key loads, starts, or deletes the save depending on state.

        :param event: The Pygame event to process.
        :return: "DELETE", "LOAD", or "START" action string, or None.
        """
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
        """Reset the delete button hover state when the slot loses focus."""
        if not self.hover:
            self.delete_hover = False

    def start_hover_effect(self):
        """Enable the hover state, highlighting the slot row."""
        self.hover = True

    def end_hover_effect(self):
        """Disable the hover state, reverting to the default appearance."""
        self.hover = False