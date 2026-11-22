
import sys
import pygame

import settings
from src.level import Level
from src.player import Player
from src.enemy import Enemy
from src.effects import Effect
from src.menu import Menu
from src.settings_menu import SettingsMenu
from src.victory_screen import VictoryScreen


def start_level(index, sounds):
    """Crea el nivel, el jugador y los enemigos de un nivel (0 = nivel 1)."""
    level = Level(settings.LEVELS[index])

    player = Player(
        level.player_start,
        sounds,
        settings.LEVEL_WEAPONS.get(index + 1)
    )

    types = settings.LEVEL_ENEMY_TYPES.get(
        index + 1,
        ["zombie_normal"]
    )

    enemies = []

    for i, spawn in enumerate(level.zombie_spawns):
        kind = types[min(i, len(types) - 1)]
        enemies.append(Enemy(kind, spawn, level))

    return level, player, enemies


# Casillas de arma: (tecla, nombre interno, texto)
HOTBAR = (
    ("1", "rifle", "RIFLE"),
    ("2", "axe", "HACHA"),
    ("3", "shotgun", "ESCOPETA"),
)


def resolve_melee(player, enemies, effects, level):
    """Aplica el golpe de hacha a los enemigos que estén al alcance."""

    for enemy in player.melee_targets(enemies):
        enemy.take_damage(settings.AXE_DAMAGE)

        enemy.knockback(
            (enemy.pos.x - player.pos.x, 0),
            settings.AXE_KNOCKBACK,
            level
        )

        effects.append(
            Effect("blood", enemy.hit_rect().center, scale=0.9)
        )


def collect_pickups(level, player, floating):
    """Recoge los suministros que el soldado esté pisando."""

    if not player.alive:
        return

    for pickup in level.pickups:

        if pickup.collected:
            continue

        if player.pos.distance_to(pickup.pos) > settings.PICKUP_RADIUS:
            continue

        message = player.collect(pickup.kind)

        # None = no se pudo usar: se queda en el piso
        if message is not None:
            pickup.collected = True

            floating.append([
                message,
                pygame.Vector2(
                    player.pos.x,
                    player.pos.y - 110
                ),
                0.0
            ])


def draw_hotbar(canvas, font, player):
    x, y = 12, canvas.get_height() - 54

    for key, slot, label in HOTBAR:

        if slot not in player.unlocked:
            continue

        selected = slot == player.equipped
        rect = pygame.Rect(x, y, 150, 42)

        pygame.draw.rect(canvas, (20, 20, 20), rect)

        pygame.draw.rect(
            canvas,
            (255, 220, 90) if selected else (120, 120, 120),
            rect,
            2
        )

        canvas.blit(
            font.render(f"[{key}] {label}", True, (255, 255, 255)),
            (x + 8, y + 5)
        )

        if slot in player.ammo:
            ammo = player.ammo[slot]

            empty = (
                ammo["mag"] == 0
                and ammo["reserve"] == 0
            )

            text = (
                "SIN BALAS"
                if empty
                else f"{ammo['mag']} / {ammo['reserve']}"
            )

            color = (
                (230, 70, 70)
                if empty or ammo["mag"] == 0
                else (255, 220, 120)
            )

        else:
            text = "cuerpo a cuerpo"
            color = (190, 190, 190)

        canvas.blit(
            font.render(text, True, color),
            (x + 8, y + 23)
        )

        x += 158


def draw_hud(canvas, font, big_font, level, player, enemies):
    alive = sum(1 for e in enemies if e.alive)

    canvas.blit(
        font.render(level.name, True, (255, 255, 255)),
        (12, 10)
    )

    # Barra de vida del jugador
    bar_w = 240
    ratio = player.hp / player.max_hp

    pygame.draw.rect(
        canvas,
        (40, 0, 0),
        (12, 34, bar_w, 18)
    )

    pygame.draw.rect(
        canvas,
        (200, 40, 40),
        (12, 34, round(bar_w * ratio), 18)
    )

    pygame.draw.rect(
        canvas,
        (255, 255, 255),
        (12, 34, bar_w, 18),
        2
    )

    canvas.blit(
        font.render(
            f"VIDA {round(player.hp)}/{player.max_hp}",
            True,
            (255, 255, 255)
        ),
        (20, 37)
    )

    canvas.blit(
        font.render(
            f"Enemigos restantes: {alive}",
            True,
            (255, 220, 120)
        ),
        (12, 60)
    )

    draw_hotbar(canvas, font, player)

    # Pantalla de Game Over
    if player.dead_done:

        overlay = pygame.Surface(
            canvas.get_size(),
            pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 160))
        canvas.blit(overlay, (0, 0))

        title = big_font.render(
            "GAME OVER",
            True,
            (220, 40, 40)
        )

        hint = font.render(
            "R: reintentar    ESC: menu",
            True,
            (255, 255, 255)
        )

        cx = canvas.get_width() // 2

        canvas.blit(
            title,
            title.get_rect(center=(cx, 300))
        )

        canvas.blit(
            hint,
            hint.get_rect(center=(cx, 370))
        )


