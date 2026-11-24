import random

import pygame

import settings
from src.spritesheet import SpriteSheet

# Los cuadros de cada tipo de enemigo se cargan una sola vez y se comparten
_SPRITE_CACHE = {}


def _load_sprites(kind):
    if kind in _SPRITE_CACHE:
        return _SPRITE_CACHE[kind]

    cfg = settings.ENEMY_TYPES[kind]
    sheet = SpriteSheet(
        cfg["sheet"],
        cfg.get("frame_size", settings.ENEMY_FRAME_SIZE),
        cfg.get("cols", settings.ENEMY_COLS),
        cfg["rows"],
    )

    sprites = {}
    for name, spec in cfg["anim"].items():
        if spec is None:
            continue
        row, count = spec
        frames = sheet.get_row(row, cfg["scale"], count)
        flipped = [pygame.transform.flip(f, True, False) for f in frames]
        sprites[name] = (frames, flipped)

    _SPRITE_CACHE[kind] = sprites
    return sprites


class Enemy:
    """Enemigo genérico; sus atributos y sprites se definen en settings."""

    def __init__(self, kind, pos, level=None, patrol_type="none", patrol_points=None,
                 horde_group=None):
        self.kind = kind
        self.cfg = settings.ENEMY_TYPES[kind]
        self.sprites = _load_sprites(kind)

        pos = pygame.Vector2(pos)
        if level is not None:
            pos = level.free_position(pos, self.cfg["foot"])
        self.pos = pos
        self.home = pos.copy()
        self.patrol_type = patrol_type
        self.patrol_points = [pygame.Vector2(point) for point in (patrol_points or [])]
        if self.patrol_type == "ab" and len(self.patrol_points) < 2:
            self.patrol_points = [self.home + pygame.Vector2(-70, 0), self.home + pygame.Vector2(70, 0)]
        if self.patrol_type == "waypoints" and not self.patrol_points:
            self.patrol_points = [self.home.copy()]
        self.patrol_index = 1 if self.patrol_type in ("ab", "waypoints") else 0
        self.horde_group = horde_group
        self.horde_link_radius = 550
        self.ai_state = "PATROL" if patrol_type == "states" else "PATROL"
        self.alert_timer = 0.0
        self.lost_sight_timer = 0.0
        self.returning = False

        self.max_hp = self.cfg["hp"]
        self.hp = self.max_hp
        self.alive = True

        self.facing = -1          # los sprites originales miran a la derecha
        self.state = "idle"
        self.index = 0
        self.timer = 0.0
        self.finished = False

        self.aggro = False
        self.attack_cd = random.uniform(0.0, 0.5)
        self.hit_done = False
        self.stagger_cd = 0.0

        # Rodeo cuando se atora con una pared
        self.detour_timer = 0.0
        self.detour_sign = 1
        self.stuck_time = 0.0

    # --------------------------------
    # ANIMACIÓN
    # --------------------------------

    def _set_state(self, state):
        if state == self.state:
            return
        self.state = state
        self.index = 0
        self.timer = 0.0
        self.finished = False

    def _advance(self, dt, loop):
        frames = self.sprites[self.state][0]
        self.timer += dt
        step = 1.0 / self.cfg["fps"][self.state]
        while self.timer >= step:
            self.timer -= step
            if self.index < len(frames) - 1:
                self.index += 1
            elif loop:
                self.index = 0
            else:
                self.finished = True
                self.timer = 0.0
                break

    # --------------------------------
    # CAJAS
    # --------------------------------

    def foot_rect(self, pos=None):
        pos = self.pos if pos is None else pos
        rect = pygame.Rect(0, 0, *self.cfg["foot"])
        rect.midbottom = (round(pos.x), round(pos.y))
        return rect

    def hit_rect(self):
        rect = pygame.Rect(0, 0, *self.cfg["hit"])
        rect.midbottom = (round(self.pos.x), round(self.pos.y))
        return rect

    # --------------------------------
    # DAÑO
    # --------------------------------

    def take_damage(self, amount):
        if not self.alive:
            return

        self.hp -= amount
        self.aggro = True
        if self.patrol_type == "states":
            self.ai_state = "ALERT"
            self.alert_timer = 0.45

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self._set_state("dead")
            return

        # Cooldown para que no quede paralizado bajo el fuego continuo
        if self.stagger_cd <= 0 and self.state != "attack":
            self._set_state("hurt")
            self.stagger_cd = 0.7

    def knockback(self, direction, distance, level):
        """Empuja al enemigo (golpe de hacha). El tanque casi no se mueve."""
        if not self.alive or distance <= 0:
            return
        direction = pygame.Vector2(direction)
        if direction.length_squared() == 0:
            return
        self._move(direction.normalize() * distance * self.cfg.get("knockback", 1.0), level)

    # --------------------------------
    # MOVIMIENTO
    # --------------------------------

    def _move(self, step, level):
        moved_from = self.pos.copy()
        for axis in ("x", "y"):
            candidate = self.pos.copy()
            setattr(candidate, axis, getattr(candidate, axis) + getattr(step, axis))
            candidate.x = max(0, min(level.width, candidate.x))
            candidate.y = max(0, min(level.height, candidate.y))
            if not level.collides(self.foot_rect(candidate)):
                self.pos = candidate
        return (self.pos - moved_from).length()

    def _separation(self, enemies):
        push = pygame.Vector2()
        for other in enemies:
            if other is self or not other.alive:
                continue
            diff = self.pos - other.pos
            dist = diff.length()
            if 0 < dist < 26:
                push += diff / dist * (26 - dist) / 26
        return push

    # --------------------------------
    # ACTUALIZAR
    # --------------------------------

    def _move_toward(self, target, dt, level, enemies, speed=None):
        target = pygame.Vector2(target)
        delta = target - self.pos
        distance = delta.length()
        if distance <= 3:
            return True
        self.facing = 1 if delta.x > 0 else -1 if delta.x < 0 else self.facing
        direction = delta.normalize()
        direction += self._separation(enemies) * 0.6
        if direction.length_squared():
            direction = direction.normalize()
        step = direction * (speed or self.cfg["speed"]) * dt
        self._move(step, level)
        return self.pos.distance_to(target) <= 8

    def _patrol(self, dt, level, enemies):
        if not self.patrol_points:
            self._set_state("idle")
            self._advance(dt, loop=True)
            return
        target = self.patrol_points[self.patrol_index]
        if self._move_toward(target, dt, level, enemies, self.cfg["speed"] * 0.65):
            if self.patrol_type == "ab":
                self.patrol_index = 1 - self.patrol_index
            else:
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
        self._set_state("walk")
        self._advance(dt, loop=True)

    def update(self, dt, player, level, enemies, sounds=None):
        # Muerto: reproducir la caída y quedarse en el último cuadro
        if not self.alive:
            if not self.finished:
                self._advance(dt, loop=False)
            return

        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.stagger_cd = max(0.0, self.stagger_cd - dt)

        to_player = player.pos - self.pos
        dist = to_player.length()

        # Detección y lógica de IA
        if player.alive:
            if not self.aggro:
                detected_player = dist <= self.cfg["detect"]
                detected_ally = False

                # En el nivel 2, al detectar al jugador un zombi puede alertar
                # a los integrantes cercanos de su mismo grupo.
                if not detected_player and self.horde_group is not None:
                    detected_ally = any(
                        other is not self
                        and other.alive
                        and other.horde_group == self.horde_group
                        and other.aggro
                        and self.pos.distance_to(other.pos) <= self.horde_link_radius
                        for other in enemies
                    )

                if detected_player or detected_ally:
                    self.aggro = True
                    if sounds:
                        sounds.play_zombie("growl")
                    if self.patrol_type == "states":
                        self.ai_state = "ALERT"
                        self.alert_timer = 0.45
            if self.patrol_type == "states" and self.ai_state in ("CHASE", "ATTACK"):
                if dist > self.cfg["detect"] * 1.35:
                    self.lost_sight_timer += dt
                    if self.lost_sight_timer >= 2.5:
                        self.aggro = False
                        self.ai_state = "RETURN"
                else:
                    self.lost_sight_timer = 0.0
        else:
            self.aggro = False
            if self.patrol_type == "states":
                self.ai_state = "RETURN"

        if self.patrol_type == "states":
            if self.ai_state == "ALERT":
                self.alert_timer -= dt
                self._set_state("idle")
                self._advance(dt, loop=True)
                if self.alert_timer <= 0:
                    self.ai_state = "CHASE"
                return
            if self.ai_state == "RETURN" and not self.aggro:
                if self.pos.distance_to(self.home) <= 9:
                    self.ai_state = "PATROL"
                    self.patrol_index = 1 if len(self.patrol_points) > 1 else 0
                else:
                    self._set_state("walk")
                    self._move_toward(self.home, dt, level, enemies, self.cfg["speed"])
                    self._advance(dt, loop=True)
                    return


        # ---- Golpeado: se detiene un instante
        if self.state == "hurt":
            self._advance(dt, loop=False)
            if self.finished:
                self._set_state("walk" if self.aggro else "idle")
            return

        # ---- Atacando
        if self.state == "attack":
            self._advance(dt, loop=False)
            if (not self.hit_done
                    and self.index >= self.cfg["attack_hit_frame"]):
                self.hit_done = True
                self._try_hit(player, dist, sounds, tolerance=1.4)
            if self.finished:
                self.attack_cd = self.cfg["attack_cooldown"]
                self._set_state("walk" if self.aggro else "idle")
            return

        # ---- Sin objetivo
        if not self.aggro:
            if self.patrol_type in ("ab", "waypoints", "states"):
                if self.patrol_type == "states" and not self.patrol_points:
                    self.patrol_points = [self.home + pygame.Vector2(-48, 0), self.home + pygame.Vector2(48, 0)]
                self._patrol(dt, level, enemies)
            else:
                self._set_state("idle")
                self._advance(dt, loop=True)
            return

        # ---- Perseguir / atacar
        if to_player.x:
            self.facing = 1 if to_player.x > 0 else -1

        in_range = dist <= self.cfg["attack_range"]
        if self.patrol_type == "states":
            self.ai_state = "ATTACK" if in_range else "CHASE"

        if in_range and self.attack_cd <= 0:
            if self.cfg["anim"]["attack"] is None:
                # Sin animación de ataque (tanque): daño por contacto
                self._try_hit(player, dist, sounds, tolerance=1.0)
                self.attack_cd = self.cfg["attack_cooldown"]
            else:
                self.hit_done = False
                self._set_state("attack")
                return

        if in_range:
            # Cerca del jugador: espera su turno de ataque
            self._set_state("idle")
            self._advance(dt, loop=True)
            return

        self._set_state("walk")

        direction = to_player / dist if dist else pygame.Vector2()

        # Rodear obstáculos cuando se atora
        if self.detour_timer > 0:
            self.detour_timer -= dt
            direction = (direction + direction.rotate(90 * self.detour_sign) * 1.2)
            if direction.length_squared():
                direction = direction.normalize()

        direction += self._separation(enemies) * 0.6
        if direction.length_squared():
            direction = direction.normalize()

        step = direction * self.cfg["speed"] * dt
        moved = self._move(step, level)

        if moved < step.length() * 0.3:
            self.stuck_time += dt
            if self.stuck_time > 0.25 and self.detour_timer <= 0:
                self.detour_timer = 0.6
                self.detour_sign = random.choice((-1, 1))
                self.stuck_time = 0.0
        else:
            self.stuck_time = 0.0

        self._advance(dt, loop=True)

    def _try_hit(self, player, dist, sounds, tolerance):
        if player.alive and dist <= self.cfg["attack_range"] * tolerance:
            # source = de dónde viene el golpe (el escudo solo cubre el frente)
            player.take_damage(self.cfg["damage"], source=self.pos)
            if sounds:
                sounds.play_zombie("attack")

    # --------------------------------
    # DIBUJAR
    # --------------------------------

    def draw(self, screen, camera):
        frames, flipped = self.sprites[self.state if self.state in self.sprites else "idle"]
        frame = (flipped if self.facing < 0 else frames)[min(self.index, len(frames) - 1)]

        px, py = (v * self.cfg["scale"] for v in self.cfg["pivot"])
        if self.facing < 0:
            px = frame.get_width() - px

        screen.blit(frame, (round(self.pos.x - camera.x - px),
                            round(self.pos.y - camera.y - py)))

        # Barra de vida solo cuando ya recibió daño
        if self.alive and self.hp < self.max_hp:
            w = max(30, self.cfg["hit"][0])
            x = round(self.pos.x - camera.x - w / 2)
            y = round(self.pos.y - camera.y - self.cfg["hit"][1] - 10)
            pygame.draw.rect(screen, (40, 0, 0), (x, y, w, 5))
            pygame.draw.rect(screen, (210, 40, 40), (x, y, round(w * self.hp / self.max_hp), 5))
            pygame.draw.rect(screen, (0, 0, 0), (x, y, w, 5), 1)