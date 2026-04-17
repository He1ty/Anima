"""
tags_manager.py  –  TagsManager component
Plugs into GroupsManager: call tags_manager.handle_event(event, overlay, offset)
and tags_manager.render(overlay) each frame.
"""
import pygame


# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers (flat, dark-mode-friendly)
# ─────────────────────────────────────────────────────────────────────────────
_PARENT_COLORS = [
    (83,  74, 183),   # purple
    (15, 110,  86),   # teal
    (186, 90,  48),   # coral
    (170,  53, 86),   # pink
    (56,  95, 138),   # blue
]
_TEXT_LIGHT    = (230, 230, 230)
_TEXT_DIM      = (160, 160, 160)
_TEXT_DARK     = (20,  20,  20)
_CHILD_BG      = (45,  45,  45)
_CHILD_HOVER   = (60,  60,  60)
_CHILD_EDIT_HOVER = (70, 70, 90)   # subtle blue tint to hint it's clickable
_MINUS_BG      = (140,  40,  40)
_MINUS_HOVER   = (180,  55,  55)
_ADD_TAG_BG    = (50,  90, 160)
_ADD_TAG_HOVER = (70, 115, 190)
_INPUT_BORDER  = (80, 130, 200)
_INPUT_BG      = (35,  35,  35)
_INPUT_ACTIVE  = (50,  50,  70)
_EDIT_BORDER   = (100, 160, 100)
_EDIT_BG       = (35,  50,  35)


ROW_H      = 28   # height of every row
INDENT     = 18   # child indentation
GAP        = 3    # vertical gap between rows
MINUS_W    = 22   # width of the − button column


# ─────────────────────────────────────────────────────────────────────────────
# Internal row descriptors  (plain data, no pygame.Rect until draw-time)
# ─────────────────────────────────────────────────────────────────────────────
class _ParentRow:
    def __init__(self, tag_name: str, color: tuple):
        self.tag_name = tag_name
        self.color    = color
        self.rect: pygame.Rect | None = None
        self.minus_rect: pygame.Rect | None = None


class _ChildRow:
    def __init__(self, tag_name: str, info_key: str, info_val: str):
        self.tag_name  = tag_name
        self.info_key  = info_key
        self.info_val  = info_val
        self.rect: pygame.Rect | None = None
        self.minus_rect: pygame.Rect | None = None
        self.hover = False


class _EditRow:
    """Inline value-editor that appears as a sibling after a _ChildRow."""
    def __init__(self, tag_name: str, info_key: str, current_val: str):
        self.tag_name  = tag_name
        self.info_key  = info_key
        self.text      = current_val
        self.rect: pygame.Rect | None = None
        self.active    = True


class _InputRow:
    """A live text-input row (used for both new-tag and new-info)."""
    def __init__(self, kind: str, tag_name: str = ""):
        # kind: "tag" | "info"
        self.kind     = kind
        self.tag_name = tag_name
        self.text     = ""
        self.rect: pygame.Rect | None = None
        self.active   = True


class _AddButton:
    """The dashed '+ add tag' / '+ add info' row."""
    def __init__(self, kind: str, tag_name: str = ""):
        self.kind     = kind
        self.tag_name = tag_name
        self.rect: pygame.Rect | None = None


# ─────────────────────────────────────────────────────────────────────────────
# TagsManager
# ─────────────────────────────────────────────────────────────────────────────

