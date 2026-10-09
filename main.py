from __future__ import annotations
import argparse
import math
import random
from array import array
from dataclasses import dataclass
import pygame

# ============================================================
# EIDOLON // PROJECT 015
# ANT COLONY — SWARM INTELLIGENCE
# ============================================================

WIDTH, HEIGHT = (1280, 800)
FPS = 60
HUD_H = 84
FOOTER_H = 34
WORLD_BOTTOM = HEIGHT - FOOTER_H
CELL = 8
GRID_W = WIDTH // CELL
GRID_H = (WORLD_BOTTOM - HUD_H) // CELL

# Performance settings
INITIAL_ANTS = 180
MAX_ANTS = 500

ANT_SPEED = 74.0
SENSOR_DISTANCE = 23.0
SENSOR_ANGLE = 0.6
RANDOM_TURN = 0.36
TURN_RATE = 3.6

PHEROMONE_DEPOSIT = 0.72
PHEROMONE_DECAY = 0.993
PHEROMONE_DIFFUSION = 0.035
PHEROMONE_MAX = 22.0

NEST_RADIUS = 27
FOOD_RADIUS = 16
OBSTACLE_RADIUS = 19

PALETTES = [
    {
        'name': 'EIDOLON',
        'bg': (6, 8, 16),
        'panel': (11, 16, 29),
        'panel2': (15, 23, 38),
        'grid': (20, 29, 44),
        'accent': (90, 244, 207),
        'accent2': (60, 150, 255),
        'ant': (222, 250, 243),
        'trail': (37, 224, 173),
        'food': (255, 186, 83),
        'nest': (84, 166, 255),
        'obstacle': (102, 120, 145),
        'text': (222, 232, 245),
        'muted': (109, 130, 153)
    },
    {
        'name': 'EMBER',
        'bg': (17, 7, 8),
        'panel': (29, 12, 14),
        'panel2': (42, 18, 18),
        'grid': (49, 24, 24),
        'accent': (255, 124, 74),
        'accent2': (255, 62, 67),
        'ant': (255, 225, 205),
        'trail': (255, 82, 46),
        'food': (255, 218, 93),
        'nest': (255, 104, 73),
        'obstacle': (131, 82, 78),
        'text': (255, 231, 220),
        'muted': (166, 117, 111)
    },
    {
        'name': 'MATRIX',
        'bg': (3, 11, 7),
        'panel': (6, 20, 12),
        'panel2': (9, 29, 17),
        'grid': (15, 42, 23),
        'accent': (95, 255, 132),
        'accent2': (36, 205, 100),
        'ant': (208, 255, 213),
        'trail': (40, 235, 88),
        'food': (224, 255, 93),
        'nest': (89, 255, 137),
        'obstacle': (67, 115, 76),
        'text': (221, 255, 224),
        'muted': (104, 158, 113)
    },
    {
        'name': 'OCEAN',
        'bg': (4, 9, 20),
        'panel': (8, 17, 33),
        'panel2': (12, 26, 47),
        'grid': (17, 36, 59),
        'accent': (86, 194, 255),
        'accent2': (110, 116, 255),
        'ant': (218, 242, 255),
        'trail': (47, 159, 255),
        'food': (255, 200, 115),
        'nest': (73, 207, 255),
        'obstacle': (75, 109, 141),
        'text': (222, 239, 255),
        'muted': (109, 139, 174)
    }
]


def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, amount):
    return a + (b - a) * amount


def mix_color(a, b, amount):
    return tuple(int(lerp(a[i], b[i], amount)) for i in range(3))


def dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def angle_delta(target, current):
    return (target - current + math.pi) % math.tau - math.pi


