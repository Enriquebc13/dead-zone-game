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
from src.pause_menu import PauseMenu
from src.level_transition import LevelTransition
from src import minimap
from src.game_state import GameState


# Nivel 4: posiciones (en la lista de enemigos) de cada tramo del recorrido
STREET_GROUP = range(0, 5)    # calle inicial
GATE_PEN = range(5, 10)       # encerrados tras la reja


def street_cleared(enemies):
    """True cuando los 5 infectados de la calle inicial ya murieron."""
    return all(not e.alive for e in enemies[STREET_GROUP.start:STREET_GROUP.stop])


def interact_lever(level, player, enemies, floating, sounds):
    """E junto a la palanca: abre la reja si la primera calle esta despejada."""
    if not player.alive or not level.near_lever(player.pos):
        return
    if level.gate_open or level.gate_opening:
        return

    if not street_cleared(enemies):
        message = "ELIMINA A LOS 5 DE LA CALLE"
    elif level.begin_gate_open():
        message = "¡LA REJA SE ABRE! BUSCA COBERTURA"
        # Los encerrados oyen el mecanismo y salen directo hacia el jugador
        for enemy in enemies[GATE_PEN.start:GATE_PEN.stop]:
            if enemy.alive:
                enemy.aggro = True
        sounds.play_zombie("growl")
    else:
        return

    floating.append([message, pygame.Vector2(player.pos.x, player.pos.y - 110), 0.0])


def level_objective(level, enemies):
    """Texto de objetivo del nivel con reja (None si el nivel no tiene)."""
    if level.gate_rect is None:
        return None
    if not street_cleared(enemies):
        left = sum(1 for e in enemies[STREET_GROUP.start:STREET_GROUP.stop] if e.alive)
        return f"OBJETIVO: elimina a los infectados de la calle ({left} restantes)"
    if not (level.gate_opening or level.gate_open):
        return "OBJETIVO: baja la palanca (E), lejos de la reja, y busca cobertura"
    if any(e.alive for e in enemies[GATE_PEN.start:GATE_PEN.stop]):
        return "OBJETIVO: ¡resiste a los infectados que salieron de la reja!"
    return "OBJETIVO: avanza al este y elimina a todos los infectados"


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
        patrol_type = "none"
        patrol_points = None

        # Los seis enemigos del nivel 1 se dividen en tres comportamientos.
        # Los demás niveles conservan su comportamiento anterior.
        if index == 0 and i < 6:
            if i in (0, 1):
                patrol_type = "ab"
                route = level.patrol_routes.get(i, {})
                patrol_points = [route[key] for key in ("a", "b") if key in route]
            elif i in (2, 3):
                patrol_type = "waypoints"
                patrol_points = level.waypoint_routes.get(i, [])
            else:
                patrol_type = "states"
                # La máquina de estados patrulla alrededor de su posición inicial.
                patrol_points = [spawn + pygame.Vector2(-48, 0), spawn + pygame.Vector2(48, 0)]

        # Nivel 3: mezcla los tres patrones de patrullaje y reserva los dos
        # tanques del final de la lista como jefes.
        if index == 2:
            if i < 6:
                patrol_type = "ab"
                route = level.patrol_routes.get(i, {})
                patrol_points = [route[key] for key in ("a", "b") if key in route]
            elif i < 11:
                patrol_type = "waypoints"
                patrol_points = level.waypoint_routes.get(i, [])
            else:
                patrol_type = "states"
                patrol_points = [spawn + pygame.Vector2(-64, 0), spawn + pygame.Vector2(64, 0)]

        # Nivel 4 (zona urbana): 5 infectados patrullan la calle inicial,
        # 5 quedan encerrados tras la reja (indices 5-9, sin patrulla: esperan
        # quietos) y los 10 restantes patrullan la zona final.
        if index == 3 and not GATE_PEN.start <= i < GATE_PEN.stop:
            patrol_type = "states"
            patrol_points = [
                spawn + pygame.Vector2(-48, 0),
                spawn + pygame.Vector2(48, 0),
            ]

        # Nivel 5 (estacionamiento): 10 patrullan A<->B, 10 siguen waypoints
        # y los 10 últimos hacen guardia con máquina de estados.
        if index == 4:
            if i < 10:
                patrol_type = "ab"
                route = level.patrol_routes.get(i, {})
                patrol_points = [route[key] for key in ("a", "b") if key in route]
            elif i < 20:
                patrol_type = "waypoints"
                patrol_points = level.waypoint_routes.get(i, [])
            else:
                patrol_type = "states"
                patrol_points = [spawn + pygame.Vector2(-48, 0), spawn + pygame.Vector2(48, 0)]

        # En el nivel 2 los enemigos se organizan en tres grupos de horda.
        # Cada grupo despierta cuando uno de sus integrantes detecta al jugador.
        horde_group = None
        if index == 1:
            if i in (0, 1, 6, 9):
                horde_group = 1  # zona oeste
            elif i in (2, 3, 10, 11):
                horde_group = 2  # zona central
            elif i in (4, 5, 7, 8):
                horde_group = 3  # zona este

        enemies.append(
            Enemy(kind, spawn, level, patrol_type, patrol_points, horde_group)
        )

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


