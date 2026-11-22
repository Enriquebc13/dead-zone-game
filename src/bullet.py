import pygame

from src.effects import Effect, tracer_image


class Bullet:
    """Bala del jugador: viaja en línea recta hasta chocar o agotar su alcance."""

    def __init__(self, pos, direction, damage, speed, max_distance,
                 pellet=False, lead_from=None):
        self.pos = pygame.Vector2(pos)
        self.dir = pygame.Vector2(direction).normalize()
        self.damage = damage
        self.speed = speed
        self.remaining = max_distance
        self.pellet = pellet
        self.alive = True

        # Tramo pecho -> boca del arma: se revisa una vez para poder
        # pegarle a un zombie que ya está pegado al soldado
        self.lead_from = pygame.Vector2(lead_from) if lead_from is not None else None

    def _hit_enemy(self, enemy, point, effects):
        enemy.take_damage(self.damage)
        effects.append(Effect("blood", point, scale=0.8 if enemy.max_hp < 200 else 1.1))
        self.alive = False

    def update(self, dt, level, enemies, effects):
        if not self.alive:
            return

        # Primer cuadro: tramo entre el cuerpo y la boca del arma
        if self.lead_from is not None:
            a = (round(self.lead_from.x), round(self.lead_from.y))
            b = (round(self.pos.x), round(self.pos.y))
            for enemy in enemies:
                if not enemy.alive:
                    continue
                clip = enemy.hit_rect().clipline(a, b)
                if clip:
                    self._hit_enemy(enemy, clip[0], effects)
                    return
            self.lead_from = None

        distance = min(self.speed * dt, self.remaining)
        # Dos pasos por cuadro para no atravesar enemigos delgados
        steps = 2
        for _ in range(steps):
            self.pos += self.dir * (distance / steps)

            if not (0 <= self.pos.x <= level.width and 0 <= self.pos.y <= level.height):
                self.alive = False
                return

            if level.collides(pygame.Rect(int(self.pos.x) - 1, int(self.pos.y) - 1, 2, 2)):
                effects.append(Effect("sparks", self.pos, self.dir, scale=0.7))
                self.alive = False
                return

            for enemy in enemies:
                if enemy.alive and enemy.hit_rect().collidepoint(self.pos):
                    self._hit_enemy(enemy, self.pos, effects)
                    return

        self.remaining -= distance
        if self.remaining <= 0:
            self.alive = False

    def draw(self, screen, camera):
        x, y = self.pos.x - camera.x, self.pos.y - camera.y

        if self.pellet:
            tail = self.pos - self.dir * 6
            pygame.draw.line(screen, (255, 200, 90), (x, y),
                             (tail.x - camera.x, tail.y - camera.y), 2)
            return

        img = tracer_image(self.dir)
        screen.blit(img, img.get_rect(center=(round(x), round(y))))
