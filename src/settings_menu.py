
import pygame


class SettingsMenu:

    def __init__(self, sounds):

        self.sounds = sounds

        self.width = 1280
        self.height = 720

        # Fuentes
        self.title_font = pygame.font.Font(None, 65)
        self.label_font = pygame.font.Font(None, 32)
        self.value_font = pygame.font.Font(None, 27)
        self.button_font = pygame.font.Font(None, 32)

        # Panel de configuración
        self.panel = pygame.Rect(340, 120, 600, 490)

        # Posiciones de las barras
        self.slider_x = 430
        self.slider_width = 420
        self.slider_height = 10

        # Valores iniciales tomados de SoundManager
        self.volumes = {
            "menu": sounds.menu_volume,
            "music": sounds.game_music_volume,
            "effects": sounds.effects_volume
        }

        self.sliders = {
            "menu": pygame.Rect(
                self.slider_x, 280,
                self.slider_width, self.slider_height
            ),
            "music": pygame.Rect(
                self.slider_x, 380,
                self.slider_width, self.slider_height
            ),
            "effects": pygame.Rect(
                self.slider_x, 480,
                self.slider_width, self.slider_height
            )
        }

        self.active_slider = None

        # Botón volver
        self.back_button = pygame.Rect(540, 540, 200, 48)

    # --------------------------------
    # ACTUALIZAR VOLUMEN
    # --------------------------------

    def update_volume(self, name, mouse_x):

        slider = self.sliders[name]

        value = (mouse_x - slider.x) / slider.width
        value = max(0.0, min(1.0, value))

        self.volumes[name] = value

        if name == "menu":
            self.sounds.set_menu_volume(value)

        elif name == "music":
            self.sounds.set_game_music_volume(value)

        elif name == "effects":
            self.sounds.set_effects_volume(value)

    # --------------------------------
    # EVENTOS
    # --------------------------------

    def handle_event(self, event):

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active_slider = None
                return "back"

        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                if self.back_button.collidepoint(event.pos):
                    self.active_slider = None
                    return "back"

                for name, slider in self.sliders.items():

                    hitbox = slider.inflate(20, 30)

                    if hitbox.collidepoint(event.pos):
                        self.active_slider = name
                        self.update_volume(name, event.pos[0])
                        break

        if event.type == pygame.MOUSEMOTION:

            if self.active_slider is not None:
                self.update_volume(
                    self.active_slider,
                    event.pos[0]
                )

        if event.type == pygame.MOUSEBUTTONUP:

            if event.button == 1:
                self.active_slider = None

        return None

    # --------------------------------
    # DIBUJAR BARRAS
    # --------------------------------

    def draw_slider(self, screen, name, label):

        slider = self.sliders[name]
        value = self.volumes[name]

        # Nombre de la opción
        text = self.label_font.render(
            label, True, (235, 235, 235)
        )
        screen.blit(text, (slider.x, slider.y - 42))

        # Porcentaje
        percentage = self.value_font.render(
            f"{int(value * 100)}%", True, (255, 255, 255)
        )
        screen.blit(
            percentage,
            (slider.right + 25, slider.y - 9)
        )

        # Barra de fondo
        pygame.draw.rect(
            screen,
            (75, 70, 80),
            slider,
            border_radius=8
        )

        # Barra de progreso
        filled_width = int(slider.width * value)

        if filled_width > 0:
            filled_rect = pygame.Rect(
                slider.x,
                slider.y,
                filled_width,
                slider.height
            )

            pygame.draw.rect(
                screen,
                (190, 45, 45),
                filled_rect,
                border_radius=8
            )

        # Indicador circular
        knob_x = slider.x + filled_width
        knob_y = slider.centery

        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (knob_x, knob_y),
            11
        )

        pygame.draw.circle(
            screen,
            (190, 45, 45),
            (knob_x, knob_y),
            6
        )

    # --------------------------------
    # DIBUJAR CONFIGURACIÓN
    # --------------------------------

    def draw(self, screen):

        # Fondo oscuro transparente
        overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 145))
        screen.blit(overlay, (0, 0))

        # Panel semitransparente
        panel_surface = pygame.Surface(
            self.panel.size,
            pygame.SRCALPHA
        )

        panel_surface.fill((20, 14, 25, 225))

        screen.blit(
            panel_surface,
            self.panel.topleft
        )

        pygame.draw.rect(
            screen,
            (150, 40, 45),
            self.panel,
            2,
            border_radius=12
        )

        # Título
        title = self.title_font.render(
            "CONFIGURACION", True, (220, 45, 45)
        )

        title_rect = title.get_rect(
            center=(640, 190)
        )

        screen.blit(title, title_rect)

        # Barras de volumen
        self.draw_slider(
            screen, "menu", "VOLUMEN DEL MENU"
        )

        self.draw_slider(
            screen, "music", "MUSICA DEL JUEGO"
        )

        self.draw_slider(
            screen, "effects", "EFECTOS DE SONIDO"
        )

        # Botón volver
        pygame.draw.rect(
            screen,
            (125, 30, 35),
            self.back_button,
            border_radius=7
        )

        pygame.draw.rect(
            screen,
            (230, 80, 80),
            self.back_button,
            2,
            border_radius=7
        )

        back_text = self.button_font.render(
            "VOLVER", True, (255, 255, 255)
        )

        back_rect = back_text.get_rect(
            center=self.back_button.center
        )

        screen.blit(back_text, back_rect)
