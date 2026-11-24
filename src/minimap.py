"""Minimapa del nivel con los enemigos restantes (tecla M para ocultarlo)."""

import pygame

import settings

# Colores por tipo de enemigo en el minimapa
ENEMY_COLORS = {
    "zombie_normal": (235, 70, 70),
    "zombie_corredor": (255, 225, 60),
    "perro_infectado": (255, 150, 40),
    "zombie_tanque": (230, 70, 230),
}

_visible = True


def toggle():
    """Muestra u oculta el minimapa."""

    global _visible
    _visible = not _visible


def _base(level):
    """Mapa reducido (se calcula una sola vez por nivel)."""

    cached = getattr(level, "_minimap_cache", None)

    if cached is not None:
        return cached

    max_w, max_h = settings.MINIMAP_SIZE
    scale = min(max_w / level.width, max_h / level.height)
    size = (max(1, round(level.width * scale)), max(1, round(level.height * scale)))

    surf = pygame.transform.smoothscale(level.surface, size)
    surf = surf.convert_alpha()

    # Se oscurece para que los puntos destaquen
    shade = pygame.Surface(size, pygame.SRCALPHA)
    shade.fill((0, 0, 0, 90))
    surf.blit(shade, (0, 0))

    level._minimap_cache = (surf, scale)

    return level._minimap_cache


def draw_minimap(canvas, font, level, player, enemies):
    """Dibuja el minimapa arriba a la derecha de la pantalla."""

    if not _visible:
        return

    base, scale = _base(level)
    w, h = base.get_size()

    margin = 12
    x0 = canvas.get_width() - w - margin
    y0 = margin + 20

    canvas.blit(base, (x0, y0))

    def to_map(pos):
        return (x0 + round(pos.x * scale), y0 + round(pos.y * scale))

    # Suministros que aún no se recogen
    for pickup in level.pickups:
        if not pickup.collected:
            px, py = to_map(pickup.pos)
            pygame.draw.rect(canvas, (90, 255, 120), (px - 1, py - 1, 3, 3))

    # Salida del nivel
    exit_rect = getattr(level, "exit_rect", None)

    if exit_rect is not None:
        pygame.draw.rect(
            canvas,
            (80, 220, 255),
            (
                x0 + round(exit_rect.x * scale),
                y0 + round(exit_rect.y * scale),
                max(2, round(exit_rect.w * scale)),
                max(2, round(exit_rect.h * scale)),
            ),
            1,
        )

    # Enemigos vivos
    for enemy in enemies:
        if not enemy.alive:
            continue

        px, py = to_map(enemy.pos)
        color = ENEMY_COLORS.get(enemy.kind, (235, 70, 70))
        radius = 3 if enemy.kind == "zombie_tanque" else 2

        pygame.draw.circle(canvas, color, (px, py), radius)

    # Jugador
    px, py = to_map(player.pos)
    pygame.draw.circle(canvas, (255, 255, 255), (px, py), 4)
    pygame.draw.circle(canvas, (60, 140, 255), (px, py), 3)

    # Zona visible de la cámara
    cam_w, cam_h = canvas.get_size()
    cam_x = max(0, min(level.width - cam_w, player.pos.x - cam_w / 2))
    cam_y = max(0, min(level.height - cam_h, player.pos.y - cam_h / 2))
    pygame.draw.rect(
        canvas,
        (255, 255, 255),
        (
            x0 + round(cam_x * scale),
            y0 + round(cam_y * scale),
            min(w, round(cam_w * scale)),
            min(h, round(cam_h * scale)),
        ),
        1,
    )

    pygame.draw.rect(canvas, (225, 205, 150), (x0 - 1, y0 - 1, w + 2, h + 2), 2)

    alive = sum(1 for e in enemies if e.alive)
    title = font.render(f"ZOMBIES: {alive}/{len(enemies)}", True, (255, 220, 120))
    canvas.blit(title, (x0 + w - title.get_width(), margin - 2))


def draw_enemy_counter(canvas, font, enemies, pos):
    """Barra con el progreso de enemigos eliminados."""

    total = max(1, len(enemies))
    killed = sum(1 for e in enemies if not e.alive)
    bar_w = 240

    pygame.draw.rect(canvas, (30, 30, 30), (*pos, bar_w, 4))
    pygame.draw.rect(
        canvas, (230, 70, 70), (*pos, round(bar_w * killed / total), 4)
    )
    pygame.draw.rect(canvas, (255, 255, 255), (*pos, bar_w, 4), 1)
