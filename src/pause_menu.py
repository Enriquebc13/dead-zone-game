import pygame


class PauseMenu:
    """Menú de pausa: continuar, reiniciar, información, configuración,
    volver al menú y salir."""

    ITEMS = (
        ("resume", "CONTINUAR"),
        ("restart", "REINICIAR NIVEL"),
        ("info", "INFORMACION DE LA PARTIDA"),
        ("settings", "CONFIGURACION"),
        ("menu", "VOLVER AL MENU"),
        ("quit", "SALIR DEL JUEGO"),
    )

    WEAPON_NAMES = {
        "rifle": "RIFLE",
        "axe": "HACHA",
        "shotgun": "ESCOPETA",
    }

    CONTROLS = (
        "WASD: mover        SHIFT: correr",
        "MOUSE: apuntar        CLIC IZQ / J: disparar",
        "CLIC DER / K: escudo        R: recargar",
        "1 / 2 / 3: rifle / hacha / escopeta        H: hachazo",
        "ESC / P: pausa        F11: pantalla completa",
    )

    def __init__(self):
        self.title_font = pygame.font.Font(None, 72)
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 24)
        self.tiny_font = pygame.font.Font(None, 22)

        self.selected = 0
        self.show_info = False

    def reset(self):
        """Se llama al abrir la pausa."""
        self.selected = 0
        self.show_info = False

    # --------------------------------
    # DISEÑO
    # --------------------------------

    def _layout(self, width, height):
        cx = width // 2
        top = height // 2 - 190

        rects = [
            pygame.Rect(cx - 190, top + 90 + i * 58, 380, 46)
            for i in range(len(self.ITEMS))
        ]

        panel = pygame.Rect(
            cx - 250, top - 10, 500, 90 + len(self.ITEMS) * 58 + 20
        )

        return panel, rects

    def _activate(self, index):
        action = self.ITEMS[index][0]

        if action == "info":
            self.show_info = True
            return None

        return action

    # --------------------------------
    # EVENTOS
    # --------------------------------

    def handle_event(self, event, window_size, canvas_size):
        """
        Retorna: 'resume', 'restart', 'settings', 'menu', 'quit' o None.
        Funciona con teclado, mouse USB y touchpad.
        """

        # Panel de información: cualquier tecla de salida o clic lo cierra
        if self.show_info:

            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_SPACE,
                pygame.K_p,
            ):
                self.show_info = False

            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                self.show_info = False

            return None

        count = len(self.ITEMS)

        if event.type == pygame.KEYDOWN:

            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                return "resume"

            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % count

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % count

            elif event.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_SPACE,
            ):
                return self._activate(self.selected)

        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):

            window_width, window_height = window_size
            canvas_width, canvas_height = canvas_size

            mouse_pos = (
                int(event.pos[0] * canvas_width / window_width),
                int(event.pos[1] * canvas_height / window_height)
            )

            _, rects = self._layout(canvas_width, canvas_height)

            for i, rect in enumerate(rects):

                if rect.collidepoint(mouse_pos):

                    self.selected = i

                    if (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                    ):
                        return self._activate(i)

        return None

    # --------------------------------
    # DIBUJO
    # --------------------------------

    def draw(self, canvas, level, player, enemies, elapsed, game_state=None):

        width, height = canvas.get_size()
        cx = width // 2

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        canvas.blit(overlay, (0, 0))

        if self.show_info:
            self._draw_info(canvas, level, player, enemies, elapsed, game_state)
            return

        panel, rects = self._layout(width, height)

        pygame.draw.rect(canvas, (15, 19, 23), panel, border_radius=14)
        pygame.draw.rect(
            canvas, (85, 180, 105), panel, 3, border_radius=14
        )

        title = self.title_font.render("PAUSA", True, (105, 225, 125))
        canvas.blit(title, title.get_rect(center=(cx, panel.top + 52)))

        remaining = sum(1 for enemy in enemies if enemy.alive)
        status = self.small_font.render(
            f"VIDAS: {player.lives}     ENEMIGOS RESTANTES: {remaining}",
            True,
            (245, 220, 150)
        )
        canvas.blit(status, status.get_rect(center=(cx, panel.top + 82)))

        for i, (rect, (action, label)) in enumerate(
            zip(rects, self.ITEMS)
        ):

            selected = i == self.selected
            danger = action == "quit"

            if selected:
                background = (120, 45, 45) if danger else (65, 115, 75)
                border = (240, 120, 120) if danger else (130, 230, 145)
                color = (255, 255, 255)
            else:
                background = (70, 28, 28) if danger else (35, 75, 45)
                border = (170, 80, 80) if danger else (90, 185, 110)
                color = (235, 245, 235)

            pygame.draw.rect(canvas, background, rect, border_radius=8)
            pygame.draw.rect(canvas, border, rect, 2, border_radius=8)

            text = self.font.render(label, True, color)
            canvas.blit(text, text.get_rect(center=rect.center))

    def _draw_info(self, canvas, level, player, enemies, elapsed, game_state=None):

        width, height = canvas.get_size()
        cx, cy = width // 2, height // 2

        panel = pygame.Rect(cx - 320, cy - 300, 640, 600)

        pygame.draw.rect(canvas, (15, 19, 23), panel, border_radius=14)
        pygame.draw.rect(
            canvas, (85, 180, 105), panel, 3, border_radius=14
        )

        title = self.title_font.render(
            "PARTIDA", True, (105, 225, 125)
        )
        canvas.blit(title, title.get_rect(center=(cx, panel.top + 45)))

        killed = sum(1 for e in enemies if not e.alive)
        total = len(enemies)

        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        rows = [
            ("NIVEL", level.name),
            ("TIEMPO TOTAL", (
                f"{int(game_state.elapsed_time // 60):02}:"
                f"{int(game_state.elapsed_time % 60):02}"
                if game_state else f"{minutes:02}:{seconds:02}"
            )),
            ("ENEMIGOS ELIMINADOS", f"{killed} / {total}"),
            ("ENEMIGOS RESTANTES", str(total - killed)),
            ("VIDAS RESTANTES", str(player.lives)),
            ("PUNTAJE", str(game_state.score if game_state else 0)),
            ("ENEMIGOS RESTANTES", str(game_state.enemies_remaining if game_state else sum(1 for e in enemies if e.alive))),
            ("MUERTES", str(game_state.deaths if game_state else 0)),
            ("OBJETOS RECOLECTADOS", str(game_state.pickups_collected if game_state else 0)),
            ("MUNICION PERDIDA", str(game_state.objects_lost if game_state else player.objects_lost)),
            (
                "SALUD ACTUAL",
                f"{round(player.hp)} / {player.max_hp}"
            ),
            (
                "ARMA EQUIPADA",
                self.WEAPON_NAMES.get(player.equipped, player.equipped)
            ),
        ]

        for gun in ("rifle", "shotgun"):

            if gun in player.unlocked and gun in player.ammo:
                ammo = player.ammo[gun]
                rows.append((
                    f"MUNICION {self.WEAPON_NAMES[gun]}",
                    f"{ammo['mag']} / {ammo['reserve']}"
                ))

        y = panel.top + 82

        for label, value in rows:

            label_surface = self.small_font.render(
                label, True, (155, 165, 165)
            )
            value_surface = self.font.render(
                value, True, (245, 245, 245)
            )

            canvas.blit(label_surface, (panel.left + 40, y))
            canvas.blit(
                value_surface,
                value_surface.get_rect(
                    midright=(panel.right - 40, y + 9)
                )
            )

            y += 24

        # Controles
        y += 6

        pygame.draw.line(
            canvas, (65, 100, 75),
            (panel.left + 40, y),
            (panel.right - 40, y), 2
        )

        y += 12

        heading = self.small_font.render(
            "CONTROLES", True, (105, 225, 125)
        )
        canvas.blit(heading, (panel.left + 40, y))

        y += 22

        for line in self.CONTROLS:
            text = self.tiny_font.render(line, True, (205, 215, 210))
            canvas.blit(text, (panel.left + 40, y))
            y += 20

        hint = self.tiny_font.render(
            "ESC / ENTER / clic: volver", True, (155, 165, 165)
        )
        canvas.blit(
            hint, hint.get_rect(center=(cx, panel.bottom - 24))
        )
