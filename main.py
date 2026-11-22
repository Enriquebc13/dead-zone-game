
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
    player = Player(
        level.player_start, sounds,
        settings.LEVEL_WEAPONS.get(index + 1)
    )

    types = settings.LEVEL_ENEMY_TYPES.get(index + 1, ["zombie_normal"])
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
            settings.AXE_KNOCKBACK, level
        )
        effects.append(Effect("blood", enemy.hit_rect().center, scale=0.9))


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

        # None = no se pudo usar (vida llena, reserva llena...): se queda en el piso
        if message is not None:
            pickup.collected = True
            floating.append([message, pygame.Vector2(player.pos.x, player.pos.y - 110), 0.0])


def draw_hotbar(canvas, font, player):
    x, y = 12, canvas.get_height() - 54

    for key, slot, label in HOTBAR:

        if slot not in player.unlocked:
            continue

        selected = slot == player.equipped
        rect = pygame.Rect(x, y, 150, 42)

        pygame.draw.rect(canvas, (20, 20, 20), rect)
        pygame.draw.rect(
            canvas, (255, 220, 90) if selected else (120, 120, 120), rect, 2
        )

        canvas.blit(
            font.render(f"[{key}] {label}", True, (255, 255, 255)),
            (x + 8, y + 5)
        )

        if slot in player.ammo:
            ammo = player.ammo[slot]
            empty = ammo["mag"] == 0 and ammo["reserve"] == 0
            text = "SIN BALAS" if empty else f"{ammo['mag']} / {ammo['reserve']}"
            color = (230, 70, 70) if empty or ammo["mag"] == 0 else (255, 220, 120)
        else:
            text, color = "cuerpo a cuerpo", (190, 190, 190)

        canvas.blit(font.render(text, True, color), (x + 8, y + 23))

        x += 158


def draw_hud(canvas, font, big_font, level, player, enemies):
    alive = sum(1 for e in enemies if e.alive)

    canvas.blit(
        font.render(f"{level.name}", True, (255, 255, 255)),
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

    draw_hotbar(canvas, font, player)

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
    floating = []            # textos flotantes (+30 balas, +25 vida...)
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
                        floating = []

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
                        floating = []

                        menu.sounds.stop_horde()
                        menu.sounds.stop_footsteps()
                        menu.sounds.play_menu_music()

                    # 1 = rifle, 2 = hacha, 3 = escopeta (si ya la recogiste)
                    elif event.key == pygame.K_1:
                        player.equip("rifle")

                    elif event.key == pygame.K_2:
                        player.equip("axe")

                    elif event.key == pygame.K_3:
                        player.equip("shotgun")

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
                            floating = []
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

            # Atacar (dispara o golpea con el hacha según el arma equipada):
            # clic izquierdo o tecla J, se puede mantener
            if pygame.mouse.get_pressed()[0] or keys[pygame.K_j]:
                player.attack()

            player.update(dt, keys, level)

            # Golpe de hacha en el cuadro de impacto
            if player.pending_melee:
                player.pending_melee = False
                resolve_melee(player, enemies, effects, level)

            # Suministros del mapa
            collect_pickups(level, player, floating)

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

            for item in floating:
                item[1].y -= 30 * dt
                item[2] += dt
            floating = [f for f in floating if f[2] < 1.4]

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

            for text, pos, age in floating:
                label = font.render(text, True, (255, 255, 160))
                canvas.blit(
                    label,
                    label.get_rect(center=(round(pos.x - camera.x), round(pos.y - camera.y)))
                )

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