class TagsManager:
    """
    Manages the tags panel inside GroupsManager's overlay surface.

    Public API
    ----------
    render(overlay, x, y, w)          → draws everything, returns total height used
    handle_event(event, offset)        → call with overlay's topleft as offset
    """

    def __init__(self, groups_manager):
        self.gm   = groups_manager
        self._font: pygame.font.Font | None = None

        # Runtime state
        self._rows: list = []
        self._pending_input: _InputRow | None = None
        self._pending_edit:  _EditRow  | None = None
        self._dirty = True
        self._scroll_y: int = 0  # ← add
        self._content_h: int = 0  # ← add (total height of all rows)
        self._panel_max_h: int = 9999  # ← add (set by caller each frame)
        self._panel_x: int = 0
        self._panel_y: int = 0

    # ── public trigger ────────────────────────────────────────────────────────

    def mark_dirty(self):
        """Call whenever the underlying data changes."""
        self._dirty = True

    # ── rendering ─────────────────────────────────────────────────────────────

    def render(self, overlay: pygame.Surface, x: int, y: int, w: int, max_h: int = 9999) -> int:
        """
        Draw the tag list into *overlay* starting at (x, y) with width w.
        max_h limits the visible height; content beyond it is scrollable.
        Returns the total pixel height consumed (capped at max_h).
        """
        font = self._get_font()
        editor = self.gm.tags_editor

        self._panel_x = x  # ← store
        self._panel_y = y  # ← store
        self._panel_max_h = max_h  # store for scroll clamping / hit-test

        if self._dirty:
            self._rebuild_rows()
            self._dirty = False

        # ── draw into a tall scratch surface ──────────────────────────────────
        # First pass: measure total height
        scratch_h = max(max_h, self._measure_height())
        scratch = pygame.Surface((w, scratch_h), pygame.SRCALPHA)
        scratch.fill((0, 0, 0, 0))

        cursor_y = 0
        for row in self._rows:
            if isinstance(row, _ParentRow):
                cursor_y = self._draw_parent(scratch, row, 0, cursor_y, w, editor, font)
            elif isinstance(row, _ChildRow):
                cursor_y = self._draw_child(scratch, row, 0, cursor_y, w, editor, font)
            elif isinstance(row, _EditRow):
                cursor_y = self._draw_edit_row(scratch, row, 0, cursor_y, w, font)
            elif isinstance(row, _InputRow):
                cursor_y = self._draw_input(scratch, row, 0, cursor_y, w, font)
            elif isinstance(row, _AddButton):
                cursor_y = self._draw_add_button(scratch, row, 0, cursor_y, w, font)

        self._content_h = cursor_y

        # Clamp scroll
        max_scroll = max(0, self._content_h - max_h)
        self._scroll_y = max(0, min(self._scroll_y, max_scroll))

        # ── blit the visible slice ─────────────────────────────────────────────
        visible_h = min(max_h, self._content_h)
        if visible_h > 0:
            clip_rect = pygame.Rect(0, self._scroll_y, w, visible_h)
            overlay.blit(scratch, (x, y), clip_rect)

        # ── scrollbar ─────────────────────────────────────────────────────────
        if self._content_h > max_h:
            self._draw_scrollbar(overlay, x + w + 3, y, 6, max_h)

        return visible_h
    # ── draw helpers ──────────────────────────────────────────────────────────

    def _draw_parent(self, surf, row: _ParentRow, x, y, w, editor, font) -> int:
        minus_space = MINUS_W + 4
        rect = pygame.Rect(x, y, w - minus_space, ROW_H)
        row.rect = rect

        pygame.draw.rect(surf, row.color, rect, border_radius=5)
        lbl = font.render(row.tag_name, True, _TEXT_LIGHT)
        surf.blit(lbl, (rect.x + 8, rect.centery - lbl.get_height() // 2))

        mr = pygame.Rect(x + w - MINUS_W, y, MINUS_W, ROW_H)
        row.minus_rect = mr
        pygame.draw.rect(surf, _MINUS_BG, mr, border_radius=4)
        m = font.render("X", True, _TEXT_LIGHT)
        surf.blit(m, (mr.centerx - m.get_width() // 2, mr.centery - m.get_height() // 2))


        return y + ROW_H + GAP

    def _draw_child(self, surf, row: _ChildRow, x, y, w, editor, font) -> int:
        minus_space = MINUS_W + 4 if editor else 0
        rect = pygame.Rect(x + INDENT, y, w - INDENT - minus_space, ROW_H)
        row.rect = rect

        # In view mode, use a slightly different hover colour to hint clickability
        if editor:
            bg = _CHILD_HOVER if row.hover else _CHILD_BG
        else:
            bg = _CHILD_EDIT_HOVER if row.hover else _CHILD_BG



        pygame.draw.rect(surf, bg, rect, border_radius=4)

        # In view mode, draw a small pencil hint on hover
        if not editor and row.hover:
            hint = font.render("»", True, _TEXT_DIM)
            surf.blit(hint, (rect.x + 4, rect.centery - hint.get_height() // 2))
            key_x = rect.x + 4 + hint.get_width() + 4
        else:
            key_x = rect.x + 6

        key_surf = font.render(row.info_key, True, _TEXT_DIM)
        val_surf = font.render(str(row.info_val), True, _TEXT_LIGHT)
        surf.blit(key_surf, (key_x, rect.centery - key_surf.get_height() // 2))
        surf.blit(val_surf, (rect.right - val_surf.get_width() - 6,
                             rect.centery - val_surf.get_height() // 2))

        if editor:
            mr = pygame.Rect(x + w - MINUS_W, y, MINUS_W, ROW_H)
            row.minus_rect = mr
            pygame.draw.rect(surf, _MINUS_BG, mr, border_radius=4)
            m = font.render("X", True, _TEXT_LIGHT)
            surf.blit(m, (mr.centerx - m.get_width() // 2, mr.centery - m.get_height() // 2))
        else:
            row.minus_rect = None

        return y + ROW_H + GAP

    def _draw_edit_row(self, surf, row: _EditRow, x, y, w, font) -> int:
        """Sibling edit row rendered just below the child row being edited."""
        rect = pygame.Rect(x + INDENT * 2, y, w - INDENT * 2, ROW_H)
        row.rect = rect

        pygame.draw.rect(surf, _EDIT_BG, rect, border_radius=4)
        pygame.draw.rect(surf, _EDIT_BORDER, rect, 1, border_radius=4)

        # Key label on the left
        key_surf = font.render(row.info_key + " =", True, _TEXT_DIM)
        surf.blit(key_surf, (rect.x + 6, rect.centery - key_surf.get_height() // 2))

        # Editable value on the right with blinking cursor
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        display = row.text + cursor if row.text else (cursor or "value…")
        val_color = _TEXT_LIGHT if row.text else _TEXT_DIM
        val_surf = font.render(display, True, val_color)
        surf.blit(val_surf, (rect.right - val_surf.get_width() - 6,
                             rect.centery - val_surf.get_height() // 2))

        return y + ROW_H + GAP

    def _draw_input(self, surf, row: _InputRow, x, y, w, font) -> int:
        indent = INDENT if row.kind == "info" else 0
        rect = pygame.Rect(x + indent, y, w - indent, ROW_H)
        row.rect = rect

        bg = _INPUT_ACTIVE if row.active else _INPUT_BG
        pygame.draw.rect(surf, bg, rect, border_radius=4)
        pygame.draw.rect(surf, _INPUT_BORDER, rect, 1, border_radius=4)

        display = row.text + ("|" if row.active and (pygame.time.get_ticks() // 500) % 2 == 0 else "")
        txt = font.render(display or ("tag name…" if row.kind == "tag" else "info key…"),
                          True,
                          _TEXT_LIGHT if row.text else _TEXT_DIM)
        surf.blit(txt, (rect.x + 6, rect.centery - txt.get_height() // 2))

        return y + ROW_H + GAP

    def _draw_add_button(self, surf, row: _AddButton, x, y, w, font) -> int:
        indent = INDENT if row.kind == "info" else 0
        rect = pygame.Rect(x + indent, y, w - indent, ROW_H)
        row.rect = rect

        pygame.draw.rect(surf, (0, 0, 0, 0), rect)
        pygame.draw.rect(surf, (80, 80, 80), rect, 1, border_radius=4)

        label = "+ add tag" if row.kind == "tag" else "+ add info"
        lbl = font.render(label, True, _TEXT_DIM)
        surf.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                        rect.centery - lbl.get_height() // 2))

        return y + ROW_H + GAP

    def _draw_scrollbar(self, surf: pygame.Surface, x: int, y: int, w: int, h: int):
        """Draw a minimal scrollbar to the right of the panel."""
        track_rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surf, (60, 60, 60), track_rect, border_radius=3)

        ratio = h / self._content_h
        thumb_h = max(20, int(h * ratio))
        scroll_range = self._content_h - h
        thumb_y = y + int((self._scroll_y / scroll_range) * (h - thumb_h)) if scroll_range > 0 else y
        thumb_rect = pygame.Rect(x, thumb_y, w, thumb_h)
        pygame.draw.rect(surf, (130, 130, 130), thumb_rect, border_radius=3)

    # ── event handling ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event, offset: tuple):
        """
        Call from GroupsManager.handle_event() *before* any other group buttons.
        offset = overlay's topleft on the actual screen.
        """
        # ── scroll wheel ──────────────────────────────────────────────────────
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_y -= event.y * (ROW_H + GAP)
            max_scroll = max(0, self._content_h - self._panel_max_h)
            self._scroll_y = max(0, min(self._scroll_y, max_scroll))
            return True

        # ── keyboard: feed active edit row ────────────────────────────────────
        if self._pending_edit and event.type == pygame.KEYDOWN:
            row = self._pending_edit
            if event.key == pygame.K_RETURN:
                self._commit_edit(row)
            elif event.key == pygame.K_ESCAPE:
                self._cancel_edit()
            elif event.key == pygame.K_BACKSPACE:
                row.text = row.text[:-1]
            elif event.unicode and event.unicode.isprintable():
                row.text += event.unicode
            return True

        # ── keyboard: feed active input row ───────────────────────────────────
        if self._pending_input and event.type == pygame.KEYDOWN:
            row = self._pending_input
            if event.key == pygame.K_RETURN:
                self._commit_input(row)
            elif event.key == pygame.K_ESCAPE:
                self._cancel_input()
            elif event.key == pygame.K_BACKSPACE:
                row.text = row.text[:-1]
            elif event.unicode and event.unicode.isprintable():
                row.text += event.unicode
            return True

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        pos = event.pos

        local_pos = (
            pos[0] - self._panel_x,
            pos[1] - self._panel_y + self._scroll_y
        )

        # ── click outside active edit row → cancel ────────────────────────────
        if self._pending_edit:
            row = self._pending_edit
            if row.rect and not row.rect.move(offset).collidepoint(local_pos):
                self._cancel_edit()
                return True

        # ── click outside active input → cancel ───────────────────────────────
        if self._pending_input:
            row = self._pending_input
            if row.rect and not row.rect.move(offset).collidepoint(local_pos):
                self._cancel_input()
                return True

        # ── hit-test each row ─────────────────────────────────────────────────
        for row in self._rows:
            if isinstance(row, _AddButton):
                if row.rect and row.rect.move(offset).collidepoint(local_pos):
                    self._start_input(row.kind, row.tag_name)
                    return True

            elif isinstance(row, _InputRow):
                pass  # focus handled above

            elif isinstance(row, _EditRow):
                pass  # focus handled above

            elif isinstance(row, _ParentRow):
                if row.minus_rect and row.minus_rect.move(offset).collidepoint(local_pos):
                    self._remove_tag(row.tag_name)
                    return True

            elif isinstance(row, _ChildRow):
                if self.gm.tags_editor:
                    if row.minus_rect and row.minus_rect.move(offset).collidepoint(local_pos):
                        self._remove_info(row.tag_name, row.info_key)
                        return True
                else:
                    # View mode: click the child row to edit its value
                    if row.rect and row.rect.move(offset).collidepoint(local_pos):
                        self._start_edit(row.tag_name, row.info_key, row.info_val)
                        return True

        return False

    def handle_motion(self, event: pygame.event.Event, offset: tuple):
        """Call from GroupsManager to update child hover states."""
        if event.type != pygame.MOUSEMOTION:
            return
        pos = event.pos

        local_pos = (
            pos[0] - self._panel_x,
            pos[1] - self._panel_y + self._scroll_y
        )
        for row in self._rows:
            if isinstance(row, _ChildRow):
                row.hover = bool(row.rect and row.rect.move(offset).collidepoint(local_pos))

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            try:
                self._font = self.gm.buttons_font
            except AttributeError:
                self._font = pygame.font.SysFont(None, 20)
        return self._font

    def _rebuild_rows(self):
        """Re-read data and rebuild the flat row list."""
        self._rows = []
        editor = self.gm.tags_editor
        group_id = self.gm.current_group

        if editor:
            # Editor mode: show all known tags from tags.json,
            # with per-group info values merged in.
            import os, json
            tags_path = "data/tags.json"
            all_tags: dict = {}
            if os.path.exists(tags_path):
                with open(tags_path) as f:
                    all_tags = json.load(f)

            group_tags: dict = (self.gm.editor.tilemap.tag_groups
                                .get(group_id, {})
                                .get("tags", {}))

            color_idx = 0
            for tag_name, tag_infos in all_tags.items():
                color = _PARENT_COLORS[color_idx % len(_PARENT_COLORS)]
                color_idx += 1

                group_vals = group_tags.get(tag_name, {})
                self._rows.append(_ParentRow(tag_name, color))

                for info_key, _ in tag_infos.items():
                    val = group_vals.get(info_key, "")
                    self._rows.append(_ChildRow(tag_name, info_key, val))
                    # inject edit sibling if one is active for this cell
                    if (self._pending_edit
                            and self._pending_edit.tag_name == tag_name
                            and self._pending_edit.info_key == info_key):
                        self._rows.append(self._pending_edit)

                # "add info" button (or live input row) for this tag
                if (self._pending_input
                        and self._pending_input.kind == "info"
                        and self._pending_input.tag_name == tag_name):
                    self._rows.append(self._pending_input)
                else:
                    self._rows.append(_AddButton("info", tag_name))

        else:
            # View mode: only show tags that belong to current group.
            group_tags: dict = (self.gm.editor.tilemap.tag_groups
                                .get(group_id, {})
                                .get("tags", {}))
            color_idx = 0
            for tag_name, tag_infos in group_tags.items():
                color = _PARENT_COLORS[color_idx % len(_PARENT_COLORS)]
                color_idx += 1
                self._rows.append(_ParentRow(tag_name, color))
                for info_key, info_val in tag_infos.items():
                    self._rows.append(_ChildRow(tag_name, info_key, info_val))
                    # inject edit sibling if one is active for this cell
                    if (self._pending_edit
                            and self._pending_edit.tag_name == tag_name
                            and self._pending_edit.info_key == info_key):
                        self._rows.append(self._pending_edit)

        # "add tag" button (or live input row) at bottom
        if self._pending_input and self._pending_input.kind == "tag":
            self._rows.append(self._pending_input)
        else:
            self._rows.append(_AddButton("tag"))

    def _measure_height(self) -> int:
        """Estimate total pixel height without drawing."""
        return len(self._rows) * (ROW_H + GAP)

    # ── input flow ────────────────────────────────────────────────────────────

    def _start_input(self, kind: str, tag_name: str = ""):
        self._cancel_edit()   # close any open edit row
        self._pending_input = _InputRow(kind, tag_name)
        self._dirty = True

    def _cancel_input(self):
        self._pending_input = None
        self._dirty = True

    def _commit_input(self, row: _InputRow):
        name = row.text.strip()
        editor = self.gm.tags_editor
        if not name:
            self._cancel_input()
            return

        if row.kind == "tag":
            self.gm.create_tag(name)
            infos = self.gm.get_tag_infos(name) or {}
            if not editor:
                self.gm.add_tag_to_group(self.gm.current_group, {name: {k: "" for k in infos}})

        elif row.kind == "info":
            self.gm.create_info(row.tag_name, name)
            for gid in self.gm.editor.tilemap.tag_groups:
                self.gm.update_group_tags(gid)

        self._pending_input = None
        self._dirty = True

    # ── edit flow ─────────────────────────────────────────────────────────────

    def _start_edit(self, tag_name: str, info_key: str, current_val: str):
        self._cancel_input()  # close any open input row
        self._pending_edit = _EditRow(tag_name, info_key, current_val)
        self._dirty = True

    def _cancel_edit(self):
        self._pending_edit = None
        self._dirty = True

    def _commit_edit(self, row: _EditRow):
        self.gm.set_info_value(self.gm.current_group, row.tag_name, row.info_key, row.text)
        self._pending_edit = None
        self._dirty = True

    # ── deletion ──────────────────────────────────────────────────────────────

    def _remove_tag(self, tag_name: str):
        """Remove tag from global schema AND all groups."""
        editor = self.gm.tags_editor
        if editor:
            self.gm.delete_tag(tag_name)
            for gid, group in self.gm.editor.tilemap.tag_groups.items():
                if tag_name in group.get("tags", {}):
                    group["tags"].pop(tag_name)
        else:
            group = self.gm.current_group
            self.gm.remove_tag_from_group(group, tag_name)
        self._dirty = True

    def _remove_info(self, tag_name: str, info_key: str):
        """Remove an info field from the global tag schema (cascades via delete_info)."""
        self.gm.delete_info(tag_name, info_key)
        self._dirty = True