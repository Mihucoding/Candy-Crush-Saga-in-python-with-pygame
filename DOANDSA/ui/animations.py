import math
import random
import pygame
from constants import (
    CELL_SIZE, GRID_OFFSET_X, GRID_OFFSET_Y,
    ANIM_SWAP_DURATION, ANIM_POP_DURATION, ANIM_FALL_SPEED,
    SCREEN_WIDTH, SCREEN_HEIGHT, CANDY_COLORS,
)
from game.candy import STRIPED_H, STRIPED_V, WRAPPED, COLOR_BOMB


def _cell_center(row: int, col: int) -> tuple[float, float]:
    return (
        GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE / 2,
        GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE / 2,
    )


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _ease_out(t: float) -> float:
    return 1 - (1 - t) ** 2


def _ease_in_out_cubic(t: float) -> float:
    return 4 * t**3 if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2


def _ease_out_back(t: float) -> float:
    c1 = 1.70158
    c2 = c1 * 1.525
    return 1 + c2 * (t - 1) ** 3 + c1 * (t - 1) ** 2


class SwapAnim:
    """Smooth candy swap animation with easing, arc path, and invalid swap shake.
    
    Features:
    - Cubic in-out easing for smooth motion
    - Arc path (perpendicular to swap direction) for natural feel
    - Scale pulse (1.0 → 1.12 → 1.0) for weight and bounce
    - Invalid swap: high-frequency shake that diminishes over time
    - Optional alpha fade for invalid swaps
    """
    def __init__(self, r1, c1, r2, c2, valid: bool):
        self.cells = [(r1, c1), (r2, c2)]
        self.valid = valid
        self.elapsed = 0.0
        self.phase = 0  # 0: swap out, 1: swap back (for invalid)
        self.done = False
        self.start = [_cell_center(r1, c1), _cell_center(r2, c2)]
        self.end = [_cell_center(r2, c2), _cell_center(r1, c1)]
        self._pos = list(self.start)
        self.is_horizontal = (r1 == r2)
        self._current_scale = 1.0
        self._current_alpha = 255
        # Store individual shake offsets for each candy
        self._shake_offset_0_x = 0.0
        self._shake_offset_0_y = 0.0
        self._shake_offset_1_x = 0.0
        self._shake_offset_1_y = 0.0

    def update(self, dt: float):
        self.elapsed += dt
        t = min(self.elapsed / ANIM_SWAP_DURATION, 1.0)
        
        # Determine easing function for position
        et = _ease_in_out_cubic(t)
        if not self.valid and self.phase == 1:
            et = _ease_out_back(t)  # Bouncy return for invalid swaps

        # Scaling: 1.0 → 1.12 → 1.0 (peaks at t=0.5)
        scale_t = math.sin(t * math.pi)
        self._current_scale = 1.0 + 0.12 * scale_t

        # Arc value: perpendicular to swap direction
        arc_ease_t = _ease_in_out_cubic(t)
        arc_val = math.sin(arc_ease_t * math.pi) * 25

        # Reset shake offsets
        self._shake_offset_0_x = self._shake_offset_0_y = 0.0
        self._shake_offset_1_x = self._shake_offset_1_y = 0.0
        self._current_alpha = 255

        if not self.valid:
            # Invalid swap: high-frequency shake that diminishes
            shake_freq = 40 if self.phase == 0 else 50
            shake_amp = 7 if self.phase == 0 else 10
            shake_val = math.sin(t * math.pi * shake_freq) * shake_amp * (1 - t)

            # Shake perpendicular to swap + slight along
            if self.is_horizontal:
                self._shake_offset_0_y = shake_val
                self._shake_offset_1_y = -shake_val
                self._shake_offset_0_x = shake_val * 0.2
                self._shake_offset_1_x = -shake_val * 0.2
            else:
                self._shake_offset_0_x = shake_val
                self._shake_offset_1_x = -shake_val
                self._shake_offset_0_y = shake_val * 0.2
                self._shake_offset_1_y = -shake_val * 0.2
            
            # Alpha fade for invalid swaps
            self._current_alpha = int(_lerp(255, 100, t))

        s = self.start if self.phase == 0 else self.end
        e = self.end if self.phase == 0 else self.start
        
        new_positions = []
        for i in range(2):
            bx = _lerp(s[i][0], e[i][0], et)
            by = _lerp(s[i][1], e[i][1], et)
            
            # Apply arc perpendicular to swap direction
            if self.is_horizontal:
                dy_arc = arc_val if i == 0 else -arc_val
                new_positions.append((
                    bx + (self._shake_offset_0_x if i == 0 else self._shake_offset_1_x),
                    by - dy_arc + (self._shake_offset_0_y if i == 0 else self._shake_offset_1_y)
                ))
            else:
                dx_arc = arc_val if i == 0 else -arc_val
                new_positions.append((
                    bx + dx_arc + (self._shake_offset_0_x if i == 0 else self._shake_offset_1_x),
                    by + (self._shake_offset_0_y if i == 0 else self._shake_offset_1_y)
                ))
        
        self._pos = new_positions

        if t >= 1.0:
            if self.phase == 0 and not self.valid:
                self.phase = 1
                self.elapsed = 0.0
            else:
                self.done = True

    def get_overrides(self) -> dict[tuple, tuple]:
        """Return position overrides: {(row, col): (x, y, scale, alpha)}"""
        return {
            self.cells[i]: (self._pos[i][0], self._pos[i][1], self._current_scale, self._current_alpha)
            for i in range(2)
        }


