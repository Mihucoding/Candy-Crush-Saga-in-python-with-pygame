import random
import math
import pygame
from constants import (
    GRID_ROWS, GRID_COLS, CELL_SIZE,
    GRID_OFFSET_X, GRID_OFFSET_Y,
    CANDY_COLORS, CANDY_GLOW_COLORS,
    SCREEN_WIDTH, SCREEN_HEIGHT,
)
from game.candy import NORMAL, STRIPED_H, STRIPED_V, WRAPPED, COLOR_BOMB

# Cache background to avoid re-rendering each frame
_cached_bg_surface = None
_cached_bg_sparkles = None


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _get_gem_points(candy_type: str, size: int) -> list:
    cx, cy, r = size // 2, size // 2, size // 2 - 2
    if candy_type == 'red':   # Heart
        pts = []
        for a in range(0, 360, 10):
            rad = math.radians(a)
            px = 16 * math.sin(rad) ** 3
            py = -(13*math.cos(rad) - 5*math.cos(2*rad) - 2*math.cos(3*rad) - math.cos(4*rad))
            pts.append((cx + px*(size/35), cy + py*(size/35) + 2))
        return pts
    if candy_type == 'orange':  # Diamond
        return [(cx, 2), (size-2, cy), (cx, size-2), (2, cy)]
    if candy_type == 'yellow':  # Hexagon
        return [(cx + r*math.cos(math.radians(i*60-30)),
                 cy + r*math.sin(math.radians(i*60-30))) for i in range(6)]
    if candy_type == 'green':   # Octagon
        return [(cx + r*math.cos(math.radians(i*45+22.5)),
                 cy + r*math.sin(math.radians(i*45+22.5))) for i in range(8)]
    if candy_type == 'purple':  # 5-point Star
        pts = []
        for i in range(10):
            dist = r if i % 2 == 0 else r * 0.45
            a = math.radians(i * 36 - 90)
            pts.append((cx + dist*math.cos(a), cy + dist*math.sin(a)))
        return pts
    # blue — smooth 16-gon
    return [(cx + r*math.cos(math.radians(i*22.5)),
             cy + r*math.sin(math.radians(i*22.5))) for i in range(16)]


def _draw_star_shape(surface, color, cx, cy, r_outer, r_inner=None, alpha=255):
    """Draw a 5-point star at (cx, cy)."""
    if r_inner is None:
        r_inner = r_outer * 0.4
    pts = []
    for i in range(10):
        r = r_outer if i % 2 == 0 else r_inner
        a = math.radians(i * 36 - 90)
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    if alpha < 255:
        s = pygame.Surface((int(r_outer*2+4), int(r_outer*2+4)), pygame.SRCALPHA)
        adj = [(p[0] - cx + r_outer + 2, p[1] - cy + r_outer + 2) for p in pts]
        pygame.draw.polygon(s, (*color[:3], alpha), adj)
        surface.blit(s, (int(cx - r_outer - 2), int(cy - r_outer - 2)))
    else:
        pygame.draw.polygon(surface, color[:3], pts)


