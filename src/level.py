import math

import pygame
import pytmx

import settings


class Pickup:
    """Suministro del mapa. Su imagen es el tile que estaba en esa celda."""

    def __init__(self, kind, col, row, tile_size, image):
        self.kind = kind
        self.col = col
        self.row = row
        self.image = image
        self.pos = pygame.Vector2(
            col * tile_size + tile_size / 2,
            row * tile_size + tile_size / 2,
        )
        self.image2 = None  # mitad derecha de la escopeta (ocupa 2 casillas)
        self.collected = False


class Level:
    def __init__(self, path):
        # pygame.display.set_mode() debe llamarse antes (pytmx usa convert_alpha)
        self.tmx = pytmx.load_pygame(str(path))
        self.tile_w, self.tile_h = self.tmx.tilewidth, self.tmx.tileheight
        self.width = self.tmx.width * self.tile_w
        self.height = self.tmx.height * self.tile_h
        self.name = self.tmx.properties.get("nombre", "")
        self._badge_font = None
        self._ui_font = None
        self.dark_ambience = bool(self.tmx.properties.get("ambiente_oscuro", False))

        self.collisions = []
        self.player_start = pygame.Vector2(self.width / 2, self.height / 2)
        self.zombie_spawns = []
        self.patrol_routes = {}
        self.waypoint_routes = {}
        self.exit_rect = None
        self.pickups = []

        # Reja con palanca (nivel 4). gate_anim va de 0 (cerrada) a 1 (abierta);
        # la colisión de la reja solo desaparece cuando termina la animación.
        self.gate_rect = None
        self.gate_open = False
        self.gate_opening = False
        self.gate_anim = 0.0
        self.lever_pos = None
        self.lever_ready = False      # main.py lo activa al despejar la primera calle
        self.signs = []               # (posición, líneas de texto)

        # Solo lo que está en LEVEL_COLLECTIBLES se puede recoger;
        # el resto de objetos del mapa se queda como adorno
        number = self.tmx.properties.get("nivel")
        collectible = settings.LEVEL_COLLECTIBLES.get(
            number, settings.LEVEL_COLLECTIBLES[1]
        )
        for layer in self.tmx.layers:
            if not isinstance(layer, pytmx.TiledObjectGroup):
                continue
            for obj in layer:
                if layer.name == "colisiones":
                    self.collisions.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
                elif layer.name == "puntos":
                    if obj.name == "jugador":
                        self.player_start = pygame.Vector2(obj.x, obj.y)
                    elif obj.name == "zombie":
                        self.zombie_spawns.append(pygame.Vector2(obj.x, obj.y))
                    elif obj.name.startswith("patrol_"):
                        # Nombres esperados: patrol_1_a / patrol_1_b
                        parts = obj.name.split("_")
                        if len(parts) == 3 and parts[1].isdigit():
                            self.patrol_routes.setdefault(int(parts[1]) - 1, {})[parts[2]] = pygame.Vector2(obj.x, obj.y)
                    elif obj.name.startswith("waypoint_"):
                        # Nombres esperados: waypoint_3_1, waypoint_3_2...
                        parts = obj.name.split("_")
                        if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                            self.waypoint_routes.setdefault(int(parts[1]) - 1, []).append(
                                (int(parts[2]), pygame.Vector2(obj.x, obj.y))
                            )
                    elif obj.name == "salida":
                        self.exit_rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                    elif obj.name == "reja":
                        self.gate_rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                    elif obj.name == "palanca":
                        self.lever_pos = pygame.Vector2(obj.x, obj.y)
                    elif obj.name == "letrero":
                        text = str(obj.properties.get("texto", "BAJA LA PALANCA"))
                        self.signs.append((pygame.Vector2(obj.x, obj.y), text.split("|")))
                    elif obj.name in collectible:
                        col, row = int(obj.x // self.tile_w), int(obj.y // self.tile_h)
                        self.pickups.append(Pickup(obj.name, col, row, self.tile_w, None))

        for enemy_index, points in self.waypoint_routes.items():
            self.waypoint_routes[enemy_index] = [point for _, point in sorted(points, key=lambda item: item[0])]

        # El tile del suministro se dibuja aparte (para poder quitarlo al recogerlo)
        skip = set()
        tile_layers = [
            l for l in self.tmx.layers
            if isinstance(l, pytmx.TiledTileLayer) and l.name != "suelo"
        ]
        for pickup in self.pickups:
            for layer in tile_layers:
                gid = layer.data[pickup.row][pickup.col]
                if gid:
                    pickup.image = self.tmx.get_tile_image_by_gid(gid)
                    skip.add((layer.name, pickup.col, pickup.row))
                    # La escopeta del tileset mide 2 casillas de ancho
                    if pickup.kind == "escopeta" and pickup.col + 1 < self.tmx.width:
                        gid2 = layer.data[pickup.row][pickup.col + 1]
                        if gid2 == gid + 1:
                            pickup.image2 = self.tmx.get_tile_image_by_gid(gid2)
                            pickup.pos.x += self.tile_w / 2
                            skip.add((layer.name, pickup.col + 1, pickup.row))
                    break

        # El mapa no cambia: se dibuja una sola vez en una superficie
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for layer in self.tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, image in layer.tiles():
                    if (layer.name, x, y) in skip:
                        continue
                    self.surface.blit(image, (x * self.tile_w, y * self.tile_h))

    def free_position(self, pos, size=(18, 10), margin=6):
        """Si pos cae dentro de una colisión, busca el punto libre más cercano."""
        def ok(p):
            r = pygame.Rect(0, 0, size[0] + margin, size[1] + margin)
            r.midbottom = (round(p.x), round(p.y))
            return (not self.collides(r)
                    and 0 < p.x < self.width and 0 < p.y < self.height)

        p = pygame.Vector2(pos)
        if ok(p):
            return p
        for radius in range(8, 400, 8):
            for angle in range(0, 360, 30):
                q = p + pygame.Vector2(radius, 0).rotate(angle)
                if ok(q):
                    return q
        return p

    # --------------------------------
    # REJA Y PALANCA
    # --------------------------------

    GATE_TIME = 1.6   # segundos que tarda en abrirse la reja

    def near_lever(self, pos, radius=64):
        return self.lever_pos is not None and pos.distance_to(self.lever_pos) <= radius

    def begin_gate_open(self):
        """Baja la palanca: arranca la animación. Devuelve True si se accionó."""
        if self.gate_rect is None or self.gate_open or self.gate_opening:
            return False
        self.gate_opening = True
        return True

    def update_gate(self, dt):
        if self.gate_opening and not self.gate_open:
            self.gate_anim = min(1.0, self.gate_anim + dt / self.GATE_TIME)
            if self.gate_anim >= 1.0:
                self.gate_open = True
                self.gate_opening = False

    def collides(self, rect):
        if rect.collidelist(self.collisions) != -1:
            return True
        # La reja cerrada bloquea a jugador, enemigos y balas
        return (self.gate_rect is not None and not self.gate_open
                and rect.colliderect(self.gate_rect))

    def _font(self):
        if self._ui_font is None:
            self._ui_font = pygame.font.Font(None, 20)
        return self._ui_font

    def _draw_gate(self, screen, camera):
        gate = self.gate_rect.move(-round(camera.x), -round(camera.y))
        if gate.right < 0 or gate.left > screen.get_width():
            return

        # Una vez abierta no se dibuja nada: queda el suelo del paso libre
        if self.gate_open:
            return

        # Fondo oscuro del hueco (se ve entre las hojas mientras se abren)
        pygame.draw.rect(screen, (22, 22, 26), gate)

        # Dos hojas que se recogen hacia los extremos (arriba y abajo)
        half = gate.height // 2
        leaf = max(0, round(half * (1.0 - self.gate_anim)))
        if leaf == 0:
            return
        leaves = (
            pygame.Rect(gate.left, gate.top, gate.width, leaf),
            pygame.Rect(gate.left, gate.bottom - leaf, gate.width, leaf),
        )
        for rect in leaves:
            pygame.draw.rect(screen, (38, 41, 46), rect)
            for gy in range(rect.top + 3, rect.bottom, 8):
                pygame.draw.line(screen, (150, 158, 164), (rect.left, gy), (rect.right - 1, gy), 2)
            for gx in (rect.left + 5, rect.centerx, rect.right - 6):
                pygame.draw.line(screen, (190, 198, 204), (gx, rect.top), (gx, rect.bottom), 3)
            pygame.draw.rect(screen, (215, 220, 225), rect, 2)
        # Temblor de las hojas mientras se mueve
        if self.gate_opening:
            pygame.draw.rect(screen, (255, 200, 80), gate, 1)

    def _draw_lever(self, screen, camera):
        lx = round(self.lever_pos.x - camera.x)
        ly = round(self.lever_pos.y - camera.y)
        pulled = self.gate_opening or self.gate_open
        pygame.draw.rect(screen, (28, 28, 30), (lx - 16, ly - 6, 32, 20), border_radius=4)
        pygame.draw.rect(screen, (120, 125, 130), (lx - 16, ly - 6, 32, 20), 2, border_radius=4)
        tip = (lx + 4, ly + 20) if pulled else (lx + 14, ly - 24)
        color = (90, 220, 110) if pulled else (230, 170, 45)
        pygame.draw.line(screen, color, (lx, ly + 4), tip, 5)
        pygame.draw.circle(screen, color, tip, 5)

        if pulled:
            text, tcolor = "REJA ABIERTA", (140, 235, 150)
        elif self.lever_ready:
            text, tcolor = "E: BAJAR PALANCA", (255, 245, 190)
        else:
            text, tcolor = "BLOQUEADA", (230, 120, 110)
        label = self._font().render(text, True, tcolor)
        rect = label.get_rect(midtop=(lx, ly + 22))
        pygame.draw.rect(screen, (10, 10, 12), rect.inflate(8, 4), border_radius=3)
        screen.blit(label, rect)

    def _draw_sign(self, screen, camera, pos, lines):
        font = self._font()
        labels = [font.render(line, True, (255, 245, 190)) for line in lines]
        w = max(l.get_width() for l in labels) + 18
        h = 10 + 17 * len(labels)
        cx, cy = round(pos.x - camera.x), round(pos.y - camera.y)
        if cx < -w or cx > screen.get_width() + w:
            return
        board = pygame.Rect(0, 0, w, h)
        board.center = (cx, cy)
        # Poste
        pygame.draw.rect(screen, (60, 38, 20), (cx - 3, board.bottom, 6, 16))
        pygame.draw.rect(screen, (75, 48, 24), board, border_radius=4)
        pygame.draw.rect(screen, (225, 205, 150), board, 2, border_radius=4)
        for i, label in enumerate(labels):
            screen.blit(label, label.get_rect(center=(cx, board.top + 5 + 8 + 17 * i)))

    def draw(self, screen, camera):
        screen.blit(self.surface, (0, 0),
                    pygame.Rect(round(camera.x), round(camera.y), *screen.get_size()))
        if self.dark_ambience:
            shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            shade.fill((8, 12, 24, 92))
            screen.blit(shade, (0, 0))

        if self.gate_rect is not None:
            self._draw_gate(screen, camera)
        if self.lever_pos is not None:
            self._draw_lever(screen, camera)
        for pos, lines in self.signs:
            self._draw_sign(screen, camera, pos, lines)

        # Suministros que se pueden recoger (con un aro que late)
        pulse = 14 + 3 * math.sin(pygame.time.get_ticks() / 200)
        for pickup in self.pickups:
            if pickup.collected:
                continue
            x = pickup.col * self.tile_w - round(camera.x)
            y = pickup.row * self.tile_h - round(camera.y)
            if pickup.image is not None:
                screen.blit(pickup.image, (x, y))
            if pickup.image2 is not None:
                screen.blit(pickup.image2, (x + self.tile_w, y))
            if pickup.kind in ("municion_rifle", "municion_escopeta") and pickup.image is not None:
                # Insignia pequeña: R = munición de rifle, S = munición de escopeta
                label = "R" if pickup.kind == "municion_rifle" else "S"
                badge = (x + self.tile_w - 6, y + 6)
                pygame.draw.circle(screen, (18, 18, 22), badge, 8)
                pygame.draw.circle(screen, (235, 205, 90), badge, 8, 1)
                if self._badge_font is None:
                    self._badge_font = pygame.font.Font(None, 16)
                glyph = self._badge_font.render(label, True, (255, 255, 255))
                screen.blit(glyph, glyph.get_rect(center=badge))
            elif pickup.image is None:
                pygame.draw.circle(screen, (25, 25, 25), (x + self.tile_w // 2, y + self.tile_h // 2), 13)
                pygame.draw.circle(screen, (235, 205, 90), (x + self.tile_w // 2, y + self.tile_h // 2), 13, 2)
            if settings.PICKUP_RING:
                center = (round(pickup.pos.x - camera.x), round(pickup.pos.y - camera.y))
                pygame.draw.circle(screen, (255, 240, 120), center, round(pulse), 1)