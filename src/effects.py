import math

import pygame

import settings

# efectos_spritesheet.png: celdas de 64x64, 8 columnas x 5 filas
#   fila 1: balas / trazadoras / casquillos
#   fila 2: sangre (7 cuadros)
#   fila 3: chispas de impacto en objetos (7 cuadros)
#   fila 4: impacto sobre el escudo, anillos azules (7 cuadros)
CELL = 64
EFFECT_ROWS = {"blood": 2, "sparks": 3, "shield": 4}
EFFECT_FRAMES = 7

_sheet = None
_cache = {}
_tracer_cache = {}


def _get_sheet():
    global _sheet
    if _sheet is None:
        _sheet = pygame.image.load(str(settings.EFFECTS_SHEET)).convert_alpha()
    return _sheet


def _cell(col, row):
    return _get_sheet().subsurface(
        pygame.Rect(col * CELL, row * CELL, CELL, CELL)
    ).copy()


def _frames(kind, scale, angle):
    key = (kind, scale, round(angle / 15) * 15)
    if key in _cache:
        return _cache[key]

    frames = []
    for col in range(EFFECT_FRAMES):
        img = _cell(col, EFFECT_ROWS[kind])
        size = round(CELL * scale)
        img = pygame.transform.scale(img, (size, size))
        if key[2]:
            img = pygame.transform.rotate(img, key[2])
        frames.append(img)

    _cache[key] = frames
    return frames


class Effect:
    """Animación corta (sangre, chispas, impacto de escudo) en una posición."""

    def __init__(self, kind, pos, direction=None, scale=0.9, fps=22):
        self.pos = pygame.Vector2(pos)
        self.fps = fps
        self.timer = 0.0
        self.alive = True

        # Las chispas salen de vuelta hacia el tirador
        angle = 0
        if kind == "sparks" and direction is not None and direction.length_squared():
            d = pygame.Vector2(direction).normalize()
            angle = math.degrees(math.atan2(-d.x, -d.y))

        self.frames = _frames(kind, scale, angle)

    def update(self, dt):
        self.timer += dt
        if int(self.timer * self.fps) >= len(self.frames):
            self.alive = False

    def draw(self, screen, camera):
        if not self.alive:
            return
        img = self.frames[min(int(self.timer * self.fps), len(self.frames) - 1)]
        rect = img.get_rect(center=(round(self.pos.x - camera.x),
                                    round(self.pos.y - camera.y)))
        screen.blit(img, rect)


def tracer_image(direction):
    """Trazadora del rifle girada hacia donde viaja la bala (cabeza en el centro)."""
    angle = round(math.degrees(math.atan2(-direction.y, direction.x)) / 3) * 3
    if angle in _tracer_cache:
        return _tracer_cache[angle]

    cell = _cell(1, 1)                       # trazadora larga
    box = cell.get_bounding_rect()
    img = cell.subsurface(box).copy()
    img = pygame.transform.smoothscale(
        img, (max(1, round(img.get_width() * 0.7)), max(1, round(img.get_height() * 0.7)))
    )

    w, h = img.get_size()
    pad = pygame.Surface((2 * w + 2, 2 * h + 2), pygame.SRCALPHA)
    cx, cy = pad.get_width() // 2, pad.get_height() // 2
    pad.blit(img, (cx - w, cy - h // 2))     # cabeza (derecha) en el centro
    rotated = pygame.transform.rotate(pad, angle)

    _tracer_cache[angle] = rotated
    return rotated