def collect_pickups(level, player, floating, game_state=None):
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
            if game_state is not None:
                game_state.register_pickup(pickup.kind)

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


def draw_hud(canvas, font, big_font, level, player, enemies, elapsed=0.0, game_state=None):
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

    killed = len(enemies) - alive

    canvas.blit(
        font.render(
            f"VIDAS: {player.lives}",
            True,
            (255, 100, 100)
        ),
        (270, 34)
    )

    canvas.blit(
        font.render(
            f"Eliminados: {killed}    Restantes: {alive}",
            True,
            (255, 220, 120)
        ),
        (12, 60)
    )

    minutes, seconds = divmod(int(elapsed), 60)

    canvas.blit(
        font.render(
            f"TIEMPO {minutes:02d}:{seconds:02d}",
            True,
            (150, 210, 255)
        ),
        (12, 84)
    )

    if game_state is not None:
        canvas.blit(
            font.render(
                f"PUNTAJE: {game_state.score}    RESTANTES: {game_state.enemies_remaining}",
                True, (255, 220, 120)
            ),
            (270, 60)
        )

    # Progreso de enemigos eliminados y minimapa
    minimap.draw_enemy_counter(canvas, font, enemies, (12, 78))
    minimap.draw_minimap(canvas, font, level, player, enemies)

    objective = level_objective(level, enemies)
    if objective:
        canvas.blit(font.render(objective, True, (255, 245, 190)), (12, 108))

    draw_hotbar(canvas, font, player)

    # Tablero de Game Over con resumen de la partida.
    if player.dead_done and player.lives <= 0:
        overlay = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        canvas.blit(overlay, (0, 0))

        cx, cy = canvas.get_width() // 2, canvas.get_height() // 2
        panel = pygame.Rect(cx - 270, cy - 250, 540, 500)
        pygame.draw.rect(canvas, (15, 19, 23), panel, border_radius=14)
        pygame.draw.rect(canvas, (180, 55, 55), panel, 3, border_radius=14)

        title = big_font.render("GAME OVER", True, (230, 55, 55))
        canvas.blit(title, title.get_rect(center=(cx, panel.top + 58)))

        total_time = game_state.elapsed_time if game_state else elapsed
        minutes, seconds = divmod(int(total_time), 60)
        stats = [
            ("NIVEL ALCANZADO", str(game_state.current_level if game_state else level.name)),
            ("PUNTAJE TOTAL", str(game_state.score if game_state else 0)),
            ("ENEMIGOS ELIMINADOS", str(game_state.enemies_killed if game_state else len(enemies) - alive)),
            ("ENEMIGOS RESTANTES", str(game_state.enemies_remaining if game_state else alive)),
            ("MUERTES", str(game_state.deaths if game_state else 0)),
            ("TIEMPO JUGADO", f"{minutes:02d}:{seconds:02d}"),
            ("OBJETOS RECOLECTADOS", str(game_state.pickups_collected if game_state else 0)),
            ("MUNICION PERDIDA", str(game_state.objects_lost if game_state else player.objects_lost)),
        ]
        y = panel.top + 112
        for label, value in stats:
            left = font.render(label, True, (175, 185, 185))
            right = font.render(value, True, (250, 245, 225))
            canvas.blit(left, (panel.left + 38, y))
            canvas.blit(right, right.get_rect(midright=(panel.right - 38, y + 10)))
            y += 32

        hint = font.render("R: reintentar nivel    ESC: volver al menu", True, (255, 255, 255))
        canvas.blit(hint, hint.get_rect(center=(cx, panel.bottom - 35)))


def draw_scene(
    canvas, font, big_font, level, player, enemies,
    bullets, effects, floating, camera, elapsed=0.0, game_state=None
):
    """Dibuja el estado actual del nivel sin actualizarlo (para la pausa)."""

    canvas.fill((15, 15, 15))

    level.draw(canvas, camera)

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
            label.get_rect(
                center=(
                    round(pos.x - camera.x),
                    round(pos.y - camera.y)
                )
            )
        )

    draw_hud(canvas, font, big_font, level, player, enemies, elapsed, game_state)