def _draw_special_overlay(surf: pygame.Surface, special_type: str, size: int) -> None:
    if special_type == NORMAL:
        return
    cx, cy = size // 2, size // 2
    if special_type in (STRIPED_H, STRIPED_V):
        for i in range(-1, 2):
            offs = i * (size // 4)
            if special_type == STRIPED_V:
                p = [(cx-8, cy+offs-4), (cx, cy+offs), (cx+8, cy+offs-4)]
            else:
                p = [(cx+offs-4, cy-8), (cx+offs, cy), (cx+offs-4, cy+8)]
            pygame.draw.lines(surf, (255, 255, 255, 220), False, p, 3)
    elif special_type == WRAPPED:
        pygame.draw.circle(surf, (255, 255, 255, 190), (cx, cy), size//2-2, 3)
        pygame.draw.circle(surf, (255, 255, 255, 110), (cx, cy), size//3, 2)
    elif special_type == COLOR_BOMB:
        tick_angle = (pygame.time.get_ticks() * 0.2) % 360
        for i in range(12):
            a = math.radians(i*30 + tick_angle)
            x2 = int(cx + math.cos(a)*(size//2-2))
            y2 = int(cy + math.sin(a)*(size//2-2))
            pygame.draw.line(surf, (255, 255, 255, 160), (cx, cy), (x2, y2), 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), size//4)


def _generate_bg_once():
    """Generate and cache the static background surface."""
    global _cached_bg_surface, _cached_bg_sparkles

    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # --- Bright gradient: Sky Blue → Lavender → Gold (16 bands for smooth look) ---
    colors = [(130, 200, 255), (200, 140, 255), (255, 220, 150)]
    num_bands = 16
    bh = SCREEN_HEIGHT / num_bands
    for band in range(num_bands):
        ratio = band / max(num_bands - 1, 1)
        if ratio < 0.5:
            t = ratio * 2
            c = tuple(int(_lerp(colors[0][i], colors[1][i], t)) for i in range(3))
        else:
            t = (ratio - 0.5) * 2
            c = tuple(int(_lerp(colors[1][i], colors[2][i], t)) for i in range(3))
        bs = pygame.Surface((SCREEN_WIDTH, int(bh) + 2))
        bs.fill(c)
        surf.blit(bs, (0, int(band * bh)))

    # White brightness overlay (slight luminosity boost)
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((255, 255, 255, 18))
    surf.blit(ov, (0, 0))

    # --- Grid panel ---
    panel = pygame.Rect(GRID_OFFSET_X - 12, GRID_OFFSET_Y - 12,
                        GRID_COLS * CELL_SIZE + 24, GRID_ROWS * CELL_SIZE + 24)

    # Panel drop shadow
    shad = pygame.Surface((panel.w + 16, panel.h + 16), pygame.SRCALPHA)
    pygame.draw.rect(shad, (0, 0, 60, 90), shad.get_rect(), border_radius=34)
    surf.blit(shad, (panel.x + 8, panel.y + 10))

    # Panel fill (deep dark purple keeps candy visible)
    pygame.draw.rect(surf, (14, 7, 42), panel, border_radius=28)

    # Golden outer border
    pygame.draw.rect(surf, (220, 170, 80), panel, width=5, border_radius=28)
    # Light-gold inner border
    pygame.draw.rect(surf, (255, 235, 140), panel.inflate(-10, -10), width=2, border_radius=24)

    # --- Candy cells (checkerboard, dark for contrast) ---
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            x = GRID_OFFSET_X + c * CELL_SIZE
            y = GRID_OFFSET_Y + r * CELL_SIZE
            cell = pygame.Rect(x + 4, y + 4, CELL_SIZE - 8, CELL_SIZE - 8)
            shade = (26, 12, 58) if (r + c) % 2 == 0 else (40, 20, 75)
            pygame.draw.rect(surf, shade, cell, border_radius=14)
            pygame.draw.rect(surf, (68, 42, 128), cell, width=2, border_radius=14)
            glow_shade = tuple(min(255, int(s * 1.7)) for s in shade)
            pygame.draw.rect(surf, glow_shade, cell.inflate(-6, -6), width=1, border_radius=10)

    # --- Corner gem decorations (4 corners of panel) ---
    gem_half = 14
    corner_pts_list = [
        (panel.left,  panel.top),
        (panel.right, panel.top),
        (panel.left,  panel.bottom),
        (panel.right, panel.bottom),
    ]
    for gcx, gcy in corner_pts_list:
        gs = pygame.Surface((gem_half*2+6, gem_half*2+6), pygame.SRCALPHA)
        dp = [(gem_half+3, 3), (gem_half*2+3, gem_half+3),
              (gem_half+3, gem_half*2+3), (3, gem_half+3)]
        pygame.draw.polygon(gs, (255, 215, 80, 230), dp)
        pygame.draw.polygon(gs, (255, 250, 180, 180), dp, 2)
        # Inner highlight
        inner_dp = [(_lerp(gem_half+3, dp[i][0], 0.5), _lerp(gem_half+3, dp[i][1], 0.5)) for i in range(4)]
        pygame.draw.polygon(gs, (255, 255, 220, 120), inner_dp)
        surf.blit(gs, (gcx - gem_half - 3, gcy - gem_half - 3))

    _cached_bg_surface = surf

    # --- Static sparkles (stars + circles outside panel) ---
    sp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    extended = panel.inflate(50, 50)
    random.seed(42)
    for _ in range(90):
        sx = random.randint(8, SCREEN_WIDTH - 8)
        sy = random.randint(8, SCREEN_HEIGHT - 8)
        if extended.collidepoint(sx, sy):
            continue
        size = random.randint(2, 7)
        alpha = random.randint(130, 220)
        use_star = random.random() > 0.45
        if use_star:
            _draw_star_shape(sp_surf, (255, 255, 220), sx, sy, size, alpha=alpha)
        else:
            pygame.draw.circle(sp_surf, (255, 255, 240, alpha), (sx, sy), size)
    random.seed()
    _cached_bg_sparkles = sp_surf


def draw_grid_background(surface: pygame.Surface) -> None:
    """Blit cached background + static sparkles."""
    global _cached_bg_surface, _cached_bg_sparkles
    if _cached_bg_surface is None:
        _generate_bg_once()
    surface.blit(_cached_bg_surface, (0, 0))
    surface.blit(_cached_bg_sparkles, (0, 0))


def draw_candy(
    surface: pygame.Surface,
    candy_type: str,
    cx: float, cy: float,
    scale: float = 1.0,
    alpha: int = 255,
    special_type: str = NORMAL,
) -> None:
    size = int(CELL_SIZE * 0.85 * scale)
    if size < 4:
        return

    is_bomb = (special_type == COLOR_BOMB)
    color   = (40, 40, 60) if is_bomb else CANDY_COLORS.get(candy_type, (200, 200, 200))
    glow_c  = (150, 150, 255) if is_bomb else CANDY_GLOW_COLORS.get(candy_type, (200, 200, 200))

    pts = _get_gem_points(candy_type, size)

    # --- Glow ring on main surface (BLEND_RGBA_ADD for luminous feel) ---
    tick = pygame.time.get_ticks()
    glow_pulse = (math.sin(tick * 0.003) + 1) * 0.5
    if special_type != NORMAL:
        g_alpha = int(70 + 130 * glow_pulse)
        g_extra = int(7 + 12 * glow_pulse)
    else:
        g_alpha = int(18 + 35 * glow_pulse)
        g_extra = 5
    g_size = size + g_extra
    ratio  = g_size / max(size, 1)
    gp     = [(p[0]*ratio + 4, p[1]*ratio + 4) for p in pts]
    glow_surf = pygame.Surface((g_size + 8, g_size + 8), pygame.SRCALPHA)
    if len(gp) >= 3:
        pygame.draw.polygon(glow_surf, (*glow_c[:3], g_alpha),
                            [(int(x), int(y)) for x, y in gp])
    surface.blit(glow_surf,
                 (int(cx - g_size//2 - 4), int(cy - g_size//2 - 4)),
                 special_flags=pygame.BLEND_RGBA_ADD)

    # --- Temp surface for candy body ---
    temp = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)

    # 1. Drop shadow
    shadow_pts = [(p[0]+2, p[1]+4) for p in pts]
    pygame.draw.polygon(temp, (0, 0, 0, 100), shadow_pts)

    # 2. Main body
    pygame.draw.polygon(temp, (*color[:3], alpha), pts)

    # 3. Inner gradient highlight (lighter center polygon)
    inner_pts = [((p[0] - size/2)*0.65 + size/2,
                  (p[1] - size/2)*0.65 + size/2) for p in pts]
    light_color = tuple(min(255, c + 75) for c in color[:3])
    pygame.draw.polygon(temp, (*light_color, int(alpha*0.55)),
                        [(int(x), int(y)) for x, y in inner_pts])

    # 4. Crisp white outline
    pygame.draw.polygon(temp, (255, 255, 255, int(alpha*0.38)), pts, 2)

    # 5. Shine streak (bright ellipse at upper-left of gem)
    shine_w = max(3, size // 3)
    shine_h = max(2, size // 5)
    shine_surf = pygame.Surface((shine_w, shine_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shine_surf, (255, 255, 255, int(alpha * 0.70)),
                        shine_surf.get_rect())
    rotated = pygame.transform.rotate(shine_surf, -30)
    sx_off = max(0, size // 5)
    sy_off = max(0, size // 7)
    temp.blit(rotated, (sx_off, sy_off))

    # 6. Special overlay
    if special_type != NORMAL:
        _draw_special_overlay(temp, special_type, size)

    surface.blit(temp, (int(cx - size//2), int(cy - size//2)))


def draw_hostage(surface: pygame.Surface, cx: float, cy: float, t: float = 0.0) -> None:
    """Draws a cute, animated character icon that needs rescuing."""
    size = int(CELL_SIZE * 0.8)
    s = pygame.Surface((size + 20, size + 20), pygame.SRCALPHA)
    sc_x, sc_y = (size + 20) // 2, (size + 20) // 2
    
    # Breathing/Bouncing animation
    bounce = math.sin(t * 5.0) * 3
    squash = math.cos(t * 5.0) * 0.05
    
    # 1. Soft Glow Aura
    glow_pulse = (math.sin(t * 3.0) + 1) * 0.5
    glow_r = int(size * 0.45 + 5 * glow_pulse)
    pygame.draw.circle(s, (0, 255, 255, int(40 + 30 * glow_pulse)), (sc_x, sc_y + 5), glow_r)

    # 2. Body (Rounded "Bean" shape)
    body_w = int(size * 0.5 * (1.0 + squash))
    body_h = int(size * 0.65 * (1.0 - squash))
    body_rect = pygame.Rect(sc_x - body_w // 2, sc_y - body_h // 2 + int(bounce), body_w, body_h)
    
    # Body Colors (Cyan gradient look)
    pygame.draw.ellipse(s, (0, 180, 220), body_rect) # Main
    pygame.draw.ellipse(s, (100, 240, 255), body_rect.inflate(-6, -10)) # Highlight center
    pygame.draw.ellipse(s, (255, 255, 255, 150), body_rect.inflate(-body_w*0.6, -body_h*0.7).move(0, -body_h*0.1)) # Shine

    # 3. Eyes (Blinking animation)
    eye_blink = 0 if (int(t * 2) % 5 == 0 and (t * 2) % 5 < 0.2) else 1
    eye_y = sc_y - body_h * 0.15 + bounce
    for side in [-1, 1]:
        eye_x = sc_x + side * (body_w * 0.2)
        if eye_blink > 0:
            pygame.draw.circle(s, (255, 255, 255), (int(eye_x), int(eye_y)), 5)
            pygame.draw.circle(s, (0, 0, 0), (int(eye_x), int(eye_y)), 2)
        else:
            pygame.draw.line(s, (0, 0, 0), (int(eye_x - 4), int(eye_y)), (int(eye_x + 4), int(eye_y)), 2)

    # 4. SOS Bubble
    bubble_pulse = math.sin(t * 4.0 + 1.5) * 2
    bx, by = sc_x + body_w * 0.5, sc_y - body_h * 0.6 + bubble_pulse
    pygame.draw.ellipse(s, (255, 255, 255), (bx - 18, by - 10, 36, 20))
    pygame.draw.polygon(s, (255, 255, 255), [(bx - 5, by + 8), (bx - 12, by + 15), (bx, by + 8)])
    
    # SOS Text
    try:
        font = pygame.font.SysFont("Arial", 12, bold=True)
    except:
        font = pygame.font.Font(None, 18)
    sos_text = font.render("SOS", True, (255, 50, 50))
    s.blit(sos_text, (bx - sos_text.get_width() // 2, by - sos_text.get_height() // 2))

    surface.blit(s, (int(cx - sc_x), int(cy - sc_y)))


def draw_cage_overlay(surface: pygame.Surface, cx: float, cy: float, hp: int) -> None:
    """Draws a metallic cage overlay. hp=2: solid, hp=1: broken/cracked."""
    size = int(CELL_SIZE * 0.9)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = s.get_rect()
    
    metal_dark = (60, 60, 70)
    metal_mid = (110, 115, 130)
    metal_light = (190, 195, 210)
    gold = (210, 170, 50)
    
    if hp == 2:
        # 1. Outer Frame
        pygame.draw.rect(s, metal_dark, rect, width=6, border_radius=12)
        pygame.draw.rect(s, metal_mid, rect.inflate(-4, -4), width=2, border_radius=10)
        
        # 2. Vertical Bars (Cylindrical look)
        bar_x_positions = [size * 0.25, size * 0.5, size * 0.75]
        for x in bar_x_positions:
            # Bar Shadow/Depth
            pygame.draw.line(s, metal_dark, (x-2, 5), (x-2, size-5), 5)
            pygame.draw.line(s, metal_mid, (x, 5), (x, size-5), 3)
            pygame.draw.line(s, metal_light, (x+1, 8), (x+1, size-8), 1)
            
        # 3. Horizontal Crossbars
        for y in [size * 0.3, size * 0.7]:
            pygame.draw.rect(s, metal_dark, (5, y-3, size-10, 6))
            pygame.draw.line(s, metal_light, (8, y-1), (size-8, y-1), 1)

        # 4. Padlock in Center
        lock_rect = pygame.Rect(size//2 - 10, size//2 - 8, 20, 16)
        # Lock Shackle
        pygame.draw.arc(s, metal_light, (size//2 - 7, size//2 - 15, 14, 14), 0, math.pi, 3)
        # Lock Body
        pygame.draw.rect(s, gold, lock_rect, border_radius=3)
        pygame.draw.circle(s, (40, 40, 40), (size//2, size//2), 3) # Keyhole
        
    elif hp == 1:
        # Cracked / Broken State
        # Faint Frame
        pygame.draw.rect(s, (80, 80, 90, 150), rect, width=4, border_radius=12)
        
        # Broken Bars
        # Left bar partially broken
        pygame.draw.line(s, metal_mid, (size*0.25, 5), (size*0.25, size*0.4), 3)
        pygame.draw.line(s, metal_mid, (size*0.25, size*0.7), (size*0.25, size-5), 3)
        
        # Middle bar skewed/cracked
        pygame.draw.line(s, metal_mid, (size*0.5, 5), (size*0.55, size-5), 3)
        
        # Right bar gone or just bits
        pygame.draw.line(s, metal_mid, (size*0.75, size*0.6), (size*0.75, size-10), 3)

        # Jagged Crack Overlays
        crack_color = (200, 200, 255, 180)
        pts = [(size*0.1, size*0.5), (size*0.3, size*0.45), (size*0.5, size*0.55), (size*0.9, size*0.4)]
        pygame.draw.lines(s, crack_color, False, pts, 2)
        
        # Broken Padlock (hanging)
        pygame.draw.rect(s, (150, 120, 40), (size//2 - 8, size//2 + 5, 18, 14), border_radius=3)
        pygame.draw.line(s, metal_mid, (size//2 - 5, size//2 - 5), (size//2 - 10, size//2 + 5), 2)

    surface.blit(s, (int(cx - size // 2), int(cy - size // 2)))



def draw_selection(surface: pygame.Surface, row: int, col: int, t: float = 0.0) -> None:
    x = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
    y = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
    pulse = 1.0 + 0.12 * math.sin(t * 8.0)

    # Outer glow rings
    for i in range(3):
        sz = int(CELL_SIZE * pulse) + i * 5
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        col_alpha = 200 - i * 55
        pygame.draw.rect(s, (255, 255, 140, col_alpha), s.get_rect(),
                         width=3, border_radius=14)
        surface.blit(s, (x - sz//2, y - sz//2))

    # Corner bracket accents
    br = int(CELL_SIZE * 0.52 * pulse)
    arm = 12
    bracket_color = (255, 255, 80, 230)
    bc_surf = pygame.Surface((br*2, br*2), pygame.SRCALPHA)
    # Top-left
    pygame.draw.line(bc_surf, bracket_color, (0, arm), (0, 0), 3)
    pygame.draw.line(bc_surf, bracket_color, (0, 0), (arm, 0), 3)
    # Top-right
    pygame.draw.line(bc_surf, bracket_color, (br*2-arm, 0), (br*2, 0), 3)
    pygame.draw.line(bc_surf, bracket_color, (br*2, 0), (br*2, arm), 3)
    # Bottom-left
    pygame.draw.line(bc_surf, bracket_color, (0, br*2-arm), (0, br*2), 3)
    pygame.draw.line(bc_surf, bracket_color, (0, br*2), (arm, br*2), 3)
    # Bottom-right
    pygame.draw.line(bc_surf, bracket_color, (br*2-arm, br*2), (br*2, br*2), 3)
    pygame.draw.line(bc_surf, bracket_color, (br*2, br*2-arm), (br*2, br*2), 3)
    surface.blit(bc_surf, (x - br, y - br))


def draw_hint(surface: pygame.Surface, hint, t: float) -> None:
    if hint is None:
        return
    pulse = (math.sin(t * 5.0) + 1) * 0.5
    for row, col in hint:
        x = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
        y = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
        sz = int(CELL_SIZE * (0.88 + 0.14 * pulse))
        alph = int(120 + 135 * pulse)
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(s, (255, 255, 80, alph), s.get_rect(), width=4, border_radius=14)
        surface.blit(s, (x - sz//2, y - sz//2))


# Pre-compute sparkle positions for animated twinkle (seed=99)
_TWINKLE_SPARKLES = None


def _ensure_twinkle_sparkles():
    global _TWINKLE_SPARKLES
    if _TWINKLE_SPARKLES is not None:
        return
    panel = pygame.Rect(GRID_OFFSET_X - 12, GRID_OFFSET_Y - 12,
                        GRID_COLS * CELL_SIZE + 24, GRID_ROWS * CELL_SIZE + 24)
    ext = panel.inflate(50, 50)
    random.seed(99)
    _TWINKLE_SPARKLES = []
    for _ in range(35):
        sx = random.randint(8, SCREEN_WIDTH - 8)
        sy = random.randint(8, SCREEN_HEIGHT - 8)
        if ext.collidepoint(sx, sy):
            continue
        _TWINKLE_SPARKLES.append({
            'x': sx, 'y': sy,
            'size': random.randint(2, 5),
            'phase': random.uniform(0, math.pi * 2),
            'speed': random.uniform(2.5, 6.0),
            'star': random.random() > 0.5,
        })
    random.seed()


def draw_board(
    surface: pygame.Surface,
    board,
    anim_manager=None,
    selected=None,
    t: float = 0.0,
    hint=None,
    shake_offset: tuple = (0, 0),
) -> None:
    """Draw the complete board: background → animated sparkles → candies → UI."""
    _ensure_twinkle_sparkles()

    # Apply screen-shake offset via a sub-surface blit
    ox, oy = int(shake_offset[0]), int(shake_offset[1])

    # 1. Background
    draw_grid_background(surface)

    # 2. Animated twinkling sparkles
    sp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for sp in _TWINKLE_SPARKLES:
        alpha = int(100 + 120 * (0.5 + 0.5 * math.sin(t * sp['speed'] + sp['phase'])))
        alpha = max(0, min(255, alpha))
        draw_x = sp['x'] + ox
        draw_y = sp['y'] + oy
        if sp['star']:
            _draw_star_shape(sp_surf, (255, 255, 200), draw_x, draw_y, sp['size'], alpha=alpha)
        else:
            pygame.draw.circle(sp_surf, (255, 255, 230, alpha), (draw_x, draw_y), sp['size'])
    surface.blit(sp_surf, (0, 0))

    # 3. Draw candies
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            cx = GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE // 2 + ox
            cy = GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE // 2 + oy
            override = anim_manager.get_override(r, c) if anim_manager else None
            if override:
                cx, cy, sc, al = override
                cx += ox; cy += oy
            else:
                sc, al = 1.0, 255
            candy = board.get_candy(r, c)
            if candy:
                draw_candy(surface, candy.candy_type, cx, cy, sc, al, candy.special_type)

    # 3b. Cage overlays (drawn on top of candy)
    if hasattr(board, 'cages'):
        for (r, c), hp in board.cages.items():
            cx = GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE // 2 + ox
            cy = GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE // 2 + oy
            draw_cage_overlay(surface, cx, cy, hp)

    # 3c. Hostage icons (drawn on top of candy)
    if hasattr(board, 'hostages'):
        for (r, c) in board.hostages:
            cx = GRID_OFFSET_X + c * CELL_SIZE + CELL_SIZE // 2 + ox
            cy = GRID_OFFSET_Y + r * CELL_SIZE + CELL_SIZE // 2 + oy
            draw_hostage(surface, cx, cy, t=t)

    # 4. Selection indicator
    if selected is not None:
        draw_selection(surface, selected[0], selected[1], t=t)

    # 5. Hint overlay
    if hint is not None:
        draw_hint(surface, hint, t)
