class GameState:
    """Concentra las estadísticas y el progreso de una partida completa."""

    ENEMY_POINTS = {
        "perro_infectado": 150,
        "zombie_corredor": 120,
        "zombie_normal": 100,
        "zombie_tanque": 250,
        "zombie_tanque_boss": 1000,
    }

    PICKUP_POINTS = {
        "botiquin": 25,
        "municion": 10,
        "municion_rifle": 10,
        "municion_escopeta": 10,
        "escopeta": 50,
    }

    def __init__(self):
        self.reset()

    def reset(self):
        self.lives = 3
        self.deaths = 0
        self.enemies_killed = 0
        self.enemies_remaining = 0
        self.score = 0
        self.elapsed_time = 0.0
        self.current_level = 1
        self.pickups_collected = 0
        self.objects_lost = 0
        self._counted_enemies = set()

    def start_level(self, level_number):
        self.current_level = level_number
        self._counted_enemies.clear()

    def update_player(self, player):
        self.lives = player.lives

    def update_enemies(self, enemies):
        self.enemies_remaining = sum(1 for enemy in enemies if enemy.alive)

    def update_time(self, dt, running=True):
        if running:
            self.elapsed_time += max(0.0, dt)

    def register_enemy(self, enemy):
        key = id(enemy)
        if not enemy.alive and key not in self._counted_enemies:
            self._counted_enemies.add(key)
            self.enemies_killed += 1
            self.enemies_remaining = max(0, self.enemies_remaining - 1)
            self.score += self.ENEMY_POINTS.get(enemy.kind, 100)
            return True
        return False

    def register_pickup(self, kind):
        self.pickups_collected += 1
        self.score += self.PICKUP_POINTS.get(kind, 10)

    def register_death(self, player):
        self.deaths += 1
        self.lives = player.lives
