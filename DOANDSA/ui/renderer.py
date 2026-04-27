import random
import math
import pygame
from constants import (
    GRID_ROWS, GRID_COLS, CELL_SIZE,
    GRID_OFFSET_X, GRID_OFFSET_Y,
    CANDY_COLORS, GRID_BG_COLOR, GRID_LINE_COLOR,
    SCREEN_WIDTH, SCREEN_HEIGHT
)
from game.candy import NORMAL, STRIPED_H, STRIPED_V, WRAPPED, COLOR_BOMB

# Cache background surface to avoid re-rendering each frame
_cached_bg_surface = None
_cached_bg_sparkles = None


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _generate_bg_once():
    """Generate background once and cache it for reuse."""
    global _cached_bg_surface, _cached_bg_sparkles
    
    # 1. Draw gradient directly on surface (faster than line-by-line)
    _cached_bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    start_color = (130, 200, 255)   # Sky blue
    mid_color = (230, 150, 255)     # Lavender
    end_color = (255, 220, 150)     # Gold
    
    # Use fewer gradient bands (8 instead of 960)
    num_bands = 8
    band_height = SCREEN_HEIGHT / num_bands
    
    for band in range(num_bands):
        ratio = band / (num_bands - 1) if num_bands > 1 else 0
        if ratio < 0.5:
            t_blend = ratio * 2
            c = tuple(int(_lerp(start_color[i], mid_color[i], t_blend)) for i in range(3))
        else:
            t_blend = (ratio - 0.5) * 2
            c = tuple(int(_lerp(mid_color[i], end_color[i], t_blend)) for i in range(3))
        
        band_surf = pygame.Surface((SCREEN_WIDTH, int(band_height) + 1))
        band_surf.fill(c)
        _cached_bg_surface.blit(band_surf, (0, int(band * band_height)))
    
    # 2. Simple dark overlay vignette (faster than pixel-by-pixel)
    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (0, 0, 0, 40), vignette.get_rect())  # Subtle dark overlay
    _cached_bg_surface.blit(vignette, (0, 0))
    
    # 3. Grid panel
    panel_rect = pygame.Rect(GRID_OFFSET_X - 10, GRID_OFFSET_Y - 10,
                             GRID_COLS * CELL_SIZE + 20, GRID_ROWS * CELL_SIZE + 20)
    pygame.draw.rect(_cached_bg_surface, (180, 140, 90), panel_rect, width=7, border_radius=28)
    pygame.draw.rect(_cached_bg_surface, (230, 200, 160), panel_rect, width=4, border_radius=28)

    # 4. Candy cells (darker for better candy visibility)
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            x = GRID_OFFSET_X + c * CELL_SIZE
            y = GRID_OFFSET_Y + r * CELL_SIZE
            cell = pygame.Rect(x + 5, y + 5, CELL_SIZE - 10, CELL_SIZE - 10)
            
            # Much darker purple for better candy contrast
            shade = (40, 20, 70) if (r + c) % 2 == 0 else (60, 30, 90)
            pygame.draw.rect(_cached_bg_surface, shade, cell, border_radius=15)
            pygame.draw.rect(_cached_bg_surface, (80, 50, 140), cell, width=3, border_radius=15)
            
            inner = cell.inflate(-8, -8)
            glow = tuple(min(255, int(s * 1.5)) for s in shade)  # Reduced glow to match darker theme
            pygame.draw.rect(_cached_bg_surface, glow, inner, width=2, border_radius=10)

    # 5. Static sparkles (cached, only 60 instead of 120)
    random.seed(42)
    _cached_bg_sparkles = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    
    for _ in range(60):
        sx = random.randint(0, SCREEN_WIDTH)
        sy = random.randint(0, SCREEN_HEIGHT)
        
        if not panel_rect.inflate(30, 30).collidepoint(sx, sy):
            size = random.randint(2, 5)
            alpha = random.randint(120, 180)
            pygame.draw.circle(_cached_bg_sparkles, (255, 255, 230, alpha), (sx, sy), size)
    
    random.seed()


