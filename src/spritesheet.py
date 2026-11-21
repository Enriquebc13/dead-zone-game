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

    def get_row(self, row, scale=1.0):
        return [self.get_frame(c, row, scale) for c in range(self.cols)]