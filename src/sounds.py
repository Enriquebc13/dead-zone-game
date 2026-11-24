import pygame
import settings


class SoundManager:

    def __init__(self):
        # Inicializar el sistema de audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # Música
        self.menu_music = settings.MENU_MUSIC

        # Efectos de sonido
        self.select_level = pygame.mixer.Sound(
            str(settings.MENU_SELECT_SOUND)
        )
        self.start_game = pygame.mixer.Sound(
            str(settings.MENU_START_SOUND)
        )
        self.pause_select = pygame.mixer.Sound(
            str(settings.PAUSE_SELECT_SOUND)
        )

        # Sonidos del soldado
        self.soldier_sounds = {
            "shield": pygame.mixer.Sound(
                str(settings.SOLDIER_SHIELD_SOUND)
            ),
            "rifle": pygame.mixer.Sound(
                str(settings.SOLDIER_RIFLE_SOUND)
            ),
            "shotgun": pygame.mixer.Sound(
                str(settings.SOLDIER_SHOTGUN_SOUND)
            ),
            "walk": pygame.mixer.Sound(
                str(settings.SOLDIER_WALK_SOUND)
            ),
            "run": pygame.mixer.Sound(
                str(settings.SOLDIER_RUN_SOUND)
            ),
            "reload_rifle": pygame.mixer.Sound(
                str(settings.SOLDIER_RELOAD_RIFLE_SOUND)
            ),
            "reload_shotgun": pygame.mixer.Sound(
                str(settings.SOLDIER_RELOAD_SHOTGUN_SOUND)
            ),
            "pickup": pygame.mixer.Sound(
                str(settings.SOLDIER_PICKUP_SOUND)
            ),
            "dead": pygame.mixer.Sound(
                str(settings.SOLDIER_DEAD_SOUND)
            ),
            "damage": pygame.mixer.Sound(
                str(settings.SOLDIER_DAMAGE_SOUND)
            ),
            "axe": pygame.mixer.Sound(
                str(settings.SOLDIER_AXE_HIT_SOUND)
            ),
            "victory": pygame.mixer.Sound(
                str(settings.SOLDIER_VICTORY_SOUND)
            ),
        }

        # Sonidos de zombies (opcionales: se detectan por el nombre del archivo)
        #   *ataque*         -> golpe del zombie
        #   *gru* / gr...    -> gruñido al detectar al jugador
        #   zobie / horda    -> ambiente de la horda (en bucle, bajito)
        self.zombie_sounds = {}
        self.zombie_volume_mult = {"horde": 0.35, "attack": 1.0, "growl": 0.7}
        self.horde_channel = None
        self._last_growl = 0

        zdir = settings.ZOMBIE_SOUNDS_DIR
        if zdir.exists():
            for f in sorted(zdir.glob("*.mp3")):
                name = f.stem.lower()
                if "ataque" in name:
                    key = "attack"
                elif "gru" in name or name.startswith("gr"):
                    key = "growl"
                elif "zobie" in name or "zombie" in name or "horda" in name:
                    key = "horde"
                else:
                    continue
                try:
                    self.zombie_sounds[key] = pygame.mixer.Sound(str(f))
                except pygame.error:
                    pass

        # Volúmenes independientes
        self.menu_volume = 0.5
        self.game_music_volume = 0.20
        self.effects_volume = 0.5
        self.ui_volume = 0.20

        # Identificar qué tipo de música está reproduciéndose
        self.current_music_type = None

        # Canal de pasos
        self.footsteps_channel = None
        self.current_footstep_type = None

        # Los sonidos de interfaz siguen el volumen general del menú.
        self.ui_volume = self.menu_volume
        self.select_level.set_volume(self.menu_volume)
        self.start_game.set_volume(self.menu_volume)
        self.pause_select.set_volume(self.menu_volume)

        # Volumen inicial de efectos del juego
        for sound in self.soldier_sounds.values():
            sound.set_volume(self.effects_volume)
        self._apply_zombie_volumes()

    # --------------------------------
    # CONFIGURACIÓN DE VOLUMEN
    # --------------------------------

    def set_menu_volume(self, volume):
        self.menu_volume = max(0.0, min(1.0, volume))
        self.ui_volume = self.menu_volume

        # El control "VOLUMEN DEL MENU" afecta música y sonidos de interfaz.
        self.select_level.set_volume(self.menu_volume)
        self.start_game.set_volume(self.menu_volume)
        self.pause_select.set_volume(self.menu_volume)

        if self.current_music_type == "menu":
            pygame.mixer.music.set_volume(self.menu_volume)

    def set_game_music_volume(self, volume):
        self.game_music_volume = max(0.0, min(1.0, volume))

        if self.current_music_type == "game":
            pygame.mixer.music.set_volume(self.game_music_volume)

    def set_effects_volume(self, volume):
        self.effects_volume = max(0.0, min(1.0, volume))

        for sound in self.soldier_sounds.values():
            sound.set_volume(self.effects_volume)

        self._apply_zombie_volumes()

    def _apply_zombie_volumes(self):
        for key, sound in self.zombie_sounds.items():
            sound.set_volume(self.effects_volume * self.zombie_volume_mult[key])

    # --------------------------------
    # SONIDOS DE ZOMBIES
    # --------------------------------

    def play_horde(self):
        sound = self.zombie_sounds.get("horde")
        if sound is None:
            return
        if self.horde_channel is not None and self.horde_channel.get_busy():
            return
        self.horde_channel = sound.play(-1)

    def stop_horde(self):
        if self.horde_channel is not None:
            self.horde_channel.stop()
        self.horde_channel = None

    def play_zombie(self, key):
        sound = self.zombie_sounds.get(key)
        if sound is None:
            return
        # Evitar que 10 zombies gruñan al mismo tiempo
        if key == "growl":
            now = pygame.time.get_ticks()
            if now - self._last_growl < 1500:
                return
            self._last_growl = now
        sound.play()

    def play_reload_sound(self, weapon):
        sound_name = f"reload_{weapon}"

        if sound_name in self.soldier_sounds:
            self.soldier_sounds[sound_name].play()

    # --------------------------------
    # REPRODUCCIÓN DE MÚSICA
    # --------------------------------

    def play_menu_music(self):
        pygame.mixer.music.load(str(self.menu_music))
        pygame.mixer.music.set_volume(self.menu_volume)
        pygame.mixer.music.play(-1)

        self.current_music_type = "menu"

    def play_level_music(self, level_number):
        if level_number < 1 or level_number > 5:
            return

        music_path = (
            settings.BASE_DIR
            / "assets"
            / "sounds"
            / "music"
            / f"nivel_{level_number}.mp3"
        )

        pygame.mixer.music.load(str(music_path))
        pygame.mixer.music.set_volume(self.game_music_volume)
        pygame.mixer.music.play(-1)

        self.current_music_type = "game"

    # --------------------------------
    # EFECTOS DE SONIDO
    # --------------------------------

    def play_select_sound(self):
        self.select_level.play()

    def play_start_game_sound(self):
        """Reproduce el sonido al aparecer el título de transición del nivel."""
        self.start_game.play()

    def play_pause_select_sound(self):
        """Reproduce el sonido al cambiar la opción seleccionada en pausa."""
        self.pause_select.play()

    def play_shield_sound(self):
        self.soldier_sounds["shield"].play()

    def play_shoot_sound(self, weapon):
        if weapon in ("rifle", "shotgun"):
            self.soldier_sounds[weapon].play()

    def play_pickup_sound(self):
        self.soldier_sounds["pickup"].play()

    def play_damage_sound(self):
        """Reproduce el efecto cuando el jugador recibe daño real."""
        self.soldier_sounds["damage"].play()

    def play_dead_sound(self):
        # Cortar los pasos para que no suenen mientras cae
        self.stop_footsteps()

        # Opcional: bajar la música del nivel al morir
        # pygame.mixer.music.fadeout(800)

        self.soldier_sounds["dead"].play()
    
    def play_axe_sound(self):
        self.soldier_sounds["axe"].play()
    def play_victory_sound(self):
        self.soldier_sounds["victory"].play()

    # --------------------------------
    # PASOS DEL SOLDADO
    # --------------------------------

    def play_footsteps(self, movement_type):

        if movement_type not in ("walk", "run"):
            return

        # Si ya está reproduciendo el sonido correcto,
        # no volver a iniciarlo
        if (
            self.current_footstep_type == movement_type
            and self.footsteps_channel is not None
            and self.footsteps_channel.get_busy()
        ):
            return

        # Detener pasos anteriores
        self.stop_footsteps()

        sound = self.soldier_sounds[movement_type]

        # Reproducir continuamente mientras se mueve
        self.footsteps_channel = sound.play(-1)
        self.current_footstep_type = movement_type

    def stop_footsteps(self):

        if self.footsteps_channel is not None:
            self.footsteps_channel.stop()

        self.footsteps_channel = None
        self.current_footstep_type = None

    # --------------------------------
    # DETENER MÚSICA
    # --------------------------------

    def stop_music(self):
        pygame.mixer.music.stop()
        self.current_music_type = None