def draw_grid_background(surface: pygame.Surface) -> None:
    """Draw cached background - much faster than regenerating each frame."""
    global _cached_bg_surface, _cached_bg_sparkles
    
    # Initialize cache on first call
    if _cached_bg_surface is None:
        _generate_bg_once()
    
    # Blit cached background
    surface.blit(_cached_bg_surface, (0, 0))
    surface.blit(_cached_bg_sparkles, (0, 0))


def _get_gem_points(candy_type: str, size: int) -> list[tuple[float, float]]:
    cx, cy, r = size // 2, size // 2, size // 2 - 2
    if candy_type == 'red':  # Heart
        pts = []
        for a in range(0, 360, 10):
            rad = math.radians(a)
            px = 16 * math.sin(rad) ** 3
            py = -(13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad))
            pts.append((cx + px * (size / 35), cy + py * (size / 35) + 2))
        return pts
    if candy_type == 'orange':  # Diamond
        return [(cx, 2), (size - 2, cy), (cx, size - 2), (2, cy)]
    if candy_type == 'yellow':  # Hexagon
        return [(cx + r * math.cos(math.radians(i * 60 - 30)),
                 cy + r * math.sin(math.radians(i * 60 - 30))) for i in range(6)]
    if candy_type == 'green':  # Octagon
        return [(cx + r * math.cos(math.radians(i * 45 + 22.5)),
                 cy + r * math.sin(math.radians(i * 45 + 22.5))) for i in range(8)]
    if candy_type == 'purple':  # Star
        pts = []
        for i in range(10):
            dist = r if i % 2 == 0 else r * 0.45
            a = math.radians(i * 36 - 90)
            pts.append((cx + dist * math.cos(a), cy + dist * math.sin(a)))
        return pts
    # blue — 16-gon (circle)
    return [(cx + r * math.cos(math.radians(i * 22.5)),
             cy + r * math.sin(math.radians(i * 22.5))) for i in range(16)]


