import random
import pygame
import settings
import math

from src.animation import Animation
from src.bullet import Bullet
from src.spritesheet import SpriteSheet


class Player:

    def __init__(self, pos, sounds, weapons=None):

        self.pos = pygame.Vector2(pos)
        self.facing = 1

        # "weapon" = arma de fuego que se ve en pantalla (rifle / shotgun)
        self.weapon = "rifle"
        self.state = "idle"

        # Armas del nivel ("axe" = hacha) y la que está equipada
        self.unlocked = set(weapons or ("rifle", "axe"))
        self.equipped = "rifle"

        # Munición por arma de fuego: cargador (mag) y reserva
        self.ammo = {gun: dict(values) for gun, values in settings.AMMO.items()}

        # Golpe de hacha
        self.axe_hit_done = False
        self.pending_melee = False

        self.sounds = sounds

        # Vida y combate
        self.max_hp = settings.PLAYER_MAX_HP
        self.hp = self.max_hp
        self.alive = True
        self.dead_done = False
        self.invuln = 0.0

        self.aim = pygame.Vector2(pos) + (100, 0)
        self.pending_bullets = []
        self.pending_effects = []

        self.aim_angle = 0.0
        self.aim_dir = ""
        self.fire_dir = ""
        self.fire_frames_done = []

        self.shield_active = False
        self.shield_sound_played = False

        # Control de sonidos
        self.shoot_sounds_played = []
        self.pickup_sound_played = False
        self.dead_sound_played = False
        self.axe_sound_played = False

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
            ),

            "axe": self._build_extra(
                settings.SOLDIER_AXE_SHEET,
                settings.SOLDIER_AXE_COLS,
                settings.SOLDIER_AXE_ROWS,
                "axe",
                frame_size=(320, 220)
            ),

            # Animación al sacar el hacha
            "switch_axe": self._build_extra(
                settings.SOLDIER_SWITCH_AXE_SHEET,
                settings.SOLDIER_SWITCH_AXE_COLS,
                settings.SOLDIER_SWITCH_AXE_ROWS,
                "switch_axe",
                frame_size=settings.SOLDIER_SWITCH_AXE_FRAME_SIZE
            ),

            # Caminar con el hacha equipada (en bucle)
            "walk_axe": self._build_extra(
                settings.SOLDIER_WALK_AXE_SHEET,
                settings.SOLDIER_WALK_AXE_COLS,
                settings.SOLDIER_WALK_AXE_ROWS,
                "walk_axe",
                frame_size=settings.SOLDIER_WALK_AXE_FRAME_SIZE,
                loop=True
            ),
        }

        # Reposo con hacha: primer cuadro de la caminata
        self.extra_anims["idle_axe"] = Animation(
            [self.extra_anims["walk_axe"].frames[0]],
            settings.ANIMATION_FPS["idle"]
        )

        self.anim_key = "idle"
        self.anim = self.anims[self.weapon]["idle"]

        # Acciones que no pueden interrumpirse
        self.action_states = (
            "shoot",
            "shield",
            "reload",
            "remove_shield",
            "dead",
            "pickup",
            "axe",
            "switch_axe"
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
        f = settings.IDLE_AIM_FRAME

        return {

            # Reposo apuntando
            "idle": Animation(
                [sheet.get_frame(f, settings.ROW_FIRE, s)],
                fps["idle"]
            ),

            "idle_up": Animation(
                [sheet.get_frame(f, settings.ROW_FIRE_UP, s)],
                fps["idle"]
            ),

            "idle_down": Animation(
                [sheet.get_frame(f, settings.ROW_FIRE_DOWN, s)],
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

            "shoot_up": Animation(
                sheet.get_row(settings.ROW_FIRE_UP, s),
                fps["shoot"],
                loop=False
            ),

            "shoot_down": Animation(
                sheet.get_row(settings.ROW_FIRE_DOWN, s),
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
    def _build_extra(
        sheet_path,
        cols,
        rows,
        animation_name,
        frame_size=None,
        loop=False
    ):

        if frame_size is None:
            frame_size = settings.SOLDIER_FRAME_SIZE

        sheet = SpriteSheet(
            sheet_path,
            frame_size,
            cols,
            rows
        )

        return Animation(
            sheet.get_row(0, settings.SOLDIER_SCALE),
            settings.ANIMATION_FPS[animation_name],
            loop=loop
        )

    # --------------------------------
    # REPRODUCIR ANIMACIONES DE PRUEBA
    # --------------------------------

    def play_test_animation(self, animation_name):

        if animation_name not in self.extra_anims:
            return

        if self.state in self.action_states:
            return

        if not self.alive:
            return

        self.sounds.stop_footsteps()

        self.state = animation_name
        self.anim_key = animation_name
        self.anim = self.extra_anims[animation_name]
        self.anim.reset()

        if animation_name == "pickup":
            self.pickup_sound_played = False

        elif animation_name == "dead":
            self.dead_sound_played = False

        elif animation_name == "axe":
            self.axe_sound_played = False

    # --------------------------------
    # REPOSO SEGÚN EL ARMA EQUIPADA
    # --------------------------------

    def _rest_anim(self):
        """Clave y animación de reposo según el arma equipada."""

        if self.equipped == "axe":
            return "idle_axe", self.extra_anims["idle_axe"]

        key = "idle" + self.aim_dir
        return key, self.anims[self.weapon][key]

    # --------------------------------
    # CAMBIAR ARMA
    # --------------------------------

    def set_weapon(self, weapon):

        if weapon not in self.anims:
            return

        if weapon == self.weapon:
            return

        if self.state in self.action_states:
            return

        key = self.anim_key

        # Si la animación actual no existe en la otra arma
        # (por ejemplo walk_axe), usar el reposo
        if key not in self.anims[weapon]:
            key = "idle" + self.aim_dir

        new_anim = self.anims[weapon][key]

        if key == self.anim_key:
            new_anim.index = self.anim.index
            new_anim.timer = self.anim.timer

        self.anim_key = key
        self.weapon = weapon
        self.anim = new_anim

    # --------------------------------
    # INICIAR ACCIÓN
    # --------------------------------

    def play_action(self, action):

        if action not in ("shoot", "reload", "axe"):
            return

        if not self.alive:
            return

        if self.state in self.action_states:
            return

        # Recargar solo si falta munición en el cargador y hay reserva
        if action == "reload":

            ammo = self.ammo[self.weapon]
            full = settings.AMMO[self.weapon]["mag_size"]

            if ammo["mag"] >= full or ammo["reserve"] <= 0:
                return

        self.sounds.stop_footsteps()

        self.state = action

        if action == "shoot":

            self.fire_dir = self.aim_dir
            self.anim_key = "shoot" + self.fire_dir

            self.anim = self.anims[self.weapon][self.anim_key]

            self.shoot_sounds_played = []
            self.fire_frames_done = []

        elif action == "axe":

            self.anim_key = "axe"
            self.anim = self.extra_anims["axe"]

            self.axe_sound_played = False
            self.axe_hit_done = False

        else:

            self.anim_key = action
            self.anim = self.anims[self.weapon][self.anim_key]

            if action == "reload":
                self.sounds.play_reload_sound(self.weapon)

        self.anim.reset()

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
            self.anim_key = "remove_shield"

            shield_frames = self.anims[self.weapon]["shield"].frames

            self.anim = Animation(
                list(reversed(shield_frames)),
                settings.ANIMATION_FPS["shield"],
                loop=False
            )

            return

        # No activar durante otras acciones
        if self.state in self.action_states:
            return

        self.sounds.stop_footsteps()

        self.shield_active = True
        self.shield_sound_played = False

        self.state = "shield"
        self.anim_key = "shield"

        self.anim = self.anims[self.weapon]["shield"]
        self.anim.reset()

    # --------------------------------
    # DISPARO
    # --------------------------------

    def muzzle(self):

        """Punta del cañón en el mundo."""

        s = settings.SOLDIER_SCALE
        tip_x, tip_y = settings.GUN_TIP[self.weapon][self.fire_dir]
        piv_x, piv_y = settings.SOLDIER_PIVOT

        return pygame.Vector2(
            self.pos.x + self.facing * (tip_x - piv_x) * s,
            self.pos.y + (tip_y - piv_y) * s
        )

    def _update_aim_angle(self, dt):

        s = settings.SOLDIER_SCALE

        hip_up = (
            settings.SOLDIER_PIVOT[1] - settings.TORSO_HIP[1]
        ) * s

        dx = max(1.0, abs(self.aim.x - self.pos.x))
        dy = (self.pos.y - hip_up) - self.aim.y

        target = math.degrees(math.atan2(dy, dx))

        limit = settings.AIM_MAX_ANGLE
        target = max(-limit, min(limit, target))

        self.aim_angle += (
            (target - self.aim_angle)
            * min(1.0, settings.AIM_SMOOTH * dt)
        )

        self._update_aim_dir()

    def _update_aim_dir(self):

        a = self.aim_angle
        enter, leave = settings.AIM_ENTER, settings.AIM_LEAVE

        d = self.aim_dir

        if d == "_up" and a < leave:
            d = ""

        elif d == "_down" and a > -leave:
            d = ""

        if d == "":

            if a > enter:
                d = "_up"

            elif a < -enter:
                d = "_down"

        self.aim_dir = d

    def try_shoot(self):

        self.attack()

    def attack(self):
        """Clic izquierdo / J: dispara el arma de fuego o golpea con el hacha."""

        if not self.alive:
            return

        # Hacha equipada: golpe cuerpo a cuerpo
        if self.equipped == "axe":
            self.play_action("axe")
            return

        ammo = self.ammo[self.weapon]

        if ammo["mag"] > 0:
            self.play_action("shoot")

        # Cargador vacío: recarga sola si hay reserva
        elif ammo["reserve"] > 0:
            self.play_action("reload")

        # Sin ninguna bala: hachazo
        elif "axe" in self.unlocked:
            self.play_action("axe")

    def _fire(self):

        # Cada bala (o cartucho de escopeta) gasta munición del cargador
        ammo = self.ammo[self.weapon]

        if ammo["mag"] <= 0:
            return

        ammo["mag"] -= 1

        origin = self.muzzle()
        direction = self.aim - origin

        if direction.length() < 8:
            direction = pygame.Vector2(self.facing, 0)

        direction = direction.normalize()

        lead = pygame.Vector2(self.pos.x, origin.y)

        if self.weapon == "shotgun":

            spread = settings.SHOTGUN_SPREAD

            for _ in range(settings.SHOTGUN_PELLETS):

                self.pending_bullets.append(Bullet(
                    origin,
                    direction.rotate(random.uniform(-spread, spread)),
                    settings.SHOTGUN_DAMAGE,
                    settings.SHOTGUN_BULLET_SPEED,
                    settings.SHOTGUN_RANGE,
                    pellet=True,
                    lead_from=lead
                ))

        else:

            spread = settings.RIFLE_SPREAD

            self.pending_bullets.append(Bullet(
                origin,
                direction.rotate(random.uniform(-spread, spread)),
                settings.RIFLE_DAMAGE,
                settings.RIFLE_BULLET_SPEED,
                settings.RIFLE_RANGE,
                lead_from=lead
            ))

    # --------------------------------
    # ARMAS, MUNICIÓN Y SUMINISTROS
    # --------------------------------

    def equip(self, slot):
        """Equipa "rifle", "axe" o "shotgun" si ya está desbloqueada."""

        if slot not in self.unlocked or slot == self.equipped:
            return

        # Rifle <-> hacha se puede cambiar en pleno golpe; cambiar de arma
        # de fuego (rifle <-> escopeta) solo en reposo
        if (
            slot in self.anims
            and slot != self.weapon
            and self.state in self.action_states
        ):
            return

        previous = self.equipped
        self.equipped = slot

        if slot in self.anims:
            self.set_weapon(slot)

        # Animación al sacar el hacha (solo si no está haciendo otra acción)
        if slot == "axe" and previous != "axe":
            self.play_test_animation("switch_axe")

    def unlock_weapon(self, weapon):

        if weapon in self.unlocked:
            return

        self.unlocked.add(weapon)

        if weapon in self.ammo:

            self.ammo[weapon]["mag"] = settings.AMMO[weapon]["mag_size"]
            self.ammo[weapon]["reserve"] += settings.AMMO[weapon]["pickup"]

        self.equip(weapon)

    def _finish_reload(self):

        ammo = self.ammo[self.weapon]
        full = settings.AMMO[self.weapon]["mag_size"]

        loaded = min(full - ammo["mag"], ammo["reserve"])

        ammo["mag"] += loaded
        ammo["reserve"] -= loaded

    def heal(self, amount):

        if self.hp >= self.max_hp:
            return False

        self.hp = min(self.max_hp, self.hp + amount)

        return True

    def collect(self, kind):
        """Aplica un suministro. Devuelve el texto a mostrar, o None si no se usó."""

        if kind == "municion":

            # La caja rellena la reserva de las armas de fuego que ya tienes
            parts = []

            for gun, label in (("rifle", "balas"), ("shotgun", "cartuchos")):

                if gun not in self.unlocked:
                    continue

                ammo = self.ammo[gun]
                gain = min(
                    settings.AMMO[gun]["pickup"],
                    ammo["max_reserve"] - ammo["reserve"]
                )

                if gain > 0:
                    ammo["reserve"] += gain
                    parts.append(f"+{gain} {label}")

            if not parts:
                return None

            message = "  ".join(parts)

        elif kind == "botiquin":

            before = self.hp

            if not self.heal(settings.MEDKIT_HEAL):
                return None

            message = f"+{round(self.hp - before)} vida"

        elif kind == "escopeta":

            self.unlock_weapon("shotgun")
            message = "Escopeta"

        else:
            return None

        self._pickup_feedback()

        return message

    def _pickup_feedback(self):

        if (
            settings.PICKUP_ANIMATION
            and self.state not in self.action_states
        ):
            self.play_test_animation("pickup")

        else:
            self.sounds.play_pickup_sound()

    def melee_targets(self, enemies):
        """Enemigos vivos al alcance del hacha, delante del soldado."""

        targets = []

        for enemy in enemies:

            if not enemy.alive:
                continue

            dx = (enemy.pos.x - self.pos.x) * self.facing
            dy = abs(enemy.pos.y - self.pos.y)

            reach = settings.AXE_REACH + enemy.cfg["hit"][0] / 2
            depth = settings.AXE_DEPTH + enemy.cfg["foot"][1]

            if -10 <= dx <= reach and dy <= depth:
                targets.append(enemy)

        return targets

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
                (
                    self.pos.x + self.facing * 30,
                    self.pos.y - 45
                )
            ))

        else:

            self.pending_effects.append((
                "blood",
                (self.pos.x, self.pos.y - 50)
            ))

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
        self.anim_key = "dead"
        self.anim = self.extra_anims["dead"]

        self.anim.reset()
        self.dead_sound_played = False

    # --------------------------------
    # COLISIONES
    # --------------------------------

    def _foot_rect(self, pos):

        rect = pygame.Rect(
            0,
            0,
            *settings.FOOT_SIZE
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

        # MUERTO
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
            "pickup",
            "axe",
            "switch_axe"
        ):

            self.anim.update(dt)

            # Sonidos y disparos
            if self.state == "shoot":

                for i, frame in enumerate(settings.SHOOT_SOUND_FRAMES):

                    if (
                        self.anim.index >= frame - 1
                        and i not in self.shoot_sounds_played
                    ):

                        self.sounds.play_shoot_sound(self.weapon)
                        self.shoot_sounds_played.append(i)

                # Las balas salen en los cuadros configurados
                for i, frame in enumerate(
                    settings.FIRE_FRAMES[self.weapon]
                ):

                    if (
                        self.anim.index >= frame
                        and i not in self.fire_frames_done
                    ):

                        self._fire()
                        self.fire_frames_done.append(i)

            # Sonido de recoger suministro
            elif self.state == "pickup":

                if (
                    not self.pickup_sound_played
                    and self.anim.index >= settings.PICKUP_SOUND_FRAME - 1
                ):

                    self.sounds.play_pickup_sound()
                    self.pickup_sound_played = True

            # Sonido del golpe con hacha
            elif self.state == "axe":

                if (
                    not self.axe_sound_played
                    and self.anim.index >= settings.AXE_SOUND_FRAME - 1
                ):

                    self.sounds.play_axe_sound()
                    self.axe_sound_played = True

                # El golpe cae en el cuadro configurado
                if (
                    not self.axe_hit_done
                    and self.anim.index >= settings.AXE_HIT_FRAME
                ):

                    self.axe_hit_done = True
                    self.pending_melee = True

            # Sonido de muerte
            elif self.state == "dead":

                if (
                    not self.dead_sound_played
                    and self.anim.index >= settings.DEAD_SOUND_FRAME - 1
                ):

                    self.sounds.play_dead_sound()
                    self.dead_sound_played = True

            # Cuando termina la animación, regresar al reposo
            if self.anim.finished:

                if self.state == "reload":
                    self._finish_reload()

                self.state = "idle"
                self.anim_key, self.anim = self._rest_anim()
                self.anim.reset()

            return

        # --------------------------------
        # MOVIMIENTO
        # --------------------------------

        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w]
        )

        # Moverse hacia atrás (contra donde mira) solo permite caminar
        backwards = (
            direction.x != 0
            and (direction.x > 0) != (self.facing > 0)
        )

        run = (
            (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            and not backwards
        )

        moving = direction.length_squared() > 0
        axe = self.equipped == "axe"

        new_state = (
            "run" if run else "walk"
        ) if moving else "idle"

        if moving:
            new_key = "walk_axe" if axe else new_state
            new_anim = (
                self.extra_anims["walk_axe"] if axe
                else self.anims[self.weapon][new_state]
            )
        else:
            new_key, new_anim = self._rest_anim()

        if new_key != self.anim_key:

            if (
                new_state in ("walk", "run")
                and self.state in ("walk", "run")
            ):

                new_anim.index = self.anim.index
                new_anim.timer = self.anim.timer

            else:

                new_anim.reset()

            self.state = new_state
            self.anim_key = new_key
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
    # DIBUJAR JUGADOR
    # --------------------------------

    def draw(self, screen, camera):

        frame = self.anim.image(
            flipped=self.facing < 0
        )

        # Parpadeo rojo al recibir daño
        if (
            self.alive
            and self.invuln > 0
            and int(self.invuln * 20) % 2 == 0
        ):

            frame = frame.copy()

            frame.fill(
                (120, 0, 0),
                special_flags=pygame.BLEND_RGB_ADD
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