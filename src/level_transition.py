import pygame


class LevelTransition:
    """Transición reutilizable entre el menú y los niveles de Dead Zone."""

    FADE_TO_BLACK = 0.45
    TITLE_HOLD = 1.15
    FADE_FROM_BLACK = 0.65

    def __init__(self, sounds=None):
        self.sounds = sounds
        self.active = False
        self.level_number = 1
        self.elapsed = 0.0
        self.start_sound_played = False
        self.font = pygame.font.Font(None, 92)
        self.small_font = pygame.font.Font(None, 25)

    def start(self, level_number):
        """Inicia la transición mostrando el número del nivel."""
        self.level_number = level_number
        self.elapsed = 0.0
        self.start_sound_played = False
        self.active = True

    def update(self, dt):
        """Avanza la animación. Devuelve True mientras siga activa."""
        if not self.active:
            return False

        previous_elapsed = self.elapsed
        self.elapsed += dt

        # El texto del nivel aparece al terminar el primer fundido.
        # Reproducir el sonido exactamente una vez en ese momento.
        if (
            not self.start_sound_played
            and previous_elapsed < self.FADE_TO_BLACK <= self.elapsed
        ):
            if self.sounds is not None:
                self.sounds.play_start_game_sound()
            self.start_sound_played = True

        total = (
            self.FADE_TO_BLACK
            + self.TITLE_HOLD
            + self.FADE_FROM_BLACK
        )

        if self.elapsed >= total:
            self.active = False

        return self.active

    def draw(self, canvas):
        """Dibuja el fundido y el título encima de la escena actual."""
        if not self.active:
            return

        elapsed = self.elapsed
        fade_end = self.FADE_TO_BLACK
        hold_end = fade_end + self.TITLE_HOLD
        total = hold_end + self.FADE_FROM_BLACK

        if elapsed < fade_end:
            # La escena se oscurece gradualmente.
            progress = elapsed / self.FADE_TO_BLACK
            alpha = int(255 * progress)
            title_alpha = 0
        elif elapsed < hold_end:
            # El título permanece sobre la pantalla negra.
            alpha = 255
            title_alpha = 255
        else:
            # El título y el negro desaparecen para revelar el nivel.
            progress = (elapsed - hold_end) / self.FADE_FROM_BLACK
            alpha = int(255 * (1.0 - progress))
            title_alpha = alpha

        overlay = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, max(0, min(255, alpha))))
        canvas.blit(overlay, (0, 0))

        if title_alpha > 0:
            title = self.font.render(
                f"NIVEL {self.level_number}",
                True,
                (235, 235, 235)
            )
            title.set_alpha(title_alpha)

            subtitle = self.small_font.render(
                "PREPARATE PARA SOBREVIVIR",
                True,
                (180, 45, 45)
            )
            subtitle.set_alpha(title_alpha)

            center_x = canvas.get_width() // 2
            center_y = canvas.get_height() // 2
            canvas.blit(title, title.get_rect(center=(center_x, center_y - 12)))
            canvas.blit(subtitle, subtitle.get_rect(center=(center_x, center_y + 48)))
