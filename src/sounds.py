
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
        }


        # Volúmenes independientes
        self.menu_volume = 0.5
        self.game_music_volume = 0.5
        self.effects_volume = 0.20
        self.ui_volume = 0.20

        # Identificar qué tipo de música está reproduciéndose
        self.current_music_type = None
        
         # Canal de pasos
        self.footsteps_channel = None
        self.current_footstep_type = None
# Sonido del menú independiente
        self.select_level.set_volume(self.ui_volume)

# Volumen inicial de efectos del juego
        for sound in self.soldier_sounds.values():
            sound.set_volume(self.effects_volume)

    # --------------------------------
    # CONFIGURACIÓN DE VOLUMEN
    # --------------------------------

    def set_menu_volume(self, volume):
        self.menu_volume = max(0.0, min(1.0, volume))

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
        
    def play_shield_sound(self):
        self.soldier_sounds["shield"].play()

    def play_shoot_sound(self, weapon):
        if weapon in ("rifle", "shotgun"):
            self.soldier_sounds[weapon].play()
            
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
