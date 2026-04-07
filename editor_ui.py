import sys

from io import TextIOWrapper
from scripts.game import Game
from scripts.physics import PhysicsPlayer

from scripts.button import EditorButton, LevelCarousel, IconButton, TextButton, ParentButton
from scripts.text import load_game_font
from scripts.utils import *
from scripts.tilemap import Tilemap
import pygame

import os
import copy
import json
import shutil
import re

class EditorCameraSetup:

    HANDLE_SIZE = 8  # pixels around border that trigger resize

    def __init__(self, editor_instance):
        self.editor = editor_instance
        self.cursor_pos = list(editor_instance.mpos_scaled)
        self.tile_size = editor_instance.tilemap.tile_size
        self.initial_cursor_pos = self.cursor_pos
        self.cursor_rect = pygame.Rect(self.cursor_pos[0], self.cursor_pos[1], 0, 0)
        self.cameras = editor_instance.tilemap.camera_zones
        self.creating = False
        self.clicking = False

        # Resize state
        self.resizing = False
        self.resize_index = None      # index in self.cameras being resized
        self.resize_edges = None      # tuple of active edges e.g. ('left', 'top')
        self.resize_origin = None     # world-space rect before drag started
        self.resize_mouse_origin = None  # mouse world pos when drag started

    # ------------------------------------------------------------------ helpers

    def _screen_to_world(self, screen_pos):
        return [self.tile_size*((screen_pos[0] + self.editor.scroll[0])//self.tile_size),
                self.tile_size*((screen_pos[1] + self.editor.scroll[1])//self.tile_size)]

    def _get_rect(self, camera_str):
        x, y, w, h = (int(v) for v in camera_str.split(";"))
        return pygame.Rect(x, y, w, h)

    def _rect_to_str(self, rect):
        return f"{rect.x};{rect.y};{rect.width};{rect.height}"

    def _get_edges(self, world_rect, world_mouse):
        mx, my = world_mouse
        hs = self.HANDLE_SIZE

        left = world_rect.left
        right = world_rect.left + world_rect.width - hs - 1
        top = world_rect.top
        bottom = world_rect.top + world_rect.height - hs - 1


        near_left = left - hs < mx < left + hs
        near_right = right - hs < mx < right + hs
        near_top = top - hs < my < top + hs
        near_bottom = bottom - hs < my < bottom + hs

        in_x = left - hs < mx < right + hs
        in_y = top - hs < my < bottom + hs

        edges = []
        if near_left and in_y: edges.append('left')
        if near_right and in_y: edges.append('right')
        if near_top and in_x: edges.append('top')
        if near_bottom and in_x: edges.append('bottom')
        return tuple(edges) if edges else None

    def _edges_to_cursor(self, edges):
        """Map edge tuple to a pygame system cursor."""
        if not edges:
            return pygame.SYSTEM_CURSOR_ARROW
        has_lr = 'left'  in edges or 'right'  in edges
        has_tb = 'top'   in edges or 'bottom' in edges
        if has_lr and has_tb:
            # corner — pick diagonal based on which corner
            if ('left' in edges and 'top' in edges) or ('right' in edges and 'bottom' in edges):
                return pygame.SYSTEM_CURSOR_SIZENWSE
            return pygame.SYSTEM_CURSOR_SIZENESW
        if has_lr:
            return pygame.SYSTEM_CURSOR_SIZEWE
        return pygame.SYSTEM_CURSOR_SIZENS

    def _apply_resize(self, world_mouse):
        dx = world_mouse[0] - self.resize_mouse_origin[0]
        dy = world_mouse[1] - self.resize_mouse_origin[1]

        r = self.resize_origin.copy()

        if 'left' in self.resize_edges:
            new_left = r.left + dx
            new_width = r.right - new_left
            if new_width > self.tile_size:
                r.left = new_left
                r.width = new_width

        if 'right' in self.resize_edges:
            new_width = r.width + dx
            if new_width > self.tile_size:
                r.width = new_width


        if 'top' in self.resize_edges:
            new_top = r.top + dy
            new_height = r.bottom - new_top
            if new_height > self.tile_size:
                r.top = new_top
                r.height = new_height

        if 'bottom' in self.resize_edges:
            new_height = r.height + dy
            if new_height > self.tile_size:
                r.height = new_height

        self.cameras[self.resize_index] = self._rect_to_str(r)

    def _get_selected_zone(self):
        for zone in self.cameras:
            x, y, w, h = (int(v) for v in zone.split(";"))
            left, right, bottom, top = x, x+w, y+h, y
            mx, my = tuple(self._screen_to_world(self.editor.mpos_scaled))
            if left < mx < right and top < my < bottom:
                return zone
        return None

    # ------------------------------------------------------------------ public

    def create_zone(self, rect_str):
        self.editor.tilemap.camera_zones.append(rect_str)

    def rect_pos_update(self):
        self.cursor_pos = [
            self.tile_size * (int(self.editor.mpos_scaled[0] + self.editor.scroll[0]) // self.tile_size),
            self.tile_size * (int(self.editor.mpos_scaled[1] + self.editor.scroll[1]) // self.tile_size)
        ]
        distx = self.cursor_pos[0] - self.initial_cursor_pos[0]
        disty = self.cursor_pos[1] - self.initial_cursor_pos[1]
        left = self.initial_cursor_pos[0]
        top  = self.initial_cursor_pos[1]
        if distx < 0: left = self.cursor_pos[0]
        if disty < 0: top  = self.cursor_pos[1]
        self.cursor_rect = pygame.Rect(left, top, abs(distx), abs(disty))

    def update(self):
        """Call once per frame to handle resize dragging & cursor icon."""
        self.rect_pos_update()
        self.cameras = self.editor.tilemap.camera_zones
        world_mouse = self._screen_to_world(self.editor.mpos_scaled)

        if self.resizing:
            self._apply_resize(world_mouse)
            return  # skip cursor-hover logic while dragging

        # Hover: find the first zone whose edge the mouse is near
        hovered_edges = None
        for camera in self.cameras:
            wrect = self._get_rect(camera)
            edges = self._get_edges(wrect, world_mouse)
            if edges:
                hovered_edges = edges
                break

        pygame.mouse.set_cursor(self._edges_to_cursor(hovered_edges))

    def draw(self, surface):
        if self.creating:
            overlay = pygame.Surface(self.cursor_rect.size)
            overlay.fill((50, 50, 100))
            surface.blit(overlay, (
                self.cursor_rect.left - self.editor.scroll[0],
                self.cursor_rect.top  - self.editor.scroll[1]
            ))

        for i, camera in enumerate(self.cameras):
            x, y, w, h = (int(v) for v in camera.split(";"))
            zone_rect = pygame.Rect(
                x - self.editor.scroll[0],
                y - self.editor.scroll[1], w, h
            )
            color = ((150*(x+1)) % 255, (30*y*h) % 255, (30*w) % 255)
            overlay = create_rect_alpha(color, zone_rect, 50)
            surface.blit(overlay, (zone_rect.x, zone_rect.y))
            pygame.draw.rect(surface, color, zone_rect, 5)

            # Draw resize handles as small squares on the border
            hs = self.HANDLE_SIZE
            handle_color = (255, 255, 100) if i == self.resize_index else (200, 200, 200)
            for hx, hy in [
                (zone_rect.left,               zone_rect.top),
                (zone_rect.centerx - hs // 2,  zone_rect.top),
                (zone_rect.right - hs,          zone_rect.top),
                (zone_rect.left,               zone_rect.centery - hs // 2),
                (zone_rect.right - hs,          zone_rect.centery - hs // 2),
                (zone_rect.left,               zone_rect.bottom - hs),
                (zone_rect.centerx - hs // 2,  zone_rect.bottom - hs),
                (zone_rect.right - hs,          zone_rect.bottom - hs),
            ]:
                pygame.draw.rect(surface, handle_color, (hx, hy, hs, hs))

    def handle_event(self, event):
        world_mouse = self._screen_to_world(self.editor.mpos_scaled)
        if not self.editor.ui.toolbar_rect.collidepoint(self.editor.mpos):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if we're clicking a resize handle before starting creation
                for i, camera in enumerate(self.cameras):
                    wrect = self._get_rect(camera)
                    edges = self._get_edges(wrect, world_mouse)
                    if edges:
                        self.resizing = True
                        self.resize_index = i
                        self.resize_edges = edges
                        self.resize_origin = wrect.copy()
                        self.resize_mouse_origin = list(world_mouse)
                        return   # consume event — don't start a new zone

                # No handle hit → normal zone creation
                self.creating = True
                self.initial_cursor_pos = self.cursor_pos.copy()

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.clicking = False
                    if self.resizing:
                        self.editor._save_action()   # push undo snapshot after resize
                        self.resizing = False
                        self.resize_index = None
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                        return

                    if self.creating and self.cursor_rect.width and self.cursor_rect.height:
                        current_state = self.editor._create_snapshot()
                        if current_state != self.editor.temp_snapshot:
                            self.editor._save_action()
                        rect_str = f"{self.cursor_rect.x};{self.cursor_rect.y};{self.cursor_rect.width};{self.cursor_rect.height}"
                        self.create_zone(rect_str)
                    self.creating = False
                if event.button == 3:
                    deleted_zone = self._get_selected_zone()
                    if deleted_zone:
                        self.editor.tilemap.camera_zones.remove(deleted_zone)

class Selector:
    BASE_GROUP = {"tiles": [],
                  "tags": {},
                  "flags":{
                      "AutoTile": True,
                      "Matched": False,
                      "Global": False},
                  "matches":{}
                  }
    def __init__(self, editor_instance):
        self.editor = editor_instance
        self.pos = self.editor.mpos_scaled
        self.initial_pos = self.pos
        self.rect = pygame.Rect(self.pos[0], self.pos[1], 0, 0)
        self.rect_displayed = False
        self.link = []
        self.link_pivot = None

    def get_coordinates_in_rect(self, rect):
        grid = []
        for x in range(rect.left//self.editor.tile_size, rect.right//self.editor.tile_size + 1):
            for y in range(rect.top//self.editor.tile_size, rect.bottom//self.editor.tile_size + 1):
                grid.append(f"{x};{y}")

        return grid

    def get_link_pivot(self, link):
        left, right, top, bottom = (float(link[0].split(";")[0]), float(link[0].split(";")[0]), float(link[0].split(";")[1]), float(link[0].split(";")[1]))
        for loc in link:
            pos = [float(coord) for coord in loc.split(";")]
            if pos[0] < left:
                left = pos[0]
            elif pos[0] > right:
                right = pos[0]

            if pos[1] < top:
                top = pos[1]
            elif pos[1] > bottom:
                bottom = pos[1]

        return [(right+left)/2, (top+bottom)/2]

    def draw(self, surface):
        if self.rect_displayed:
            overlay = pygame.Surface(self.rect.size)
            overlay.fill((10,10,100))
            surface.blit(overlay, (self.rect.left - self.editor.scroll[0], self.rect.top - self.editor.scroll[1]))

    def rect_pos_update(self):
        self.pos = [self.editor.mpos_scaled[0] + self.editor.scroll[0],
                    self.editor.mpos_scaled[1] + self.editor.scroll[1]]
        distx = self.pos[0] - self.initial_pos[0]
        disty = self.pos[1] - self.initial_pos[1]
        left = self.initial_pos[0]
        top = self.initial_pos[1]
        if distx < 0:
            left = self.pos[0]
        if disty < 0:
            top = self.pos[1]
        self.rect = pygame.Rect(left,
                                top,
                                abs(distx),
                                abs(disty))

    def tile_has_link(self, tile_pos):
        if self.editor.ignore_links:
            return []
        if self.editor.current_layer in self.editor.tilemap.links:
            for group in self.editor.tilemap.links[self.editor.current_layer]:
                if tile_pos in group:
                    return group
        return []

    def get_link_in_rect(self, rect, check_offgrid=True):
        link = []
        ongrid = self.get_coordinates_in_rect(rect)
        for tile_pos in ongrid:
            if tile_pos in self.editor.tilemap.tilemap[self.editor.current_layer]:
                tile_link = self.tile_has_link(tile_pos)
                if tile_link:
                    if not set(tile_link).issubset(set(link)):
                        link += tile_link
                else:
                    link.append(tile_pos)

        if check_offgrid and self.editor.current_layer in self.editor.tilemap.offgrid_tiles:
            for tile_pos in self.editor.tilemap.offgrid_tiles[self.editor.current_layer]:
                pos = [float(val) for val in tile_pos.split(";")]
                if (rect.left <= pos[0] <= rect.right and
                        rect.top <= pos[1] <= rect.bottom):
                    tile_link = self.tile_has_link(tile_pos)
                    if tile_link:
                        if not set(tile_link).issubset(set(link)):
                            link += tile_link
                    else:
                        link.append(tile_pos)

        if link:
            self.link_pivot = self.get_link_pivot(link)
        else:
            self.link_pivot = None

        return link

    def delete_link(self):
        if self.link:
            for tile_loc in self.link:
                space = self.editor.check_tile_space(tile_loc)
                if space == "tilemap":
                    del self.editor.tilemap.tilemap[self.editor.current_layer][tile_loc]
                else:
                    del self.editor.tilemap.offgrid_tiles[self.editor.current_layer][tile_loc]
            self.link = []

    def unlink_link(self, link):
        current_layer = self.editor.current_layer
        tilemap = self.editor.tilemap

        tilemap.links[current_layer].remove(link)
        if not tilemap.links[current_layer]:
            del tilemap.links[current_layer]

    def link_link(self):
        current_layer = self.editor.current_layer

        if current_layer in self.editor.tilemap.links:
            groups = self.editor.tilemap.links[current_layer]
            for group in groups:
                if set(group).issubset(set(self.link)) and group != self.link:
                    self.unlink_link(group)
        else:
            self.editor.tilemap.links[current_layer] = []

        if current_layer not in self.editor.tilemap.links:
            self.editor.tilemap.links[current_layer] = []
        self.editor.tilemap.links[current_layer].append(self.link.copy())

    def add_link_to_group(self, group_id:str):
        for tile_loc in self.link:
            if group_id not in self.editor.tilemap.tag_groups:
                self.editor.tilemap.tag_groups[group_id] = self.BASE_GROUP
            self.editor.tilemap.tag_groups[group_id]["tiles"].append([tile_loc, self.editor.current_layer])

    def rotate_link_90(self):
        """Rotate selector.link 90° clockwise around its centroid, in-place."""
        if not self.link:
            return

        pivot = self.get_link_pivot(self.link)
        cx, cy = pivot  # these are always in tile units from get_link_pivot

        tilemap_tmp = {}
        offgrid_tmp = {}

        # 0. Check if no block will be overlapped
        for loc in self.link:
            pos = [float(v) for v in loc.split(";")]
            space = self.editor.check_tile_space(loc)

            if space == "tilemap":
                cx = round(cx)
                cy = round(cy)
                dx = pos[0] - cx
                dy = pos[1] - cy
                new_x = int(cx - dy)
                new_y = int(cy + dx)
                new_loc = f"{new_x};{new_y}"
                if new_loc in self.editor.tilemap.tilemap[self.editor.current_layer] and new_loc not in self.link:
                    print("Rotation blocked: collision on grid.")
                    return

            elif space == "offgrid":
                pcx = cx
                pcy = cy
                dx = pos[0] - pcx
                dy = pos[1] - pcy
                new_x = pcx - dy
                new_y = pcy + dx
                new_loc = f"{new_x};{new_y}"
                if new_loc in self.editor.tilemap.offgrid_tiles[self.editor.current_layer] and new_loc not in self.link:
                    print("Rotation blocked: collision off grid.")
                    return

        # 1. Pull all tiles out
        for loc in self.link:

            space = self.editor.check_tile_space(loc)
            if space == "tilemap":
                tilemap_tmp[loc] = self.editor.tilemap.tilemap[self.editor.current_layer].pop(loc)
            elif space == "offgrid":
                offgrid_tmp[loc] = self.editor.tilemap.offgrid_tiles[self.editor.current_layer].pop(loc)

        new_link = []
        old_to_new = {}

        # 2. Compute rotated positions and write back
        for loc in self.link:
            pos = [float(v) for v in loc.split(";")]

            if loc in tilemap_tmp:
                # Tile coords: rotate 90° clockwise around pivot
                cx = round(cx)
                cy = round(cy)
                dx = pos[0] - cx
                dy = pos[1] - cy
                new_x = int(cx - dy)
                new_y = int(cy + dx)
                new_loc = f"{new_x};{new_y}"
                packed = tilemap_tmp[loc]
                tile_id, variant, rot, flip_h, flip_v = self.editor.tilemap.tile_manager.unpack_tile(packed)
                new_rot = (rot + 1) % 4
                self.editor.tilemap.tilemap[self.editor.current_layer][new_loc] = \
                    self.editor.tilemap.tile_manager.pack_tile(tile_id, variant, new_rot, flip_h, flip_v)
                self.editor.update_group_tile(loc, new_loc, self.editor.current_layer)

            else:  # offgrid — pixel coords
                # Pivot is in tile units, convert to pixels for the rotation
                pcx = cx
                pcy = cy
                dx = pos[0] - pcx
                dy = pos[1] - pcy
                new_x = pcx - dy
                new_y = pcy + dx
                new_loc = f"{new_x};{new_y}"
                packed = offgrid_tmp[loc]
                tile_id, variant, rot, flip_h, flip_v = self.editor.tilemap.tile_manager.unpack_tile(packed)
                new_rot = (rot + 1) % 4
                if self.editor.current_layer not in self.editor.tilemap.offgrid_tiles:
                    self.editor.tilemap.offgrid_tiles[self.editor.current_layer] = {}
                self.editor.tilemap.offgrid_tiles[self.editor.current_layer][new_loc] = \
                    self.editor.tilemap.tile_manager.pack_tile(tile_id, variant, new_rot, flip_h, flip_v)
                self.editor.update_group_tile(loc, new_loc, self.editor.current_layer)

            old_to_new[loc] = new_loc
            new_link.append(new_loc)

        # 3. Update links groups
        if self.editor.current_layer in self.editor.tilemap.links:
            updated_groups = []
            for group in self.editor.tilemap.links[self.editor.current_layer]:
                updated_groups.append([old_to_new.get(t, t) for t in group])
            self.editor.tilemap.links[self.editor.current_layer] = updated_groups

        self.link = new_link
        self.link_pivot = self.get_link_pivot(new_link)

    def copy_link(self):
        """Copy the current selector.link into the clipboard."""
        if not self.link:
            return

        clipboard_ongrid = {}
        clipboard_offgrid = {}
        pivot = self.get_link_pivot(self.link)

        for loc in self.link:
            space = self.editor.check_tile_space(loc)
            if space == "tilemap":
                clipboard_ongrid[loc] = self.editor.tilemap.tilemap[self.editor.current_layer][loc]
            elif space == "offgrid":
                clipboard_offgrid[loc] = self.editor.tilemap.offgrid_tiles[self.editor.current_layer][loc]

        self.clipboard = {
            "ongrid": copy.deepcopy(clipboard_ongrid),
            "offgrid": copy.deepcopy(clipboard_offgrid),
            "pivot": pivot,  # tile-unit centroid of the original group
        }
        print(f"Copied {len(self.link)} tiles to clipboard.")

    def paste_link(self):
        """Paste the clipboard at the current mouse position."""
        if not self.clipboard:
            return

        pivot = self.clipboard["pivot"]  # [cx, cy] in tile units

        if self.editor.ongrid:
            # Target anchor = current tile_pos
            target_cx = self.editor.tile_pos[0]
            target_cy = self.editor.tile_pos[1]
            dx = target_cx - pivot[0]
            dy = target_cy - pivot[1]

            new_locs = []
            for loc, packed in self.clipboard["ongrid"].items():
                pos = [float(v) for v in loc.split(";")]
                new_x = int(pos[0] + dx)
                new_y = int(pos[1] + dy)
                new_loc = f"{new_x};{new_y}"
                # Collision check
                if new_loc in self.editor.tilemap.tilemap[self.editor.current_layer]:
                    print("Paste blocked: collision on grid.")
                    return
                new_locs.append((new_loc, packed))

            for loc, packed in self.clipboard["offgrid"].items():
                pos = [float(v) for v in loc.split(";")]
                new_x = int(pos[0] + dx * self.editor.tile_size)
                new_y = int(pos[1] + dy * self.editor.tile_size)
                new_loc = f"{new_x};{new_y}"
                new_locs.append((new_loc, packed))

            pasted_link = []
            for new_loc, packed in new_locs:
                self.editor.tilemap.tilemap[self.editor.current_layer][new_loc] = packed
                pasted_link.append(new_loc)

        else:
            # Off-grid paste: anchor to pixel mouse position
            target_px = self.editor.mpos_scaled[0] + self.editor.scroll[0]
            target_py = self.editor.mpos_scaled[1] + self.editor.scroll[1]
            pivot_px = pivot[0] * self.editor.tile_size
            pivot_py = pivot[1] * self.editor.tile_size
            dx_px = target_px - pivot_px
            dy_px = target_py - pivot_py

            pasted_link = []
            if self.editor.current_layer not in self.editor.tilemap.offgrid_tiles:
                self.editor.tilemap.offgrid_tiles[self.editor.current_layer] = {}

            for loc, packed in self.clipboard["ongrid"].items():
                pos = [float(v) for v in loc.split(";")]
                new_x = pos[0] * self.editor.tile_size + dx_px
                new_y = pos[1] * self.editor.tile_size + dy_px
                new_loc = f"{new_x};{new_y}"
                self.editor.tilemap.offgrid_tiles[self.editor.current_layer][new_loc] = packed
                pasted_link.append(new_loc)

            for loc, packed in self.clipboard["offgrid"].items():
                pos = [float(v) for v in loc.split(";")]
                new_x = pos[0] + dx_px
                new_y = pos[1] + dy_px
                new_loc = f"{new_x};{new_y}"
                self.editor.tilemap.offgrid_tiles[self.editor.current_layer][new_loc] = packed
                pasted_link.append(new_loc)

        self.link = pasted_link
        self.link_pivot = self.get_link_pivot(pasted_link)
        print(f"Pasted {len(pasted_link)} tiles.")

    def remove_link_from_group(self, group_id:str):
        for tile_loc in self.link:
            if [tile_loc, self.editor.current_layer] in self.editor.tilemap.tag_groups[group_id]["tiles"]:
                self.editor.tilemap.tag_groups[group_id]["tiles"].remove([tile_loc, self.editor.current_layer])
            if self.editor.tilemap.tag_groups[group_id]["tiles"] == self.BASE_GROUP["tiles"] and self.editor.tilemap.tag_groups[group_id]["tags"] == self.BASE_GROUP["tags"]:
                del self.editor.tilemap.tag_groups[group_id]
                break

    def get_link_groups(self):
        groups = {"common": [], "uncommon": []}

        for group_id, group_data in self.editor.tilemap.tag_groups.items():
            group_positions = {tile[0] for tile in group_data["tiles"]}
            link_set = set(self.link)

            if link_set.issubset(group_positions):
                groups["common"].append(group_id)
            elif group_positions & link_set:
                groups["uncommon"].append(group_id)

        return groups

    def handle_selection_rect(self, event):
        if not(self.editor.ui.toolbar_rect.collidepoint(self.editor.mpos)
                or self.editor.ui.assets_section_rect.collidepoint(self.editor.mpos)):
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 :
                    button_collision = False
                    for button in self.editor.ui.on_selection_buttons:
                        if button.rect.collidepoint(self.editor.mpos):
                            button_collision = True
                    if not self.rect_displayed and not button_collision:
                        self.rect_displayed = True
                        self.initial_pos = self.pos

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.rect_displayed:
                    self.rect_displayed = False
                    group = self.get_link_in_rect(self.rect)
                    if group:
                        self.link = list(set(self.link) | (set(group)))
                    else:
                        self.link = []

        self.rect_pos_update()

    def handle_event(self, event):
        if event:
            self.handle_selection_rect(event)

class EditorLevelManager:
    def __init__(self, editor_instance):
        self.editor = editor_instance

    def get_file_name(self, map_id):
        return f"{map_id:03d}.json"

    def get_next_file_id(self):
        existing_ids = []
        # 1. Look at actual files on disk
        if os.path.exists('data/maps/'):
            for f in os.listdir('data/maps/'):
                if f.endswith('.json'):
                    match = re.search(r'\d+', f)
                    if match:
                        existing_ids.append(int(match.group()))

        if not existing_ids:
            return 1
        return max(existing_ids) + 1

    def delete_map(self, level_id):
        # Remove ONLY from active maps. We leave it in editor.environments
        # so environments.json retains it if the user quits without a full_save.
        if level_id in self.editor.active_maps:
            self.editor.active_maps.remove(level_id)

        # Re-route the user to an existing level if they deleted the one they are on
        if self.editor.level_id == level_id:
            if self.editor.active_maps:
                self.change_level(self.editor.active_maps[-1])
            else:
                # Fallback if they deleted the very last map
                new_id = self.get_next_file_id()
                self.editor.active_maps.append(new_id)
                self.change_level(new_id)

    def map_data_reset(self):
        file_name = self.get_file_name(self.editor.level_id)
        filepath = f'data/maps/{file_name}'

        try:
            self.editor.tilemap.load(filepath)
        except FileNotFoundError:
            if not os.path.exists('data/maps/'):
                os.makedirs('data/maps/')
            with open(filepath, 'w') as f:
                f: TextIOWrapper
                json.dump({'tilemap': {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}, "5": {}, "6": {}},
                           'tilesize': 16, 'offgrid': {}}, f)
            self.editor.tilemap.load(filepath)

        self.editor.reload()

    def change_level(self, new_level_id):
        # Save current level before moving to the next
        if self.editor.level_id in self.editor.active_maps:
            current_file_name = self.get_file_name(self.editor.level_id)

            if self.editor.tilemap.tilemap != {"0": {}, "1": {}, "2": {}, "3": {}, "4": {}, "5": {}, "6": {}}:
                self.editor.tilemap.save(f'data/maps/{current_file_name}')

        self.editor.level_id = new_level_id
        self.map_data_reset()

    def load_level(self):
        self.editor.playtest.level_id = self.editor.level_id
        self.editor.playtest.level = f"{self.editor.level_id:03d}"
        self.editor.playtest.tilemap = self.editor.tilemap.copy(self.editor.playtest)
        self.editor.playtest.player = PhysicsPlayer(self.editor.playtest, self.editor.playtest.tilemap, self.editor.player_start, (16, 16))

        self.editor.playtest.levers = []
        self.editor.playtest.doors = []
        self.editor.playtest.spikes = []
        self.editor.playtest.fake_tiles = []
        self.editor.playtest.pickups = []
        self.editor.playtest.leaf_spawners = []
        self.editor.playtest.camera_zones = []
        for group_id in self.editor.playtest.tilemap.tag_groups:
            group = self.editor.playtest.tilemap.tag_groups[group_id]
            group_tags = group["tags"]
            match group_tags:
                case _ if "lever" in group_tags:
                    tag = group_tags["lever"]
                    for tile_loc, tile_layer in group["tiles"]:
                        self.editor.playtest.tilemap.extract(tile_loc, tile_layer)
                        #self.editor.playtest.levers.append(Lever(group_id, tile_pos, tag["target_group"]))
                        pass
                case _ if "door" in group_tags:
                    pass
                case _ if "spike" in group_tags:
                    pass
                case _ if "fake_tile" in group_tags:
                    pass

            # Set scroll on player spawn position at the very start (before any save), it updates later in load_game function in saving.py

        for zone in self.editor.playtest.tilemap.camera_zones:
            self.editor.playtest.camera_zones.append([int(val) for val in zone.split(";")])

        target_x = self.editor.playtest.player.rect().centerx - self.editor.playtest.display.get_width() / 2
        target_y = self.editor.playtest.player.rect().centery - self.editor.playtest.display.get_height() / 2

        self.editor.playtest.scroll = [target_x, target_y]

        # Reset VFX and interaction pools
        self.editor.playtest.cutscene = False
        self.editor.playtest.particles = []
        self.editor.playtest.sparks = []
        self.editor.playtest.transition = -30
        self.editor.playtest.max_falling_depth = 50000000000
        self.editor.playtest.shader.update_light()

    def full_save(self):
        # 1. Save current map to disk
        if self.editor.level_id in self.editor.active_maps:
            current_file_name = self.get_file_name(self.editor.level_id)
            self.editor.tilemap.save(f'data/maps/{current_file_name}')

        # 2. Re-sequence IDs sequentially for surviving active_maps
        sorted_active = sorted(self.editor.active_maps)
        id_mapping = {old_id: (index + 1) for index, old_id in enumerate(sorted_active)}

        temp_dir = 'data/maps/temp_save'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # 3. Move valid files to temp directory with new names
        for old_id in sorted_active:
            new_id = id_mapping[old_id]

            old_file = self.get_file_name(old_id)
            new_file = self.get_file_name(new_id)

            src = f'data/maps/{old_file}'
            dst = f'{temp_dir}/{new_file}'

            if os.path.exists(src):
                shutil.copy2(src, dst)

        # 4. Clear old files and replace with temp
        for f in os.listdir('data/maps/'):
            if f.endswith('.json'):
                os.remove(f'data/maps/{f}')

        for f in os.listdir(temp_dir):
            shutil.move(f'{temp_dir}/{f}', f'data/maps/{f}')
        os.rmdir(temp_dir)

        # 5. Update running active maps
        self.editor.active_maps = list(id_mapping.values())
        self.editor.level_id = id_mapping.get(self.editor.level_id, 1)

        print("Full Save Complete: Maps reordered and deleted files removed.")

class PlayTest(Game):
    MENU_STATE = "MENU"
    PLAYING_STATE = "PLAYING"

    def __init__(self, editor_instance):

        # ── 1. Window & display ────────────────────────────────────────────────
        self.editor = editor_instance
        super().__init__()
        self.level_manager = editor_instance.level_manager
        self.tilemap = editor_instance.tilemap.copy(self)
        self.player = PhysicsPlayer(self, self.tilemap, editor_instance.player_start, (16, 16))

        # ── 5. Level & map data ────────────────────────────────────────────────
        self.level_id = editor_instance.level_id
        self.level = f"{self.level_id:03f}"

        self.state = self.PLAYING_STATE

    def _init_display(self):
        self.screen = self.editor.screen
        self.display = self.editor.display
        self.clock = pygame.time.Clock()
        self.debug_mode = False

    def save_game(self, slot=1):
        return False

    def load_game(self, slot=1):
        return False

    def leave(self):
        self.editor.state = "MapEditor"
        self.state = self.PLAYING_STATE
        self.editor.screen = self.screen
        self.editor.screen_width, self.editor.screen_height = self.screen.get_size()
        self.editor.screen = pygame.display.set_mode((self.editor.screen_width, self.editor.screen_height), pygame.RESIZABLE)
        self.editor.ui.reload()
        self.music_sound_manager.stop('title_screen')

    def run(self):
        """
        The main program entry point.
        This function implements a state machine to switch between the Intro, Profile Menu, and Gameplay.
        """
        match self.state:
            case self.MENU_STATE:
                self.menu.draw()
                if self.menu.menu_state == self.menu.TITLE_STATE:
                    self.leave()
            case self.PLAYING_STATE:
                self.main_game_logic()
                self.menu.draw_player_souls()
        self.apply_brightness()
        pygame.display.update()

class EditorSimulation:
    SW = 960
    SH = 600

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Editor")
        self.screen_width = self.SW
        self.screen_height = self.SH
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        self.display = pygame.Surface((self.screen_width / 2, self.screen_height / 2))
        self.clock = pygame.time.Clock()
        self.zoom = 1
        self.scroll = [0, 0]
        self.movement = [0, 0, 0, 0]

        self.current_tool = "Brush"
        self.selecting_environment_mode = False

        # Undo/Redo
        self.history = []
        self.history_index = -1
        self.max_history = 50
        self.temp_snapshot = None

        # EditorLevelManager — doit être créé AVANT d'utiliser active_maps/environments
        self.level_manager = EditorLevelManager(self)

        self.active_maps = []
        for ids in os.listdir("data/maps"):
            self.active_maps.append(int(ids[:-5]))
        self.active_maps.sort()

        self.level_id = self.active_maps[0] if self.active_maps else 1

        self.tile_variant = 0

        self.environments = load_editor_tiles()
        self.categories = {}
        for category_dict in self.environments.values():
            for category_name, category_tiles in category_dict.items():
                if category_name in self.categories:
                    self.categories[category_name].update(category_tiles)
                else:
                    self.categories[category_name] = category_tiles

        self.assets = {}
        for category in self.environments.values():
            for tile in category.values():
                self.assets.update(tile)



        self.tile_type = next(iter(self.environments[next(iter(self.environments))][next(iter(self.environments[next(iter(self.environments))]))]))

        self.showing_all_layers = False
        self.current_layer = "0"
        self.current_category = 0

        self.tilemap = Tilemap(self)

        self.tile_size = self.tilemap.tile_size

        try:
            file_name = self.level_manager.get_file_name(self.level_id)
            filepath = f'data/maps/{file_name}'
            self.tilemap.load(filepath)
        except FileNotFoundError:
            pass

        self.clicking = False
        self.rotation = 0
        self.state = "MapEditor"

        self.mpos = pygame.mouse.get_pos()
        self.main_area_width = self.screen_width
        self.main_area_height = self.screen_height

        scale_x = 960 / (self.screen.get_size()[0])
        scale_y = 600 / (self.screen.get_size()[1])
        self.mpos_scaled = ((self.mpos[0] / 2) * scale_x * self.zoom,
                            (self.mpos[1] / 2) * scale_y * self.zoom)

        self.mpos_scaled_onclick = self.mpos_scaled

        self.mpos_in_mainarea = self.mpos[0] < self.main_area_width and self.mpos[1] < self.main_area_height

        self.ongrid = True

        self.selector = Selector(self)

        self.holding_i = False
        self.holding_b = False
        self.holding_y = False
        self.holding_tab = False
        self.shift = False

        self.moved_link = {"ongrid": {}, "offgrid": {}}
        self.player_start = (100, 0)

        self.ui = UI(self)
        self.camera_setup = EditorCameraSetup(self)
        self.playtest = PlayTest(self)
        self.ignore_links = False
        self.clipboard = None

        self._save_action()

    def update_group_tile(self, old_loc, new_loc, layer):
        for group_id in self.tilemap.tag_groups:
            if [old_loc, layer] in self.tilemap.tag_groups[group_id]["tiles"]:
                self.tilemap.tag_groups[group_id]["tiles"].remove([old_loc, layer])
                self.tilemap.tag_groups[group_id]["tiles"].append([new_loc, layer])

    def _create_snapshot(self):
        # Creates a deep copy of the current map state
        return {
            'tilemap': copy.deepcopy(self.tilemap.tilemap),
            'offgrid': copy.deepcopy(self.tilemap.offgrid_tiles),
            'camera_zones': copy.deepcopy(self.tilemap.camera_zones),
            'selected_link': copy.deepcopy(self.selector.link),
            'links': copy.deepcopy(self.tilemap.links),
        }

    def _restore_snapshot(self, snapshot):
        # 1. Load data
        self.tilemap.tilemap = copy.deepcopy(snapshot['tilemap'])
        self.tilemap.offgrid_tiles = copy.deepcopy(snapshot['offgrid'])
        self.tilemap.camera_zones = copy.deepcopy(snapshot["camera_zones"])
        self.tilemap.links = copy.deepcopy(snapshot['links'])
        self.selector.link = copy.deepcopy(snapshot['selected_link'])

    def _undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self._restore_snapshot(self.history[self.history_index])
            print(f"Undo: Step {self.history_index}")

    def _redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._restore_snapshot(self.history[self.history_index])
            print(f"Redo: Step {self.history_index}")

    def _save_action(self):
        # 1. Create snapshot
        snapshot = self._create_snapshot()

        # 2. If we aren't at the end of history (because we undid), cut the future
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        # 3. Add new state
        self.history.append(snapshot)
        self.history_index += 1

        # 4. Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.history_index -= 1

    def get_categories(self):
        self.current_category = 0
        self.tile_type = next(iter(self.environments[next(iter(self.environments))][next(iter(self.environments[next(iter(self.environments))]))]))

    def get_assets(self):
        self.assets = {}
        self.assets = {}
        for category in self.environments.values():
            for tile in category.values():
                self.assets.update(tile)

    def check_tile_space(self, tile_loc):
        current_layer = self.current_layer
        tilemap = self.tilemap
        if current_layer in tilemap.tilemap:
            if tile_loc in tilemap.tilemap[current_layer]:
                return "tilemap"
        if current_layer in tilemap.offgrid_tiles:
            if tile_loc in tilemap.offgrid_tiles[current_layer]:
                return "offgrid"
        return None

    def reload(self):
        self.scroll = [0, 0]
        self.get_categories()
        self.get_assets()

        self.history = []
        self.history_index = -1
        self.selector.link = []
        self._save_action()  # Save the initial state (Index 0)

    def mpos_update(self):
        self.mpos = pygame.mouse.get_pos()
        self.main_area_width = self.screen_width
        self.main_area_height = self.screen_height
        if self.mpos[0] < self.main_area_width and self.mpos[
            1] < self.main_area_height:  # Only if mouse is over main area
            # Scale mouse position to account for display scaling
            scale_x = 960 / (self.screen.get_size()[0])
            scale_y = 600 / (self.screen.get_size()[1])
            self.mpos_scaled = ((self.mpos[0] / 2) * scale_x * self.zoom,
                                (self.mpos[1] / 2) * scale_y * self.zoom)
            self.tile_pos = (int((self.mpos_scaled[0] + self.scroll[0]) // self.tilemap.tile_size),
                             int((self.mpos_scaled[1] + self.scroll[1]) // self.tilemap.tile_size))
        else:

            # Default values if out of bounds to prevent crash
            self.tile_pos = (0, 0)
            self.mpos_scaled = (0, 0)

        self.tile_pos_onclick = (int((self.mpos_scaled_onclick[0] + self.scroll[0]) // self.tilemap.tile_size),
                             int((self.mpos_scaled_onclick[1] + self.scroll[1]) // self.tilemap.tile_size))
        self.mpos_in_mainarea = self.mpos[0] < self.main_area_width and self.mpos[1] < self.main_area_height

    def move_visual_to(self, tile_pos):
        scale_x = 960 / self.screen.get_size()[0]
        scale_y = 600 / self.screen.get_size()[1]
        pos = [0,0]
        if self.current_layer in self.tilemap.tilemap:
            if tile_pos in self.tilemap.tilemap[self.current_layer]:
                pos = [int(val) for val in tile_pos.split(";")]
        if self.current_layer in self.tilemap.offgrid_tiles:
            if tile_pos in self.tilemap.offgrid_tiles[self.current_layer]:
                pos = [int(float(val)/self.tilemap.tile_size) for val in tile_pos.split(";")]

        self.scroll = list(self.scroll)

        self.scroll[0] = (pos[0] * 16 - self.screen_width * scale_x) // (
                2 * int(2 * self.zoom))
        self.scroll[1] = pos[1] * 16 - self.screen_height * scale_y // (2 * int(2 * self.zoom))

    #TODO: group removed from global_groups when global is unchecked
    def create_tag(self, tag: str):
        filepath = "data/tags.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                tags = json.load(f)
        else:
            tags = {}  # Handle missing file case

        # 2. Modify the data in memory
        # Use .setdefault() to avoid KeyErrors if tile_type doesn't exist yet
        tags[tag] = {}

        # 3. Save the data back
        with open(filepath, "w") as f:
            f: TextIOWrapper
            json.dump(tags, f, indent=4)

    def delete_tag(self, tag: str):
        filepath = "data/tags.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                tags = json.load(f)
        else:
            tags = {tag:{}}  # Handle missing file case

        # 2. Modify the data in memory
        # Use .setdefault() to avoid KeyErrors if tile_type doesn't exist yet
        del tags[tag]

        # 3. Save the data back
        with open(filepath, "w") as f:
            f: TextIOWrapper
            json.dump(tags, f, indent=4)

    def set_info_value(self, group_id: str, tag: str, info: str, value: str):
        self.tilemap.tag_groups[group_id]["tags"][tag][info] = value

    def get_tag_and_infos(self, tag: str) -> dict | bool:
        filepath = "data/tags.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                tags = json.load(f)
                if tag in tags:
                    return tags[tag]
                else:
                    self.create_tag(tag)
                    return {tag:{}}
        else:
            print(f"filepath: {filepath} not found")
        return False

    def add_tag_to_group(self, group_id: str, tag: dict):
        self.tilemap.tag_groups[group_id]["tags"].update(tag)
        if self.tilemap.tag_groups[group_id]["flags"]["Global"]:
            self.update_global_group(group_id)

    def remove_tag_from_group(self, group_id: str, tag_name: str):
        del self.tilemap.tag_groups[group_id]["tags"][tag_name]
        if self.tilemap.tag_groups[group_id]["flags"]["Global"]:
            self.update_global_group(group_id)

    def update_group_tags(self, group_id: str):
        with open("data/tags.json", "r") as f:
            tags = json.load(f)
            for tag_name in self.tilemap.tag_groups[group_id]["tags"]:
                tag = self.tilemap.tag_groups[group_id]["tags"][tag_name]
                if tag.keys() != tags[tag_name].keys():
                    tag.update({info:"" for info in tags[tag_name].keys() if info not in tag.keys()})
        if self.tilemap.tag_groups[group_id]["flags"]["Global"]:
            self.update_global_group(group_id)

    #Tu dois appeller les parents "tags" et les fils "infos"

    '''WHEN PARENT PLUS IS PRESSED
        add_tag_to_group(group_id, get_tag_and_infos(parent_label))'''

    '''WHEN PARENT MINUS IS PRESSED
        remove_tag_from_group(group_id, parent_label)'''

    '''WHEN CHILD PLUS IS PRESSED
        create_info(parent_label, child_label)'''

    '''WHEN CHILD MINUS IS PRESSED
        delete_info(parent_label, child_label)'''



    def create_info(self, tag: str, info: str):
        filepath = "data/tags.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                tags = json.load(f)
        else:
            tags = {}  # Handle missing file case

        # 2. Modify the data in memory
        # Use .setdefault() to avoid KeyErrors if tile_type doesn't exist yet
        tags[tag][info] = ""

        # 3. Save the data back
        with open(filepath, "w") as f:
            f: TextIOWrapper
            json.dump(tags, f, indent=4)

    def delete_info(self, tag: str, info: str):
        filepath = "data/tags.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                tags = json.load(f)
        else:
            tags = {tag:{info:""}}  # Handle missing file case

        # 2. Modify the data in memory
        # Use .setdefault() to avoid KeyErrors if tile_type doesn't exist yet
        del tags[tag][info]

        # 3. Save the data back
        with open(filepath, "w") as f:
            f: TextIOWrapper
            json.dump(tags, f, indent=4)

        for group_id in self.tilemap.tag_groups:
            self.update_group_tags(group_id)

    def update_global_group(self, group_id):
        # GLOBAL GROUPS SAVE
        filepath = "data/global_groups.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                global_groups = json.load(f)
        else:
            global_groups = {}  # Handle missing file case


        global_groups[group_id] = self.tilemap.tag_groups[group_id].copy()
        global_groups[group_id]["tiles"] = []

        # 3. Save the data back
        with open(filepath, "w") as g:
            g: TextIOWrapper
            json.dump(global_groups, g, indent=4)  # indent=4 makes it human-readable

    def remove_global_group(self, group_id):
        # GLOBAL GROUPS SAVE
        filepath = "data/global_groups.json"

        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                global_groups = json.load(f)
        else:
            global_groups = {}  # Handle missing file case

        if group_id in global_groups:
            del global_groups[group_id]

        # 3. Save the data back
        with open(filepath, "w") as g:
            g: TextIOWrapper
            json.dump(global_groups, g, indent=4)  # indent=4 makes it human-readable

    def toggle_group_global(self, group_id):
        self.tilemap.tag_groups[group_id]["flags"]["Global"] = not self.tilemap.tag_groups[group_id]["flags"]["Global"]
        if self.tilemap.tag_groups[group_id]["flags"]["Global"]:
            self.update_global_group(group_id)
        else:
            self.remove_global_group(group_id)



    def handle_brush_tool(self):
        self.selector.link = []
        self.moved_link = {"ongrid":{}, "offgrid":{}}
        if self.clicking:
            t = self.tile_type
            t_id = self.tilemap.tile_manager.get_id(t)
            t_groups = self.tilemap.tile_manager.tiles[t_id].groups
            if self.ongrid:
                tile_loc = str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])
                self.tilemap.tilemap[self.current_layer][tile_loc] = (
                    self.tilemap.tile_manager.pack_tile(t_id, self.tile_variant, self.rotation))

            else:
                if self.current_layer not in self.tilemap.offgrid_tiles:
                    self.tilemap.offgrid_tiles[self.current_layer] = {}
                tile_loc = str(self.mpos_scaled[0] + self.scroll[0])+";"+ str(self.mpos_scaled[1] + self.scroll[1])
                self.tilemap.offgrid_tiles[self.current_layer][tile_loc] = (
                    self.tilemap.tile_manager.pack_tile(t_id, self.tile_variant, self.rotation))

            if t_groups:
                for group_id in t_groups:
                    if [tile_loc, self.current_layer] not in self.tilemap.tag_groups[group_id]["tiles"]:
                        self.tilemap.tag_groups[group_id]["tiles"].append([tile_loc, self.current_layer])

    def handle_eraser_tool(self):
        self.selector.link = []
        if self.clicking:
            tile_loc = str(self.tile_pos[0]) + ";" + str(self.tile_pos[1])
            if tile_loc in self.tilemap.tilemap[self.current_layer]:
                del self.tilemap.tilemap[self.current_layer][tile_loc]


            if self.current_layer in self.tilemap.offgrid_tiles:
                for loc in self.tilemap.offgrid_tiles[self.current_layer].copy():
                    pos = [float(val) for val in loc.split(";")]
                    tile_id, variant, rot, flip_h, flip_v  = self.tilemap.tile_manager.unpack_tile(self.tilemap.offgrid_tiles[self.current_layer][loc])
                    images = self.tilemap.tile_manager.tiles[tile_id].images.copy()
                    if isinstance(images, Animation):
                        tile_img = images.img()
                    else:
                        tile_img = images[variant]
                    tile_r = pygame.Rect(pos[0] - self.scroll[0],
                                         pos[1] - self.scroll[1],
                                         tile_img.get_width(),
                                         tile_img.get_height())
                    if tile_r.collidepoint(self.mpos_scaled):  # Check both to be safe
                        del self.tilemap.offgrid_tiles[self.current_layer][loc]

            tile_link = self.selector.tile_has_link(tile_loc)
            if tile_link:
                self.tilemap.links[self.current_layer].remove(tile_link)
                tile_link.remove(tile_loc)
                self.tilemap.links[self.current_layer].append(tile_link)

            for group_id in self.tilemap.tag_groups:
                if [tile_loc, self.current_layer] in self.tilemap.tag_groups[group_id]["tiles"]:
                    self.tilemap.tag_groups[group_id]["tiles"].remove([tile_loc, self.current_layer])

    def handle_move_tool(self, event):
        if self.clicking:
            tilepos_onclick = (int((self.mpos_scaled_onclick[0]) // self.tilemap.tile_size),
                               int((self.mpos_scaled_onclick[1]) // self.tilemap.tile_size))
            mpos_scaled_onclick = (
                self.mpos_scaled_onclick[0] - self.scroll[0], self.mpos_scaled_onclick[1] - self.scroll[1])
            if self.selector.link:
                for loc in self.selector.link:
                    offgrid_tile = False
                    if loc in self.tilemap.tilemap[self.current_layer]:
                        pass
                    else:
                        offgrid_tile = True

                    pos = [float(val) for val in loc.split(";")]

                    if self.ongrid:
                        # Convert to tile units if offgrid, otherwise pos is already in tile units
                        tx = pos[0] // self.tilemap.tile_size if offgrid_tile else pos[0]
                        ty = pos[1] // self.tilemap.tile_size if offgrid_tile else pos[1]


                        x, y = tx + self.tile_pos[0] - tilepos_onclick[0], ty + self.tile_pos[1] - tilepos_onclick[1]
                        self.moved_link["offgrid"] = {}
                        self.moved_link["ongrid"][loc] = f"{int(x)};{int(y)}"
                    else:
                        # Convert to pixel units if ongrid, otherwise pos is already in pixels
                        px = pos[0] * self.tile_size if not offgrid_tile else pos[0]
                        py = pos[1] * self.tile_size if not offgrid_tile else pos[1]
                        x, y = px + self.mpos_scaled[0] - mpos_scaled_onclick[0], py + self.mpos_scaled[1] - \
                               mpos_scaled_onclick[1]
                        self.moved_link["ongrid"] = {}
                        self.moved_link["offgrid"][loc] = f"{x};{y}"

        if self.selector.link:
            can_place_check = True
            if self.moved_link["ongrid"]:
                for tile_loc in self.selector.link:
                    if (self.moved_link["ongrid"][tile_loc] in self.tilemap.tilemap[self.current_layer] and
                            self.moved_link["ongrid"][tile_loc] not in self.moved_link["ongrid"]):
                        can_place_check = False
                        break
            elif self.moved_link["offgrid"]:
                for tile_loc in self.selector.link:
                    if self.current_layer in self.tilemap.offgrid_tiles:
                        if (self.moved_link["offgrid"][tile_loc] in self.tilemap.offgrid_tiles[self.current_layer] and
                                self.moved_link["offgrid"][tile_loc] not in self.moved_link["offgrid"]):
                            can_place_check = False
                            break

            if self.clicking and event.type == pygame.MOUSEBUTTONUP:
                current_state = self._create_snapshot()
                # Simply comparing the dicts detects if anything changed
                if current_state != self.temp_snapshot:
                    self._save_action()


                if event.button == 1 and self.selector.link:
                    if can_place_check:
                        tilemap_tmp = {}
                        offgrid_tmp = {}
                        if self.moved_link["ongrid"]:

                            for tile_loc in self.selector.link:
                                space = self.check_tile_space(tile_loc)
                                if space == "tilemap":
                                    tilemap_tmp[tile_loc] = self.tilemap.tilemap[self.current_layer][tile_loc]
                                    del self.tilemap.tilemap[self.current_layer][tile_loc]
                                else:
                                    offgrid_tmp[tile_loc] = self.tilemap.offgrid_tiles[self.current_layer][tile_loc]
                                    del self.tilemap.offgrid_tiles[self.current_layer][tile_loc]


                            for tile_loc in self.selector.link:
                                new_loc = self.moved_link["ongrid"][tile_loc]
                                if tile_loc in tilemap_tmp:
                                    tmp = tilemap_tmp[tile_loc]

                                else:  # <=> tile_loc in self.tilemap.offgrid_tiles[self.current_layer]
                                    tmp = offgrid_tmp[tile_loc]
                                    pos = [int(float(val)) for val in new_loc.split(";")]
                                    new_loc = f"{pos[0]};{pos[1]}"

                                if self.current_layer not in self.tilemap.tilemap:
                                    self.tilemap.tilemap[self.current_layer] = {}

                                self.tilemap.tilemap[self.current_layer][new_loc] = tmp
                                self.update_group_tile(tile_loc, new_loc, self.current_layer)

                            if self.current_layer in self.tilemap.links:
                                for link in self.tilemap.links[self.current_layer]:
                                    edited_link = link.copy()
                                    for tile_loc in link:
                                        if tile_loc in self.moved_link["ongrid"]:
                                            edited_link.remove(tile_loc)
                                            edited_link.append(self.moved_link["ongrid"][tile_loc])
                                    if edited_link != link:
                                        self.tilemap.links[self.current_layer].remove(link)
                                        self.tilemap.links[self.current_layer].append(edited_link)

                            self.selector.link = list(self.moved_link["ongrid"].values())
                            self.selector.link_pivot = self.selector.get_link_pivot(self.selector.link)

                        elif self.moved_link["offgrid"]:
                            for tile_loc in self.selector.link:
                                space = self.check_tile_space(tile_loc)
                                if space == "tilemap":
                                    tilemap_tmp[tile_loc] = self.tilemap.tilemap[self.current_layer][tile_loc]
                                    del self.tilemap.tilemap[self.current_layer][tile_loc]
                                else:
                                    offgrid_tmp[tile_loc] = self.tilemap.offgrid_tiles[self.current_layer][tile_loc]
                                    del self.tilemap.offgrid_tiles[self.current_layer][tile_loc]

                            for tile_loc in self.selector.link:
                                new_loc = self.moved_link["offgrid"][tile_loc]
                                if tile_loc in tilemap_tmp:
                                    tmp = tilemap_tmp[tile_loc]
                                else:  # <=> tile_loc in self.tilemap.offgrid_tiles[self.current_layer]
                                    tmp = offgrid_tmp[tile_loc]

                                if self.current_layer not in self.tilemap.offgrid_tiles:
                                    self.tilemap.offgrid_tiles[self.current_layer] = {}
                                self.tilemap.offgrid_tiles[self.current_layer][new_loc] = tmp
                                self.update_group_tile(tile_loc, new_loc, self.current_layer)

                            if self.current_layer in self.tilemap.links:
                                for link in self.tilemap.links[self.current_layer]:
                                    edited_link = link.copy()
                                    for tile_loc in link:
                                        if tile_loc in self.moved_link["offgrid"]:
                                            edited_link.remove(tile_loc)
                                            edited_link.append(self.moved_link["offgrid"][tile_loc])
                                    if edited_link != link:
                                        self.tilemap.links[self.current_layer].remove(link)
                                        self.tilemap.links[self.current_layer].append(edited_link)

                            self.selector.link = list(self.moved_link["offgrid"].values())
                            self.selector.link_pivot = self.selector.get_link_pivot(self.selector.link)


                    self.moved_link = {"ongrid": {}, "offgrid": {}}

    def handle_selection_tool(self, event):
        self.selector.handle_event(event)

    def handle_map_editor(self, event):

        if self.ui.toolbar_rect.collidepoint(self.mpos) or self.ui.assets_section_rect.collidepoint(self.mpos):
            self.clicking = False

        if not self.ui.in_group_editor and not self.ui.in_group_selector:
            if self.mpos_in_mainarea:
                match self.current_tool:
                    case "Brush":
                        self.handle_brush_tool()
                    case "Eraser":
                        self.handle_eraser_tool()
                    case "Selection":
                        self.handle_selection_tool(event)
                    case "Move":
                        self.handle_move_tool(event)
                    case "CameraSetup":
                        self.camera_setup.handle_event(event)

            if event.type == pygame.MOUSEWHEEL:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    self.zoom -= 0.1 * event.y
                    self.zoom = max(0.2, min(self.zoom, 8))
                else:
                    self.tile_variant = (self.tile_variant + event.y) % len(
                        self.assets[self.tile_type])
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 3):  # Left or Right click
                    self.temp_snapshot = self._create_snapshot()

                if event.button == 1:
                    self.clicking = True
                    self.mpos_scaled_onclick = (self.mpos_scaled[0] + self.scroll[0], self.mpos_scaled[1] + self.scroll[1])
                if event.button == 3:
                    self.right_clicking = True
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    if event.key == pygame.K_g:
                        if self.shift:
                            self.shift = False
                            self.player_start = (self.tile_pos[0]*self.tile_size, self.tile_pos[1]*self.tile_size)
                        self.state = "PlayTest"
                        self.zoom = 1
                        self.playtest.display = pygame.Surface((480 * self.zoom, 300 * self.zoom))
                        self.playtest.SCREEN_WIDTH, self.playtest.SCREEN_HEIGHT = self.screen.get_size()
                        self.playtest.load_settings()
                        self.playtest.level_manager.load_level()

                    if event.key == pygame.K_c:
                        self.selector.copy_link()
                    if event.key == pygame.K_v:
                        self.selector.paste_link()
                        self._save_action()

                    if event.key == pygame.K_z:
                        self._undo()
                    if event.key == pygame.K_y:
                        self._redo()
                    if event.key == pygame.K_DOWN:
                        if self.current_layer == "0":
                            print("Layer 0, can't go down")
                        else:
                            self.tilemap.tilemap[self.current_layer], self.tilemap.tilemap[
                                str(int(self.current_layer) - 1)] \
                                = self.tilemap.tilemap[str(int(self.current_layer) - 1)], \
                                self.tilemap.tilemap[self.current_layer]
                            self.current_layer = str(int(self.current_layer) - 1)
                            print(f"Current layer moved to layer {self.current_layer}")
                    if event.key == pygame.K_UP:
                        if self.tilemap.tilemap[self.current_layer] == {} and str(
                                int(self.current_layer) + 1) not in self.tilemap.tilemap:
                            print("This layer is the last layer, can't go up")
                        else:
                            self.tilemap.tilemap[self.current_layer], self.tilemap.tilemap[
                                str(int(self.current_layer) + 1)] \
                                = self.tilemap.tilemap[str(int(self.current_layer) + 1)], \
                                self.tilemap.tilemap[self.current_layer]
                            self.current_layer = str(int(self.current_layer) + 1)
                            print(f"Current layer moved to layer {self.current_layer}")
                    if event.key == pygame.K_d:
                        self.selector.link = []

                    if event.key == pygame.K_MINUS:
                        self.zoom += 0.1
                        self.zoom = max(0.2, min(self.zoom, 8))
                    if event.key == pygame.K_PLUS:
                        self.zoom -= 0.1
                        self.zoom = max(0.2, min(self.zoom, 8))

                else:
                    if event.key == pygame.K_i and not self.holding_i:
                        self.holding_i = True
                    if event.key == pygame.K_DOWN:
                        if self.current_layer == "0":
                            print("Layer 0, can't make any new layer under this one")
                        else:
                            self.current_layer = str(int(self.current_layer) - 1)
                            self.selector.link = []
                            print(f"Current layer : {self.current_layer}")
                        if self.current_layer not in self.tilemap.tilemap:
                            self.tilemap.tilemap[self.current_layer] = {}
                    if event.key == pygame.K_UP:
                        if int(self.current_layer) + 1 == len(self.tilemap.tilemap.keys()) and \
                                self.tilemap.tilemap[self.current_layer] == {}:
                            print("This layer is empty, can't make any new layer")
                        else:
                            self.current_layer = str(int(self.current_layer) + 1)
                            self.selector.link = []
                            print(f"Current layer : {self.current_layer}")

                        if self.current_layer not in self.tilemap.tilemap:
                            self.tilemap.tilemap[self.current_layer] = {}
                    if event.key == pygame.K_TAB and not self.holding_tab:
                        self.holding_tab = True
                    # Show camera setup zones
                    if event.key == pygame.K_b and not self.holding_b:
                        self.current_tool = "Brush"
                        self.rotation = 0
                        self.holding_b = True
                    if event.key == pygame.K_e:
                        self.current_tool = "Eraser"
                        self.rotation = 0

                    if event.scancode == 4:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.scancode == 26:
                        self.movement[2] = True
                    if event.key == pygame.K_s:
                        self.movement[3] = True

                    if event.key == pygame.K_g:
                        self.ongrid = not self.ongrid
                    if event.key == pygame.K_t:
                        self.tilemap.autotile(self.current_layer)
                        self._save_action()
                    if event.key == pygame.K_o:
                        self.level_manager.full_save()

                    if event.key == pygame.K_c:
                        print((self.tile_pos[0] * 16, self.tile_pos[1] * 16))
                    if event.key == pygame.K_r:
                        if self.selector.link and not self.clicking:
                            self.selector.rotate_link_90()
                            self._save_action()
                        else:
                            self.rotation = (self.rotation + 1) % 4

                    if event.key == pygame.K_DELETE:
                        self.selector.delete_link()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_y:
                    self.holding_y = False
                if event.key == pygame.K_b:
                    self.holding_b = False
                if event.key == pygame.K_i:
                    self.holding_i = False
                if event.scancode == 4:
                    self.movement[0] = False
                if event.key == pygame.K_d:
                    self.movement[1] = False
                if event.scancode == 26:
                    self.movement[2] = False
                if event.key == pygame.K_s:
                    self.movement[3] = False
                if event.key == pygame.K_TAB:
                    self.holding_tab = False


    def render_brush_tool(self):
        current_tile_img = self.assets[self.tile_type][self.tile_variant].copy()
        current_tile_img.set_alpha(100)
        current_tile_img = pygame.transform.rotate(current_tile_img, self.rotation * -90)

        if self.ongrid:
            self.display.blit(current_tile_img, (self.tile_pos[0] * self.tilemap.tile_size - self.scroll[0],
                                                 self.tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
        else:
            self.display.blit(current_tile_img, self.mpos_scaled)

    def render_move_tool(self):
        grid = "ongrid"
        if self.moved_link["offgrid"]:
            grid = "offgrid"

        if self.moved_link[grid]:
            self.tilemap.set_render_filter(self.selector.link, 0)

            for old_loc, loc in self.moved_link[grid].items():
                x, y = (float(val) for val in loc.split(";"))
                if old_loc in self.tilemap.tilemap[self.current_layer]:
                    tile_id, variant, rot, flip_h, flip_v = self.tilemap.tile_manager.unpack_tile(
                        self.tilemap.tilemap[self.current_layer][old_loc]
                    )
                else:
                    tile_id, variant, rot, flip_h, flip_v = self.tilemap.tile_manager.unpack_tile(
                        self.tilemap.offgrid_tiles[self.current_layer][old_loc]
                    )

                tile_img = self.tilemap.tile_manager.get_tile_img(tile_id, variant)
                tile_img = pygame.transform.rotate(tile_img, rot * -90)
                tile_img = pygame.transform.flip(tile_img, flip_h, flip_v)
                if grid == "ongrid":
                    draw_pos = (x * self.tilemap.tile_size - self.scroll[0], y * self.tilemap.tile_size - self.scroll[1])
                else:
                    draw_pos = (x - self.scroll[0], y - self.scroll[1])

                self.display.blit(tile_img, draw_pos)

    def render_selection_tool(self):
        self.selector.draw(self.display)

    def render_map_editor(self):
        match self.current_tool:
            case "Brush":
                self.render_brush_tool()
            case "Selection":
                self.render_selection_tool()
            case "Move":
                self.render_move_tool()
            case "CameraSetup":
                self.camera_setup.draw(self.display)
        self.render_map()
        self.render_display()
        self.ui.draw()

    def render_map(self):
        self.scroll[0] += (self.movement[1] - self.movement[0]) * 8
        self.scroll[1] += (self.movement[3] - self.movement[2]) * 8
        render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

        self.tilemap.set_render_filter(self.selector.link, (152, 242, 255, 50))

        self.tilemap.render(self.display, offset=render_scroll,
                            precise_layer=self.current_layer if not self.showing_all_layers else None,
                            with_player=False)

        self.tilemap.render_filters = {}

    def render_display(self):
        changing_size = False
        screenshot = self.screen.copy()

        if self.display.get_size() != (int(480 * self.zoom), int(300 * self.zoom)):
            self.display = pygame.Surface((480 * self.zoom, 300 * self.zoom))
            changing_size = True

        scaled_display = pygame.transform.scale(self.display, self.screen.get_size())

        self.screen.blit(scaled_display, (0, 0))

        if changing_size:
            self.screen.blit(screenshot, (0, 0))


    def run(self):
        while True:
            match self.state:
                case "MapEditor":
                    self.display.fill((0, 0, 0))
                    self.mpos_update()
                    for event in pygame.event.get():
                        if self.current_tool == "LevelSelector":
                            pass
                        else:
                            self.handle_map_editor(event)
                        self.ui.handle_ui_event(event)
                        if self.current_tool == "CameraSetup":
                            self.camera_setup.update()

                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_LSHIFT:
                                self.shift = True
                        if event.type == pygame.KEYUP:
                            if event.key == pygame.K_LSHIFT:
                                self.shift = False
                        if event.type == pygame.MOUSEBUTTONUP:
                            if event.button == 1:
                                self.clicking = False
                                self.waiting_for_click_release = False
                            if event.button == 3:
                                self.right_clicking = False
                            if event.button in (1, 3) and self.temp_snapshot:
                                current_state = self._create_snapshot()
                                # Simply comparing the dicts detects if anything changed
                                if current_state != self.temp_snapshot:
                                    self._save_action()
                        if event.type == pygame.VIDEORESIZE:
                            # Update screen dimensions
                            self.screen_width = max(event.w, 480)  # Minimum width
                            self.screen_height = max(event.h, 300)  # Minimum height
                            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height),
                                                                  pygame.RESIZABLE)
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()

                    self.render_map_editor()
                    self.clock.tick(60)

                case "PlayTest":
                    self.playtest.run()
            pygame.display.update()

class UI:
    TOOLBAR_COLOR = (64,64,64)
    ASSETS_SECTION_COLOR = (32,32,32)
    PADDING = 5

    def __init__(self, editor_instance):
        self.editor = editor_instance
        self.editor_previous_tool = self.editor.current_tool
        self.screen = editor_instance.screen
        self.screen_width, self.screen_height = self.screen.get_size()

        self.level_carousel = None

        self.title_font = load_game_font(24)
        self.buttons_font = load_game_font(18)

        self.state = "Editor"


        self.toolbar_width = self.screen_width * 5 / 96
        self.toolbar_default_width = self.screen_width * 5 / 96
        self.toolbar_rect = pygame.Rect(self.screen_width - self.toolbar_default_width, 0,self.screen_width * 5 / 96,self.screen_height)

        self.toolbar_buttons_width = self.toolbar_rect.width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_rect.width * (3 / 5)

        self.group_selector_rect = pygame.Rect(0, 0, self.screen_width * 0.75, self.screen_height * 0.75)
        self.group_selector_rect.center = (self.screen_width - self.toolbar_rect.width) / 2, self.screen_height / 2
        self.in_group_selector = False
        self.group_selector_buttons = []
        self.group_selector_labels = ["Next","Left","Right","Add"]
        self.group_selector_images = {"Next":load_image("ui/next.png"),
                                      "Left":pygame.transform.flip(load_image("ui/right.png"), True, False),
                                      "Right":load_image("ui/right.png"),
                                      "Add":load_image("ui/plus.png"),
                                      "Close":load_image("ui/close.png")}
        self.current_group_id = 0
        self.group_list = {"common":[], "uncommon":[]}
        self.group_buttons_list = {"common":[], "uncommon":[]}

        self.tools_buttons = []
        self.tools_buttons_labels = ["Brush", "Eraser", "Selection", "Move", "Groups", "CameraSetup", "LevelSelector"]
        self.check_buttons = []
        self.check_buttons_labels = ["All_layers", "On_grid"]
        self.on_selection_buttons = []
        self.on_selection_buttons_labels = ["Plus", "Link","Unlink","IgnoreLinks"]
        #self.tools_buttons_images = {tool: load_image(f"ui/{tool.lower()}.png") for tool in self.tools_buttons_labels}
        self.buttons_images = {"Brush": load_image("ui/brush.png"),
                               "Eraser": load_image("ui/eraser.png"),
                               "Selection": load_image("ui/selection.png"),
                               "Move": load_image("ui/move.png"),
                               "LevelSelector": load_image("ui/level_selector.png"),
                               "On_grid": load_image("ui/ongrid.png"),
                               "All_layers": load_image("ui/skull.png"),
                               "Groups" : load_image("ui/properties.png"),
                               "Link": load_image("ui/link.png"),
                               "Unlink": load_image("ui/unlink.png"),
                               "Plus":load_image("ui/plus.png"),
                               "CameraSetup": load_image("ui/skull.png"),
                               "IgnoreLinks": load_image("ui/skull.png")}

        self.spectial_buttons_labels = {"Brush": [],
                                        "Eraser": [],
                                        "Selection": []}

        self.selection_rect = pygame.Rect(0,0,0,0)
        self.selecting = False
        self.selection_pos = None



        self.assets_section_default_width = self.screen_width * 20/96
        self.assets_section_rect = pygame.Rect(self.screen_width - self.toolbar_rect.width - self.assets_section_default_width,
                                               self.screen_height - self.screen_width * 25/96,
                                               self.screen_width * 20 / 96, self.screen_width * 25 / 96)

        self.current_category = 0
        self.categories = editor_instance.categories
        self.current_category_name = list(self.editor.categories.keys())[self.current_category]

        self.assets_section_buttons_width = self.assets_section_rect.width * (1 / 6)
        self.assets_section_buttons_height = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons = []
        self.assets_section_buttons_labels = ["Previous", "Next"]
        self.assets_section_buttons_images = {"Previous": pygame.transform.flip(load_image("ui/right.png"), True, False),
                                              "Next": load_image("ui/right.png")}
        self.assets_button_width = self.assets_section_rect.width * (1 / 10)
        self.assets_button_height = self.assets_section_rect.width * (1 / 10)
        self.assets_buttons = []

        self.group_editor_rect = pygame.Rect(0, 0, self.screen_width * 0.75, self.screen_height * 0.75)
        self.group_editor_rect.center = (self.screen_width - self.toolbar_rect.width) / 2, self.screen_height / 2

        self.group_editor_buttons_width = self.group_editor_rect.width * (1 / 8)
        self.group_editor_buttons_height = self.group_editor_rect.width * (1 / 8)
        self.group_editor_buttons = []
        self.group_editor_buttons_parents = []
        self.in_group_editor = False



        self.init_buttons()
        self.closing = False

    def init_buttons(self):
        self.tools_buttons = []
        self.assets_section_buttons = []
        self.check_buttons = []
        self.on_selection_buttons = []
        self.group_selector_buttons = []
        self.group_editor_buttons = []

        button_x, button_y = self.toolbar_rect.width/2, self.toolbar_rect.width/2
        for label in self.tools_buttons_labels:
            button = EditorButton(label, self.buttons_images[label],
                                  (button_x, button_y),
                                  self.toolbar_buttons_width,
                                  self.toolbar_buttons_height,
                                  (64,64,64),
                                  self.screen_width / self.editor.SW)

            if label == self.tools_buttons_labels[-2]:
                button_y = self.screen_height - 1*self.toolbar_buttons_height
            else:
                button_y += self.toolbar_buttons_height + (self.PADDING/self.editor.SH)*self.screen_height
            self.tools_buttons.append(button)

        button_x, button_y = (30/self.editor.SW)*self.screen_width, (20/self.editor.SH)*self.screen_height
        for label in self.assets_section_buttons_labels:
            button = EditorButton(label, self.assets_section_buttons_images[label], (button_x, button_y), self.assets_section_buttons_width, self.assets_section_buttons_height, (24,24,24), self.screen_width/self.editor.SW)
            button_x = self.assets_section_rect.width - button_x
            self.assets_section_buttons.append(button)

        self.level_carousel = LevelCarousel(self.screen_width / 2, self.screen_height / 2,
                                            (self.screen_width * 5 / 16, self.screen_height * 3 / 10),
                                            self.editor.active_maps + [None])


        button_x,button_y = self.toolbar_rect.width/2, self.toolbar_rect.height-3*self.toolbar_buttons_height
        for label in self.check_buttons_labels:
            button = EditorButton(label, self.buttons_images[label],
                                  (button_x, button_y),
                                  0.7*self.toolbar_buttons_width,
                                  0.7*self.toolbar_buttons_height,
                                  (64, 64, 64),
                                  resize=0.8)
            button_y -= self.toolbar_buttons_height - (0.5*self.PADDING/self.editor.SW)*self.screen_width
            self.check_buttons.append(button)

        self.init_assets_buttons(self.categories)

        button_x,button_y = self.toolbar_rect.x - self.toolbar_rect.width/2 , self.toolbar_rect.width/2
        for label in self.on_selection_buttons_labels:
            color = ()
            toggle = False
            if label == "Plus":
                button_y = self.toolbar_buttons_height
                color = (42, 90, 57)
            if label == "Link":
                button_y = self.screen_height - self.toolbar_buttons_height
                color = (98, 171, 212)
            if label == "Unlink":
                color = (235, 217, 103)
            if label == "IgnoreLinks":
                color = (255,0,0)
                toggle = True
            if color:
                button = IconButton(label,self.buttons_images[label],(button_x, button_y),self.toolbar_buttons_width,
                           self.toolbar_buttons_height,color,resize=0.8,toggle=toggle)
                button_y -= self.toolbar_buttons_height + 5*(self.PADDING/self.editor.SH)*self.screen_height
                self.on_selection_buttons.append(button)

        button_y = int(self.group_selector_rect.height/4)
        for label in self.group_selector_labels:
            button = None
            match label:
                case "Next":
                    color = (98, 171, 212)
                    button_x = int(self.group_selector_rect.width/3)
                    button = IconButton(label,self.group_selector_images[label],(button_x, button_y),self.toolbar_buttons_width,
                           self.toolbar_buttons_height,color,resize=0.8)
                    button.activated = True
                case "Left":
                    button_x += 2*self.toolbar_buttons_width + (self.PADDING/self.editor.SW)*self.screen_width
                    button = EditorButton(label, self.group_selector_images[label], (button_x, button_y),
                                          self.toolbar_buttons_width, self.toolbar_buttons_height, self.TOOLBAR_COLOR,
                                          resize=0.8)
                case "Right":
                    button_x += self.group_selector_rect.width/8+ 4*(self.PADDING/self.editor.SW)*self.screen_width
                    button = EditorButton(label, self.group_selector_images[label], (button_x, button_y),
                                          self.toolbar_buttons_width, self.toolbar_buttons_height, self.TOOLBAR_COLOR,
                                          resize=0.8)
                case "Add":
                    color = (98, 171, 212)
                    button_x += 2*self.toolbar_buttons_width + (self.PADDING/self.editor.SW)*self.screen_width
                    button = IconButton(label, self.group_selector_images[label], (button_x, button_y),
                               self.toolbar_buttons_width,
                               self.toolbar_buttons_height, color, resize=0.8)
                    button.activated = True
            self.group_selector_buttons.append(button)
            close_button = IconButton("Close", self.group_selector_images["Close"],
                                      (self.group_selector_rect.x, self.group_selector_rect.y),
                                      self.toolbar_buttons_width, self.toolbar_buttons_height, (200, 50, 50),
                                      resize=0.8)
            self.group_selector_buttons.append(close_button)

        if len(self.group_editor_buttons_parents) == 0:
            button = ParentButton(self.group_editor_rect.x + 50, self.group_editor_rect.y + 50, self.screen_height / 20, self.screen_height / 20, self.buttons_font)
            self.group_editor_buttons_parents.append(button)
        else:
            for parent in self.group_editor_buttons_parents:
                parent.reload(self.screen_height/20,self.screen_height/20,self.buttons_font)



    def init_assets_buttons(self, categories):
        self.assets_buttons = []

        initial_x = (20 / self.editor.SW) * self.screen_width

        button_x, button_y = initial_x, (60 / self.editor.SH) * self.screen_height
        for tile in categories[self.current_category_name]:
            img = categories[self.current_category_name][tile].copy()[0]
            button = EditorButton(tile, img, (button_x, button_y), self.assets_button_width, self.assets_button_height,
                                  (24, 24, 24),resize=0.9)
            if button_x + self.assets_button_width + self.PADDING*self.screen_width/self.editor.SW > self.assets_section_rect.width - self.assets_button_width:
                button_y = (button_y + self.assets_button_height + self.PADDING*self.screen_height/self.editor.SH %
                            self.screen_height)
                button_x = initial_x
            else:
                button_x = ((button_x + self.assets_button_width + self.PADDING*self.screen_width/self.editor.SW) %
                            (self.assets_section_rect.width - self.assets_button_width))
            if button_x < initial_x:
                button_x = initial_x
            if button_y + self.assets_button_height/2 > self.assets_section_rect.height:
                self.assets_section_rect.height += self.assets_button_height + self.PADDING*self.screen_height/self.editor.SH
            self.assets_buttons.append(button)

    def render_toolbar(self):

        overlay = pygame.Surface((self.toolbar_rect.width, self.toolbar_rect.height))
        overlay.fill(self.TOOLBAR_COLOR)

        for button in self.tools_buttons:
            button.draw(overlay)
            if button.label == self.editor.current_tool:
                button.activated = True
            else:
                button.activated = False
        for button in self.check_buttons:
            button.draw(overlay)

            if button.label == "On_grid":
                if self.editor.ongrid:
                    button.activated = True
                else:
                    button.activated = False
            elif button.label == "All_layers":
                if self.editor.showing_all_layers:
                    button.activated = True
                else:
                    button.activated = False

        self.toolbar_rect.x,self.toolbar_rect.y = (self.screen_width - self.toolbar_rect.width, 0)

        self.screen.blit(overlay, (self.toolbar_rect.x,self.toolbar_rect.y))

    def render_assets_section(self, x, y):
        if self.assets_section_rect.width == 0 and not self.closing:
            self.reload_assets_section_rect()
        self.assets_section_rect.x,self.assets_section_rect.y = x,y
        overlay = pygame.Surface((self.assets_section_rect.width, self.assets_section_rect.height))
        overlay.fill(self.ASSETS_SECTION_COLOR)

        category_text = self.title_font.render(self.current_category_name, True, (255, 255, 255))
        category_x = (self.assets_section_rect.width - category_text.get_width())/2
        category_y = (10 / self.editor.SH) * self.screen_height
        overlay.blit(category_text, (category_x, category_y))

        for button in self.assets_buttons:
            button.draw(overlay)
            if button.label == self.editor.tile_type:
                button.activated = True
            else:
                button.activated = False

        for button in self.assets_section_buttons:
            button.draw(overlay)

        self.screen.blit(overlay, self.assets_section_rect.topleft)

    def render_level_selector(self):
        overlay = create_rect_alpha((0, 0, 0), (0, 0, self.screen_width, self.screen_height), 100)
        self.level_carousel.draw(overlay)
        self.level_carousel.update()
        self.screen.blit(overlay, (0, 0))

    def render_on_selection(self, centerx):
        for button in self.on_selection_buttons:

            match button.label:
                case "Link":
                    if len(self.editor.selector.link) > 1 and not self.editor.ignore_links:
                        button.activated = True
                    else:
                        button.activated = False

                case "Plus":
                    if len(self.editor.selector.link) >= 1:
                        button.activated = True
                    else:
                        button.activated = False

                case "IgnoreLinks":
                    button.activated = True

                case _ :
                    button.activated = False
                    if self.editor.current_layer in self.editor.tilemap.links:
                        for link in self.editor.tilemap.links[self.editor.current_layer]:
                            if set(link).issubset(set(self.editor.selector.link)):
                                button.activated = True
                                break

            button.rect.centerx = centerx
            button.draw(self.screen)

    def render_group_selector(self):
        # Update rect
        self.group_selector_rect.center = (self.screen_width - self.toolbar_rect.width) / 2, self.screen_height / 2

        # Creating the Overlay where everything will be blit
        overlay = pygame.Surface((self.group_selector_rect.width, self.group_selector_rect.height))
        overlay.fill(self.TOOLBAR_COLOR)

        # Drawing the buttons
        for button in self.group_selector_buttons:
            if button.label != "Close":
                button.draw(overlay)
            if button.label == "Add" or button.label == "Next" or button.label == "Close":
                button.activated = True

        # Drawing the rectangle where the group ID will be displayed
        grp_id_rect = pygame.Rect(0,0,self.group_selector_rect.width/15,self.group_selector_rect.height/18)
        grp_id_rect.center = (overlay.get_rect().centerx,int(self.group_selector_rect.height/4))
        grp_id_txt = self.title_font.render(f"{self.current_group_id}", True, (255, 255, 255))
        grp_id_txt_rect = grp_id_txt.get_rect(center=grp_id_rect.center)
        pygame.draw.rect(overlay,(24,24,24),grp_id_rect)
        overlay.blit(grp_id_txt,grp_id_txt_rect)

        # Displaying text
        grp_txt = self.title_font.render("Groups :",True,(255,255,255))
        grp_rect = grp_txt.get_rect(center=(overlay.get_rect().centerx,overlay.get_rect().height/6))
        overlay.blit(grp_txt, grp_rect)

        # Creating the rectangle where the group created will be drawn
        big_rect = pygame.Rect(0,0,self.group_selector_rect.width*0.80,self.group_selector_rect.height/1.8)
        big_rect.center = int(overlay.get_rect().centerx),int(overlay.get_rect().height*2/3)
        pygame.draw.rect(overlay,(24,24,24),big_rect)

        # Drawing the group on the big rectangle
        self.render_group_button(overlay,big_rect)

        self.screen.blit(overlay, (self.group_selector_rect.x, self.group_selector_rect.y))
        close_button = self.group_selector_buttons[-1]
        close_button.rect.center = (self.group_selector_rect.x,self.group_selector_rect.y)
        close_button.draw(self.screen)

    def render_group_button(self,surface,rect):
        self.group_buttons_list = {"common":[], "uncommon":[]}
        nc = len(self.group_list["common"])
        nu = len(self.group_list["uncommon"])
        if nc == 0 and nu == 0:
            return
        max_per_row = 8
        max_per_col = 5
        padding = 5
        outer_padding = 5
        small_width = (
                              rect.width - 2 * outer_padding - (max_per_row - 1) * padding
                      ) / max_per_row

        small_height = (
                               rect.height - 2 * outer_padding - (max_per_col - 1) * padding
                       ) / max_per_col

        centers = []

        i = 0
        for c in self.group_list:
            for label in self.group_list[c]:
                row = i // max_per_row
                col = i % max_per_row

                if row >= max_per_col:
                    break

                x = rect.x + outer_padding + col * (small_width + padding)
                y = rect.y + outer_padding + row * (small_height + padding)

                center_x = x + small_width / 2
                center_y = y + small_height / 2

                if c == "uncommon":
                    color = (200, 200, 130)
                else:
                    color = (255, 255, 255)

                button = TextButton(str(label),(center_x,center_y),small_width,small_height,self.title_font, text_color=color)
                self.group_buttons_list[c].append(button)
                i+=1

        for c in self.group_list:
            for button in self.group_buttons_list[c]:
                button.draw(surface)

    def render_group_editor(self):
        # Update rect
        self.group_editor_rect.center = (self.screen_width - self.toolbar_rect.width) / 2, self.screen_height / 2

        # Creating the Overlay where everything will be blit
        overlay = pygame.Surface((self.group_editor_rect.width, self.group_editor_rect.height))
        overlay.fill(self.TOOLBAR_COLOR)

        current_y = 50
        for p in self.group_editor_buttons_parents:
            p.draw(overlay, p.rect.x, current_y)
            current_y += p.get_total_height()
        self.screen.blit(overlay, self.group_editor_rect)



    def check_closed(self):
        if self.closing:
            self.toolbar_rect.width = max(0, self.toolbar_rect.width - 5)
            match self.editor.current_tool:
                case "Brush":
                    self.assets_section_rect.width = max(0, self.assets_section_rect.width - 20)
        else:
            self.toolbar_rect.width = min(self.toolbar_default_width, self.toolbar_rect.width + 5)
            match self.editor.current_tool:
                case "Brush":
                    self.assets_section_rect.width = min(self.assets_section_default_width, self.assets_section_rect.width + 20)

    def reload(self):
        self.screen_width, self.screen_height = self.editor.screen.get_size()

        self.title_font = load_game_font(int((24/self.editor.SH)*self.screen_height))
        self.buttons_font = load_game_font(int((18/self.editor.SH)*self.screen_height))

        self.toolbar_default_width = self.screen_width * 5 / 96
        self.toolbar_rect = pygame.Rect(self.screen_width - self.toolbar_default_width, 0, self.screen_width * 5 / 96,
                                        self.screen_height)
        self.toolbar_default_width = self.screen_width * 5/96
        self.toolbar_buttons_width = self.toolbar_rect.width * (3 / 5)
        self.toolbar_buttons_height = self.toolbar_rect.width * (3 / 5)


        self.assets_section_default_width = self.screen_width * 20 / 96
        self.reload_assets_section_rect()
        self.assets_section_buttons_width = self.assets_section_rect.width * (1 / 8)
        self.assets_section_buttons_height = self.assets_section_rect.width * (1 / 8)
        self.assets_button_width = self.assets_section_rect.width * (1 / 10)
        self.assets_button_height = self.assets_section_rect.width * (1 / 10)
        self.init_assets_buttons(self.categories)

        self.group_selector_rect = pygame.Rect(0, 0, self.screen_width * 0.75, self.screen_height * 0.75)
        self.group_selector_rect.center = (self.screen_width - self.toolbar_rect.width) / 2, self.screen_height / 2

        self.group_editor_rect = pygame.Rect(0, 0, self.screen_width * 0.75, self.screen_height * 0.75)
        self.group_editor_rect.center = (self.screen_width - self.toolbar_rect.width) / 2, self.screen_height / 2

        self.init_buttons()

    def reload_assets_section_rect(self):
        self.assets_section_rect = pygame.Rect(
            self.screen_width - self.toolbar_rect.width - self.assets_section_default_width,
            self.screen_height - self.screen_width * 25 / 96,
            self.screen_width * 20 / 96, self.screen_width * 25 / 96)

    def reload_assets_section(self):
        categories = self.categories
        self.current_category = 0
        self.current_category_name = list(categories.keys())[self.current_category]
        self.init_assets_buttons(categories)

    def clear_sections_rect(self):
        if self.editor.current_tool != "Brush":
            if self.assets_section_rect.width:
                self.assets_section_rect.width = 0

    def draw(self):

        self.clear_sections_rect()
        self.check_closed()
        self.render_toolbar()
        match self.editor.current_tool:
            case "Brush":
                self.render_assets_section(self.screen_width - self.toolbar_rect.width  - self.assets_section_rect.width,
                                   self.screen_height - self.assets_section_rect.height)
            case "LevelSelector":
                    self.render_level_selector()
            case "Groups":
                self.render_group_editor()
            case "Selection" | "Move":
                self.render_on_selection(self.toolbar_rect.x - 30*(self.screen_width/self.editor.SW))
        if self.in_group_selector:
            self.render_group_selector()

    def handle_ui_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self.closing = not self.closing
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                print("Saving to disk...")
                self.editor.level_manager.full_save()
        if event.type == pygame.VIDEORESIZE:
            self.reload()
            match self.editor.current_tool:
                case "Brush":
                    self.reload_assets_section_rect()
        if event.type == pygame.QUIT:
            pygame.quit()
        self.handle_toolbar_event(event)
        match self.editor.current_tool:
            case "Brush":
                self.handle_assets_section_event(event)
            case "LevelSelector":
                self.handle_level_selector_event(event)
            case "Groups":
                self.handle_properties_section_event(event)
            case "Selection"|"Move":
                self.handle_on_selection_event(event)
        if self.in_group_selector:
            self.handle_group_selector_event(event)
        if self.editor.current_tool == "Groups":
            self.in_group_editor = True
        else:
            self.in_group_editor = False

    def handle_toolbar_event(self, event):
        for button in self.tools_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width, 0)):
                self.editor.rotation = 0
                self.editor_previous_tool = self.editor.current_tool
                self.editor.current_tool = button.label
        for button in self.check_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width, 0)):
                match button.label:
                    case "On_grid":
                        self.editor.ongrid = not self.editor.ongrid
                    case "All_layers":
                        self.editor.showing_all_layers = not self.editor.showing_all_layers

    def handle_assets_section_event(self, event):
        categories = self.categories
        for button in self.assets_section_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                                                  self.screen_height - self.assets_section_rect.height)):
                if button.label == "Next":
                    self.current_category = (self.current_category + 1) % len(categories)
                elif button.label == "Previous":
                    self.current_category = (self.current_category - 1) % len(categories)
                button.activated = True
                self.current_category_name = list(categories.keys())[self.current_category]
                self.init_assets_buttons(categories)
            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION and not button.is_selected(
                    event,
                    offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                            self.screen_height - self.assets_section_rect.height)):
                button.activated = False
        for button in self.assets_buttons:
            if button.handle_event(event, offset=(self.screen_width - self.toolbar_rect.width - self.assets_section_rect.width,
                                                  self.screen_height - self.assets_section_rect.height)):
                self.editor.rotation = 0
                self.editor.tile_type = button.label
                self.editor.tile_variant = 0

    def handle_level_selector_event(self, event):
        level_selector_state = self.level_carousel.handle_event(event)
        match level_selector_state:
            case "AddLevel":
                new_id = self.editor.level_manager.get_next_file_id()

                if new_id not in self.editor.active_maps:
                    self.editor.active_maps.append(new_id)
                # Refresh carousel mapping
                self.level_carousel.levels = self.editor.active_maps + [None]
                self.level_carousel.selected = self.editor.active_maps.index(new_id)

                self.editor.level_manager.change_level(new_id)

                self.reload_assets_section()
                self.editor.current_tool = self.editor_previous_tool
            case "DeleteLevel":
                deleted_id = self.level_carousel.levels[self.level_carousel.selected]
                self.level_carousel.levels.pop(self.level_carousel.selected)
                self.editor.level_manager.delete_map(deleted_id)
                self.level_carousel.levels = self.editor.active_maps + [None]
                self.level_carousel.selected = max(0, self.level_carousel.selected - 1)
            case "LoadLevel":
                loaded_id = self.level_carousel.levels[self.level_carousel.selected]
                self.editor.level_manager.change_level(loaded_id)
                self.editor.current_tool = self.editor_previous_tool
                self.editor.camera_setup.creating = False
                self.reload_assets_section()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.editor.current_tool = self.editor_previous_tool

    def handle_on_selection_event(self, event):
        for button in self.on_selection_buttons:
            if button.handle_event(event):
                match button.label:
                    case "Link":
                        self.editor.selector.link_link()
                    case "Unlink":
                        if self.editor.current_layer in self.editor.tilemap.links:
                            for group in self.editor.tilemap.links[self.editor.current_layer]:
                                if set(group).issubset(set(self.editor.selector.link)):
                                    self.editor.selector.unlink_link(group)
                    case "Plus":
                        self.in_group_selector = True
                        self.group_list = self.editor.selector.get_link_groups()
                    case "IgnoreLinks":
                        self.editor.ignore_links = True
            else:
                match button.label:
                    case "IgnoreLinks":
                        self.editor.ignore_links = False

    def handle_group_selector_event(self, event):
        for button in self.group_selector_buttons:
            offset = (self.group_selector_rect.x,self.group_selector_rect.y)
            if button.handle_event(event,offset if button.label != "Close" else None):
                match button.label:
                    case "Add":
                        if str(self.current_group_id) not in self.group_list["common"]:
                            self.group_list["common"].append(str(self.current_group_id))
                            if str(self.current_group_id) in self.group_list["uncommon"]:
                                self.group_list["uncommon"].remove(str(self.current_group_id))
                                self.editor.selector.remove_link_from_group(str(self.current_group_id))
                            self.editor.selector.add_link_to_group(str(self.current_group_id))
                            self.current_group_id += 1
                    case "Next":
                        new_id = 0
                        while str(new_id) in self.group_list["common"] or str(new_id) in self.group_list["uncommon"]:
                            new_id += 1
                        self.current_group_id = new_id
                        print(new_id)
                    case "Left":
                        if self.current_group_id > 0:
                            self.current_group_id -= 1
                    case "Right":
                        self.current_group_id += 1
                    case "Close":
                        self.in_group_selector = False
                button.activated = True
            elif event.type == pygame.MOUSEBUTTONUP or event.type == pygame.MOUSEMOTION and not button.is_selected(event,offset if button.label != "Close" else None):
                if button.label == "Left" or button.label == "Right":
                    button.activated = False

        for c in self.group_list:
            if self.group_buttons_list[c]:
                for button in self.group_buttons_list[c]:
                    if button.handle_event(event,offset=(self.group_selector_rect.x,self.group_selector_rect.y)):
                        self.group_buttons_list[c].remove(button)
                        if button.label in self.group_list[c]:
                            self.group_list[c].remove(button.label)
                            self.editor.selector.remove_link_from_group(button.label)

    def handle_properties_section_event(self,event):
        for i,p in enumerate(self.group_editor_buttons_parents):
            result = p.handle_event(event, self.group_editor_rect.topleft)
            if result == "TOGGLE" and not p.is_expanded:
                if len(self.group_editor_buttons_parents) > 2:
                    self.group_editor_buttons_parents.remove(p)
                else:
                    self.group_editor_buttons_parents.remove(self.group_editor_buttons_parents[i + 1])
        if self.group_editor_buttons_parents[-1].is_expanded:
            new_y = self.group_editor_buttons_parents[-1].rect.y + self.group_editor_buttons_parents[-1].rect.width * 1.2
            new_parent = ParentButton(self.group_editor_buttons_parents[-1].rect.x, new_y, self.screen_height / 20, self.screen_height / 20, self.buttons_font)
            self.group_editor_buttons_parents.append(new_parent)


if __name__ == "__main__":
    editor = EditorSimulation()
    editor.run()