class PopAnim:
    def __init__(self, positions: list[tuple], candy_colors: dict = None):
        self.positions = positions
        self.elapsed = 0.0
        self.done = False
        self.particles: list[dict] = []
        _fallback = [
            (255, 255, 255), (255, 240, 80), (255, 190, 40),
            (255, 120, 200), (100, 220, 255), (160, 255, 100),
        ]
        for r, c in positions:
            cx, cy = _cell_center(r, c)
            ctype = candy_colors.get((r, c)) if candy_colors else None
            base = CANDY_COLORS.get(ctype) if ctype else None
            for _ in range(16):
                ang = random.uniform(0, 2 * math.pi)
                spd = random.uniform(150, 400)
                if base:
                    v = random.randint(-40, 60)
                    color = tuple(max(0, min(255, ch + v)) for ch in base)
                else:
                    color = random.choice(_fallback)
                self.particles.append({
                    'x': cx, 'y': cy,
                    'vx': math.cos(ang) * spd,
                    'vy': math.sin(ang) * spd,
                    'life': 1.0,
                    'size': random.randint(3, 7),
                    'color': color,
                })

    def update(self, dt: float):
        self.elapsed += dt
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 700 * dt # Higher gravity
            p['life'] -= dt / ANIM_POP_DURATION
        if self.elapsed >= ANIM_POP_DURATION:
            self.done = True

    def get_overrides(self) -> dict[tuple, tuple]:
        t = min(self.elapsed / ANIM_POP_DURATION, 1.0)
        # Bouncier pop scale
        scale = 1.0 + 0.6 * math.sin(t * math.pi) if t < 0.4 else max(0.0, 1.6 * (1.0 - (t - 0.4) / 0.6))
        alpha = 255 if t < 0.3 else max(0, int(255 * (1.0 - (t - 0.3) / 0.7)))
        return {
            pos: (_cell_center(*pos)[0], _cell_center(*pos)[1], scale, alpha)
            for pos in self.positions
        }


class FallAnim:
    def __init__(self, falls: list[tuple[int, int, int, int]]):
        self.falls = falls
        self.elapsed = 0.0
        self.done = False
        self.durations = [
            abs(tr - fr) * CELL_SIZE / ANIM_FALL_SPEED
            for fr, fc, tr, tc in falls
        ]
        self.max_dur = max(self.durations) if self.durations else 0.001

    def update(self, dt: float):
        self.elapsed += dt
        if self.elapsed >= self.max_dur:
            self.done = True

    def get_overrides(self) -> dict[tuple, tuple]:
        result = {}
        for i, (fr, fc, tr, tc) in enumerate(self.falls):
            dur = self.durations[i]
            t = min(self.elapsed / dur, 1.0) if dur > 0 else 1.0
            et = _ease_out(t)
            sx, sy = _cell_center(fr, fc)
            ex, ey = _cell_center(tr, tc)
            squash = math.sin(t * math.pi) * 0.15 if t > 0.8 else 0.0
            result[(tr, tc)] = (_lerp(sx, ex, et), _lerp(sy, ey, et), 1.0 - squash, 255)
        return result


