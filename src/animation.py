import pygame


class Animation:
    def __init__(self, frames, fps, loop=True):
        self.frames = list(frames)
        self.flipped = [pygame.transform.flip(f, True, False) for f in self.frames]
        self.fps = fps
        self.loop = loop
        self.reset()

    def reset(self):
        self.index = 0
        self.timer = 0.0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.timer += dt
        step = 1.0 / self.fps
        while self.timer >= step:
            self.timer -= step
            if self.index < len(self.frames) - 1:
                self.index += 1
            elif self.loop:
                self.index = 0
            else:
                self.finished = True
                break

    def image(self, flipped=False):
        return (self.flipped if flipped else self.frames)[self.index]