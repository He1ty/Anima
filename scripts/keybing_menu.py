import pygame
import sys
import json
import os
from scripts.button import MenuButton
from scripts.text import load_game_font
from scripts.utils import load_image, draw_rect_alpha,key_name,build_items

pygame.init()
# ─── CLASSE PRINCIPALE ────────────────────────────────────────────────────────

class ControlsMenu:
    """
    Menu des contrôles scrollable avec réassignation de touches.

    Usage dans ta boucle de jeu :
        menu = ControlsMenu(screen, game, title_font, button_font)
        ...
        for event in pygame.event.get():
            menu.handle_event(event)          # gère navigation + rebind
        menu.draw_controls_menu()             # dessine tout
    """

    # ── Dimensions internes ──────────────────────────────────────────────────
    ITEM_H   = 48
    CAT_H    = 36
    PADDING  = 8
    MARGIN_X = 90
    SB_W     = 10

    def __init__(self, screen: pygame.Surface, game, title_font: pygame.font.Font,
                 button_font: pygame.font.Font):
        self.screen      = screen
        self.screen_size = screen.get_size()
        self.game        = game
        self.title_font  = title_font
        self.button_font = button_font

        # Polices internes (cohérentes avec le reste du projet)
        self.font_cat    = self.button_font
        self.font_action = load_game_font(size=20)
        self.font_key    = load_game_font(20)
        self.font_hint   = pygame.font.SysFont("Consolas", 12)

        # Données
        self.bindings     = self.game.save_system.load_bindings()
        self.items        = build_items(self.bindings)
        self.bind_indices = [i for i, it in enumerate(self.items) if it[0] == "bind"]

        # Navigation
        self.command_nb  = 0      # index parmi bind_indices (= ligne sélectionnée)
        self.scroll_y = 0  # This will be our "current" interpolated position
        self.target_scroll = 0  # This is where we WANT to go
        self.scroll_speed = 0.3  # Adjust between 0.05 (slow) and 0.3 (fast)
        self.rebinding   = False
        self.flash_timer = 0

        # Bouton retour (même style que MenuButton dans ton projet)
        self._init_back_button()
        self._compute_layout()

        self.pressing_down = False
        self.pressing_up = False

    # ── Init bouton retour ───────────────────────────────────────────────────

    def _init_back_button(self):
        """Crée le bouton BACK avec MenuButton — adapte le texte à ta langue."""
        sw, sh = self.screen.get_size()
        # On importe MenuButton localement pour éviter un import circulaire
        # si ce fichier est séparé ; sinon retire cet import
          # ← adapte selon ton chemin d'import
        self.back_button = MenuButton(
            text="BACK",
            font=self.button_font,
            pos_center=(sw // 2, sh - 30),
            text_color=(255, 255, 255),
        )

    # ── Layout ──────────────────────────────────────────────────────────────

    def _compute_layout(self):
        sw, sh = self.screen.get_size()
        y = 50  # espace sous le titre
        self.row_rects = []
        for it in self.items:
            h = self.CAT_H if it[0] == "cat" else self.ITEM_H
            self.row_rects.append((y, h))
            y += h + self.PADDING

        self.total_h  = y
        self.view_top = 85
        self.view_h   = sh - self.view_top - 55
        self.max_scroll = max(0, self.total_h - self.view_h)

    # ── Helpers navigation ───────────────────────────────────────────────────

    def _sel_item(self):
        return self.items[self.bind_indices[self.command_nb]]
    def _get_key_from_value(self, value):
        for cat in self.bindings:
            for bind in self.bindings[cat]:
                if value  == self.bindings[cat][bind]:
                    return cat,bind
        return None,None


    def _ensure_visible(self):
        idx = self.bind_indices[self.command_nb]
        y_abs, h = self.row_rects[idx]

        # Include the category header if it's right above us
        top_margin = self.PADDING
        if idx > 0 and self.items[idx - 1][0] == "cat":
            top_margin += self.row_rects[idx - 1][1] + self.PADDING

        # We update target_scroll instead of scroll_y directly
        if y_abs - self.target_scroll < top_margin:
            self.target_scroll = max(0, y_abs - top_margin)
        elif y_abs + h - self.target_scroll > self.view_h:
            self.target_scroll = min(self.max_scroll, y_abs + h - self.view_h + self.PADDING)

    def update_scroll(self):
        """Call this every frame to handle the sliding motion."""
        diff = self.target_scroll - self.scroll_y

        # If the distance is tiny, just snap to avoid micro-stuttering
        if abs(diff) < 0.5:
            self.scroll_y = self.target_scroll
        else:
            self.scroll_y += diff * self.scroll_speed

    # ── Gestion des événements (même signature que les autres menus) ──────────

    def handle_event(self, event: pygame.event.Event):
        """
        À appeler dans la boucle d'événements principale.
        Retourne None normalement, "back" quand l'utilisateur quitte ce menu.
        """
        # ── Mode réassignation ──────────────────────────────────────────────
        if self.rebinding:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.rebinding = False
                else:
                    _, cat, action = self._sel_item()
                    cat2,key = self._get_key_from_value(event.key)
                    if key is not None:
                        self.bindings[cat2][key] = None
                    self.bindings[cat][action] = event.key
                    self.items        = build_items(self.bindings)
                    self.bind_indices = [i for i, it in enumerate(self.items) if it[0] == "bind"]
                    self._compute_layout()
                    self.game.save_system.save_bindings(self.bindings)
                    self.flash_timer = 90
                    self.rebinding   = False
            return None

        # ── Navigation normale ──────────────────────────────────────────────
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.command_nb = min(self.command_nb + 1, len(self.bind_indices) - 1)
                self._ensure_visible()

            elif event.key == pygame.K_UP:
                self.command_nb = max(0, self.command_nb - 1)
                self._ensure_visible()

            elif event.key == pygame.K_RETURN:
                # ENTRÉE sur le bouton back (dernier élément virtuel)
                # → le bouton back n'est pas dans bind_indices,
                #   on le gère via MenuButton.handle_event ci-dessous
                self.rebinding = True

            elif event.key == pygame.K_ESCAPE:
                self.game.save_system.save_bindings(self.bindings)
                self.command_nb = 0
                return "back"

            elif event.key == pygame.K_r:
                self.bindings     = {cat: dict(actions) for cat, actions in self.game.save_system.DEFAULT_BINDINGS.items()}
                self.items        = build_items(self.bindings)
                self.bind_indices = [i for i, it in enumerate(self.items) if it[0] == "bind"]
                self._compute_layout()
                self.game.save_system.save_bindings(self.bindings)
                self.flash_timer  = 90

        # ── Bouton BACK (clic souris ou ENTRÉE quand hover) ──────────────────
        if self.back_button.handle_event(event):
            self.game.save_system.save_bindings(self.bindings)
            self.command_nb = 0
            return "back"

        return None

    # ── Dessin ───────────────────────────────────────────────────────────────

    def draw_controls_menu(self):
        """
        Méthode principale de rendu.
        Reproduit la structure draw_audio_settings_menu / draw_video_settings_menu.
        """
        sw, sh = self.screen.get_size()

        if self.game.previous_state == self.game.TITLE_STATE:
            self.game.menu.draw_title_screen_background_animation()
        else:
            self.screen.fill(self.game.menu.COLORS["black"])

        self.update_scroll()

        # Overlay semi-transparent

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # — Titre ─────────────────────────────────────────────────────────────
        controls_title = self.title_font.render("CONTROLS", True, (255, 255, 255))
        self.screen.blit(controls_title,
                         controls_title.get_rect(center=(sw // 2, 45)))

        # — Zone scrollable ───────────────────────────────────────────────────
        view_rect = pygame.Rect(0, self.view_top,
                                sw, self.view_h)


        clip = pygame.Rect(view_rect.x, view_rect.y,
                           view_rect.w - self.SB_W - 4, view_rect.h)
        self.screen.set_clip(clip)

        sel_flat = self.bind_indices[self.command_nb]

        for i, it in enumerate(self.items):
            y_abs, h = self.row_rects[i]
            y_scr = y_abs - self.scroll_y + self.view_top

            if y_scr + h < self.view_top or y_scr > self.view_top + self.view_h:
                continue

            x = view_rect.x+self.MARGIN_X + 14
            w = view_rect.w-2*self.MARGIN_X - 28 - self.SB_W

            if it[0] == "cat":
                # ── En-tête de catégorie ─────────────────────────────────
                cat_rect = pygame.Rect(x - 4, y_scr, w, h)
                lbl = self.font_cat.render(it[1].upper(), True, (197, 160, 90))
                self.screen.blit(lbl, (x + 10, y_scr + (h - lbl.get_height()) // 2))

            else:
                # ── Ligne de binding ─────────────────────────────────────
                _, cat, action = it
                is_sel   = (i == sel_flat)
                row_rect = pygame.Rect(x - 4, y_scr, w, h)

                if is_sel:
                    # Petites images hover (Opera_senza_titolo) si disponibles
                    self._draw_hover_arrows(row_rect)

                # Nom de l'action
                act_color = (230, 230, 240) if is_sel else (120, 125, 140)
                act_surf  = self.font_action.render(action, True, act_color)
                self.screen.blit(act_surf, (x + 14, y_scr + (h - act_surf.get_height()) // 2))

                # Touche assignée  [ KEY ]
                key_label = key_name(self.bindings[cat][action])
                key_color = (197, 160, 90) if is_sel else (55, 60, 78)
                key_surf  = self.font_key.render(f"[ {key_label} ]", True, key_color)
                kx = row_rect.right - key_surf.get_width() - 16
                self.screen.blit(key_surf, (kx, y_scr + (h - key_surf.get_height()) // 2))

        self.screen.set_clip(None)

        # — Hints bas ─────────────────────────────────────────────────────────
        self._draw_hints(sw, sh)

        # — Overlay réassignation ─────────────────────────────────────────────
        if self.rebinding:
            self._draw_rebind_overlay(sw, sh)

        # — Flash sauvegarde ──────────────────────────────────────────────────
        if self.flash_timer > 0:
            msg = self.font_hint.render("Saved", True, (80, 200, 120))
            self.screen.blit(msg, (sw - msg.get_width() - 20, sh - 30))
            self.flash_timer -= 1

    # ── Helpers de rendu ─────────────────────────────────────────────────────

    def _draw_hover_arrows(self, row_rect: pygame.Rect):
        """Affiche les images Opera_senza_titolo si elles sont disponibles."""
        try:
            img_l = load_image("ui/Opera_senza_titolo.png")
            img_r = pygame.transform.flip(img_l, True, False)
            ix = row_rect.x - img_l.get_width() - 5
            iy = row_rect.y + (row_rect.h - img_l.get_height()) // 2
            self.screen.blit(img_l, (ix, iy))
            ix2 = row_rect.right + 5
            self.screen.blit(img_r, (ix2, iy))
        except Exception:
            pass  # Si les assets ne sont pas dispo, on ignore simplement

    def _draw_scrollbar(self, view_rect: pygame.Rect):
        sb_x    = view_rect.right - self.SB_W - 2
        sb_rect = pygame.Rect(sb_x, view_rect.y + 4, self.SB_W, view_rect.h - 8)
        pygame.draw.rect(self.screen, (50, 58, 85), sb_rect, border_radius=5)
        if self.max_scroll > 0:
            thumb_h = max(30, int(self.view_h * self.view_h / self.total_h))
            thumb_y = sb_rect.y + int(self.scroll_y / self.max_scroll * (sb_rect.h - thumb_h))
            thumb   = pygame.Rect(sb_x, thumb_y, self.SB_W, thumb_h)
            pygame.draw.rect(self.screen, (100, 115, 160), thumb, border_radius=5)

    def _draw_hints(self, sw: int, sh: int):
        hints = [
            ("UP/DOWN", "Navigate"),
            ("ENTER", "Rebind"),
            ("R", "Reset all"),
            ("ESC", "Back"),
        ]
        hx = self.MARGIN_X
        for key_label, desc in hints:
            k = self.font_hint.render(key_label, True, (197, 160, 90))
            d = self.font_hint.render(f" {desc}   ", True, (120, 125, 140))
            self.screen.blit(k, (hx, sh - 22))
            hx += k.get_width()
            self.screen.blit(d, (hx, sh - 22))
            hx += d.get_width()

    def _draw_rebind_overlay(self, sw: int, sh: int):
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        _, cat, action = self._sel_item()
        bw, bh = 400, 180
        bx = sw // 2 - bw // 2
        by = sh // 2 - bh // 2

        pygame.draw.rect(self.screen, (30, 15, 15), (bx, by, bw, bh), border_radius=12)
        pygame.draw.rect(self.screen, (220, 80, 80),  (bx, by, bw, bh), width=2, border_radius=12)

        font_big   = pygame.font.SysFont("Georgia", 20, bold=True)
        font_small = pygame.font.SysFont("Consolas", 14)

        t1 = font_big.render("REBIND KEY", True, (220, 80, 80))
        t2 = font_small.render(f"Action : {action}", True, (230, 230, 240))
        t3 = font_small.render("Press any key...   (ESC to cancel)", True, (120, 125, 140))

        self.screen.blit(t1, (bx + bw // 2 - t1.get_width() // 2, by + 20))
        self.screen.blit(t2, (bx + bw // 2 - t2.get_width() // 2, by + 72))
        self.screen.blit(t3, (bx + bw // 2 - t3.get_width() // 2, by + 130))

        if (pygame.time.get_ticks() // 500) % 2 == 0:
            dot = font_big.render("●", True, (220, 80, 80))
            self.screen.blit(dot, (bx + bw // 2 - dot.get_width() // 2, by + 100))

    def _draw_title_background(self):
        """Fallback si tu as une animation titre dans ton game object."""
        if hasattr(self.game, 'draw_title_screen_background_animation'):
            self.game.draw_title_screen_background_animation()
        else:
            self.screen.fill((0, 0, 0))

