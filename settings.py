# guardarás los valores generales que se utilizarán
# en diferentes archivos, para no repetirlos.
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Resolución interna del juego
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
# Pantalla
RESIZABLE = True
FPS = 60
TITLE = "Dead Zone"
# Recursos de soldado
SOLDIER_RIFLE_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "soldado_spritesheet.png"
SOLDIER_SHOTGUN_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "soldado_spritesheet_escopeta.png"
SOLDIER_DEAD_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "dead_player.png"
SOLDIER_PICKUP_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "recoger_suministro.png"
SOLDIER_AXE_SHEET =   BASE_DIR / "assets" / "sprites" / "soldier" / "ataque_hacha.png"
SOLDIER_SWITCH_AXE_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "cambiar_arma_hacha.png"

SOLDIER_WALK_AXE_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "caminar_hacha.png"
SOLDIER_WALK_AXE_COLS = 10
SOLDIER_WALK_AXE_ROWS = 1
SOLDIER_WALK_AXE_FRAME_SIZE = (320, 220)

MAPS_DIR = BASE_DIR / "maps"
LEVELS = [MAPS_DIR / f"mapa_{n}" / f"mapa_{n}.tmx" for n in range(1, 6)]

# Recursos del menú
MENU_BACKGROUND = BASE_DIR / "assets" / "images" / "backgrounds" / "menu_fondo.png"
MENU_MUSIC = BASE_DIR / "assets" / "sounds" / "music" / "pantalla_inicio.mp3"
MENU_SELECT_SOUND = BASE_DIR / "assets" / "sounds" / "ui" / "seleccionar_nivel.mp3"

# Musica para mapas
LEVEL_1_MUSIC = BASE_DIR / "assets" / "sounds" / "music" / "nivel_1.mp3"



# Sonidos del soldado
SOLDIER_SHIELD_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "coloca escudo.mp3"
)

SOLDIER_SHOTGUN_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "disparo_escopeta.mp3"
)

SOLDIER_RIFLE_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "disparo_rifle.mp3"
)

SOLDIER_RUN_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "pasos_correr.mp3"
)

SOLDIER_WALK_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "pasos.mp3"
)
SOLDIER_RELOAD_RIFLE_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "recarga_rifle.mp3"
)

SOLDIER_RELOAD_SHOTGUN_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "recarga_escopeta.mp3"
)
SOLDIER_PICKUP_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "recolectar.mp3"
)

SOLDIER_DEAD_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "game_over.mp3"
)

SOLDIER_AXE_HIT_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "golpe_hacha.mp3"
)
SOLDIER_VICTORY_SOUND = (
    BASE_DIR / "assets" / "sounds" / "soldier" / "victory.mp3"
)


# Hoja del soldado: 2400x1540 -> 10 columnas x 7 filas -> celdas de 240x220
SOLDIER_FRAME_SIZE = (240, 220)
SOLDIER_COLS = 10
SOLDIER_ROWS = 7
SOLDIER_PIVOT = (100, 205)      # los pies dentro de la celda
SOLDIER_SCALE = 0.55            # tiles de 32 px: 0.35 = soldado de ~2 tiles de alto

SOLDIER_DEAD_COLS = 10
SOLDIER_DEAD_ROWS = 1

SOLDIER_PICKUP_COLS = 10
SOLDIER_PICKUP_ROWS = 1

SOLDIER_AXE_COLS = 10
SOLDIER_AXE_ROWS = 1

SOLDIER_SWITCH_AXE_COLS = 10
SOLDIER_SWITCH_AXE_ROWS = 1
SOLDIER_SWITCH_AXE_FRAME_SIZE = (320, 220)   # ajústalo si tu PNG mide distinto


ROW_WALK = 0
ROW_RUN = 1
ROW_SHIELD = 2
ROW_FIRE = 3
ROW_RELOAD = 4
ROW_FIRE_UP = 5                 # disparo apuntando +45 grados
ROW_FIRE_DOWN = 6               # disparo apuntando -45 grados

# Cuadro de la fila de disparo usado como pose de apuntado en reposo
# (2 = arma levantada; 0 = arma baja)
IDLE_AIM_FRAME = 2

ANIMATION_FPS = {
    "idle": 1,
    "walk": 12,
    "run": 20,
    "shield": 12,
    "shoot": 15,
    "reload": 10,
    "dead": 10,
    "pickup": 12,
    "axe": 12,
    "switch_axe": 14,
    "walk_axe": 12,
}

