import pygame


class VictoryScreen:
    """Pantalla de victoria y resultados del nivel."""

    def __init__(self):
        self.title_font = pygame.font.Font(None, 76)
        self.subtitle_font = pygame.font.Font(None, 23)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        self.next_button = pygame.Rect(0, 0, 340, 48)
        self.menu_button = pygame.Rect(0, 0, 340, 48)

    def _get_buttons(self, canvas):
        """Calcula la posición de los botones según el tamaño del canvas."""
        cx = canvas.get_width() // 2
        cy = canvas.get_height() // 2

        self.next_button = pygame.Rect(
            cx - 170, cy + 145, 340, 48
        )

        self.menu_button = pygame.Rect(
            cx - 170, cy + 205, 340, 48
        )

    def _draw_button(self, canvas, rect, text, mouse_pos, enabled=True):
        """Dibuja un botón con efecto hover."""
        hovered = rect.collidepoint(mouse_pos)

        if not enabled:
            background = (38, 45, 40)
            border = (90, 105, 90)
            text_color = (145, 155, 145)
        elif hovered:
            background = (65, 115, 75)
            border = (130, 230, 145)
            text_color = (255, 255, 255)
        else:
            background = (35, 75, 45)
            border = (90, 185, 110)
            text_color = (235, 245, 235)

        pygame.draw.rect(
            canvas, background, rect, border_radius=8
        )
        pygame.draw.rect(
            canvas, border, rect, 2, border_radius=8
        )

        label = self.font.render(text, True, text_color)
        canvas.blit(label, label.get_rect(center=rect.center))

    def draw(
        self, canvas, level, player, enemies, elapsed_time, mouse_pos,
        has_next=False, game_state=None
    ):
        """Dibuja el tablero con los resultados de la partida."""

        width = canvas.get_width()
        height = canvas.get_height()

        cx = width // 2
        cy = height // 2

        panel = pygame.Rect(
            cx - 270, cy - 245, 540, 520
        )

        # Oscurecer el juego
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 215))
        canvas.blit(overlay, (0, 0))

        # Panel
        pygame.draw.rect(
            canvas, (15, 19, 23), panel, border_radius=14
        )
        pygame.draw.rect(
            canvas, (85, 180, 105), panel, 3, border_radius=14
        )

        # Título
        title = self.title_font.render(
            "VICTORIA", True, (105, 225, 125)
        )
        canvas.blit(
            title,
            title.get_rect(center=(cx, cy - 195))
        )

        subtitle = self.subtitle_font.render(
            "TODOS LOS ENEMIGOS HAN SIDO ELIMINADOS",
            True, (195, 205, 200)
        )
        canvas.blit(
            subtitle,
            subtitle.get_rect(center=(cx, cy - 145))
        )

        # Separador
        pygame.draw.line(
            canvas, (65, 100, 75),
            (cx - 220, cy - 115),
            (cx + 220, cy - 115), 2
        )

        # Estadísticas
        killed = sum(1 for enemy in enemies if not enemy.alive)
        total = len(enemies)

        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        total_ammo = sum(
            ammo["mag"] + ammo["reserve"]
            for ammo in player.ammo.values()
        )

        stats = [
            ("NIVEL", level.name),
            ("ENEMIGOS ELIMINADOS", f"{killed} / {total}"),
            ("TIEMPO DE PARTIDA", f"{minutes:02}:{seconds:02}"),
            (
                "SALUD RESTANTE",
                f"{round(player.hp)} / {player.max_hp}"
            ),
            ("MUNICION RESTANTE", str(total_ammo)),
            ("PUNTAJE", str(game_state.score if game_state else 0)),
            ("MUERTES", str(game_state.deaths if game_state else 0)),
        ]

        start_y = cy - 85

        for label, value in stats:
            label_surface = self.small_font.render(
                label, True, (155, 165, 165)
            )
            value_surface = self.font.render(
                value, True, (245, 245, 245)
            )

            canvas.blit(label_surface, (cx - 210, start_y))
            canvas.blit(
                value_surface,
                value_surface.get_rect(
                    midright=(cx + 210, start_y + 10)
                )
            )

            start_y += 31

        # Botones
        self._get_buttons(canvas)

        self._draw_button(
            canvas,
            self.next_button,
            "SIGUIENTE NIVEL" if has_next
            else "SIGUIENTE NIVEL - PROXIMAMENTE",
            mouse_pos,
            enabled=has_next
        )

        self._draw_button(
            canvas,
            self.menu_button,
            "VOLVER AL MENU",
            mouse_pos
        )

    def handle_event(self, event, window_size, canvas_size, has_next=False):
        """
        Procesa los eventos de la pantalla.

        Retorna:
        - 'next': pasar al siguiente nivel (solo si has_next).
        - 'menu': regresar al menú principal.
        - None: permanecer en la pantalla.
        """

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                return "menu"

            # ENTER / ESPACIO = siguiente nivel
            if has_next and event.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_SPACE,
            ):
                return "next"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            window_width, window_height = window_size
            canvas_width, canvas_height = canvas_size

            mouse_pos = (
                int(event.pos[0] * canvas_width / window_width),
                int(event.pos[1] * canvas_height / window_height)
            )

            if self.menu_button.collidepoint(mouse_pos):
                return "menu"

            if has_next and self.next_button.collidepoint(mouse_pos):
                return "next"

        return None