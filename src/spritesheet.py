import pygame


class SpriteSheet:
    def __init__(self, path, frame_size, cols, rows):
        self.image = pygame.image.load(str(path)).convert_alpha()
        self.fw, self.fh = frame_size
        self.cols, self.rows = cols, rows
        expected = (self.fw * cols, self.fh * rows)
        if self.image.get_size() != expected:
            raise ValueError(f"{path}: mide {self.image.get_size()}, se esperaba {expected}")

    def get_frame(self, col, row, scale=1.0):
        frame = self.image.subsurface(pygame.Rect(col * self.fw, row * self.fh, self.fw, self.fh)).copy()
        if scale != 1.0:
            frame = pygame.transform.smoothscale(
                frame, (round(self.fw * scale), round(self.fh * scale)))
        return frame

    def get_row(self, row, scale=1.0, count=None):
        count = self.cols if count is None else count
        return [self.get_frame(c, row, scale) for c in range(count)]

    def row_is_empty(self, row):
        """True si la fila no tiene ningún píxel visible (fila sin dibujar)."""
        rect = pygame.Rect(0, row * self.fh, self.fw * self.cols, self.fh)
        return pygame.mask.from_surface(self.image.subsurface(rect)).count() == 0

    def raw_frame(self, col, row):
        """Cuadro sin escalar (para analizar píxeles)."""
        return self.image.subsurface(
            pygame.Rect(col * self.fw, row * self.fh, self.fw, self.fh))