def grid_cell(x, y):
    gx = int(clamp(x // CELL, 0, GRID_W - 1))
    gy = int(clamp((y - HUD_H) // CELL, 0, GRID_H - 1))
    return (gx, gy)


# ============================================================
# FIX 1: SOFT GLOW WITHOUT GIANT SOLID DISKS
# ============================================================

def glow_circle(surface, color, pos, radius, strength=1.0):
    """Draw a soft glow without filling a large solid disk."""
    x, y = (int(pos[0]), int(pos[1]))
    radius = max(1, int(radius))
    extent = radius * 3

    layer = pygame.Surface(
        (extent * 2 + 2, extent * 2 + 2),
        pygame.SRCALPHA
    )
    center = (extent + 1, extent + 1)

    for scale, alpha in ((3.0, 7), (2.2, 10), (1.5, 15)):
        r = max(radius + 1, int(radius * scale))
        pygame.draw.circle(
            layer,
            (*color, int(alpha * strength)),
            center,
            r
        )

    surface.blit(layer, (x - extent - 1, y - extent - 1))

    # Only the intended small center is solid.
    pygame.draw.circle(surface, color, (x, y), radius)


def draw_text(surface, text, font, color, pos, anchor='topleft'):
    image = font.render(str(text), True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


def draw_panel(surface, rect, fill, border, radius=12, width=1):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(
        surface, border, rect, width, border_radius=radius
    )


# ============================================================
# AUDIO
# ============================================================

class Audio:
    def __init__(self):
        self.enabled = True
        self.ready = False
        self.last_food = 0
        self.last_delivery = 0

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(
                    frequency=22050,
                    size=-16,
                    channels=1,
                    buffer=512
                )
            self.ready = True
        except pygame.error:
            pass

    def tone(self, frequency, duration=0.07, volume=0.08, sweep=0):
        if not self.enabled or not self.ready:
            return

        rate = 22050
        count = max(1, int(rate * duration))
        samples = array('h')

        for i in range(count):
            progress = i / max(1, count - 1)
            t = i / rate
            freq = max(35, frequency + sweep * progress)
            envelope = (1 - progress) ** 2
            sample = math.sin(math.tau * freq * t) * envelope
            samples.append(int(32767 * volume * sample))

        try:
            pygame.mixer.Sound(buffer=samples.tobytes()).play()
        except pygame.error:
            pass

    def tick(self):
        self.tone(540, 0.045, 0.07, 100)

    def go(self):
        self.tone(560, 0.19, 0.12, 440)

    def food(self):
        now = pygame.time.get_ticks()
        if now - self.last_food < 130:
            return
        self.last_food = now
        self.tone(760, 0.045, 0.045, 180)

    def delivery(self):
        now = pygame.time.get_ticks()
        if now - self.last_delivery < 140:
            return
        self.last_delivery = now
        self.tone(390, 0.10, 0.065, 260)

    def toggle(self):
        self.enabled = not self.enabled
        if self.enabled:
            self.tick()


# ============================================================
# ENTITIES
# ============================================================

@dataclass
class Food:
    x: float
    y: float
    amount: float = 1000.0
    radius: int = FOOD_RADIUS
    phase: float = 0.0

    @property
    def active(self):
        return self.amount > 0


@dataclass
class Obstacle:
    x: float
    y: float
    radius: int = OBSTACLE_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: tuple

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.985
        self.vy *= 0.985
        self.life -= dt

    def draw(self, surface):
        if self.life <= 0:
            return

        alpha = clamp(self.life / self.max_life, 0, 1)
        radius = max(1, int(self.size * alpha))

        pygame.draw.circle(
            surface,
            mix_color((0, 0, 0), self.color, alpha),
            (int(self.x), int(self.y)),
            radius
        )


# ============================================================
# PARTICLE SYSTEM
# ============================================================

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, count=12, force=100):
        for _ in range(count):
            angle = random.random() * math.tau
            speed = random.uniform(force * 0.25, force)
            life = random.uniform(0.25, 0.85)

            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    max_life=life,
                    size=random.uniform(1.2, 3.3),
                    color=color
                )
            )

    def ambient(self, color):
        if len(self.particles) > 110:
            return

        if random.random() < 0.14:
            life = random.uniform(2.0, 4.0)
            self.particles.append(
                Particle(
                    x=random.uniform(0, WIDTH),
                    y=random.uniform(HUD_H + 10, WORLD_BOTTOM),
                    vx=random.uniform(-3, 3),
                    vy=random.uniform(-7, -1),
                    life=life,
                    max_life=life,
                    size=random.uniform(0.7, 1.8),
                    color=color
                )
            )

    def update(self, dt):
        for particle in self.particles:
            particle.update(dt)

        self.particles = [
            p for p in self.particles if p.life > 0
        ]

    def draw(self, surface):
        for particle in self.particles:
            particle.draw(surface)


# ============================================================
# FIX 2: PHEROMONE DIFFUSION FROM AN UNCHANGED SNAPSHOT
# ============================================================

class PheromoneField:
    def __init__(self):
        self.values = [
            [0.0] * GRID_W for _ in range(GRID_H)
        ]
        self.frame = 0
        self.dirty = True
        self.cached_surface = None

    def clear(self):
        for row in self.values:
            for x in range(GRID_W):
                row[x] = 0.0

        self.dirty = True

    def deposit(self, x, y, amount):
        gx, gy = grid_cell(x, y)
        self.values[gy][gx] = min(
            PHEROMONE_MAX,
            self.values[gy][gx] + amount
        )
        self.dirty = True

    def sample(self, x, y):
        gx, gy = grid_cell(x, y)
        return self.values[gy][gx]

    def update(self):
        self.frame += 1
        diffuse = self.frame % 6 == 0

        # Never modify the source while reading neighboring cells.
        old = [row[:] for row in self.values]
        new = [[0.0] * GRID_W for _ in range(GRID_H)]

        for y in range(GRID_H):
            for x in range(GRID_W):
                value = old[y][x] * PHEROMONE_DECAY

                if diffuse:
                    total = 0.0
                    count = 0

                    for nx, ny in (
                        (x - 1, y),
                        (x + 1, y),
                        (x, y - 1),
                        (x, y + 1)
                    ):
                        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                            total += old[ny][nx]
                            count += 1

                    if count:
                        average = total / count
                        value = lerp(
                            value,
                            average,
                            PHEROMONE_DIFFUSION
                        )

                new[y][x] = clamp(value, 0, PHEROMONE_MAX)

        self.values = new
        self.dirty = True

    def render(self, palette):
        if not self.dirty and self.cached_surface is not None:
            return self.cached_surface

        surface = pygame.Surface(
            (WIDTH, WORLD_BOTTOM - HUD_H),
            pygame.SRCALPHA
        )
        color = palette['trail']

        for gy, row in enumerate(self.values):
            py = gy * CELL

            for gx, value in enumerate(row):
                if value < 0.16:
                    continue

                strength = clamp(value / 7.0, 0, 1)
                alpha = int(8 + strength * 100)

                pygame.draw.rect(
                    surface,
                    (*color, alpha),
                    (gx * CELL, py, CELL + 1, CELL + 1)
                )

        self.cached_surface = surface
        self.dirty = False
        return surface

    def draw(self, surface, palette):
        surface.blit(self.render(palette), (0, HUD_H))


# ============================================================
# ANT AI
# ============================================================

class Ant:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = random.uniform(-math.pi, math.pi)
        self.carrying = False
        self.age = 0.0

        # FIX 3: Track how long the ant searches without finding food.
        self.time_without_food = 0.0

        self.walk_phase = random.uniform(0, math.tau)
        self.wander = random.uniform(0.8, 1.2)

    def sensor(self, field, angle):
        x = self.x + math.cos(angle) * SENSOR_DISTANCE
        y = self.y + math.sin(angle) * SENSOR_DISTANCE
        return field.sample(x, y)

    def steer(self, field):
        forward = self.sensor(field, self.angle)
        left = self.sensor(field, self.angle - SENSOR_ANGLE)
        right = self.sensor(field, self.angle + SENSOR_ANGLE)

        if left > forward and left > right:
            self.angle -= TURN_RATE / FPS * 2
        elif right > forward and right > left:
            self.angle += TURN_RATE / FPS * 2
        else:
            self.angle += (
                random.uniform(-RANDOM_TURN, RANDOM_TURN) * self.wander
            )

    def avoid_obstacles(self, obstacles):
        for obstacle in obstacles:
            dx = self.x - obstacle.x
            dy = self.y - obstacle.y
            d = math.hypot(dx, dy)
            minimum = obstacle.radius + 9

            if 0.001 < d < minimum:
                away = math.atan2(dy, dx)
                self.angle += angle_delta(away, self.angle) * 0.7
                self.angle += random.uniform(-0.35, 0.35)
                return

    def update(self, dt, colony, audio, particles):
        self.age += dt
        self.walk_phase += dt * 16

        if self.carrying:
            target = math.atan2(
                colony.nest_y - self.y,
                colony.nest_x - self.x
            )
            self.angle += angle_delta(target, self.angle) * min(1, 5 * dt)

            colony.field.deposit(
                self.x, self.y, PHEROMONE_DEPOSIT * 1.25
            )

            if dist(
                self.x, self.y,
                colony.nest_x, colony.nest_y
            ) < NEST_RADIUS:
                self.carrying = False
                colony.delivered += 1

                particles.burst(
                    colony.nest_x,
                    colony.nest_y,
                    colony.palette['nest'],
                    count=5,
                    force=55
                )
                audio.delivery()

        else:
            self.time_without_food += dt
            self.steer(colony.field)

            # Break out of repetitive paths after seven seconds.
            if self.time_without_food > 7.0:
                self.angle += random.uniform(-1.2, 1.2)
                self.time_without_food = 0.0

            for food in colony.foods:
                if food.active and dist(
                    self.x, self.y, food.x, food.y
                ) < food.radius + 5:
                    food.amount = max(0, food.amount - 1)
                    self.carrying = True

                    # Reset the search timer when food is found.
                    self.time_without_food = 0.0

                    self.angle = math.atan2(
                        colony.nest_y - self.y,
                        colony.nest_x - self.x
                    )

                    particles.burst(
                        food.x,
                        food.y,
                        colony.palette['food'],
                        count=5,
                        force=45
                    )
                    audio.food()
                    break

        self.avoid_obstacles(colony.obstacles)

        speed = ANT_SPEED * (0.84 if self.carrying else 1.0)
        self.x += math.cos(self.angle) * speed * dt
        self.y += math.sin(self.angle) * speed * dt

        left, right = (12, WIDTH - 12)
        top, bottom = (HUD_H + 12, WORLD_BOTTOM - 12)

        if self.x < left or self.x > right:
            self.angle = math.pi - self.angle
            self.x = clamp(self.x, left, right)

        if self.y < top or self.y > bottom:
            self.angle = -self.angle
            self.y = clamp(self.y, top, bottom)

    def draw(self, surface, palette, time):
        x, y = (int(self.x), int(self.y))
        carrying = self.carrying
        color = palette['food'] if carrying else palette['ant']

        pulse = 0.7 + 0.3 * math.sin(self.walk_phase + time)

        if carrying:
            pygame.draw.circle(
                surface, (*palette['food'], 35), (x, y), 6
            )
            pygame.draw.circle(
                surface, palette['food'], (x, y), 2
            )

        dx, dy = (math.cos(self.angle), math.sin(self.angle))
        length = 5.0 + pulse
        head = (int(x + dx * length), int(y + dy * length))
        tail = (int(x - dx * 3), int(y - dy * 3))

        pygame.draw.line(surface, color, tail, head, 2)
        pygame.draw.circle(surface, color, (x, y), 2)

        side = 1.8 * math.sin(self.walk_phase)

        for sign in (-1, 1):
            ax = x + dx * 3 - dy * sign * 2
            ay = y + dy * 3 + dx * sign * 2
            bx = ax + dx * 3 - dy * (sign * 2 + side)
            by = ay + dy * 3 + dx * (sign * 2 + side)

            pygame.draw.line(
                surface,
                palette['muted'],
                (int(ax), int(ay)),
                (int(bx), int(by)),
                1
            )


# ============================================================
# COLONY
# ============================================================

class Colony:
    def __init__(self):
        self.palette_index = 0
        self.nest_x = WIDTH * 0.5
        self.nest_y = (HEIGHT + HUD_H) * 0.5

        self.ants = []
        self.foods = []
        self.obstacles = []
        self.field = PheromoneField()
        self.particles = ParticleSystem()

        self.delivered = 0
        self.elapsed = 0.0
        self.speed = 1.0
        self.paused = False

        self.show_trails = True
        self.show_vectors = False
        self.show_grid = True
        self.show_hud = True

        self.food_mode = True
        self.obstacle_mode = False

        self.reset()

    @property
    def palette(self):
        return PALETTES[self.palette_index]

    def reset(self):
        self.ants.clear()
        self.foods.clear()
        self.obstacles.clear()
        self.field.clear()
        self.particles = ParticleSystem()

        self.delivered = 0
        self.elapsed = 0
        self.paused = False

        self.nest_x = WIDTH * 0.5
        self.nest_y = (HEIGHT + HUD_H) * 0.5

        for _ in range(INITIAL_ANTS):
            self.add_ant()

        self.add_food(self.nest_x - 300, self.nest_y - 155, 1200)
        self.add_food(self.nest_x + 300, self.nest_y - 135, 1200)
        self.add_food(self.nest_x - 265, self.nest_y + 195, 1200)
        self.add_food(self.nest_x + 290, self.nest_y + 190, 1200)

    def add_ant(self):
        if len(self.ants) >= MAX_ANTS:
            return

        angle = random.random() * math.tau
        radius = random.random() * NEST_RADIUS

        self.ants.append(
            Ant(
                self.nest_x + math.cos(angle) * radius,
                self.nest_y + math.sin(angle) * radius
            )
        )

    def remove_ants(self, amount=10):
        del self.ants[max(0, len(self.ants) - amount):]

    def add_food(self, x, y, amount=900):
        x = clamp(x, 30, WIDTH - 30)
        y = clamp(y, HUD_H + 30, WORLD_BOTTOM - 30)
        self.foods.append(Food(x, y, float(amount)))

    def add_obstacle(self, x, y):
        if len(self.obstacles) < 100:
            self.obstacles.append(Obstacle(x, y))

    def update(self, dt, audio):
        if self.paused:
            return

        scaled_dt = dt * self.speed
        self.elapsed += scaled_dt
        self.particles.ambient(self.palette['accent'])

        steps = max(1, min(5, math.ceil(self.speed)))
        sub_dt = scaled_dt / steps

        for _ in range(steps):
            for ant in self.ants:
                ant.update(sub_dt, self, audio, self.particles)
            self.field.update()

        for food in self.foods:
            food.phase += dt * 2.0

        self.foods = [food for food in self.foods if food.active]
        self.particles.update(scaled_dt)

    def draw_background(self, surface, time):
        palette = self.palette
        surface.fill(palette['bg'])

        for i in range(4):
            x = WIDTH * (0.15 + i * 0.24) + math.sin(time * 0.18 + i) * 50
            y = (HEIGHT + HUD_H) * 0.5 + math.cos(time * 0.22 + i * 1.7) * 180
            radius = 140 + int(15 * math.sin(time * 0.5 + i))

            glow_circle(
                surface,
                palette['accent2'] if i % 2 else palette['accent'],
                (x, y),
                radius,
                strength=0.06
            )

        if self.show_grid:
            grid_color = palette['grid']
            offset = int(time * 4 % 32)

            for x in range(0, WIDTH, 32):
                pygame.draw.line(
                    surface, grid_color,
                    (x, HUD_H), (x, WORLD_BOTTOM), 1
                )

            for y in range(HUD_H + offset, WORLD_BOTTOM, 32):
                pygame.draw.line(
                    surface, grid_color,
                    (0, y), (WIDTH, y), 1
                )

    def draw_nest(self, surface, time):
        p = self.palette
        x, y = (int(self.nest_x), int(self.nest_y))
        pulse = (math.sin(time * 2.6) + 1) * 0.5

        glow_circle(
            surface, p['nest'], (x, y),
            int(8 + pulse * 4), strength=0.85
        )

        for i in range(3):
            phase = (time * 0.48 + i / 3) % 1.0
            radius = int(NEST_RADIUS + phase * 28)
            alpha = int(125 * (1 - phase))

            ring = pygame.Surface(
                (radius * 2 + 4, radius * 2 + 4),
                pygame.SRCALPHA
            )

            pygame.draw.circle(
                ring,
                (*p['nest'], alpha),
                (radius + 2, radius + 2),
                radius,
                1
            )
            surface.blit(ring, (x - radius - 2, y - radius - 2))

        pygame.draw.circle(surface, p['nest'], (x, y), NEST_RADIUS, 1)
        pygame.draw.circle(surface, p['panel'], (x, y), 12)
        pygame.draw.circle(surface, p['accent'], (x, y), 4)

        draw_text(
            surface, 'NEST',
            pygame.font.SysFont('consolas', 11, bold=True),
            p['nest'], (x, y + 40), anchor='midtop'
        )

    def draw_food(self, surface, time, font):
        p = self.palette

        for food in self.foods:
            if not food.active:
                continue

            x, y = (int(food.x), int(food.y))
            pulse = (math.sin(food.phase + time * 2) + 1) * 0.5
            radius = int(food.radius + pulse * 2)

            glow_circle(
                surface, p['food'], (x, y),
                max(3, radius // 3), strength=0.55
            )

            pygame.draw.circle(surface, p['food'], (x, y), radius, 1)
            pygame.draw.circle(surface, p['food'], (x, y), 3)

            for i in range(3):
                angle = time * 0.7 + i * math.tau / 3
                sx = x + math.cos(angle) * (radius + 5)
                sy = y + math.sin(angle) * (radius + 5)

                pygame.draw.circle(
                    surface, p['food'], (int(sx), int(sy)), 1
                )

            remaining = clamp(food.amount / 1200, 0, 1)
            bar_w = 42
            bar_rect = pygame.Rect(
                x - bar_w // 2, y + radius + 7, bar_w, 3
            )

            pygame.draw.rect(
                surface, p['panel2'], bar_rect, border_radius=2
            )

            if remaining > 0:
                fill_rect = pygame.Rect(
                    bar_rect.x,
                    bar_rect.y,
                    int(bar_w * remaining),
                    bar_rect.height
                )
                pygame.draw.rect(
                    surface, p['food'], fill_rect, border_radius=2
                )

            draw_text(
                surface, str(int(food.amount)), font, p['muted'],
                (x, y + radius + 14), anchor='midtop'
            )

    def draw_obstacles(self, surface, time):
        p = self.palette

        for obstacle in self.obstacles:
            x, y = (int(obstacle.x), int(obstacle.y))
            r = obstacle.radius

            pygame.draw.circle(surface, p['panel2'], (x, y), r)
            pygame.draw.circle(surface, p['obstacle'], (x, y), r, 2)
            pygame.draw.circle(surface, p['grid'], (x, y), r - 5, 1)

            angle = time * 0.25
            x1 = x + math.cos(angle) * (r - 7)
            y1 = y + math.sin(angle) * (r - 7)
            x2 = x - math.cos(angle) * (r - 7)
            y2 = y - math.sin(angle) * (r - 7)

            pygame.draw.line(
                surface, p['obstacle'],
                (int(x1), int(y1)), (int(x2), int(y2)), 1
            )

    def draw_hud(self, surface, font, small, fps):
        p = self.palette

        pygame.draw.rect(surface, p['panel'], (0, 0, WIDTH, HUD_H))
        pygame.draw.line(
            surface, p['accent'],
            (0, HUD_H - 1), (WIDTH, HUD_H - 1), 1
        )

        pygame.draw.rect(
            surface, p['accent'], (19, 19, 3, 42), border_radius=2
        )

        draw_text(surface, 'EIDOLON', font, p['text'], (32, 16))
        draw_text(
            surface, 'PROJECT 015  /  ANT COLONY',
            small, p['accent'], (33, 48)
        )

        status_color = p['food'] if self.paused else p['accent']

        glow_circle(
            surface, status_color, (260, 29), 3, strength=0.8
        )

        draw_text(
            surface,
            'PAUSED' if self.paused else 'SIMULATION LIVE',
            small, status_color, (272, 22)
        )

        stats = [
            ('ANTS', len(self.ants), p['text']),
            ('DELIVERED', self.delivered, p['food']),
            ('FOOD SOURCES', len(self.foods), p['accent2']),
            ('SIM SPEED', f'{self.speed:.2f}x', p['accent'])
        ]

        x = 440

        for label, value, value_color in stats:
            card = pygame.Rect(x, 15, 156, 53)
            draw_panel(surface, card, p['panel2'], p['grid'], radius=8)

            draw_text(
                surface, label, small, p['muted'], (x + 11, 22)
            )
            draw_text(
                surface, value, font, value_color, (x + 11, 39)
            )
            x += 170

        draw_text(
            surface, f'{fps:.0f} FPS', small, p['muted'],
            (WIDTH - 130, 17)
        )
        draw_text(
            surface, self.palette['name'], small, p['accent'],
            (WIDTH - 130, 43)
        )

    def draw_footer(self, surface, small):
        p = self.palette

        pygame.draw.rect(
            surface, p['panel'], (0, WORLD_BOTTOM, WIDTH, FOOTER_H)
        )
        pygame.draw.line(
            surface, p['grid'],
            (0, WORLD_BOTTOM), (WIDTH, WORLD_BOTTOM)
        )

        help_text = (
            'SPACE Pause   Q/A Ants   F Trails   C Palette   '
            'O Obstacles   W Food   M Audio   R Reset   ESC Quit'
        )

        draw_text(
            surface, help_text, small, p['muted'],
            (WIDTH // 2, WORLD_BOTTOM + 10), anchor='midtop'
        )

    def draw(self, surface, time, font, small, fps):
        self.draw_background(surface, time)

        if self.show_trails:
            self.field.draw(surface, self.palette)

        self.draw_food(surface, time, small)
        self.draw_obstacles(surface, time)
        self.draw_nest(surface, time)

        for ant in self.ants:
            ant.draw(surface, self.palette, time)

        self.particles.draw(surface)

        if self.show_vectors:
            for ant in self.ants:
                end = (
                    int(ant.x + math.cos(ant.angle) * 15),
                    int(ant.y + math.sin(ant.angle) * 15)
                )
                pygame.draw.line(
                    surface,
                    self.palette['accent'],
                    (int(ant.x), int(ant.y)),
                    end,
                    1
                )

        if self.show_hud:
            self.draw_hud(surface, font, small, fps)
            self.draw_footer(surface, small)


# ============================================================
# APPLICATION
# ============================================================

class App:
    def __init__(self, smoke_test=False):
        pygame.init()
        pygame.display.set_caption('EIDOLON #015 | ANT COLONY')

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont('consolas', 19, bold=True)
        self.small = pygame.font.SysFont('consolas', 12)
        self.medium = pygame.font.SysFont('consolas', 22, bold=True)
        self.big = pygame.font.SysFont('consolas', 58, bold=True)

        self.audio = Audio()
        self.colony = Colony()

        self.started = False
        self.countdown_active = False
        self.countdown_elapsed = 0.0
        self.countdown_number = 3

        self.running = True
        self.smoke_test = smoke_test
        self.smoke_elapsed = 0.0
        self.time = 0.0

        self.mouse_down = False
        self.last_mouse_action = 0
        self.last_fps = FPS

    def start_countdown(self):
        self.countdown_active = True
        self.countdown_elapsed = 0.0
        self.countdown_number = 3
        self.audio.tick()

    def handle_key(self, key):
        c = self.colony

        if key == pygame.K_ESCAPE:
            self.running = False

        elif key == pygame.K_SPACE:
            if not self.started:
                if not self.countdown_active:
                    self.start_countdown()
            else:
                c.paused = not c.paused
                self.audio.tick()

        elif key == pygame.K_r:
            c.reset()
            self.started = False
            self.countdown_active = False

        elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            c.speed = min(5.0, c.speed + 0.25)

        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            c.speed = max(0.25, c.speed - 0.25)

        elif key == pygame.K_q:
            for _ in range(10):
                c.add_ant()

        elif key == pygame.K_a:
            c.remove_ants(10)

        elif key == pygame.K_f:
            c.show_trails = not c.show_trails

        elif key == pygame.K_v:
            c.show_vectors = not c.show_vectors

        elif key == pygame.K_g:
            c.show_grid = not c.show_grid

        elif key == pygame.K_h:
            c.show_hud = not c.show_hud

        elif key == pygame.K_c:
            c.palette_index = (c.palette_index + 1) % len(PALETTES)
            c.field.dirty = True

        elif key == pygame.K_m:
            self.audio.toggle()

        elif key == pygame.K_x:
            c.field.clear()

        elif key == pygame.K_o:
            c.obstacle_mode = True
            c.food_mode = False

        elif key == pygame.K_w:
            c.food_mode = True
            c.obstacle_mode = False

        elif key == pygame.K_DELETE:
            c.foods.clear()

        elif key == pygame.K_BACKSPACE:
            c.obstacles.clear()

        elif key == pygame.K_n:
            c.nest_x = random.randint(150, WIDTH - 150)
            c.nest_y = random.randint(HUD_H + 100, WORLD_BOTTOM - 80)

        elif key == pygame.K_s:
            c.add_food(
                random.randint(80, WIDTH - 80),
                random.randint(HUD_H + 70, WORLD_BOTTOM - 50),
                1200
            )

    def mouse_action(self, pos, erase=False):
        x, y = pos
        c = self.colony

        if y < HUD_H or y > WORLD_BOTTOM:
            return

        now = pygame.time.get_ticks()

        if now - self.last_mouse_action < 50:
            return

        self.last_mouse_action = now

        if erase:
            c.obstacles = [
                o for o in c.obstacles
                if dist(x, y, o.x, o.y) > o.radius + 8
            ]
            c.foods = [
                f for f in c.foods
                if dist(x, y, f.x, f.y) > f.radius + 8
            ]

        elif c.obstacle_mode:
            c.add_obstacle(x, y)

        elif c.food_mode:
            c.add_food(x, y, 900)
            c.particles.burst(x, y, c.palette['food'], 10, 70)

    def handle_mouse(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.mouse_down = True
                self.mouse_action(event.pos)
            elif event.button == 3:
                self.mouse_action(event.pos, erase=True)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouse_down = False

        elif event.type == pygame.MOUSEMOTION and self.mouse_down:
            self.mouse_action(event.pos)

    def draw_intro(self):
        p = self.colony.palette
        self.screen.fill(p['bg'])

        for i in range(75):
            x = (i * 173 + int(self.time * (7 + i % 4))) % WIDTH
            y = HUD_H + (i * 97) % (WORLD_BOTTOM - HUD_H)

            brightness = 0.35 + 0.65 * (
                (math.sin(self.time * 1.3 + i) + 1) / 2
            )

            color = mix_color(p['grid'], p['accent'], brightness * 0.45)
            pygame.draw.circle(self.screen, color, (x, y), 1)

        cx, cy = (WIDTH // 2, HEIGHT // 2 - 65)
        pulse = (math.sin(self.time * 2.2) + 1) * 0.5

        glow_circle(
            self.screen, p['accent'], (cx, cy),
            int(22 + pulse * 6), strength=0.85
        )

        for i in range(3):
            radius = int(65 + ((self.time * 35 + i * 48) % 145))
            alpha = 1 - ((radius - 65) / 145)

            ring = pygame.Surface(
                (radius * 2 + 2, radius * 2 + 2),
                pygame.SRCALPHA
            )

            pygame.draw.circle(
                ring,
                (*p['accent'], int(65 * alpha)),
                (radius + 1, radius + 1),
                radius,
                1
            )

            self.screen.blit(ring, (cx - radius - 1, cy - radius - 1))

        draw_text(
            self.screen, 'EIDOLON', self.medium, p['muted'],
            (WIDTH // 2, 125), anchor='midtop'
        )

        draw_text(
            self.screen, 'ANT COLONY', self.big, p['text'],
            (WIDTH // 2, HEIGHT // 2 + 15), anchor='midtop'
        )

        draw_text(
            self.screen,
            'SIMPLE RULES. EMERGENT INTELLIGENCE.',
            self.small, p['accent'],
            (WIDTH // 2, HEIGHT // 2 + 94), anchor='midtop'
        )

        lines = [
            'INDIVIDUALS SEARCH',
            'PHEROMONES CONNECT',
            'THE COLONY ORGANIZES'
        ]

        for i, line in enumerate(lines):
            draw_text(
                self.screen, line, self.small, p['muted'],
                (WIDTH // 2, HEIGHT // 2 + 140 + i * 22),
                anchor='midtop'
            )

        blink = 0.5 + 0.5 * math.sin(self.time * 3.0)
        prompt_color = mix_color(p['muted'], p['food'], blink)

        draw_text(
            self.screen, 'PRESS SPACE TO INITIALIZE',
            self.medium, prompt_color,
            (WIDTH // 2, HEIGHT - 100), anchor='midtop'
        )

        draw_text(
            self.screen, 'PROJECT 015   /   ARTIFICIAL LIFE',
            self.small, p['muted'],
            (WIDTH // 2, HEIGHT - 44), anchor='midtop'
        )

    def draw_countdown(self):
        p = self.colony.palette

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*p['bg'], 185))
        self.screen.blit(overlay, (0, 0))

        label = 'GO' if self.countdown_number == 0 else str(self.countdown_number)
        scale = 1 + 0.12 * math.sin(self.time * 9)
        font_size = int(82 * scale)
        countdown_font = pygame.font.SysFont(
            'consolas', font_size, bold=True
        )

        draw_text(
            self.screen, label, countdown_font, p['accent'],
            (WIDTH // 2, HEIGHT // 2 - 35), anchor='center'
        )

        draw_text(
            self.screen, 'COLONY INITIALIZATION',
            self.small, p['text'],
            (WIDTH // 2, HEIGHT // 2 + 45), anchor='midtop'
        )

    def update_countdown(self, dt):
        if not self.countdown_active:
            return

        self.countdown_elapsed += dt

        if self.countdown_elapsed >= 3.0:
            self.countdown_active = False
            self.started = True
            self.audio.go()
            return

        number = 3 - int(self.countdown_elapsed)

        if number != self.countdown_number:
            self.countdown_number = number
            self.audio.tick()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.time += dt
            self.last_fps = self.clock.get_fps()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)

                elif event.type in (
                    pygame.MOUSEBUTTONDOWN,
                    pygame.MOUSEBUTTONUP,
                    pygame.MOUSEMOTION
                ):
                    self.handle_mouse(event)

            if self.smoke_test:
                self.smoke_elapsed += dt
                if self.smoke_elapsed > 2.0:
                    self.running = False

            if self.started:
                self.colony.update(dt, self.audio)
            else:
                self.colony.particles.ambient(
                    self.colony.palette['accent']
                )
                self.colony.particles.update(dt)

            self.update_countdown(dt)

            if not self.started and not self.countdown_active:
                self.draw_intro()
            else:
                self.colony.draw(
                    self.screen,
                    self.time,
                    self.font,
                    self.small,
                    self.last_fps
                )

                if self.countdown_active:
                    self.draw_countdown()

            pygame.display.flip()

        pygame.quit()


def main():
    parser = argparse.ArgumentParser(
        description='EIDOLON #015 — Ant Colony'
    )

    parser.add_argument(
        '--smoke-test',
        action='store_true',
        help='Open the application briefly to test startup.'
    )

    args = parser.parse_args()
    App(smoke_test=args.smoke_test).run()


if __name__ == '__main__':
    main()