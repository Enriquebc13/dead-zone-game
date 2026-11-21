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

SOLDIER_RIFLE_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "soldado_spritesheet.png"
SOLDIER_SHOTGUN_SHEET = BASE_DIR / "assets" / "sprites" / "soldier" / "soldado_spritesheet_escopeta.png"

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
# Hoja del soldado: 2400x880 -> 10 columnas x 4 filas -> celdas de 240x220
SOLDIER_FRAME_SIZE = (240, 220)
SOLDIER_COLS = 10
SOLDIER_ROWS = 5
SOLDIER_PIVOT = (100, 205)      # los pies dentro de la celda
SOLDIER_SCALE = 0.55            # tiles de 32 px: 0.35 = soldado de ~2 tiles de alto

ROW_WALK = 0
ROW_RUN = 1
ROW_SHIELD = 2
ROW_FIRE = 3
ROW_RELOAD = 4

ANIMATION_FPS = {
    "idle": 1,
    "walk": 12,
    "run": 20,
    "shield": 12,
    "shoot": 15,
    "reload": 10
}

WALK_SPEED = 110                # píxeles por segundo
RUN_SPEED = 190
FOOT_SIZE = (18, 10)            # caja de colisión en los pies