def has_next_level(index):
    """True si existe el archivo del nivel siguiente (index = nivel actual)."""

    nxt = index + 1

    return nxt < len(settings.LEVELS) and settings.LEVELS[nxt].exists()


def play_level_music_safe(sounds, level_number):
    """Música del nivel; si no existe su archivo usa la del nivel 1."""

    try:
        sounds.play_level_music(level_number)

    except (pygame.error, OSError):
        sounds.play_level_music(1)


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
    pause_menu = PauseMenu()
    level_transition = LevelTransition()

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
    game_state = GameState()

    # Tiempo de partida
    level_start_time = 0
    level_elapsed = 0.0
    victory_elapsed = 0

    camera = pygame.Vector2()

    debug = False
    fullscreen = False

    # Evita disparar con el clic que se usó en el menú para entrar al nivel
    fire_lock = False

    # Pausa
    paused = False
    in_pause_settings = False
    pause_started = 0

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

            # Evitar que los clics/teclas usados para cambiar de nivel
            # también activen acciones dentro del nivel nuevo.
            if level_transition.active:
                continue

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
                        game_state.reset()
                        game_state.start_level(level_index + 1)

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

                        fire_lock = True

                        playing = True

                        menu.sounds.play_level_music(result + 1)
                        menu.sounds.play_horde()
                        level_elapsed = 0.0
                        level_transition.start(level_index + 1)

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
                        ),
                        has_next_level(level_index)
                    )

                    # Pasar al siguiente nivel
                    if result == "next":

                        level_index += 1
                        game_state.start_level(level_index + 1)

                        menu.sounds.stop_horde()
                        menu.sounds.stop_footsteps()

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

                        # El clic del botón no debe disparar
                        fire_lock = True

                        play_level_music_safe(menu.sounds, level_index + 1)
                        menu.sounds.play_horde()
                        level_elapsed = 0.0
                        level_transition.start(level_index + 1)

                    elif result == "menu":

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
                # MENU DE PAUSA
                # --------------------------------

                elif paused:

                    # Configuración dentro de la pausa
                    if in_pause_settings:

                        pause_event = event

                        if event.type in (
                            pygame.MOUSEMOTION,
                            pygame.MOUSEBUTTONDOWN
                        ):

                            pause_event = pygame.event.Event(
                                event.type,
                                {
                                    **event.dict,
                                    "pos": (
                                        int(
                                            event.pos[0]
                                            * settings.SCREEN_WIDTH
                                            / window_width
                                        ),
                                        int(
                                            event.pos[1]
                                            * settings.SCREEN_HEIGHT
                                            / window_height
                                        )
                                    )
                                }
                            )

                        if settings_menu.handle_event(pause_event) == "back":
                            in_pause_settings = False

                    else:

                        action = pause_menu.handle_event(
                            event,
                            screen.get_size(),
                            (
                                settings.SCREEN_WIDTH,
                                settings.SCREEN_HEIGHT
                            )
                        )

                        # Continuar
                        if action == "resume":

                            paused = False

                            # El tiempo en pausa no cuenta en la partida
                            level_start_time += (
                                pygame.time.get_ticks() - pause_started
                            )

                            # El clic de "Continuar" no debe disparar
                            fire_lock = True

                            pygame.mixer.unpause()
                            pygame.mixer.music.unpause()

                        # Reiniciar nivel
                        elif action == "restart":

                            pygame.mixer.unpause()
                            pygame.mixer.music.unpause()

                            menu.sounds.stop_footsteps()
                            menu.sounds.stop_horde()

                            game_state.start_level(level_index + 1)
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

                            fire_lock = True
                            paused = False
                            in_pause_settings = False

                            menu.sounds.play_level_music(level_index + 1)
                            menu.sounds.play_horde()
                            level_elapsed = 0.0
                            level_transition.start(level_index + 1)

                        # Configuración (volumen, etc.)
                        elif action == "settings":

                            in_pause_settings = True

                        # Volver al menú principal
                        elif action == "menu":

                            pygame.mixer.unpause()
                            pygame.mixer.music.unpause()

                            paused = False
                            in_pause_settings = False

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

                        # Salir del juego
                        elif action == "quit":

                            pygame.quit()
                            sys.exit()

                # --------------------------------
                # CONTROLES NORMALES DEL JUGADOR
                # --------------------------------

                else:

                    if event.type == pygame.KEYDOWN:

                        # ESC / P = pausa (en Game Over, ESC vuelve al menú)
                        if (
                            event.key in (pygame.K_ESCAPE, pygame.K_p)
                            and not player.dead_done
                        ):

                            paused = True
                            in_pause_settings = False
                            pause_started = pygame.time.get_ticks()

                            pause_menu.reset()

                            pygame.mixer.pause()
                            pygame.mixer.music.pause()

                        elif event.key == pygame.K_ESCAPE:

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

                        # E = accionar la palanca de la reja (nivel 4)
                        elif event.key == pygame.K_e and level.lever_pos is not None:
                            interact_lever(
                                level, player, enemies, floating, menu.sounds
                            )

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

                                game_state.start_level(level_index + 1)
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

                                fire_lock = True

                                camera = pygame.Vector2()

                                menu.sounds.play_horde()
                                level_elapsed = 0.0
                                level_transition.start(level_index + 1)

                            else:
                                player.play_action("reload")

                        elif event.key == pygame.K_F2:
                            debug = not debug

                        elif event.key == pygame.K_F3:
                            player.play_test_animation("dead")

                        elif event.key == pygame.K_F4:
                            player.play_test_animation("pickup")

                        # M = mostrar / ocultar el minimapa
                        elif event.key == pygame.K_m:
                            minimap.toggle()

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

        if playing and not victory and not paused and not level_transition.active:

            if player.alive:
                level_elapsed += dt
                game_state.update_time(dt)

            game_state.update_player(player)
            keys = pygame.key.get_pressed()

            # El jugador necesita saber quiénes lo atacan (escudo)
            player.threats = enemies

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

            # Mouse USB o touchpad: ambos llegan como botón izquierdo
            mouse_down = pygame.mouse.get_pressed()[0]

            # Hasta soltar el clic del menú no se dispara
            if fire_lock and not mouse_down:
                fire_lock = False

            if (
                (mouse_down and not fire_lock)
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
                floating,
                game_state
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
                game_state.register_enemy(enemy)
            game_state.update_enemies(enemies)

            # Reja del nivel 4: animacion de apertura y palanca habilitada
            if level.gate_rect is not None:
                level.lever_ready = street_cleared(enemies)
                level.update_gate(dt)

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

            # Una vida se descuenta cuando termina la animación de muerte.
            # Se conserva el mismo nivel: enemigos eliminados y suministros
            # recogidos permanecen tal como estaban.
            if player.dead_done and not player.death_processed:
                player.death_processed = True
                player.lives = max(0, player.lives - 1)
                lost_ammo = player.apply_death_penalty()
                game_state.objects_lost += lost_ammo
                game_state.register_death(player)

                if player.lives > 0:
                    player.respawn(level)
                    bullets.clear()
                    if lost_ammo:
                        floating.append([
                            f"PERDISTE {lost_ammo} MUNICIONES",
                            pygame.Vector2(player.pos.x, player.pos.y - 110),
                            0.0
                        ])
                    menu.sounds.play_horde()
                else:
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

                victory_elapsed = level_elapsed

                menu.sounds.stop_horde()
                menu.sounds.stop_footsteps()

                # Bajar la música del nivel para que se oiga el jingle
                pygame.mixer.music.fadeout(600)

                # Sonido de victoria (solo una vez, por el "not victory")
                menu.sounds.play_victory_sound()

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
                enemies,
                level_elapsed,
                game_state
            )

        # --------------------------------
        # ESCENA DURANTE LA TRANSICION
        # --------------------------------

        elif playing and level_transition.active and not victory:

            draw_scene(
                canvas, font, big_font, level, player, enemies,
                bullets, effects, floating, camera, level_elapsed,
                game_state
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
                enemies,
                level_elapsed,
                game_state
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
                scaled_mouse,
                has_next_level(level_index),
                game_state
            )

        # --------------------------------
        # PAUSA
        # --------------------------------

        elif playing and paused:

            draw_scene(
                canvas, font, big_font, level, player, enemies,
                bullets, effects, floating, camera, level_elapsed,
                game_state
            )

            pause_menu.draw(
                canvas,
                level,
                player,
                enemies,
                level_elapsed,
                game_state
            )

            if in_pause_settings:
                settings_menu.draw(canvas)

        # --------------------------------
        # MENU PRINCIPAL
        # --------------------------------

        else:

            menu.draw(canvas)

            if in_settings:
                settings_menu.draw(canvas)

        # --------------------------------
        # TRANSICION ENTRE NIVELES
        # --------------------------------

        if level_transition.active:
            level_transition.update(dt)
            level_transition.draw(canvas)

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