class FloatingText:
    def __init__(self, text: str, x: float, y: float, color=(255, 220, 50)):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.elapsed = 0.0
        self.duration = 1.0
        self.done = False

    def update(self, dt: float):
        self.elapsed += dt
        self.y -= 100 * dt * (1 - self.elapsed/self.duration)
        if self.elapsed >= self.duration:
            self.done = True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        t = self.elapsed / self.duration
        alpha = int(255 * (1.0 - t))
        # Add a small scale effect
        scale = 1.0 + 0.2 * math.sin(t * math.pi)
        s = font.render(self.text, True, self.color)
        if scale != 1.0:
            sw, sh = s.get_size()
            s = pygame.transform.scale(s, (int(sw * scale), int(sh * scale)))
        s.set_alpha(alpha)
        surface.blit(s, (int(self.x - s.get_width() // 2), int(self.y)))


class MatchBanner:
    def __init__(self, label: str, color: tuple):
        self.label = label
        self.color = color
        self.elapsed = 0.0
        self.life = 1.5 # Longer duration
        self.done = False

    def update(self, dt: float):
        self.elapsed += dt
        if self.elapsed >= self.life:
            self.done = True

    def draw(self, surface: pygame.Surface, font_fn):
        t = self.elapsed / self.life
        # Smooth pop-in and fade-out
        scale = 1.0 + math.exp(-10 * t) * math.sin(t * 20) if t < 0.3 else 1.0
        alpha = max(0, int(255 * (1.0 - (t - 0.7) / 0.3))) if t > 0.7 else 255

        color = self.color
        if self.label in ('AMAZING!!!', 'UNBELIEVABLE!!'):
            hue = (pygame.time.get_ticks() // 2) % 360
            c = pygame.Color(0)
            c.hsva = (hue, 90, 100, 100)
            color = (c.r, c.g, c.b)

        size = 64 if self.label in ('AMAZING!!!', 'UNBELIEVABLE!!') else 48
        font = font_fn(int(size * scale))
        text = font.render(self.label, True, color)
        text.set_alpha(alpha)

        rect = text.get_rect(center=(SCREEN_WIDTH // 2, 400 + math.sin(t * 10) * 10))
        
        # Glowing background
        bg = pygame.Surface((rect.width + 100, rect.height + 40), pygame.SRCALPHA)
        bg_alpha = int(180 * (alpha / 255) * (0.5 + 0.5 * math.sin(t * 20)))
        pygame.draw.rect(bg, (255, 255, 255, bg_alpha // 4), bg.get_rect(), border_radius=bg.get_height() // 2)
        pygame.draw.rect(bg, (0, 0, 0, int(150 * (alpha/255))), bg.get_rect().inflate(-10, -10), border_radius=bg.get_height() // 2)
        
        surface.blit(bg, bg.get_rect(center=rect.center))
        surface.blit(text, rect)


class SpecialBreakEffect:
    _DURATIONS = {
        STRIPED_H: 0.90,
        STRIPED_V: 0.90,
        WRAPPED:   1.30,
        COLOR_BOMB: 1.80,
    }

    def __init__(self, special_type: str, row: int, col: int):
        self.type = special_type
        self.cx, self.cy = _cell_center(row, col)
        self.elapsed = 0.0
        self.duration = self._DURATIONS.get(special_type, 0.5)
        self.done = False

    def update(self, dt: float):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.done = True

    def draw(self, surface: pygame.Surface):
        t = self.elapsed / self.duration
        if self.type in (STRIPED_H, STRIPED_V):
            is_h = self.type == STRIPED_H
            alpha = int(255 * (1 - t) ** 0.7)
            thickness = int(16 + 90 * (1 - t))

            beam = pygame.Surface(
                (SCREEN_WIDTH, thickness) if is_h else (thickness, SCREEN_HEIGHT),
                pygame.SRCALPHA,
            )
            for i in range(3):
                c_alpha = alpha // (i + 1)
                inflated = (beam.get_rect().inflate(0, -i * 12)
                            if is_h else beam.get_rect().inflate(-i * 12, 0))
                pygame.draw.rect(beam, (255, 250, 200, c_alpha), inflated)

            cx = SCREEN_WIDTH // 2 if is_h else int(self.cx)
            cy = int(self.cy) if is_h else SCREEN_HEIGHT // 2
            surface.blit(beam, beam.get_rect(center=(cx, cy)))

            # Sparks drawn on SRCALPHA surface so alpha is respected
            spark_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for _ in range(8):
                pos = random.uniform(0, SCREEN_WIDTH if is_h else SCREEN_HEIGHT)
                px = pos if is_h else self.cx + random.uniform(-28, 28)
                py = self.cy + random.uniform(-28, 28) if is_h else pos
                s_alpha = random.randint(max(0, alpha - 60), min(255, alpha + 40))
                pygame.draw.circle(spark_surf, (255, 255, 210, s_alpha),
                                   (int(px), int(py)), random.randint(2, 6))
            surface.blit(spark_surf, (0, 0))

        elif self.type == WRAPPED:
            ring_colors = [
                (255, 200, 80), (255, 140, 210),
                (130, 230, 255), (190, 255, 130), (255, 255, 100),
            ]
            ring_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for i in range(5):
                prog = max(0.0, t * 1.8 - i * 0.22)
                if 0 < prog < 1.0:
                    r = int(prog * 280)
                    r_alpha = int(240 * (1 - prog))
                    pygame.draw.circle(ring_surf, (*ring_colors[i], r_alpha),
                                       (int(self.cx), int(self.cy)), r, max(2, 9 - i))
            surface.blit(ring_surf, (0, 0))

            # Central flash
            flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_r = int(120 * max(0.0, 1 - t))
            if flash_r > 0:
                flash_alpha = int(220 * max(0.0, 1 - t * 2.2))
                pygame.draw.circle(flash_surf, (255, 255, 255, flash_alpha),
                                   (int(self.cx), int(self.cy)), flash_r)
            surface.blit(flash_surf, (0, 0))

            # Rotating sparkles
            spark_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for i in range(8):
                ang = i * (math.pi / 4) + t * 5
                dist = t * 130
                sx = self.cx + math.cos(ang) * dist
                sy = self.cy + math.sin(ang) * dist
                s_alpha = max(0, int(255 * (1 - t)))
                pygame.draw.circle(spark_surf, (255, 255, 190, s_alpha),
                                   (int(sx), int(sy)), 5)
            surface.blit(spark_surf, (0, 0))

        elif self.type == COLOR_BOMB:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(160 * (1 - t) ** 1.5)))
            surface.blit(flash, (0, 0))

            for i in range(24):
                ang = i * (math.pi / 12) + t * 5
                dist = 1000 * t
                x2 = self.cx + math.cos(ang) * dist
                y2 = self.cy + math.sin(ang) * dist
                c = pygame.Color(0)
                c.hsva = ((i * 15 + t * 720) % 360, 95, 100, 100)
                pygame.draw.line(surface, c, (int(self.cx), int(self.cy)),
                                 (int(x2), int(y2)), max(2, int(10 * (1 - t))))

            # Tip glows at ray ends
            tip_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for i in range(24):
                ang = i * (math.pi / 12) + t * 5
                dist = 1000 * t
                x2 = int(self.cx + math.cos(ang) * dist)
                y2 = int(self.cy + math.sin(ang) * dist)
                if 0 <= x2 < SCREEN_WIDTH and 0 <= y2 < SCREEN_HEIGHT:
                    pygame.draw.circle(tip_surf, (255, 255, 255, max(0, int(200 * (1 - t)))),
                                       (x2, y2), 7)
            surface.blit(tip_surf, (0, 0))

            # Central pulsing glow
            glow_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pulse_r = int(28 + 20 * abs(math.sin(t * math.pi * 5)))
            pygame.draw.circle(glow_surf, (255, 255, 180, max(0, int(210 * (1 - t)))),
                               (int(self.cx), int(self.cy)), pulse_r)
            surface.blit(glow_surf, (0, 0))


class ScreenShake:
    """Short camera shake — returns (dx, dy) offset each frame."""
    def __init__(self, intensity: float = 8.0, duration: float = 0.35):
        self.intensity = intensity
        self.elapsed   = 0.0
        self.duration  = duration
        self.done      = False

    def update(self, dt: float):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.done = True

    def get_offset(self) -> tuple:
        if self.done:
            return (0, 0)
        t = self.elapsed / self.duration
        decay = (1.0 - t) ** 2
        freq  = 40.0
        ox = self.intensity * decay * math.sin(t * freq)
        oy = self.intensity * decay * math.cos(t * freq * 1.3)
        return (ox, oy)


class AnimationManager:
    def __init__(self):
        self._active: list = []
        self._floating: list[FloatingText] = []
        self._banners: list[MatchBanner] = []
        self._breaks: list[SpecialBreakEffect] = []
        self._override_cache: dict[tuple, tuple] = {}

    @property
    def is_busy(self) -> bool:
        return (
            len(self._active) > 0
            or any(not b.done for b in self._banners)
            or any(not b.done for b in self._breaks)
        )

    def add(self, anim) -> None:
        self._active.append(anim)

    def add_floating(self, text: str, row: int, col: int, color=(255, 220, 50)):
        cx, cy = _cell_center(row, col)
        self._floating.append(FloatingText(text, cx, cy, color))

    def add_banner(self, label: str, color: tuple) -> None:
        self._banners = [b for b in self._banners if not b.done]
        self._banners.append(MatchBanner(label, color))

    def add_special_break(self, special_type: str, row: int, col: int) -> None:
        self._breaks.append(SpecialBreakEffect(special_type, row, col))

    def update(self, dt: float) -> None:
        self._override_cache = {}
        still_active = []
        for anim in self._active:
            anim.update(dt)
            if hasattr(anim, "get_overrides"):
                self._override_cache.update(anim.get_overrides())
            if not anim.done:
                still_active.append(anim)
        self._active = still_active

        still_floating = []
        for ft in self._floating:
            ft.update(dt)
            if not ft.done:
                still_floating.append(ft)
        self._floating = still_floating

        for b in self._banners:
            b.update(dt)
        self._banners = [b for b in self._banners if not b.done]

        for b in self._breaks:
            b.update(dt)
        self._breaks = [b for b in self._breaks if not b.done]

    def get_override(self, row: int, col: int):
        return self._override_cache.get((row, col))

    def draw_floating(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        for ft in self._floating:
            ft.draw(surface, font)
        
        # Draw particles with shimmer and trail
        particle_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for anim in self._active:
            if isinstance(anim, PopAnim):
                for p in anim.particles:
                    if p['life'] > 0:
                        alpha = int(255 * max(0.0, p['life']))
                        # Shimmer effect: flicker alpha
                        if random.random() > 0.8: alpha = min(255, alpha + 50)
                        
                        # Draw trail
                        tx, ty = p['x'] - p['vx'] * 0.03, p['y'] - p['vy'] * 0.03
                        pygame.draw.line(particle_surf, (*p['color'], alpha // 2), (int(tx), int(ty)), (int(p['x']), int(p['y'])), p['size'] - 1)
                        # Main particle
                        pygame.draw.circle(particle_surf, (*p['color'], alpha), (int(p['x']), int(p['y'])), p['size'])
        surface.blit(particle_surf, (0, 0))

    def draw_effects(self, surface: pygame.Surface, font_fn) -> None:
        for b in self._breaks:
            b.draw(surface)
        for b in self._banners:
            b.draw(surface, font_fn)