# Fotograma en el que se reproduce el sonido del escudo
SHIELD_SOUND_FRAME = 7 
SHOOT_SOUND_FRAMES = [2, 7]
PICKUP_SOUND_FRAME = 5
DEAD_SOUND_FRAME = 0
AXE_SOUND_FRAME = 7

WALK_SPEED = 110                # píxeles por segundo
RUN_SPEED = 190
FOOT_SIZE = (18, 10)            # caja de colisión en los pies

# ==============================================================
# JUGADOR: VIDA Y ARMAS
# ==============================================================
PLAYER_MAX_HP = 100
PLAYER_INVULNERABLE_TIME = 0.6   # segundos sin recibir daño tras un golpe
SHIELD_DAMAGE_MULT = 0.25        # con el escudo activo recibe solo el 25 %

# --- Apuntado: se elige la fila de la hoja (recto / arriba / abajo) según el mouse
EFFECTS_SHEET = BASE_DIR / "assets" / "sprites" / "effects" / "efectos_spritesheet.png"

AIM_MAX_ANGLE = 45               # grados máximos hacia arriba/abajo (las poses llegan a +-45)
AIM_SMOOTH = 18                  # qué tan rápido gira (mayor = más rápido)
AIM_ENTER = 25                   # pasa a la fila arriba/abajo al superar este ángulo
AIM_LEAVE = 20                   # vuelve a la fila recta al bajar de este ángulo
TORSO_HIP = (100, 128)           # solo para calcular el ángulo hacia el mouse
# Punta del cañón (píxeles de la celda 240x220) en el cuadro del disparo,
# por arma y fila: "" = recto, "_up" = arriba, "_down" = abajo
GUN_TIP = {
    "rifle":   {"": (184.5, 86.7), "_up": (154.4, 30.7), "_down": (168.5, 146.3)},
    "shotgun": {"": (176.3, 71.3), "_up": (143.3, 27.5), "_down": (172.7, 131.0)},
}
# Cuadros de la animación de disparo donde sale la bala (coinciden con el
# fogonazo dibujado en la hoja)
FIRE_FRAMES = {"rifle": [3, 5, 7], "shotgun": [3, 7]}

# Rifle: una bala por disparo (la animación dispara 2 veces)
RIFLE_DAMAGE = 10
RIFLE_BULLET_SPEED = 1000        # px por segundo
RIFLE_RANGE = 750
RIFLE_SPREAD = 1.5               # grados de dispersión

# Escopeta: varios perdigones, mucho daño pero poco alcance
SHOTGUN_PELLETS = 5
SHOTGUN_DAMAGE = 7
SHOTGUN_BULLET_SPEED = 900
SHOTGUN_RANGE = 380
SHOTGUN_SPREAD = 9               # grados

# ==============================================================
# ENEMIGOS
# ==============================================================
ENEMIES_DIR = BASE_DIR / "assets" / "sprites" / "enemies"
ZOMBIE_SOUNDS_DIR = BASE_DIR / "assets" / "sounds" / "zombies"

ENEMY_FRAME_SIZE = (288, 288)
ENEMY_COLS = 8

