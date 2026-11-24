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
        # Conteo de suministros recogidos durante el nivel/partida.
        self.inventory = {"botiquin": 0, "municion": 0, "escopeta": 0}
        self.objects_lost = 0

        # Golpe de hacha
        self.axe_hit_done = False
        self.pending_melee = False

        self.sounds = sounds

        # Vida y combate
        self.max_hp = settings.PLAYER_MAX_HP
        self.hp = self.max_hp
        self.lives = 3
        self.spawn_pos = pygame.Vector2(pos)
        self.alive = True
        self.dead_done = False
        self.death_processed = False
        self.invuln = 0.0

        # Enemigos del nivel (los asigna main.py cada cuadro); sirve para
        # saber de qué lado viene un golpe cuando el escudo está activo
        self.threats = []

        self.aim = pygame.Vector2(pos) + (100, 0)
        self.pending_bullets = []
        self.pending_effects = []

        self.aim_angle = 0.0
        self.aim_dir = ""
        self._pose_angle = 0
        self.fire_dir = ""
        self.fire_frames_done = []

        self.shield_active = False
        self.shield_sound_played = False

        # Control de sonidos
        self.shoot_sounds_played = []
        self.pickup_sound_played = False
        self.dead_sound_played = False
        self.axe_sound_played = False

        # Animaciones de ambas armas (+ poses de apuntado y punta del cañón)
        built = {
            "rifle": self._build(settings.SOLDIER_RIFLE_SHEET, "rifle"),
            "shotgun": self._build(settings.SOLDIER_SHOTGUN_SHEET, "shotgun"),
        }
        self.anims = {w: b[0] for w, b in built.items()}
        # ángulo -> sufijo de la animación ("" = recto, "_up", "_down", "_a22_5"...)
        self.aim_poses = {w: b[1] for w, b in built.items()}
        self.gun_tips = {w: b[2] for w, b in built.items()}
        self.pose_tol = {
            w: self._pose_tolerance(b[1]) for w, b in built.items()
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
    def _pose_suffix(angle):
        """Sufijo de las animaciones de una pose (los 3 viejos se conservan)."""

        if angle == 0:
            return ""
        if angle == 45:
            return "_up"
        if angle == -45:
            return "_down"

        return "_a" + f"{angle:g}".replace(".", "_")

    @staticmethod
    def _pose_tolerance(poses):
        """Desviación máxima de la bala: nunca más de media separación entre poses."""

        angles = sorted(poses)
        half = 45.0

        if len(angles) > 1:
            half = min(b - a for a, b in zip(angles, angles[1:])) / 2

        return min(settings.SHOT_POSE_TOLERANCE, half)

    @staticmethod
    def _flash_tip(sheet, row, weapon):
        """Punta del cañón = centro del fogonazo del cuadro de disparo."""

        col = settings.FIRE_FRAMES[weapon][0]
        raw = sheet.raw_frame(col, row)

        mask = pygame.mask.from_threshold(
            raw, (250, 175, 55, 255), (25, 45, 60, 255)
        )

        if mask.count() < 6:
            return None

        return mask.centroid()

    @staticmethod
    def _model_tip(weapon, angle):
        """Punta estimada (círculo alrededor del hombro) si no hay fogonazo."""

        tips = settings.GUN_TIP[weapon]
        pts = [tips["_down"], tips[""], tips["_up"]]
        (x1, y1), (x2, y2), (x3, y3) = pts

        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        ux = ((x1 * x1 + y1 * y1) * (y2 - y3)
              + (x2 * x2 + y2 * y2) * (y3 - y1)
              + (x3 * x3 + y3 * y3) * (y1 - y2)) / d
        uy = ((x1 * x1 + y1 * y1) * (x3 - x2)
              + (x2 * x2 + y2 * y2) * (x1 - x3)
              + (x3 * x3 + y3 * y3) * (x2 - x1)) / d

        radius = sum(math.hypot(x - ux, y - uy) for x, y in pts) / 3
        phis = [math.degrees(math.atan2(-(y - uy), x - ux)) for x, y in pts]

        # ángulo de la pose -> ángulo real desde el hombro (interpolado)
        if angle <= 0:
            phi = phis[1] + (phis[1] - phis[0]) / 45 * angle
        else:
            phi = phis[1] + (phis[2] - phis[1]) / 45 * angle

        rad = math.radians(phi)

        return (ux + radius * math.cos(rad), uy - radius * math.sin(rad))

    @staticmethod
    def _build(sheet_path, weapon):
        """Devuelve (animaciones, {ángulo: sufijo}, {sufijo: punta del cañón})."""

        sheet = SpriteSheet(
            sheet_path,
            settings.SOLDIER_FRAME_SIZE,
            settings.SOLDIER_COLS,
            settings.SOLDIER_ROWS
        )

        s = settings.SOLDIER_SCALE
        fps = settings.ANIMATION_FPS
        f = settings.IDLE_AIM_FRAME

        anims = {

            "walk": Animation(
                sheet.get_row(settings.ROW_WALK, s),
                fps["walk"]
            ),

            "run": Animation(
                sheet.get_row(settings.ROW_RUN, s),
                fps["run"]
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

        # Caminar con el escudo (y su versión al revés para ir hacia atrás)
        walk_path = settings.SOLDIER_SHIELD_WALK_SHEETS[weapon]

        if walk_path.exists():

            walk_sheet = SpriteSheet(
                walk_path, settings.SOLDIER_FRAME_SIZE, 10, 1
            )
            frames = walk_sheet.get_row(0, s)

            anims["shield_walk"] = Animation(frames, fps["shield_walk"])
            anims["shield_walk_back"] = Animation(
                list(reversed(frames)), fps["shield_walk"]
            )

        # Poses de apuntado: hoja nueva (todos los ángulos) o las 3 filas viejas
        poses = {}
        tips = {}
        aim_path = settings.SOLDIER_AIM_SHEETS[weapon]

        if aim_path.exists():

            angles = settings.AIM_SHEET_ANGLES

            aim_sheet = SpriteSheet(
                aim_path,
                settings.SOLDIER_FRAME_SIZE,
                settings.SOLDIER_COLS,
                len(angles)
            )

            rows = [
                (row, angle)
                for row, angle in enumerate(angles)
                if not aim_sheet.row_is_empty(row)
            ]

            legacy = False

        else:

            aim_sheet = sheet
            rows = [
                (settings.ROW_FIRE_UP, 45),
                (settings.ROW_FIRE, 0),
                (settings.ROW_FIRE_DOWN, -45),
            ]
            legacy = True

        for row, angle in rows:

            suffix = Player._pose_suffix(angle)
            frames = aim_sheet.get_row(row, s)

            anims["idle" + suffix] = Animation([frames[f]], fps["idle"])
            anims["shoot" + suffix] = Animation(
                frames, fps["shoot"], loop=False
            )

            poses[angle] = suffix

            if legacy:
                tip = settings.GUN_TIP[weapon][suffix]
            else:
                tip = Player._flash_tip(aim_sheet, row, weapon)

                if tip is None:
                    tip = settings.GUN_TIP[weapon].get(suffix)

                if tip is None:
                    tip = Player._model_tip(weapon, angle)

            tips[suffix] = tip

        if 0 not in poses:
            raise ValueError(
                f"{aim_path.name}: falta la fila de 0 grados (disparo recto)"
            )

        return anims, dict(sorted(poses.items())), tips

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

        # La otra arma puede tener otras poses: usar la más cercana
        poses = self.aim_poses[weapon]

        if self._pose_angle not in poses:
            self._pose_angle = min(
                poses, key=lambda p: abs(p - self._pose_angle)
            )

        self.aim_dir = poses[self._pose_angle]

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

            # Parte del cuadro en que está (si camina, con el escudo levantado)
            if self.anim_key.startswith("shield_walk"):
                last = settings.SHIELD_PLANT_FRAME - 1
            elif self.anim_key == "shield":
                last = self.anim.index
            else:
                last = len(shield_frames) - 1

            shield_frames = shield_frames[:last + 1]
            self.sounds.stop_footsteps()

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
        tip_x, tip_y = self.gun_tips[self.weapon][self.fire_dir]
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

        limit = min(
            settings.AIM_MAX_ANGLE,
            max(abs(a) for a in self.aim_poses[self.weapon])
        )
        target = max(-limit, min(limit, target))

        self.aim_angle += (
            (target - self.aim_angle)
            * min(1.0, settings.AIM_SMOOTH * dt)
        )

        self._update_aim_dir()

    def _update_aim_dir(self):
        """Elige la pose más cercana al ángulo del mouse (con histéresis)."""

        poses = self.aim_poses[self.weapon]
        a = self.aim_angle

        cur = self._pose_angle

        if cur not in poses:
            cur = min(poses, key=lambda p: abs(p - cur))

        best = min(poses, key=lambda p: abs(p - a))

        # Solo cambia de pose si la nueva está claramente más cerca
        if (
            best != cur
            and abs(a - best) + settings.AIM_HYSTERESIS < abs(a - cur)
        ):
            cur = best

        self._pose_angle = cur
        self.aim_dir = poses[cur]

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

    def _suffix_angle(self, suffix):
        """Ángulo (grados) de la pose cuyo sufijo es `suffix`."""

        for angle, sfx in self.aim_poses[self.weapon].items():
            if sfx == suffix:
                return angle

        return 0

    def _limit_to_pose(self, direction):
        """Limita la dirección del tiro a la pose que se ve en pantalla."""

        pose = self._suffix_angle(self.fire_dir)
        tol = self.pose_tol[self.weapon]

        angle = math.degrees(
            math.atan2(-direction.y, direction.x * self.facing)
        )

        diff = (angle - pose + 180) % 360 - 180
        diff = max(-tol, min(tol, diff))

        rad = math.radians(pose + diff)

        return pygame.Vector2(
            self.facing * math.cos(rad),
            -math.sin(rad)
        )

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

        direction = self._limit_to_pose(direction)

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

        if kind in ("municion", "municion_rifle", "municion_escopeta"):

            if kind == "municion_rifle":
                ammo_targets = (("rifle", "balas"),)
            elif kind == "municion_escopeta":
                ammo_targets = (("shotgun", "cartuchos"),)
            else:
                ammo_targets = (("rifle", "balas"), ("shotgun", "cartuchos"))

            # La caja rellena la reserva de las armas de fuego que ya tienes
            parts = []

            for gun, label in ammo_targets:

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

        # Registrar suministros para las estadísticas y la penalización al morir.
        if kind == "botiquin":
            self.inventory["botiquin"] += 1
        elif kind == "escopeta":
            self.inventory["escopeta"] += 1
        else:
            self.inventory["municion"] += 1

        self._pickup_feedback()

        return message

    def apply_death_penalty(self):
        """Al morir se pierde parte de la munición de reserva, no las armas."""
        lost = 0
        for ammo in self.ammo.values():
            penalty = (ammo["reserve"] + 3) // 4  # 25%, redondeado hacia arriba
            ammo["reserve"] = max(0, ammo["reserve"] - penalty)
            lost += penalty

        self.objects_lost += lost
        self.shield_active = False
        return lost

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

    def _nearest_threat(self):
        """Posición del enemigo vivo más cercano (el que está golpeando)."""

        best = None
        best_dist = None

        for enemy in self.threats:

            if not enemy.alive:
                continue

            dist = self.pos.distance_squared_to(enemy.pos)

            if best_dist is None or dist < best_dist:
                best = enemy.pos
                best_dist = dist

        return best

    def take_damage(self, amount, source=None):
        """source = posición de quien golpea (opcional)."""

        if not self.alive or self.invuln > 0:
            return

        if self.shield_active:

            if source is None:
                source = self._nearest_threat()

            # El escudo solo cubre el frente
            in_front = (
                source is None
                or (source.x - self.pos.x) * self.facing >= -10
            )

            amount *= (
                getattr(settings, "SHIELD_FRONT_MULT", 0.0)
                if in_front
                else getattr(settings, "SHIELD_BACK_MULT", 1.0)
            )

            self.pending_effects.append((
                "shield",
                (
                    self.pos.x + self.facing * 30,
                    self.pos.y - 45
                )
            ))

            # Golpe bloqueado por completo: sin daño
            if amount <= 0:
                self.invuln = 0.25
                return

        else:

            self.pending_effects.append((
                "blood",
                (self.pos.x, self.pos.y - 50)
            ))

        self.hp = max(0, self.hp - amount)
        self.invuln = settings.PLAYER_INVULNERABLE_TIME

        # El sonido se reproduce una sola vez por impacto válido.
        self.sounds.play_damage_sound()

        if self.hp <= 0:
            self.die()

    def respawn(self, level):
        """Reaparece conservando armas, munición y el progreso del nivel."""

        self.pos = level.free_position(self.spawn_pos)
        self.hp = self.max_hp
        self.alive = True
        self.dead_done = False
        self.death_processed = False
        self.invuln = max(settings.PLAYER_INVULNERABLE_TIME, 2.0)
        self.facing = 1
        self.aim = self.pos + pygame.Vector2(100, 0)
        self.aim_angle = 0.0
        self.aim_dir = ""
        self._pose_angle = 0
        self.fire_dir = ""
        self.shield_active = False
        self.shield_sound_played = False
        self.pending_bullets.clear()
        self.pending_effects.clear()
        self.pending_melee = False
        self.axe_hit_done = False
        self.state = "idle"
        self.anim_key, self.anim = self._rest_anim()
        self.anim.reset()
        self.sounds.stop_footsteps()

    def die(self):

        self.alive = False
        self.death_processed = False
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
    # MOVIMIENTO (compartido por caminar y disparar caminando)
    # --------------------------------

    def _read_movement(self, keys):
        """Lee WASD. Devuelve (dirección, corriendo, moviéndose)."""

        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w]
        )

        # Moverse hacia atrás (contra donde mira) solo permite caminar
        backwards = (
            direction.x != 0
            and (direction.x > 0) != (self.facing > 0)
        )

        run = bool(
            (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            and not backwards
        )

        moving = direction.length_squared() > 0

        return direction, run, moving

    def _move(self, direction, speed, dt, level):

        step = direction.normalize() * speed * dt

        # Ejes separados para evitar atravesar paredes
        for axis in ("x", "y"):

            candidate = self.pos.copy()

            setattr(
                candidate,
                axis,
                getattr(candidate, axis) + getattr(step, axis)
            )

            candidate.x = max(0, min(level.width, candidate.x))
            candidate.y = max(0, min(level.height, candidate.y))

            if not level.collides(self._foot_rect(candidate)):
                self.pos = candidate

    def _shoot_walk(self, dt, keys, level):
        """Permite caminar (más lento) mientras dura la animación de disparo."""

        direction, run, moving = self._read_movement(keys)

        if not moving:
            self.sounds.stop_footsteps()
            return

        self.sounds.play_footsteps("walk")

        speed = settings.WALK_SPEED * getattr(
            settings, "SHOOT_MOVE_MULT", 0.6
        )

        self._move(direction, speed, dt, level)

    # --------------------------------
    # ESCUDO ACTIVO: QUIETO O CAMINANDO
    # --------------------------------

    def _update_shield(self, dt, keys, level):
        """Con el escudo activo se camina más lento en cualquier dirección.

        El soldado sigue de perfil hacia el mouse; si camina contra su frente
        (hacia atrás) la animación se reproduce al revés. Al detenerse vuelve
        a plantar el escudo."""

        anims = self.anims[self.weapon]
        direction, _run, moving = self._read_movement(keys)

        # Mientras sube el escudo (primeros cuadros) todavía no se mueve
        raised = (
            self.anim_key != "shield"
            or self.anim.index >= settings.SHIELD_MOVE_MIN_FRAME
        )

        if moving and raised and "shield_walk" in anims:

            backwards = (
                direction.x != 0
                and (direction.x > 0) != (self.facing > 0)
            )

            key = "shield_walk_back" if backwards else "shield_walk"

            if key != self.anim_key:

                new = anims[key]

                if self.anim_key in ("shield_walk", "shield_walk_back"):
                    # mantiene la zancada al cambiar de sentido
                    new.index = len(new.frames) - 1 - self.anim.index
                    new.timer = self.anim.timer
                    new.finished = False
                else:
                    new.reset()

                self.anim_key = key
                self.anim = new

            speed = settings.WALK_SPEED * settings.SHIELD_MOVE_MULT

            self.sounds.play_footsteps("walk")
            self._move(direction, speed, dt, level)
            self.anim.update(dt)

            return

        # Quieto: planta el escudo de nuevo
        if self.anim_key in ("shield_walk", "shield_walk_back"):

            self.anim = anims["shield"]
            self.anim.reset()
            self.anim.index = min(
                settings.SHIELD_PLANT_FRAME, len(self.anim.frames) - 1
            )
            self.anim_key = "shield"
            self.shield_sound_played = False

        self.sounds.stop_footsteps()
        self.anim.update(dt)

        if (
            self.anim_key == "shield"
            and not self.shield_sound_played
            and self.anim.index >= settings.SHIELD_SOUND_FRAME - 1
        ):

            self.sounds.play_shield_sound()
            self.shield_sound_played = True

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

        # ESCUDO ACTIVO (se puede caminar con él)
        if self.shield_active:

            self._update_shield(dt, keys, level)
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

                # Caminar mientras se dispara
                self._shoot_walk(dt, keys, level)

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

        direction, run, moving = self._read_movement(keys)
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

            self._move(direction, speed, dt, level)

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