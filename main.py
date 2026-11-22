
import sys
import pygame

import settings
from src.level import Level
from src.player import Player
from src.enemy import Enemy
from src.effects import Effect
from src.menu import Menu
from src.settings_menu import SettingsMenu


def start_level(index, sounds):
    """Crea el nivel, el jugador y los enemigos de un nivel (0 = nivel 1)."""
    level = Level(settings.LEVELS[index])
    player = Player(level.player_start, sounds)

    types = settings.LEVEL_ENEMY_TYPES.get(index + 1, ["zombie_normal"])
    enemies = []
    for i, spawn in enumerate(level.zombie_spawns):
        kind = types[min(i, len(types) - 1)]
        enemies.append(Enemy(kind, spawn, level))

    return level, player, enemies


def draw_hud(canvas, font, big_font, level, player, enemies):
    alive = sum(1 for e in enemies if e.alive)

    canvas.blit(
        font.render(f"{level.name} | {player.weapon}", True, (255, 255, 255)),
        (12, 10)
    )

    # Barra de vida del jugador
    bar_w = 240
    ratio = player.hp / player.max_hp
    pygame.draw.rect(canvas, (40, 0, 0), (12, 34, bar_w, 18))
    pygame.draw.rect(canvas, (200, 40, 40), (12, 34, round(bar_w * ratio), 18))
    pygame.draw.rect(canvas, (255, 255, 255), (12, 34, bar_w, 18), 2)
    canvas.blit(
        font.render(f"VIDA {round(player.hp)}/{player.max_hp}", True, (255, 255, 255)),
        (20, 37)
    )

    canvas.blit(
        font.render(f"Enemigos restantes: {alive}", True, (255, 220, 120)),
        (12, 60)
    )

    if player.dead_done:
        overlay = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        canvas.blit(overlay, (0, 0))

        title = big_font.render("GAME OVER", True, (220, 40, 40))
        hint = font.render("R: reintentar    ESC: menu", True, (255, 255, 255))
        cx = canvas.get_width() // 2
        canvas.blit(title, title.get_rect(center=(cx, 300)))
        canvas.blit(hint, hint.get_rect(center=(cx, 370)))


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
    big_font = pygame.font.Font(None, 110)

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
    enemies = []
    bullets = []
    effects = []
    level_index = 0

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

                        level_index = result
                        level, player, enemies = start_level(
                            level_index, menu.sounds
                        )
                        bullets = []
                        effects = []

                        camera = pygame.Vector2()

                        playing = True

                        menu.sounds.play_level_music(result + 1)
                        menu.sounds.play_horde()

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
                        enemies = []
                        bullets = []
                        effects = []

                        menu.sounds.stop_horde()
                        menu.sounds.stop_footsteps()
                        menu.sounds.play_menu_music()

                    elif event.key == pygame.K_1:
                        player.set_weapon("rifle")

                    elif event.key == pygame.K_2:
                        player.set_weapon("shotgun")
                        
                    # K = escudo (igual que el clic derecho)
                    elif event.key == pygame.K_k:
                        player.toggle_shield()

                    # R = recargar; si ya moriste, reinicia el nivel
                    elif event.key == pygame.K_r:
                        if player.dead_done:
                            level, player, enemies = start_level(
                                level_index, menu.sounds
                            )
                            bullets = []
                            effects = []
                            menu.sounds.play_horde()
                        else:
                            player.play_action("reload")
                        
                    elif event.key == pygame.K_F2:
                        debug = not debug
                    elif event.key == pygame.K_F3:
                        player.play_test_animation("dead")

                    elif event.key == pygame.K_F4:
                        player.play_test_animation("pickup")

                # Clic derecho = escudo (el disparo con clic izquierdo
                # se lee más abajo para poder mantenerlo presionado)
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 3
                ):
                    player.toggle_shield()

        # --------------------------------
        # ACTUALIZAR JUEGO
        # --------------------------------
        if playing:

            keys = pygame.key.get_pressed()

            # Posición del mouse en el mundo (ventana -> canvas -> mapa)
            window_width, window_height = screen.get_size()
            mouse_x, mouse_y = pygame.mouse.get_pos()
            player.aim.update(
                mouse_x * settings.SCREEN_WIDTH / window_width + camera.x,
                mouse_y * settings.SCREEN_HEIGHT / window_height + camera.y
            )

            # Disparo: clic izquierdo o tecla J (se puede mantener)
            if pygame.mouse.get_pressed()[0] or keys[pygame.K_j]:
                player.try_shoot()

            player.update(dt, keys, level)

            # Balas nuevas del jugador
            bullets.extend(player.pending_bullets)
            player.pending_bullets.clear()

            # Enemigos y balas
            for enemy in enemies:
                enemy.update(dt, player, level, enemies, menu.sounds)

            for bullet in bullets:
                bullet.update(dt, level, enemies, effects)
            bullets = [b for b in bullets if b.alive]

            # Efectos de impacto sobre el jugador (sangre / escudo)
            for kind, pos in player.pending_effects:
                effects.append(Effect(kind, pos))
            player.pending_effects.clear()

            for effect in effects:
                effect.update(dt)
            effects = [e for e in effects if e.alive]

            if not player.alive:
                menu.sounds.stop_horde()

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

            # Cadáveres primero, luego vivos ordenados por profundidad (y)
            for enemy in enemies:
                if not enemy.alive:
                    enemy.draw(canvas, camera)

            actors = [e for e in enemies if e.alive] + [player]
            for actor in sorted(actors, key=lambda a: a.pos.y):
                actor.draw(canvas, camera)

            for bullet in bullets:
                bullet.draw(canvas, camera)

            for effect in effects:
                effect.draw(canvas, camera)

            # Mira del mouse
            if player.alive:
                aim_screen = (
                    round(player.aim.x - camera.x),
                    round(player.aim.y - camera.y)
                )
                pygame.draw.circle(canvas, (255, 255, 255), aim_screen, 9, 1)
                pygame.draw.line(canvas, (255, 255, 255),
                                 (aim_screen[0] - 14, aim_screen[1]),
                                 (aim_screen[0] + 14, aim_screen[1]), 1)
                pygame.draw.line(canvas, (255, 255, 255),
                                 (aim_screen[0], aim_screen[1] - 14),
                                 (aim_screen[0], aim_screen[1] + 14), 1)

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

                for enemy in enemies:
                    if enemy.alive:
                        pygame.draw.rect(
                            canvas, (255, 160, 0),
                            enemy.hit_rect().move(-camera.x, -camera.y), 1
                        )
                        pygame.draw.rect(
                            canvas, (60, 255, 60),
                            enemy.foot_rect().move(-camera.x, -camera.y), 1
                        )

            draw_hud(canvas, font, big_font, level, player, enemies)

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