def _draw_special_overlay(surf: pygame.Surface, special_type: str, size: int) -> None:
    if special_type == NORMAL:
        return
    cx, cy = size // 2, size // 2
    if special_type in (STRIPED_H, STRIPED_V):
        for i in range(-1, 2):
            offs = i * (size // 4)
            if special_type == STRIPED_V:
                p = [(cx - 8, cy + offs - 4), (cx, cy + offs), (cx + 8, cy + offs - 4)]
            else:
                p = [(cx + offs - 4, cy - 8), (cx + offs, cy), (cx + offs - 4, cy + 8)]
            pygame.draw.lines(surf, (255, 255, 255, 220), False, p, 3)
    elif special_type == WRAPPED:
        pygame.draw.circle(surf, (255, 255, 255, 180), (cx, cy), size // 2 - 2, 3)
        pygame.draw.circle(surf, (255, 255, 255, 100), (cx, cy), size // 3, 2)
    elif special_type == COLOR_BOMB:
        tick_angle = (pygame.time.get_ticks() * 0.2) % 360
        for i in range(12):
            a = math.radians(i * 30 + tick_angle)
            x2 = int(cx + math.cos(a) * (size // 2 - 2))
            y2 = int(cy + math.sin(a) * (size // 2 - 2))
            pygame.draw.line(surf, (255, 255, 255, 150), (cx, cy), (x2, y2), 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), size // 4)


def draw_candy(
    surface: pygame.Surface,
    candy_type: str,
    cx: float,
    cy: float,
    scale: float = 1.0,
    alpha: int = 255,
    special_type: str = NORMAL,
) -> None:
    size = int(CELL_SIZE * 0.85 * scale)
    if size < 4:
        return
    color = (40, 40, 60) if special_type == COLOR_BOMB else CANDY_COLORS.get(candy_type, (200, 200, 200))
    temp = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
    pts = _get_gem_points(candy_type, size)

    shadow_pts = [(p[0] + 2, p[1] + 3) for p in pts]
    pygame.draw.polygon(temp, (10, 5, 20, 150), shadow_pts)
    pygame.draw.polygon(temp, color + (alpha,), pts)

    inner_pts = [((p[0] - size / 2) * 0.7 + size / 2,
                  (p[1] - size / 2) * 0.7 + size / 2) for p in pts]
    light_color = tuple(min(255, c + 60) for c in color)
    pygame.draw.polygon(temp, light_color + (int(alpha * 0.6),), inner_pts)
    pygame.draw.polygon(temp, (255, 255, 255, int(alpha * 0.4)), pts, 2)

    # Special glow for special types
    if special_type != NORMAL:
        glow_pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 0.5
        glow_alpha = int(50 + 100 * glow_pulse)
        glow_size = size + int(4 + 8 * glow_pulse)
        glow_surf = pygame.Surface((glow_size + 4, glow_size + 4), pygame.SRCALPHA)
        pygame.draw.polygon(glow_surf, (255, 255, 255, glow_alpha), 
                           [((p[0] * glow_size / size), (p[1] * glow_size / size)) for p in pts])
        surface.blit(glow_surf, (int(cx - glow_size // 2), int(cy - glow_size // 2)), special_flags=pygame.BLEND_RGBA_ADD)

    _draw_special_overlay(temp, special_type, size)
    surface.blit(temp, (int(cx - size // 2), int(cy - size // 2)))


def draw_selection(surface: pygame.Surface, row: int, col: int, t: float = 0.0) -> None:
    x = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
    y = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
    pulse = 1.0 + 0.1 * math.sin(t * 8.0)
    for i in range(3):
        sz = int(CELL_SIZE * pulse) + i * 4
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 150, 180 - i * 50), s.get_rect(), width=3, border_radius=12)
        surface.blit(s, (x - sz // 2, y - sz // 2))


def draw_board(
    surface: pygame.Surface,
    board,
    anim_manager=None,
    selected=None,
    t: float = 0.0,
) -> None:
    """Draw the complete board with background, candies, animations, and effects.
    
    Args:
        surface: Pygame surface to draw on
        board: Game board object with get_candy(r, c)
        anim_manager: AnimationManager for position overrides
        selected: (row, col) tuple of selected candy or None
        t: Time accumulator for animations (passed from main loop)
    """
    # 1. Draw the grid background with gradient and static sparkles
    draw_grid_background(surface)
    
    # 2. Add dynamic animated sparkles (simplified and optimized)
    sparkle_overlay_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    
    grid_panel_rect = pygame.Rect(GRID_OFFSET_X - 10, GRID_OFFSET_Y - 10,
                                  GRID_COLS * CELL_SIZE + 20, GRID_ROWS * CELL_SIZE + 20)

    # Pre-generate sparkle positions once (cached internally)
    random.seed(99)
    for _ in range(30):  # Reduced from 80 to 30 for performance
        sx = random.randint(0, SCREEN_WIDTH)
        sy = random.randint(0, SCREEN_HEIGHT)

        if not grid_panel_rect.inflate(20, 20).collidepoint(sx, sy):
            size = random.randint(1, 3)
            phase_offset = random.uniform(0, math.pi * 2)
            # Simple twinkling: just alpha modulation
            twinkle_alpha = int(100 + 100 * math.sin(t * 5.0 + phase_offset))
            
            # Simple circles (no star calculations)
            pygame.draw.circle(sparkle_overlay_surf, (255, 255, 200, twinkle_alpha), (sx, sy), size)
    
    surface.blit(sparkle_overlay_surf, (0, 0))
    random.seed()

    # 3. Draw candies with animation overrides
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            cx = GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE // 2
            cy = GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE // 2
            override = anim_manager.get_override(r, c) if anim_manager else None
            if override:
                cx, cy, scale, alpha = override
            else:
                scale, alpha = 1.0, 255
            candy = board.get_candy(r, c)
            if candy:
                draw_candy(surface, candy.candy_type, cx, cy, scale, alpha, candy.special_type)
    
    # 4. Draw selection indicator if active
    if selected is not None:
        draw_selection(surface, *selected, t=t)
