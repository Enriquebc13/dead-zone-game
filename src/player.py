import random

import pygame

import settings
from src.animation import Animation
import math

from src.bullet import Bullet
from src.spritesheet import SpriteSheet


class Player:

    def __init__(self, pos, sounds):

        self.pos = pygame.Vector2(pos)
        self.facing = 1

        self.weapon = "rifle"
        self.state = "idle"

        self.sounds = sounds

        # Vida y combate
        self.max_hp = settings.PLAYER_MAX_HP
        self.hp = self.max_hp
        self.alive = True
        self.dead_done = False          # terminó la animación de muerte
        self.invuln = 0.0               # tiempo restante sin recibir daño
        self.aim = pygame.Vector2(pos) + (100, 0)   # punto del mouse en el mundo
        self.pending_bullets = []       # balas nuevas; main las recoge
        self.pending_effects = []       # efectos (sangre / escudo) nuevos
        self.aim_angle = 0.0            # giro del torso (+ = hacia arriba)
        self.fire_frames_done = []
        self._tilt_cache = {}

        self.shield_active = False
        self.shield_sound_played = False

        # Control de sonidos de disparo
        self.shoot_sounds_played = []

        # Control de sonidos de recoger suministro y muerte
        self.pickup_sound_played = False
        self.dead_sound_played = False

        # Animaciones de ambas armas
        self.anims = {
            "rifle": self._build(settings.SOLDIER_RIFLE_SHEET),
            "shotgun": self._build(settings.SOLDIER_SHOTGUN_SHEET),
        }

        # Animaciones adicionales
        self.extra_anims = {
            "dead": self._build_extra(
                settings.SOLDIER_DEAD_SHEET,
                settings.SOLDIER_DEAD_COLS,
                settings.SOLDIER_DEAD_ROWS,
                "dead"
            ),

            "pickup": self._build_extra(
                settings.SOLDIER_PICKUP_SHEET,
                settings.SOLDIER_PICKUP_COLS,
                settings.SOLDIER_PICKUP_ROWS,
                "pickup"
            )
        }

        self.anim = self.anims[self.weapon]["idle"]

        self.action_states = (
            "shoot",
            "shield",
            "reload",
            "remove_shield",
            "dead",
            "pickup"
        )

    # --------------------------------
    # CONSTRUIR ANIMACIONES
    # --------------------------------

    @staticmethod
    def _build(sheet_path):

        sheet = SpriteSheet(
            sheet_path,
            settings.SOLDIER_FRAME_SIZE,
            settings.SOLDIER_COLS,
            settings.SOLDIER_ROWS
        )

        s = settings.SOLDIER_SCALE
        fps = settings.ANIMATION_FPS

        return {

            "idle": Animation(
                [sheet.get_frame(0, settings.ROW_FIRE, s)],
                fps["idle"]
            ),

            "walk": Animation(
                sheet.get_row(settings.ROW_WALK, s),
                fps["walk"]
            ),

            "run": Animation(
                sheet.get_row(settings.ROW_RUN, s),
                fps["run"]
            ),

            "shoot": Animation(
                sheet.get_row(settings.ROW_FIRE, s),
                fps["shoot"],
                loop=False
            ),

            "shield": Animation(
                sheet.get_row(settings.ROW_SHIELD, s),
                fps["shield"],
                loop=False
            ),

            "reload": Animation(
                sheet.get_row(settings.ROW_RELOAD, s),
                fps["reload"],
                loop=False
            )
        }

    # --------------------------------
    # CONSTRUIR ANIMACIONES ADICIONALES
    # --------------------------------

    @staticmethod
    def _build_extra(sheet_path, cols, rows, animation_name):

        sheet = SpriteSheet(
            sheet_path,
            settings.SOLDIER_FRAME_SIZE,
            cols,
            rows
        )

        return Animation(
            sheet.get_row(0, settings.SOLDIER_SCALE),
            settings.ANIMATION_FPS[animation_name],
            loop=False
        )

    # --------------------------------
    # REPRODUCIR ANIMACIONES DE PRUEBA
    # --------------------------------

    def play_test_animation(self, animation_name):

        if animation_name not in self.extra_anims:
            return

        # No interrumpir otra acción
        if self.state in self.action_states:
            return

        self.sounds.stop_footsteps()

        self.state = animation_name
        self.anim = self.extra_anims[animation_name]
        self.anim.reset()

        # Preparar los sonidos de la animación
        if animation_name == "pickup":
            self.pickup_sound_played = False

        elif animation_name == "dead":
            self.dead_sound_played = False

    # --------------------------------
    # CAMBIAR ARMA
    # --------------------------------

    def set_weapon(self, weapon):

        if weapon not in self.anims:
            return

        if weapon == self.weapon:
            return

        # No cambiar de arma durante una acción
        if self.state in self.action_states:
            return

        new_anim = self.anims[weapon][self.state]

        new_anim.index = self.anim.index
        new_anim.timer = self.anim.timer

        self.weapon = weapon
        self.anim = new_anim

    # --------------------------------
    # INICIAR ACCIÓN
    # --------------------------------

    def play_action(self, action):

        if action not in ("shoot", "reload"):
            return

        if not self.alive:
            return

        # No interrumpir el escudo ni otras acciones
        if self.state in self.action_states:
            return

        self.sounds.stop_footsteps()

        self.state = action
        self.anim = self.anims[self.weapon][action]
        self.anim.reset()

        # Preparar sonidos de la acción
        if action == "shoot":

            self.shoot_sounds_played = []
            self.fire_frames_done = []

        elif action == "reload":

            self.sounds.play_reload_sound(self.weapon)

    # --------------------------------
    # ACTIVAR / DESACTIVAR ESCUDO
    # --------------------------------

    def toggle_shield(self):

        if not self.alive:
            return

        # Si el escudo está activo, comenzar a quitarlo
        if self.shield_active:

            self.shield_active = False
            self.state = "remove_shield"

            # Reproducir la animación del escudo al revés
            shield_frames = self.anims[self.weapon]["shield"].frames

            self.anim = Animation(
                list(reversed(shield_frames)),
                settings.ANIMATION_FPS["shield"],
                loop=False
            )

            return

        # No activar durante otras acciones
        if self.state in (
            "shoot",
            "reload",
            "remove_shield",
            "dead",
            "pickup"
        ):
            return

        self.sounds.stop_footsteps()

        self.shield_active = True
        self.shield_sound_played = False

        self.state = "shield"

        self.anim = self.anims[self.weapon]["shield"]
        self.anim.reset()

    # --------------------------------
    # DISPARO
    # --------------------------------

    def muzzle(self):
        """Punta del cañón en el mundo, según el giro actual del torso."""
        s = settings.SOLDIER_SCALE
        tip_x, tip_y = settings.GUN_TIP[self.weapon]
        hip_x, hip_y = settings.TORSO_HIP

        # Vector cadera -> punta del cañón (y positiva hacia arriba)
        vx = (tip_x - hip_x) * s
        vy = (hip_y - tip_y) * s

        a = math.radians(self.aim_angle)
        rx = vx * math.cos(a) - vy * math.sin(a)
        ry = vx * math.sin(a) + vy * math.cos(a)

        hip_up = (settings.SOLDIER_PIVOT[1] - hip_y) * s
        return pygame.Vector2(self.pos.x + self.facing * rx,
                              self.pos.y - hip_up - ry)

    def _update_aim_angle(self, dt):
        """Ángulo hacia el mouse (+ arriba, - abajo), suavizado y limitado."""
        s = settings.SOLDIER_SCALE
        hip_up = (settings.SOLDIER_PIVOT[1] - settings.TORSO_HIP[1]) * s
        dx = max(1.0, abs(self.aim.x - self.pos.x))
        dy = (self.pos.y - hip_up) - self.aim.y

        target = math.degrees(math.atan2(dy, dx))
        limit = settings.AIM_MAX_ANGLE
        target = max(-limit, min(limit, target))

        self.aim_angle += (target - self.aim_angle) * min(1.0, settings.AIM_SMOOTH * dt)

    def try_shoot(self):
        """Dispara si no está haciendo otra acción (la usan clic izq. y J)."""
        if self.alive:
            self.play_action("shoot")

    def _fire(self):
        origin = self.muzzle()
        direction = self.aim - origin

        if direction.length() < 8:
            direction = pygame.Vector2(self.facing, 0)
        direction = direction.normalize()

        # La bala sale de la boca del arma; lead_from cubre el tramo
        # cuerpo -> cañón por si el zombie ya está pegado al soldado
        lead = pygame.Vector2(self.pos.x, origin.y)

        if self.weapon == "shotgun":
            spread = settings.SHOTGUN_SPREAD
            for _ in range(settings.SHOTGUN_PELLETS):
                self.pending_bullets.append(Bullet(
                    origin, direction.rotate(random.uniform(-spread, spread)),
                    settings.SHOTGUN_DAMAGE, settings.SHOTGUN_BULLET_SPEED,
                    settings.SHOTGUN_RANGE, pellet=True, lead_from=lead))
        else:
            spread = settings.RIFLE_SPREAD
            self.pending_bullets.append(Bullet(
                origin, direction.rotate(random.uniform(-spread, spread)),
                settings.RIFLE_DAMAGE, settings.RIFLE_BULLET_SPEED,
                settings.RIFLE_RANGE, lead_from=lead))

    # --------------------------------
    # DAÑO Y MUERTE
    # --------------------------------

    def take_damage(self, amount):
        if not self.alive or self.invuln > 0:
            return

        if self.shield_active:
            amount *= settings.SHIELD_DAMAGE_MULT
            self.pending_effects.append((
                "shield",
                (self.pos.x + self.facing * 30, self.pos.y - 45)
            ))
        else:
            self.pending_effects.append(("blood", (self.pos.x, self.pos.y - 50)))

        self.hp = max(0, self.hp - amount)
        self.invuln = settings.PLAYER_INVULNERABLE_TIME

        if self.hp <= 0:
            self.die()

    def die(self):
        self.alive = False
        self.shield_active = False
        self.pending_bullets.clear()
        self.sounds.stop_footsteps()

        self.state = "dead"
        self.anim = self.extra_anims["dead"]
        self.anim.reset()
        self.dead_sound_played = False

    # --------------------------------
    # COLISIONES
    # --------------------------------

    def _foot_rect(self, pos):

        rect = pygame.Rect(
            0, 0, *settings.FOOT_SIZE
        )

        rect.midbottom = (
            round(pos.x),
            round(pos.y)
        )

        return rect

    # --------------------------------
    # ACTUALIZAR JUGADOR
    # --------------------------------

    def update(self, dt, keys, level):

        self.invuln = max(0.0, self.invuln - dt)

        # MUERTO: reproducir la caída y quedarse en el suelo
        if not self.alive:

            self.anim.update(dt)

            if (
                not self.dead_sound_played
                and self.anim.index >= settings.DEAD_SOUND_FRAME - 1
            ):
                self.sounds.play_dead_sound()
                self.dead_sound_played = True

            if self.anim.finished:
                self.dead_done = True

            return

        # El soldado siempre mira hacia donde apunta el mouse
        self.facing = 1 if self.aim.x >= self.pos.x else -1
        self._update_aim_angle(dt)

        # ESCUDO ACTIVO
        if self.shield_active:

            self.anim.update(dt)

            # Reproducir sonido en el fotograma configurado
            if (
                not self.shield_sound_played
                and self.anim.index >= settings.SHIELD_SOUND_FRAME - 1
            ):

                self.sounds.play_shield_sound()
                self.shield_sound_played = True

            return

        # --------------------------------
        # OTRAS ACCIONES Y ANIMACIONES
        # --------------------------------

        if self.state in (
            "shoot",
            "reload",
            "remove_shield",
            "dead",
            "pickup"
        ):

            self.anim.update(dt)

            # Sincronizar los dos disparos con la animación
            if self.state == "shoot":

                for i, frame in enumerate(settings.SHOOT_SOUND_FRAMES):

                    if (
                        self.anim.index >= frame - 1
                        and i not in self.shoot_sounds_played
                    ):

                        self.sounds.play_shoot_sound(self.weapon)
                        self.shoot_sounds_played.append(i)

                # Las balas salen en los cuadros con fogonazo
                for i, frame in enumerate(settings.FIRE_FRAMES[self.weapon]):

                    if (
                        self.anim.index >= frame
                        and i not in self.fire_frames_done
                    ):

                        self._fire()
                        self.fire_frames_done.append(i)

            # Sonido de recoger suministro en su fotograma
            elif self.state == "pickup":

                if (
                    not self.pickup_sound_played
                    and self.anim.index >= settings.PICKUP_SOUND_FRAME - 1
                ):

                    self.sounds.play_pickup_sound()
                    self.pickup_sound_played = True

            # Sonido de muerte en su fotograma
            elif self.state == "dead":

                if (
                    not self.dead_sound_played
                    and self.anim.index >= settings.DEAD_SOUND_FRAME - 1
                ):

                    self.sounds.play_dead_sound()
                    self.dead_sound_played = True

            # Cuando termina la animación,
            # regresar al estado de reposo
            if self.anim.finished:

                self.state = "idle"
                self.anim = self.anims[self.weapon]["idle"]
                self.anim.reset()

            return

        # --------------------------------
        # MOVIMIENTO
        # --------------------------------

        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w]
        )

        run = (
            keys[pygame.K_LSHIFT]
            or keys[pygame.K_RSHIFT]
        )

        moving = direction.length_squared() > 0

        new_state = (
            "run" if run else "walk"
        ) if moving else "idle"

        if new_state != self.state:

            new_anim = self.anims[self.weapon][new_state]

            if new_state in ("walk", "run") and self.state in ("walk", "run"):

                new_anim.index = self.anim.index
                new_anim.timer = self.anim.timer

            else:
                new_anim.reset()

            self.state = new_state
            self.anim = new_anim

        # --------------------------------
        # SONIDOS DE MOVIMIENTO
        # --------------------------------

        if moving:

            movement_sound = "run" if run else "walk"

            self.sounds.play_footsteps(movement_sound)

        else:

            self.sounds.stop_footsteps()

        # --------------------------------
        # DIRECCIÓN Y MOVIMIENTO
        # --------------------------------

        if moving:

            speed = (
                settings.RUN_SPEED
                if run else settings.WALK_SPEED
            )

            step = direction.normalize() * speed * dt

            # Ejes separados para evitar atravesar paredes
            for axis in ("x", "y"):

                candidate = self.pos.copy()

                setattr(
                    candidate,
                    axis,
                    getattr(candidate, axis) + getattr(step, axis)
                )

                candidate.x = max(
                    0,
                    min(level.width, candidate.x)
                )

                candidate.y = max(
                    0,
                    min(level.height, candidate.y)
                )

                if not level.collides(self._foot_rect(candidate)):
                    self.pos = candidate

        self.anim.update(dt)

    # --------------------------------
    # GIRO DEL TORSO
    # --------------------------------

    def _tilt_frame(self, frame, flipped, angle):
        """Piernas fijas; cabeza, torso y arma giran sobre la cadera."""
        if abs(angle) < 1:
            return frame

        key = (id(frame), round(angle))
        cached = self._tilt_cache.get(key)
        if cached is not None:
            return cached

        s = settings.SOLDIER_SCALE
        w, h = frame.get_size()
        cut = round(settings.TORSO_CUT * s)
        hx = settings.TORSO_HIP[0] * s
        hy = settings.TORSO_HIP[1] * s

        if flipped:
            hx = w - hx
            angle = -angle

        out = pygame.Surface((w, h), pygame.SRCALPHA)

        legs = frame.copy()
        legs.fill((0, 0, 0, 0), pygame.Rect(0, 0, w, cut))
        out.blit(legs, (0, 0))

        upper = frame.subsurface(pygame.Rect(0, 0, w, cut))
        pad = pygame.Surface((2 * w, 2 * h), pygame.SRCALPHA)
        ox, oy = round(w - hx), round(h - hy)
        pad.blit(upper, (ox, oy))

        rotated = pygame.transform.rotate(pad, angle)
        rect = rotated.get_rect(center=(w, h))
        out.blit(rotated, (rect.x - ox, rect.y - oy))

        self._tilt_cache[key] = out
        return out

    # --------------------------------
    # DIBUJAR JUGADOR
    # --------------------------------

    def draw(self, screen, camera):

        frame = self.anim.image(
            flipped=self.facing < 0
        )

        # Giro del torso hacia el mouse (solo mientras camina, está quieto o dispara)
        if self.state in ("idle", "walk", "run", "shoot", "reload"):
            frame = self._tilt_frame(frame, self.facing < 0, self.aim_angle)

        # Parpadeo rojo al recibir daño
        if self.alive and self.invuln > 0 and int(self.invuln * 20) % 2 == 0:
            frame = frame.copy()
            frame.fill((120, 0, 0), special_flags=pygame.BLEND_RGB_ADD)

        px, py = (
            v * settings.SOLDIER_SCALE
            for v in settings.SOLDIER_PIVOT
        )

        if self.facing < 0:
            px = frame.get_width() - px

        screen.blit(
            frame,
            (
                round(self.pos.x - camera.x - px),
                round(self.pos.y - camera.y - py)
            )
        )