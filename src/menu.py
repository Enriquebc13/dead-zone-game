
import pygame
import settings

from src.sounds import SoundManager


class Menu:

    def __init__(self):

        # Cargar fondo
        self.background = pygame.image.load(
            str(settings.MENU_BACKGROUND)
        ).convert()

        self.background = pygame.transform.scale(
            self.background,
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )

        # Sistema de audio
        self.sounds = SoundManager()
        self.sounds.play_menu_music()

        # Nivel seleccionado
        self.selected_level = 0

        # Fuentes
        self.title_font = pygame.font.Font(None, 100)
        self.level_font = pygame.font.Font(None, 42)
        self.info_font = pygame.font.Font(None, 25)
        self.settings_font = pygame.font.Font(None, 30)

        # Botones de niveles
        self.level_buttons = []

        for i in range(5):
            rect = pygame.Rect(
                440,
                260 + i * 65,
                400,
                52
            )

            self.level_buttons.append(rect)

        # Botón de configuración
        self.settings_button = pygame.Rect(
            1030,
            640,
            210,
            50
        )

    # --------------------------------
    # EVENTOS
    # --------------------------------

    def handle_event(self, event):

        # Navegación con teclado
        if event.type == pygame.KEYDOWN:

            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_level = (
                    self.selected_level - 1
                ) % 5

                self.sounds.play_select_sound()

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_level = (
                    self.selected_level + 1
                ) % 5

                self.sounds.play_select_sound()

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.selected_level

        # Selección con mouse
        if event.type == pygame.MOUSEMOTION:

            for i, rect in enumerate(self.level_buttons):

                if rect.collidepoint(event.pos):

                    if self.selected_level != i:
                        self.selected_level = i
                        self.sounds.play_select_sound()

        # Clics
        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                # Abrir configuración
                if self.settings_button.collidepoint(event.pos):
                    self.sounds.play_select_sound()
                    return "settings"

                # Seleccionar nivel
                for i, rect in enumerate(self.level_buttons):

                    if rect.collidepoint(event.pos):
                        self.selected_level = i
                        self.sounds.play_select_sound()
                        return self.selected_level

        return None

    # --------------------------------
    # DIBUJAR MENU
    # --------------------------------

    def draw(self, screen):

        # Fondo
        screen.blit(self.background, (0, 0))

        # Título
        title = self.title_font.render(
            "DEAD ZONE",
            True,
            (220, 35, 35)
        )

        title_rect = title.get_rect(
            center=(640, 150)
        )

        screen.blit(title, title_rect)

        # Subtítulo
        subtitle = self.info_font.render(
            "SELECCIONA UN NIVEL",
            True,
            (230, 230, 230)
        )

        subtitle_rect = subtitle.get_rect(
            center=(640, 220)
        )

        screen.blit(subtitle, subtitle_rect)

        # Botones de niveles
        for i, rect in enumerate(self.level_buttons):

            selected = i == self.selected_level

            if selected:
                color = (150, 25, 25)
                border_color = (255, 80, 80)
            else:
                color = (30, 30, 30)
                border_color = (120, 120, 120)

            pygame.draw.rect(
                screen,
                color,
                rect,
                border_radius=6
            )

            pygame.draw.rect(
                screen,
                border_color,
                rect,
                2,
                border_radius=6
            )

            text = self.level_font.render(
                f"NIVEL {i + 1}",
                True,
                (255, 255, 255)
            )

            text_rect = text.get_rect(
                center=rect.center
            )

            screen.blit(text, text_rect)

        # Botón de configuración
        mouse_pos = pygame.mouse.get_pos()

        hover = self.settings_button.collidepoint(mouse_pos)

        if hover:
            button_color = (120, 25, 30)
            border_color = (255, 80, 80)
        else:
            button_color = (30, 30, 30)
            border_color = (120, 120, 120)

        pygame.draw.rect(
            screen,
            button_color,
            self.settings_button,
            border_radius=6
        )

        pygame.draw.rect(
            screen,
            border_color,
            self.settings_button,
            2,
            border_radius=6
        )

        settings_text = self.settings_font.render(
            "CONFIGURACION",
            True,
            (255, 255, 255)
        )

        settings_rect = settings_text.get_rect(
            center=self.settings_button.center
        )

        screen.blit(settings_text, settings_rect)

        # Instrucciones
        instructions = self.info_font.render(
            "W / S o FLECHAS: Seleccionar     ENTER: Iniciar",
            True,
            (230, 230, 230)
        )

        instructions_rect = instructions.get_rect(
            center=(640, 660)
        )

        screen.blit(instructions, instructions_rect)

    # --------------------------------
    # DETENER MUSICA
    # --------------------------------

    def stop_music(self):
        self.sounds.stop_music()
