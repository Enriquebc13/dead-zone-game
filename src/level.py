import pygame
import pytmx


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

        # El mapa no cambia: se dibuja una sola vez en una superficie
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for layer in self.tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, image in layer.tiles():
                    self.surface.blit(image, (x * self.tile_w, y * self.tile_h))

    def collides(self, rect):
        return rect.collidelist(self.collisions) != -1

    def draw(self, screen, camera):
        screen.blit(self.surface, (0, 0),
                    pygame.Rect(round(camera.x), round(camera.y), *screen.get_size()))