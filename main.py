
import sys
import pygame

import settings
from src.level import Level
from src.player import Player
from src.menu import Menu
from src.settings_menu import SettingsMenu


def main():
    pygame.init()

    # Crear ventana redimensionable
    screen = pygame.display.set_mode(
        (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
        pygame.RESIZABLE
    )

    pygame.display.set_caption(settings.TITLE)

    # Superficie interna del juego
    canvas = pygame.Surface((
        settings.SCREEN_WIDTH,
        settings.SCREEN_HEIGHT
    ))

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    # Crear menú principal
    menu = Menu()

    # Crear menú de configuración
    # Se reutiliza el SoundManager del menú principal
    settings_menu = SettingsMenu(menu.sounds)

    # Estados del juego
    playing = False
    in_settings = False

    level = None
    player = None

    camera = pygame.Vector2()

    debug = False
    fullscreen = False

    while True:
        dt = min(clock.tick(settings.FPS) / 1000, 0.05)

        # Obtener tamaño actual de la ventana
        window_width, window_height = screen.get_size()

        # Eventos
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # --------------------------------
            # PANTALLA COMPLETA
            # --------------------------------
            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen

                    if fullscreen:
                        screen = pygame.display.set_mode(
                            (0, 0),
                            pygame.FULLSCREEN
                        )
                    else:
                        screen = pygame.display.set_mode(
                            (
                                settings.SCREEN_WIDTH,
                                settings.SCREEN_HEIGHT
                            ),
                            pygame.RESIZABLE
                        )

                    window_width, window_height = screen.get_size()
                    continue

            # --------------------------------
            # MENU Y CONFIGURACION
            # --------------------------------
            if not playing:

                # Adaptar posición del mouse
                # a la resolución interna
                current_event = event

                if event.type in (
                    pygame.MOUSEMOTION,
                    pygame.MOUSEBUTTONDOWN
                ):

                    mouse_x = int(
                        event.pos[0] *
                        settings.SCREEN_WIDTH / window_width
                    )

                    mouse_y = int(
                        event.pos[1] *
                        settings.SCREEN_HEIGHT / window_height
                    )

                    current_event = pygame.event.Event(
                        event.type,
                        {
                            **event.dict,
                            "pos": (mouse_x, mouse_y)
                        }
                    )

                # --------------------------------
                # CONFIGURACION
                # --------------------------------
                if in_settings:

                    result = settings_menu.handle_event(
                        current_event
                    )

                    # Regresar al menú principal
                    if result == "back":
                        in_settings = False

                # --------------------------------
                # MENU PRINCIPAL
                # --------------------------------
                else:

                    # Salir del juego
                    if event.type == pygame.KEYDOWN:

                        if event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()

                    result = menu.handle_event(current_event)

                    # Abrir configuración
                    if result == "settings":
                        in_settings = True

                    # Iniciar nivel seleccionado
                    elif isinstance(result, int):

                        menu.stop_music()

                        level = Level(
                            settings.LEVELS[result]
                        )

                        player = Player(level.player_start, menu.sounds)

                        camera = pygame.Vector2()

                        playing = True

                    
                        menu.sounds.play_level_music(result + 1)

            # --------------------------------
            # DENTRO DEL NIVEL
            # --------------------------------
            else:

                if event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_ESCAPE:

                        # Volver al menú
                        playing = False

                        level = None
                        player = None
                        
                        menu.sounds.stop_footsteps()
                        menu.sounds.play_menu_music()

                    elif event.key == pygame.K_1:
                        player.set_weapon("rifle")

                    elif event.key == pygame.K_2:
                        player.set_weapon("shotgun")
                        
                    elif event.key == pygame.K_j:
                        player.play_action("shoot")

                    elif event.key == pygame.K_k:
                        player.toggle_shield()

                    elif event.key == pygame.K_r:
                        player.play_action("reload")
                        
                    elif event.key == pygame.K_F2:
                        debug = not debug

        # --------------------------------
        # ACTUALIZAR JUEGO
        # --------------------------------
        if playing:

            player.update(
                dt,
                pygame.key.get_pressed(),
                level
            )

            # Cámara sigue al soldado
            camera.x = (
                player.pos.x - settings.SCREEN_WIDTH / 2
            )

            camera.y = (
                player.pos.y - settings.SCREEN_HEIGHT / 2
            )

            camera.x = max(
                0,
                min(
                    camera.x,
                    max(0, level.width - settings.SCREEN_WIDTH)
                )
            )

            camera.y = max(
                0,
                min(
                    camera.y,
                    max(0, level.height - settings.SCREEN_HEIGHT)
                )
            )

            # Dibujar nivel y jugador
            canvas.fill((15, 15, 15))

            level.draw(canvas, camera)
            player.draw(canvas, camera)

            # Información de depuración
            if debug:

                for rect in level.collisions:
                    pygame.draw.rect(
                        canvas,
                        (255, 60, 60),
                        rect.move(-camera.x, -camera.y),
                        2
                    )

                pygame.draw.rect(
                    canvas,
                    (60, 255, 60),
                    player._foot_rect(player.pos).move(
                        -camera.x,
                        -camera.y
                    ),
                    1
                )

            info = (
                f"{level.name} | "
                f"{player.weapon} | "
                f"{player.state}"
            )

            canvas.blit(
                font.render(info, True, (255, 255, 255)),
                (12, 10)
            )

        # --------------------------------
        # DIBUJAR MENU
        # --------------------------------
        else:

            # Dibujar menú principal
            menu.draw(canvas)

            # Dibujar configuración encima
            if in_settings:
                settings_menu.draw(canvas)

        # --------------------------------
        # ADAPTAR A LA VENTANA
        # --------------------------------
        window_width, window_height = screen.get_size()

        scaled_canvas = pygame.transform.scale(
            canvas,
            (window_width, window_height)
        )

        screen.blit(scaled_canvas, (0, 0))

        pygame.display.flip()


if __name__ == "__main__":
    main()
