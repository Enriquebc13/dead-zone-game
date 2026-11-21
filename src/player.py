import pygame

import settings
from src.animation import Animation
from src.spritesheet import SpriteSheet


class Player:

    def __init__(self, pos, sounds):

        self.pos = pygame.Vector2(pos)
        self.facing = 1

        self.weapon = "rifle"
        self.state = "idle"

        self.sounds = sounds
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

        elif action == "reload":

            self.sounds.play_reload_sound(self.weapon)

    # --------------------------------
    # ACTIVAR / DESACTIVAR ESCUDO
    # --------------------------------

    def toggle_shield(self):

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

            if direction.x:
                self.facing = 1 if direction.x > 0 else -1

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
    # DIBUJAR JUGADOR
    # --------------------------------

    def draw(self, screen, camera):

        frame = self.anim.image(
            flipped=self.facing < 0
        )

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