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
        self.collected = False


class Level:
    def __init__(self, path):
        # pygame.display.set_mode() debe llamarse antes (pytmx usa convert_alpha)
        self.tmx = pytmx.load_pygame(str(path))
        self.tile_w, self.tile_h = self.tmx.tilewidth, self.tmx.tileheight
        self.width = self.tmx.width * self.tile_w
        self.height = self.tmx.height * self.tile_h
        self.name = self.tmx.properties.get("nombre", "")

        self.collisions = []
        self.player_start = pygame.Vector2(self.width / 2, self.height / 2)
        self.zombie_spawns = []
        self.exit_rect = None
        self.pickups = []

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
                    elif obj.name == "salida":
                        self.exit_rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                    elif obj.name in collectible:
                        col, row = int(obj.x // self.tile_w), int(obj.y // self.tile_h)
                        self.pickups.append(Pickup(obj.name, col, row, self.tile_w, None))

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

    def collides(self, rect):
        return rect.collidelist(self.collisions) != -1

    def draw(self, screen, camera):
        screen.blit(self.surface, (0, 0),
                    pygame.Rect(round(camera.x), round(camera.y), *screen.get_size()))

        # Suministros que se pueden recoger (con un aro que late)
        pulse = 14 + 3 * math.sin(pygame.time.get_ticks() / 200)
        for pickup in self.pickups:
            if pickup.collected:
                continue
            x = pickup.col * self.tile_w - round(camera.x)
            y = pickup.row * self.tile_h - round(camera.y)
            if pickup.image is not None:
                screen.blit(pickup.image, (x, y))
            if settings.PICKUP_RING:
                center = (round(pickup.pos.x - camera.x), round(pickup.pos.y - camera.y))
                pygame.draw.circle(screen, (255, 240, 120), center, round(pulse), 1)