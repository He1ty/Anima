from unicodedata import category

from scripts.utils import load_image
from scripts.button import EditorButton
from scripts.text import load_game_font
from scripts.utils import load_images
import pygame
import os

class EditorSimulation:
    SW = 960
    SH = 600

    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Editor")
        self.screen_width = 960
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.current_tool = "Brush"

        self.current_environment = "white_space"

        self.categories = {category : [t for t in list(load_images(f"{self.current_environment}/{category}"))]
                           for category in sorted(os.listdir(f"assets/{self.current_environment}/images"))}

        self.ui = UI(self)

    def run(self):
        while True:
            self.ui.draw()
            self.clock.tick(60)
            pygame.display.update()

class UI:
    TOOLBAR_COLOR = (64,64,64)
    ASSETS_SECTION_COLOR = (32,32,32)
    PADDING = 5

    def __init__(self, editor):
        self.editor = editor
        self.screen = editor.screen
        self.screen_width, self.screen_height = self.screen.get_size()

        self.title_font = load_game_font(24)
        self.buttons_font = load_game_font(18)

        self.toolbar_width = self.screen_width * 5 / 96
        self.toolbar_default_width = self.screen_width * 5 / 96
        self.toolbar_buttons_width = self.toolbar_width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_width * (3 / 5)
        self.tools_buttons = []
        self.tools_buttons_labels = ["Brush", "Eraser", "Selection"]
        #self.tools_buttons_images = {tool: load_image(f"ui/{tool.lower()}.png") for tool in self.tools_buttons_labels}
        self.tools_buttons_images = {"Brush": load_image("ui/skull.png"),
                                     "Eraser": load_image("ui/skull.png"),
                                     "Selection": load_image("ui/skull.png")}

        self.assets_section_width = self.assets_section_default_width = self.screen_width * 20/96
        self.assets_section_height = self.screen_width * 25/96


        self.init_buttons()
        self.closing = False

    def init_buttons(self):
        self.tools_buttons = []

        button_x, button_y = self.toolbar_width/2, self.toolbar_width/2
        for label in self.tools_buttons_labels:
            button = EditorButton(label, self.tools_buttons_images[label] ,(button_x, button_y), self.toolbar_buttons_width,self.toolbar_buttons_height,(64,64,64))
            button_y += self.toolbar_buttons_height + (self.PADDING/self.editor.SH)*self.screen_height
            self.tools_buttons.append(button)

    def render_toolbar(self):
        self.screen.fill((0,0,0))

        overlay = pygame.Surface((self.toolbar_width, self.screen_height))
        overlay.fill(self.TOOLBAR_COLOR)

        for button in self.tools_buttons:
            button.draw(overlay)
            if button.label == self.editor.current_tool:
                button.activated = True
            else:
                button.activated = False

        self.screen.blit(overlay, (self.screen_width - self.toolbar_width, 0))

    def render_assets_section(self):
        overlay = pygame.Surface((self.assets_section_width, self.assets_section_height))
        overlay.fill(self.ASSETS_SECTION_COLOR)

        category_text = self.title_font.render(self.editor.categories, True, (255, 255, 255))
        category_x = (self.assets_section_width - category_text.get_width())/2
        category_y = (self.PADDING / self.editor.SH) * self.screen_height
        overlay.blit(category_text, (category_x, category_y))



        self.screen.blit(overlay, (self.screen_width - self.toolbar_width - self.assets_section_width,
                                   self.screen_height - self.assets_section_height))

    def check_closed(self):
        if self.closing:
            self.toolbar_width = max(0, self.toolbar_width - 5)
            self.assets_section_width = max(0, self.assets_section_width - 20)
        else:
            self.toolbar_width = min(self.toolbar_default_width, self.toolbar_width + 5)
            self.assets_section_width = min(self.assets_section_default_width, self.assets_section_width + 20)

    def reload(self):
        self.screen_width, self.screen_height = self.editor.screen.get_size()
        self.toolbar_width = self.screen_width * 5/96
        self.toolbar_default_width = self.screen_width * 5/96
        self.toolbar_buttons_width = self.toolbar_width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_width * (3 / 5)
        self.init_buttons()

    def draw(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.closing = not self.closing
            if event.type == pygame.VIDEORESIZE:
                self.reload()
            for button in self.tools_buttons:
                if button.handle_event(event,offset=(self.screen_width-self.toolbar_width, 0)):
                    self.editor.current_tool = button.label
        self.check_closed()
        self.render_toolbar()
        match self.editor.current_tool:
            case "Brush":
                self.render_assets_section()

if __name__ == "__main__":
    editor = EditorSimulation()
    editor.run()