# rows: fila de cada animación en la hoja y cuántos cuadros usa
#   (fila, cuadros).  attack = None -> el enemigo hace daño por contacto
# scale: tamaño del sprite (el soldado mide ~95 px de alto)
# pivot: pies dentro de la celda de 288x288
# foot: caja de colisión con el escenario   hit: caja donde reciben balas
ENEMY_TYPES = {
    "perro_infectado": {
        "sheet": ENEMIES_DIR / "enemigo_perro_infectado.png", "rows": 5,
        "anim": {"idle": (0, 8), "walk": (1, 8), "attack": (2, 8),
                 "hurt": (3, 4), "dead": (4, 8)},
        "fps": {"idle": 8, "walk": 16, "attack": 14, "hurt": 14, "dead": 10},
        "scale": 0.62, "pivot": (105, 276),
        "foot": (26, 10), "hit": (52, 46),
        "speed": 210, "hp": 40, "damage": 8,
        "attack_range": 40, "attack_cooldown": 0.7, "attack_hit_frame": 4,
        "detect": 520,
    },
    "zombie_corredor": {
        "sheet": ENEMIES_DIR / "enemigo_zombie_corredor.png", "rows": 5,
        "anim": {"idle": (0, 8), "walk": (1, 8), "attack": (2, 8),
                 "hurt": (3, 4), "dead": (4, 8)},
        "fps": {"idle": 8, "walk": 14, "attack": 12, "hurt": 14, "dead": 10},
        "scale": 0.62, "pivot": (155, 273),
        "foot": (18, 10), "hit": (30, 82),
        "speed": 150, "hp": 50, "damage": 10,
        "attack_range": 38, "attack_cooldown": 0.9, "attack_hit_frame": 4,
        "detect": 480,
    },
    "zombie_normal": {
        "sheet": ENEMIES_DIR / "enemigo_zombie_normal.png", "rows": 5,
        "anim": {"idle": (0, 8), "walk": (1, 8), "attack": (2, 8),
                 "hurt": (3, 4), "dead": (4, 8)},
        "fps": {"idle": 8, "walk": 8, "attack": 10, "hurt": 14, "dead": 10},
        "scale": 0.62, "pivot": (150, 272),
        "foot": (18, 10), "hit": (30, 80),
        "speed": 70, "hp": 70, "damage": 12,
        "attack_range": 36, "attack_cooldown": 1.1, "attack_hit_frame": 4,
        "detect": 380,
    },
    "zombie_tanque": {
        "sheet": ENEMIES_DIR / "enemigo_zombie_tanque.png", "rows": 4,
        "anim": {"idle": (0, 8), "walk": (1, 8), "attack": None,
                 "hurt": (2, 4), "dead": (3, 8)},
        "fps": {"idle": 8, "walk": 6, "attack": 6, "hurt": 12, "dead": 8},
        "scale": 0.75, "pivot": (150, 272),
        "foot": (34, 14), "hit": (72, 110),
        "speed": 45, "hp": 300, "damage": 25,
        "attack_range": 58, "attack_cooldown": 1.4, "attack_hit_frame": 0,
        "detect": 350, "knockback": 0.25,
    },
}

# Tipo de enemigo por cada punto "zombie" del mapa (en el orden en que
# aparecen en Tiled).  Si hay menos tipos que puntos se repite el último.
LEVEL_ENEMY_TYPES = {
    1: ["zombie_normal", "zombie_normal", "zombie_normal", "zombie_normal",
        "zombie_corredor", "zombie_normal", "zombie_normal", "perro_infectado",
        "zombie_tanque", "zombie_normal", "zombie_corredor", "zombie_normal"],
}


# ==============================================================
# ARMAS, MUNICIÓN Y SUMINISTROS
# ==============================================================
# Armas con las que empieza cada nivel.  "axe" = hacha (cuerpo a cuerpo).
# La escopeta se desbloquea al recoger el objeto "escopeta" del mapa.
LEVEL_WEAPONS = {
    1: ("rifle", "axe"),
    2: ("rifle", "axe"),
    3: ("rifle", "axe"),
    4: ("rifle", "axe"),
    5: ("rifle", "axe"),
}

# Munición por arma de fuego:
#   mag_size: balas que caben en el cargador   mag: balas cargadas al empezar
#   reserve: balas de reserva al empezar       max_reserve: tope de reserva
#   pickup: balas que da una caja de munición
AMMO = {
    "rifle":   {"mag_size": 30, "mag": 30, "reserve": 60,
                "max_reserve": 150, "pickup": 30},
    "shotgun": {"mag_size": 6,  "mag": 0,  "reserve": 0,
                "max_reserve": 36,  "pickup": 6},
}

MEDKIT_HEAL = 25                 # vida que cura un botiquín
PICKUP_RADIUS = 34               # distancia a la que se recoge un suministro
PICKUP_ANIMATION = True          # reproducir la animación de recoger
PICKUP_RING = True               # aro que late sobre lo que SÍ se puede recoger

# Objetos de la capa "puntos" que se pueden recoger en cada nivel.
# Cualquier otro objeto del mapa (gasolina, escudo...) es solo adorno.
LEVEL_COLLECTIBLES = {
    1: ("municion", "botiquin"),
    2: ("municion", "botiquin", "escopeta"),
    3: ("municion", "botiquin", "escopeta"),
    4: ("municion", "botiquin", "escopeta"),
    5: ("municion", "botiquin", "escopeta"),
}

# Hacha: golpea en el cuadro AXE_HIT_FRAME de su animación
AXE_DAMAGE = 35
AXE_REACH = 70                   # alcance frente al soldado (px)
AXE_DEPTH = 34                   # tolerancia arriba/abajo (px)
AXE_HIT_FRAME = AXE_SOUND_FRAME - 1
AXE_KNOCKBACK = 22               # empujón al enemigo (px)