def return_to_menu(menu, state):
    """Limpia la partida y regresa al menú principal."""

    state["playing"] = False
    state["victory"] = False

    state["level"] = None
    state["player"] = None
    state["enemies"] = []

    state["bullets"] = []
    state["effects"] = []
    state["floating"] = []

    menu.sounds.stop_horde()
    menu.sounds.stop_footsteps()
    menu.sounds.play_menu_music()


def main():
    pygame.init()

    # Crear ventana redimensionable
    screen = pygame.display.set_mode(
        (
            settings.SCREEN_WIDTH,
            settings.SCREEN_HEIGHT
        ),
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

    # --------------------------------
    # MENUS
    # --------------------------------

    menu = Menu()
    settings_menu = SettingsMenu(menu.sounds)
    victory_screen = VictoryScreen()

    # --------------------------------
    # ESTADOS DEL JUEGO
    # --------------------------------

    playing = False
    in_settings = False
    victory = False

    level = None
    player = None
    enemies = []

    bullets = []
    effects = []
    floating = []

    level_index = 0

    # Tiempo de partida
    level_start_time = 0
    victory_elapsed = 0

    camera = pygame.Vector2()

    debug = False
    fullscreen = False

    while True:

        dt = min(clock.tick(settings.FPS) / 1000, 0.05)

        # Obtener tamaño actual de la ventana
        window_width, window_height = screen.get_size()

        # --------------------------------
        # EVENTOS
        # --------------------------------

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

                current_event = event

                # Adaptar posición del mouse al canvas
                if event.type in (
                    pygame.MOUSEMOTION,
                    pygame.MOUSEBUTTONDOWN
                ):

                    mouse_x = int(
                        event.pos[0]
                        * settings.SCREEN_WIDTH
                        / window_width
                    )

                    mouse_y = int(
                        event.pos[1]
                        * settings.SCREEN_HEIGHT
                        / window_height
                    )

                    current_event = pygame.event.Event(
                        event.type,
                        {
                            **event.dict,
                            "pos": (mouse_x, mouse_y)
                        }
                    )

                # CONFIGURACION
                if in_settings:

                    result = settings_menu.handle_event(
                        current_event
                    )

                    if result == "back":
                        in_settings = False

                # MENU PRINCIPAL
                else:

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
                            level_index,
                            menu.sounds
                        )

                        bullets = []
                        effects = []
                        floating = []

                        camera = pygame.Vector2()

                        victory = False
                        victory_elapsed = 0

                        level_start_time = pygame.time.get_ticks()

                        playing = True

                        menu.sounds.play_level_music(result + 1)
                        menu.sounds.play_horde()

            # --------------------------------
            # DENTRO DEL NIVEL
            # --------------------------------

            else:

                # --------------------------------
                # PANTALLA DE VICTORIA
                # --------------------------------

                if victory:

                    result = victory_screen.handle_event(
                        event,
                        screen.get_size(),
                        (
                            settings.SCREEN_WIDTH,
                            settings.SCREEN_HEIGHT
                        )
                    )

                    if result == "menu":

                        state = {
                            "playing": playing,
                            "victory": victory,
                            "level": level,
                            "player": player,
                            "enemies": enemies,
                            "bullets": bullets,
                            "effects": effects,
                            "floating": floating
                        }

                        return_to_menu(menu, state)

                        playing = state["playing"]
                        victory = state["victory"]

                        level = state["level"]
                        player = state["player"]
                        enemies = state["enemies"]

                        bullets = state["bullets"]
                        effects = state["effects"]
                        floating = state["floating"]

                # --------------------------------
                # CONTROLES NORMALES DEL JUGADOR
                # --------------------------------

                else:

                    if event.type == pygame.KEYDOWN:

                        if event.key == pygame.K_ESCAPE:

                            # Volver al menú
                            state = {
                                "playing": playing,
                                "victory": victory,
                                "level": level,
                                "player": player,
                                "enemies": enemies,
                                "bullets": bullets,
                                "effects": effects,
                                "floating": floating
                            }

                            return_to_menu(menu, state)

                            playing = state["playing"]
                            victory = state["victory"]

                            level = state["level"]
                            player = state["player"]
                            enemies = state["enemies"]

                            bullets = state["bullets"]
                            effects = state["effects"]
                            floating = state["floating"]

                        # 1 = rifle
                        elif event.key == pygame.K_1:
                            player.equip("rifle")

                        # 2 = hacha
                        elif event.key == pygame.K_2:
                            player.equip("axe")

                        # 3 = escopeta
                        elif event.key == pygame.K_3:
                            player.equip("shotgun")

                        # K = escudo
                        elif event.key == pygame.K_k:
                            player.toggle_shield()

                        # R = recargar o reiniciar
                        elif event.key == pygame.K_r:

                            if player.dead_done:

                                level, player, enemies = start_level(
                                    level_index,
                                    menu.sounds
                                )

                                bullets = []
                                effects = []
                                floating = []

                                victory = False
                                victory_elapsed = 0

                                level_start_time = pygame.time.get_ticks()

                                camera = pygame.Vector2()

                                menu.sounds.play_horde()

                            else:
                                player.play_action("reload")

                        elif event.key == pygame.K_F2:
                            debug = not debug

                        elif event.key == pygame.K_F3:
                            player.play_test_animation("dead")

                        elif event.key == pygame.K_F4:
                            player.play_test_animation("pickup")

                        # H = atacar con hacha
                        elif event.key == pygame.K_h:
                            player.play_action("axe")

                    # Clic derecho = escudo
                    elif (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 3
                    ):
                        player.toggle_shield()

        # --------------------------------
        # ACTUALIZAR Y DIBUJAR JUEGO
        # --------------------------------

        if playing and not victory:

            keys = pygame.key.get_pressed()

            # --------------------------------
            # APUNTAR
            # --------------------------------

            window_width, window_height = screen.get_size()

            mouse_x, mouse_y = pygame.mouse.get_pos()

            player.aim.update(
                mouse_x * settings.SCREEN_WIDTH / window_width + camera.x,
                mouse_y * settings.SCREEN_HEIGHT / window_height + camera.y
            )

            # --------------------------------
            # ATACAR
            # --------------------------------

            if (
                pygame.mouse.get_pressed()[0]
                or keys[pygame.K_j]
            ):
                player.attack()

            player.update(dt, keys, level)

            # --------------------------------
            # GOLPE DE HACHA
            # --------------------------------

            if player.pending_melee:

                player.pending_melee = False

                resolve_melee(
                    player,
                    enemies,
                    effects,
                    level
                )

            # --------------------------------
            # SUMINISTROS
            # --------------------------------

            collect_pickups(
                level,
                player,
                floating
            )

            # --------------------------------
            # BALAS DEL JUGADOR
            # --------------------------------

            bullets.extend(player.pending_bullets)
            player.pending_bullets.clear()

            # --------------------------------
            # ACTUALIZAR ENEMIGOS
            # --------------------------------

            for enemy in enemies:
                enemy.update(
                    dt,
                    player,
                    level,
                    enemies,
                    menu.sounds
                )

            # --------------------------------
            # ACTUALIZAR BALAS
            # --------------------------------

            for bullet in bullets:
                bullet.update(
                    dt,
                    level,
                    enemies,
                    effects
                )

            bullets = [
                b for b in bullets if b.alive
            ]

            # --------------------------------
            # EFECTOS DEL JUGADOR
            # --------------------------------

            for kind, pos in player.pending_effects:
                effects.append(Effect(kind, pos))

            player.pending_effects.clear()

            # --------------------------------
            # ACTUALIZAR EFECTOS
            # --------------------------------

            for effect in effects:
                effect.update(dt)

            effects = [
                e for e in effects if e.alive
            ]

            # --------------------------------
            # TEXTOS FLOTANTES
            # --------------------------------

            for item in floating:
                item[1].y -= 30 * dt
                item[2] += dt

            floating = [
                f for f in floating if f[2] < 1.4
            ]

            # --------------------------------
            # DETECTAR MUERTE DEL JUGADOR
            # --------------------------------

            if not player.alive:
                menu.sounds.stop_horde()

            # --------------------------------
            # DETECTAR VICTORIA
            # --------------------------------

            if (
                enemies
                and not victory
                and all(
                    not enemy.alive and enemy.finished
                    for enemy in enemies
                )
            ):

                victory = True

                victory_elapsed = (
                    pygame.time.get_ticks() - level_start_time
                ) / 1000

                menu.sounds.stop_horde()
                menu.sounds.stop_footsteps()

            # --------------------------------
            # CAMARA
            # --------------------------------

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
                    max(
                        0,
                        level.width - settings.SCREEN_WIDTH
                    )
                )
            )

            camera.y = max(
                0,
                min(
                    camera.y,
                    max(
                        0,
                        level.height - settings.SCREEN_HEIGHT
                    )
                )
            )

            # --------------------------------
            # DIBUJAR NIVEL
            # --------------------------------

            canvas.fill((15, 15, 15))

            level.draw(canvas, camera)

            # Cadáveres primero
            for enemy in enemies:

                if not enemy.alive:
                    enemy.draw(canvas, camera)

            # Actores vivos ordenados por profundidad
            actors = [
                e for e in enemies if e.alive
            ] + [player]

            for actor in sorted(
                actors,
                key=lambda a: a.pos.y
            ):
                actor.draw(canvas, camera)

            # Balas
            for bullet in bullets:
                bullet.draw(canvas, camera)

            # Efectos
            for effect in effects:
                effect.draw(canvas, camera)

            # Textos flotantes
            for text, pos, age in floating:

                label = font.render(
                    text,
                    True,
                    (255, 255, 160)
                )

                canvas.blit(
                    label,
                    label.get_rect(
                        center=(
                            round(pos.x - camera.x),
                            round(pos.y - camera.y)
                        )
                    )
                )

            # --------------------------------
            # MIRA DEL MOUSE
            # --------------------------------

            if player.alive:

                aim_screen = (
                    round(player.aim.x - camera.x),
                    round(player.aim.y - camera.y)
                )

                pygame.draw.circle(
                    canvas,
                    (255, 255, 255),
                    aim_screen,
                    9,
                    1
                )

                pygame.draw.line(
                    canvas,
                    (255, 255, 255),
                    (aim_screen[0] - 14, aim_screen[1]),
                    (aim_screen[0] + 14, aim_screen[1]),
                    1
                )

                pygame.draw.line(
                    canvas,
                    (255, 255, 255),
                    (aim_screen[0], aim_screen[1] - 14),
                    (aim_screen[0], aim_screen[1] + 14),
                    1
                )

            # --------------------------------
            # DEPURACION
            # --------------------------------

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
                    player._foot_rect(
                        player.pos
                    ).move(
                        -camera.x,
                        -camera.y
                    ),
                    1
                )

                for enemy in enemies:

                    if enemy.alive:

                        pygame.draw.rect(
                            canvas,
                            (255, 160, 0),
                            enemy.hit_rect().move(
                                -camera.x,
                                -camera.y
                            ),
                            1
                        )

                        pygame.draw.rect(
                            canvas,
                            (60, 255, 60),
                            enemy.foot_rect().move(
                                -camera.x,
                                -camera.y
                            ),
                            1
                        )

            # HUD
            draw_hud(
                canvas,
                font,
                big_font,
                level,
                player,
                enemies
            )

        # --------------------------------
        # PANTALLA DE VICTORIA
        # --------------------------------

        elif playing and victory:

            # No se actualiza el nivel.
            # Solamente se dibuja el último estado.

            canvas.fill((15, 15, 15))

            level.draw(canvas, camera)

            # Dibujar cadáveres
            for enemy in enemies:
                enemy.draw(canvas, camera)

            player.draw(canvas, camera)

            for bullet in bullets:
                bullet.draw(canvas, camera)

            for effect in effects:
                effect.draw(canvas, camera)

            # HUD
            draw_hud(
                canvas,
                font,
                big_font,
                level,
                player,
                enemies
            )

            # Adaptar posición del mouse al canvas
            window_width, window_height = screen.get_size()

            mouse_x, mouse_y = pygame.mouse.get_pos()

            scaled_mouse = (
                int(
                    mouse_x
                    * settings.SCREEN_WIDTH
                    / window_width
                ),
                int(
                    mouse_y
                    * settings.SCREEN_HEIGHT
                    / window_height
                )
            )

            # Dibujar tablero de victoria
            victory_screen.draw(
                canvas,
                level,
                player,
                enemies,
                victory_elapsed,
                scaled_mouse
            )

        # --------------------------------
        # MENU PRINCIPAL
        # --------------------------------

        else:

            menu.draw(canvas)

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
