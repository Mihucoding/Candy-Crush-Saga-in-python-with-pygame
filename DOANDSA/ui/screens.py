import math, random
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, CANDY_TYPES, CANDY_COLORS, BG_COLOR, TEXT_COLOR, ACCENT_GOLD


def _get_font(size, bold=True):
    try:    return pygame.font.SysFont("Arial Rounded MT Bold", size, bold=bold)
    except: return pygame.font.SysFont("Arial", size, bold=bold)


_LILITA_CACHE: dict = {}

def _get_pixel_font(size):
    """Lilita One font with fallback to Fixedsys/bitmap."""
    if size in _LILITA_CACHE:
        return _LILITA_CACHE[size]
    import os
    ttf = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "LilitaOne.ttf")
    ttf = os.path.normpath(ttf)
    try:
        f = pygame.font.Font(ttf, size)
        _LILITA_CACHE[size] = f
        return f
    except Exception:
        pass
    for name in ("Fixedsys", "Lucida Console", "Courier New"):
        try:
            return pygame.font.SysFont(name, size, bold=False)
        except Exception:
            pass
    return pygame.font.Font(None, size)


def _render_3d(font, text, color, depth=5, shadow_col=None):
    """Render text with layered 3D extrusion effect."""
    if shadow_col is None:
        shadow_col = tuple(max(0, c - 110) for c in color)
    base = font.render(text, True, color)
    w, h = base.get_size()
    surf = pygame.Surface((w + depth, h + depth), pygame.SRCALPHA)
    for i in range(depth, 0, -1):
        layer = font.render(text, True,
                            tuple(int(shadow_col[j] + (color[j] - shadow_col[j]) * (1 - i / depth))
                                  for j in range(3)))
        surf.blit(layer, (i, i))
    surf.blit(base, (0, 0))
    return surf


def _render_arcade_title(font, text, top_color, bot_color, depth=10,
                         extrude_color=(70, 20, 80), outline_color=(30, 10, 50)):
    """Arcade-style 3D extruded title with vertical gradient face.

    Why: replicates the chunky ARCADE-poster look (gradient face + dark side
    extrusion + outline) while staying readable on the bright pastel BG.
    """
    base = font.render(text, True, (255, 255, 255))
    w, h = base.get_size()
    pad = depth + 4
    canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    cx, cy = pad, pad

    # 1) Extrusion layers (down-right diagonal) — darker shade
    for i in range(depth, 0, -1):
        t = i / depth
        col = (int(extrude_color[0] * (0.55 + 0.45 * t)),
               int(extrude_color[1] * (0.55 + 0.45 * t)),
               int(extrude_color[2] * (0.55 + 0.45 * t)))
        layer = font.render(text, True, col)
        canvas.blit(layer, (cx + i, cy + i))

    # 2) Outline (chunky black border) — render text in outline color at 8 offsets
    outline_w = 3
    for dx in range(-outline_w, outline_w + 1):
        for dy in range(-outline_w, outline_w + 1):
            if dx == 0 and dy == 0:
                continue
            if dx * dx + dy * dy > outline_w * outline_w + 1:
                continue
            canvas.blit(font.render(text, True, outline_color), (cx + dx, cy + dy))

    # 3) Front face: vertical gradient mask
    face = font.render(text, True, (255, 255, 255))
    fw, fh = face.get_size()
    grad = pygame.Surface((fw, fh), pygame.SRCALPHA)
    for y in range(fh):
        r = y / max(fh - 1, 1)
        col = (int(_lerp(top_color[0], bot_color[0], r)),
               int(_lerp(top_color[1], bot_color[1], r)),
               int(_lerp(top_color[2], bot_color[2], r)), 255)
        pygame.draw.line(grad, col, (0, y), (fw, y))
    grad.blit(face, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    canvas.blit(grad, (cx, cy))

    # 4) Top highlight band — sharper top edge to suggest light source
    hl = pygame.Surface((fw, fh), pygame.SRCALPHA)
    for y in range(max(1, fh // 4)):
        a = int(180 * (1 - y / (fh / 4)))
        pygame.draw.line(hl, (255, 255, 255, a), (0, y), (fw, y))
    hl.blit(face, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    canvas.blit(hl, (cx, cy))
    return canvas


# --- Pixel-art button -------------------------------------------------------
_BTN_PALETTE = {
    # base, top-highlight, bottom-shadow, border (dark), glow
    "green":  ((100, 200,  90), (170, 240, 150), ( 50, 140,  60), ( 30,  80,  40), ( 80, 255, 140)),
    "coral":  ((230, 110, 120), (255, 175, 185), (170,  60,  80), ( 90,  25,  40), (255, 130, 160)),
    "orange": ((255, 165,  70), (255, 215, 130), (200, 100,  30), (110,  50,  10), (255, 200, 100)),
    "yellow": ((255, 215,  70), (255, 240, 150), (210, 160,  20), (110,  80,   5), (255, 240, 120)),
    "blue":   (( 90, 175, 240), (160, 220, 255), ( 40, 110, 190), ( 15,  55, 100), (120, 210, 255)),
}

# Which palette each button label uses
_BTN_COLOR_BY_KEY = {
    "play": "green", "next": "green", "next level": "green", "resume": "green",
    "retry": "orange",
    "quit": "coral", "menu": "coral", "back": "coral",
}


def _pixel_button(surface, text, rect, hovered=False, color="coral"):
    """Pixel-art button: chamfered corners, top highlight, bottom shadow, dark border.

    Why: matches the user's chosen 8-bit retro arcade style. Hover brightens
    the base and adds a soft halo glow.
    """
    base, top_hl, bot_sh, border, glow = _BTN_PALETTE.get(color, _BTN_PALETTE["coral"])
    if hovered:
        base   = tuple(min(255, int(c * 1.18)) for c in base)
        top_hl = tuple(min(255, int(c * 1.10)) for c in top_hl)

    # Soft halo glow on hover
    if hovered:
        halo_pad = 14
        halo = pygame.Surface((rect.w + halo_pad * 2, rect.h + halo_pad * 2), pygame.SRCALPHA)
        for i in range(halo_pad, 0, -2):
            a = int(70 * (1 - i / halo_pad))
            pygame.draw.rect(halo, (*glow, a),
                             halo.get_rect().inflate(-i*2 + halo_pad*2 - rect.w*0, -i*2 + halo_pad*2 - rect.h*0),
                             border_radius=8)
        # Simpler: just draw expanding translucent rects
        halo = pygame.Surface((rect.w + halo_pad * 2, rect.h + halo_pad * 2), pygame.SRCALPHA)
        for i in range(halo_pad, 0, -2):
            a = int(60 * (1 - i / halo_pad))
            r = pygame.Rect(halo_pad - i, halo_pad - i, rect.w + 2*i, rect.h + 2*i)
            pygame.draw.rect(halo, (*glow, a), r, border_radius=6)
        surface.blit(halo, (rect.x - halo_pad, rect.y - halo_pad))

    # Chamfered corner mask (pixel-art rounded look): cut 2px from each corner
    CHAMFER = 3
    body = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    # 1) Border (full chamfered rect filled with dark border color)
    pygame.draw.rect(body, border, (CHAMFER, 0, rect.w - 2*CHAMFER, rect.h))
    pygame.draw.rect(body, border, (0, CHAMFER, rect.w, rect.h - 2*CHAMFER))
    # corner pixels (1px chamfer ladder)
    for k in range(1, CHAMFER):
        pygame.draw.rect(body, border, (CHAMFER - k, k, rect.w - 2*(CHAMFER - k), 1))
        pygame.draw.rect(body, border, (CHAMFER - k, rect.h - k - 1, rect.w - 2*(CHAMFER - k), 1))

    BORDER_W = 3
    # 2) Inner base fill (inset by border width)
    inner = pygame.Rect(BORDER_W, BORDER_W, rect.w - 2*BORDER_W, rect.h - 2*BORDER_W)
    pygame.draw.rect(body, base, inner)
    # Slightly clip inner top/bottom corners for chamfer continuity
    pygame.draw.rect(body, base, (BORDER_W + 1, BORDER_W - 1, inner.w - 2, 1))
    pygame.draw.rect(body, base, (BORDER_W + 1, rect.h - BORDER_W, inner.w - 2, 1))

    # 3) Top highlight band (2px)
    pygame.draw.rect(body, top_hl, (inner.x + 1, inner.y, inner.w - 2, 2))
    pygame.draw.rect(body, top_hl, (inner.x, inner.y + 1, 2, 1))
    pygame.draw.rect(body, top_hl, (inner.right - 2, inner.y + 1, 2, 1))

    # 4) Bottom shadow band (2px)
    pygame.draw.rect(body, bot_sh, (inner.x + 1, inner.bottom - 2, inner.w - 2, 2))

    surface.blit(body, rect.topleft)

    # 5) Label — Lilita One, white with subtle dark shadow
    font = _get_pixel_font(max(20, int(rect.h * 0.45)))
    label_surf = font.render(text, True, (255, 255, 255))
    shadow_surf = font.render(text, True, border)
    tx = rect.centerx - label_surf.get_width() // 2
    ty = rect.centery - label_surf.get_height() // 2 - 2
    surface.blit(shadow_surf, (tx + 2, ty + 2))
    surface.blit(label_surf,  (tx, ty))


def _btn(surface, text, rect, hovered, color_key=None):
    """Convenience wrapper: pick palette from text if color_key not given."""
    key = (color_key or _BTN_COLOR_BY_KEY.get(text.lower().strip(), "coral"))
    _pixel_button(surface, text, rect, hovered=hovered, color=key)


def _lerp(a, b, t): return a + (b - a) * t


def draw_gradient_bg(surface, t=0.0):
    colors = [(130, 200, 255), (200, 140, 255), (255, 220, 150)]
    num = 12; bh = SCREEN_HEIGHT / num
    for band in range(num):
        ratio = band / max(num-1, 1)
        shift = math.sin(t * 0.25 + ratio * math.pi) * 0.08
        ratio2 = max(0, min(1, ratio + shift))
        if ratio2 < 0.5:
            c = tuple(int(_lerp(colors[0][i], colors[1][i], ratio2*2)) for i in range(3))
        else:
            c = tuple(int(_lerp(colors[1][i], colors[2][i], (ratio2-0.5)*2)) for i in range(3))
        pygame.draw.rect(surface, c, (0, int(band*bh), SCREEN_WIDTH, int(bh)+2))


def _pill_button(surface, text, rect, hovered=False):
    # Draw gradient on a SRCALPHA temp surface, then clip to rounded rect
    pill_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    for i in range(rect.h):
        ratio = i / rect.h
        if hovered:
            c = (int(_lerp(160,120,ratio)), int(_lerp(100,60,ratio)), int(_lerp(240,180,ratio)), 255)
        else:
            c = (int(_lerp(100,70,ratio)), int(_lerp(60,35,ratio)), int(_lerp(190,130,ratio)), 255)
        pygame.draw.line(pill_surf, c, (0, i), (rect.w, i))
    # Mask: only keep pixels inside the rounded rect
    mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=rect.h // 2)
    pill_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(pill_surf, rect.topleft)

    border = (255, 220, 80) if hovered else (180, 120, 255)
    pygame.draw.rect(surface, border, rect, width=3, border_radius=rect.h // 2)

    # Shimmer sweep on hover
    if hovered:
        sw = 30
        shimmer_x = int((pygame.time.get_ticks() * 0.3) % (rect.w + sw)) - sw
        sh = pygame.Surface((sw, rect.h), pygame.SRCALPHA)
        for xi in range(sw):
            a = int(120 * math.sin(math.pi * xi / sw))
            pygame.draw.line(sh, (255, 255, 255, a), (xi, 0), (xi, rect.h - 1))
        surface.blit(sh, (rect.x + shimmer_x, rect.y))
        # Redraw border on top of shimmer
        pygame.draw.rect(surface, border, rect, width=3, border_radius=rect.h // 2)

    lbl = _get_font(26).render(text, True, (255, 255, 255))
    surface.blit(lbl, (rect.centerx - lbl.get_width()//2, rect.centery - lbl.get_height()//2))



class _Particle:
    def __init__(self):  self.reset(spawn=True)
    def reset(self, spawn=False):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT) if spawn else -40
        self.vy = random.uniform(40, 110); self.vx = random.uniform(-25, 25)
        self.ctype = random.choice(CANDY_TYPES); self.scale = random.uniform(0.35, 0.75)
        self.alpha = random.randint(110, 190); self.rot = 0.0
        self.rot_speed = random.uniform(-70, 70)
    def update(self, dt):
        self.y += self.vy*dt; self.x += self.vx*dt; self.rot += self.rot_speed*dt
        if self.y > SCREEN_HEIGHT + 50: self.reset()


class _Firework:
    def __init__(self):
        self.x = random.randint(100, SCREEN_WIDTH-100)
        self.y = random.uniform(SCREEN_HEIGHT*0.15, SCREEN_HEIGHT*0.55)
        self.particles = []
        self.timer = random.uniform(0, 1.5)
        self.exploded = False

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0 and not self.exploded:
            self.exploded = True
            hue = random.randint(0, 360)
            for i in range(30):
                ang = random.uniform(0, 2*math.pi)
                spd = random.uniform(80, 240)
                c = pygame.Color(0); c.hsva = ((hue + i*5) % 360, 90, 100, 100)
                self.particles.append({'x': self.x, 'y': self.y,
                    'vx': math.cos(ang)*spd, 'vy': math.sin(ang)*spd,
                    'life': 1.0, 'color': (c.r, c.g, c.b)})
        for p in self.particles:
            p['x'] += p['vx']*dt; p['y'] += p['vy']*dt
            p['vy'] += 120*dt; p['life'] -= dt * 1.4
        self.particles = [p for p in self.particles if p['life'] > 0]

    def draw(self, surface):
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for p in self.particles:
            a = int(255 * max(0, p['life'])); r = max(1, int(5 * p['life']))
            pygame.draw.circle(s, (*p['color'], a), (int(p['x']), int(p['y'])), r)
        surface.blit(s, (0,0))

    @property
    def done(self): return self.exploded and not self.particles


# ---------------------------------------------------------------------------
class MenuScreen:
    def __init__(self):
        self.particles = [_Particle() for _ in range(22)]
        self.t = 0.0
        self.buttons = {
            "play": pygame.Rect(SCREEN_WIDTH//2 - 130, 430, 260, 68),
            "quit": pygame.Rect(SCREEN_WIDTH//2 - 130, 520, 260, 68),
        }

    def update(self, dt):
        self.t += dt
        for p in self.particles: p.update(dt)

    def draw(self, surface, mouse_pos):
        draw_gradient_bg(surface, self.t)
        from ui.renderer import draw_candy
        for p in self.particles:
            draw_candy(surface, p.ctype, p.x, p.y, scale=p.scale, alpha=p.alpha)

        # Decorative rings behind title
        for i in range(3):
            r = 180 + i*60; a = int(30 - i*8)
            pulse = abs(math.sin(self.t*0.7 + i*1.2))
            r2 = r + int(15 * pulse)
            ring_s = pygame.Surface((r2*2, r2*2), pygame.SRCALPHA)
            pygame.draw.circle(ring_s, (255,255,255,a), (r2,r2), r2, 3)
            surface.blit(ring_s, (SCREEN_WIDTH//2 - r2, 300 - r2))

        # Arcade-style 3D extruded title — pink→orange→yellow gradient
        bob = int(6 * math.sin(self.t * 2.0))
        title_font = _get_pixel_font(96)
        title_surf = _render_arcade_title(
            title_font, "CANDY CRUSH",
            top_color=(255, 110, 180), bot_color=(255, 215,  80),
            depth=12, extrude_color=(110,  30, 130), outline_color=(40, 10, 60),
        )
        surface.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 130 + bob))

        # Subtitle
        sub = _get_font(22, bold=False).render("DSA EDITION", True, (90, 30, 110))
        sub.set_alpha(int(200 + 55 * math.sin(self.t * 2)))
        surface.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 290 + bob))

        for key, rect in self.buttons.items():
            _btn(surface, key.upper(), rect, hovered=rect.collidepoint(mouse_pos))

    def handle_click(self, pos):
        for key, rect in self.buttons.items():
            if rect.collidepoint(pos): return key
        return None


# ---------------------------------------------------------------------------
class GameOverScreen:
    def __init__(self, final_score):
        self.final_score = final_score; self.t = 0.0
        self.retry_btn = pygame.Rect(SCREEN_WIDTH//2 - 130, 430, 120, 58)
        self.menu_btn  = pygame.Rect(SCREEN_WIDTH//2 + 10,  430, 120, 58)
        # Falling dark drizzle particles
        self.drizzle = [{'x': random.randint(0, SCREEN_WIDTH),
                          'y': random.uniform(-SCREEN_HEIGHT, 0),
                          'vy': random.uniform(80, 180),
                          'alpha': random.randint(40, 120),
                          'size': random.randint(2, 5)} for _ in range(60)]

    def update(self, dt):
        self.t += dt
        for d in self.drizzle:
            d['y'] += d['vy'] * dt
            if d['y'] > SCREEN_HEIGHT + 10:
                d['y'] = random.uniform(-40, -5)
                d['x'] = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface, mouse_pos):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((8, 4, 20, 195)); surface.blit(ov, (0,0))

        # Drizzle
        dr = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for d in self.drizzle:
            pygame.draw.circle(dr, (120, 60, 160, d['alpha']),
                               (int(d['x']), int(d['y'])), d['size'])
        surface.blit(dr, (0,0))

        panel = pygame.Rect(SCREEN_WIDTH//2 - 170, 195, 340, 260)
        # Panel glow
        glow_s = pygame.Surface((panel.w+30, panel.h+30), pygame.SRCALPHA)
        pygame.draw.rect(glow_s, (180,40,40,40), glow_s.get_rect(), border_radius=26)
        surface.blit(glow_s, (panel.x-15, panel.y-15))
        pygame.draw.rect(surface, (22, 10, 45), panel, border_radius=22)
        pygame.draw.rect(surface, (200, 50, 50), panel, width=3, border_radius=22)

        # "GAME OVER" — arcade 3D, red→pink, with subtle flicker
        flicker = 1.0 + 0.04 * math.sin(self.t * 14)
        tf = _get_pixel_font(int(60 * flicker))
        title = _render_arcade_title(
            tf, "GAME OVER",
            top_color=(255, 200, 200), bot_color=(220,  40,  60),
            depth=9, extrude_color=(110,  10,  20), outline_color=(40, 5, 10),
        )
        surface.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 10))

        # Stars (0 since game over) — polygon to avoid missing glyph
        for i in range(3):
            pop = max(0.0, min(1.0, (self.t - i*0.3) / 0.25))
            outer_r = int(22 * pop)
            if outer_r < 2:
                continue
            inner_r = max(1, int(outer_r * 0.42))
            star_cx = panel.centerx - 44 + i * 44
            star_cy = panel.y + 104
            pts = []
            for k in range(10):
                angle = math.pi * k / 5 - math.pi / 2
                r = outer_r if k % 2 == 0 else inner_r
                pts.append((int(star_cx + r * math.cos(angle)),
                             int(star_cy + r * math.sin(angle))))
            pygame.draw.polygon(surface, (50, 40, 70), pts)

        lbl = _get_font(18, bold=False).render("Final Score", True, (160, 140, 200))
        surface.blit(lbl, (panel.centerx - lbl.get_width()//2, panel.y + 138))
        sc = _get_font(36).render(str(self.final_score), True, ACCENT_GOLD)
        surface.blit(sc, (panel.centerx - sc.get_width()//2, panel.y + 160))

        _btn(surface, "RETRY", self.retry_btn, self.retry_btn.collidepoint(mouse_pos))
        _btn(surface, "MENU",  self.menu_btn,  self.menu_btn.collidepoint(mouse_pos))

    def handle_click(self, pos):
        if self.retry_btn.collidepoint(pos): return "retry"
        if self.menu_btn.collidepoint(pos):  return "menu"
        return None


# ---------------------------------------------------------------------------
class LevelCompleteScreen:
    def __init__(self, score, stars=2):
        self.score = score; self.stars = min(max(stars, 0), 3); self.t = 0.0
        self.confetti = [{'x': random.randint(0, SCREEN_WIDTH),
                          'y': random.uniform(-200, 0),
                          'vy': random.uniform(130, 270), 'vx': random.uniform(-35, 35),
                          'color': random.choice(list(CANDY_COLORS.values())),
                          'w': random.randint(6, 14), 'h': random.randint(4, 8),
                          'rot': random.uniform(0, 360),
                          'rot_speed': random.uniform(-120, 120)} for _ in range(70)]
        self.fireworks = [_Firework() for _ in range(6)]
        self.next_btn = pygame.Rect(SCREEN_WIDTH//2 - 110, 462, 220, 56)
        self.score_display = 0.0

    def update(self, dt):
        self.t += dt
        self.score_display = min(self.score_display + self.score * dt * 2, self.score)
        for c in self.confetti:
            c['y'] += c['vy']*dt; c['x'] += c['vx']*dt; c['rot'] += c['rot_speed']*dt
            if c['y'] > SCREEN_HEIGHT + 20:
                c['y'] = random.uniform(-60, -5); c['x'] = random.randint(0, SCREEN_WIDTH)
        for fw in self.fireworks: fw.update(dt)
        self.fireworks = [fw for fw in self.fireworks if not fw.done]
        if len(self.fireworks) < 4:
            self.fireworks.append(_Firework())

    def draw(self, surface, mouse_pos):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((8, 4, 20, 175)); surface.blit(ov, (0,0))

        # Fireworks
        for fw in self.fireworks: fw.draw(surface)

        # Confetti with rotation
        for c in self.confetti:
            cs = pygame.Surface((c['w'], c['h']), pygame.SRCALPHA)
            cs.fill((*c['color'][:3], 210))
            rot = pygame.transform.rotate(cs, c['rot'])
            surface.blit(rot, (int(c['x']), int(c['y'])))

        panel = pygame.Rect(SCREEN_WIDTH//2 - 185, 155, 370, 380)
        glow_s = pygame.Surface((panel.w+30, panel.h+30), pygame.SRCALPHA)
        pygame.draw.rect(glow_s, (255,220,50,35), glow_s.get_rect(), border_radius=28)
        surface.blit(glow_s, (panel.x-15, panel.y-15))
        pygame.draw.rect(surface, (18, 10, 45), panel, border_radius=24)
        pygame.draw.rect(surface, (255, 210, 50), panel, width=3, border_radius=24)

        # Arcade 3D title — gold/orange gradient, victory feel
        tf = _get_pixel_font(54)
        title_surf = _render_arcade_title(
            tf, "LEVEL COMPLETE!",
            top_color=(255, 240, 120), bot_color=(255, 140,  40),
            depth=8, extrude_color=(140,  50,  10), outline_color=(50, 15, 5),
        )
        surface.blit(title_surf,
                     (panel.centerx - title_surf.get_width() // 2, panel.y + 10))

        # Stars with glow — drawn as polygons (font lacks ★ glyph)
        for i in range(3):
            pop = max(0.0, min(1.0, (self.t - i*0.28) / 0.22))
            outer_r = int(28 * pop)
            if outer_r < 2:
                continue
            inner_r = max(1, int(outer_r * 0.42))
            col = (255, 210, 30) if i < self.stars else (55, 45, 80)
            star_cx = panel.centerx + (i - 1) * 74
            star_cy = panel.y + 112
            if i < self.stars and pop > 0.4:
                gring = pygame.Surface((80, 80), pygame.SRCALPHA)
                pygame.draw.circle(gring, (255, 220, 50, int(130 * pop)), (40, 40), 36)
                surface.blit(gring, (star_cx - 40, star_cy - 40))
            pts = []
            for k in range(10):
                angle = math.pi * k / 5 - math.pi / 2
                r = outer_r if k % 2 == 0 else inner_r
                pts.append((int(star_cx + r * math.cos(angle)),
                             int(star_cy + r * math.sin(angle))))
            pygame.draw.polygon(surface, col, pts)

        lbl = _get_font(18, bold=False).render("Score", True, (160, 140, 200))
        surface.blit(lbl, (panel.centerx - lbl.get_width()//2, panel.y + 152))
        sc_surf = _get_font(38).render(str(int(self.score_display)), True, ACCENT_GOLD)
        surface.blit(sc_surf, (panel.centerx - sc_surf.get_width()//2, panel.y + 174))

        _btn(surface, "NEXT LEVEL", self.next_btn, self.next_btn.collidepoint(mouse_pos))

    def handle_click(self, pos):
        if self.next_btn.collidepoint(pos): return "next"
        return None


# ---------------------------------------------------------------------------
class _Slider:
    def __init__(self, cx, y, w, value):
        self._track = pygame.Rect(cx - w//2, y, w, 10)
        self.value  = max(0.0, min(1.0, value)); self._dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._track.inflate(0, 32).collidepoint(event.pos):
                self._dragging = True; self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP: self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging: self._set_from_x(event.pos[0])

    def _set_from_x(self, mx):
        self.value = max(0.0, min(1.0, (mx - self._track.x) / self._track.w))

    def draw(self, surface, color, label, font):
        lbl = font.render(label, True, (180, 160, 220))
        surface.blit(lbl, (self._track.x, self._track.y - 24))
        pct = font.render(f"{int(self.value*100)}%", True, (210, 200, 240))
        surface.blit(pct, (self._track.right - pct.get_width(), self._track.y - 24))
        # Track
        pygame.draw.rect(surface, (40, 30, 70), self._track, border_radius=5)
        fw = max(0, int(self._track.w * self.value))
        if fw:
            fill_s = pygame.Surface((fw, self._track.h), pygame.SRCALPHA)
            for xi in range(fw):
                t = xi / max(fw-1, 1)
                c = (int(_lerp(color[0]*0.6, color[0], t)),
                     int(_lerp(color[1]*0.6, color[1], t)),
                     int(_lerp(color[2]*0.6, color[2], t)), 220)
                pygame.draw.line(fill_s, c, (xi, 0), (xi, self._track.h-1))
            surface.blit(fill_s, (self._track.x, self._track.y))
        hx = self._track.x + int(self._track.w * self.value)
        pygame.draw.circle(surface, (230, 220, 255), (hx, self._track.centery), 12)
        pygame.draw.circle(surface, color, (hx, self._track.centery), 9)


class PauseScreen:
    def __init__(self, music_vol=0.5, sfx_vol=1.0):
        cx = SCREEN_WIDTH//2
        self._music_slider = _Slider(cx, 370, 280, music_vol)
        self._sfx_slider   = _Slider(cx, 430, 280, sfx_vol)
        self.resume_btn = pygame.Rect(cx - 120, 478, 220, 52)
        self.menu_btn   = pygame.Rect(cx - 120, 540, 220, 52)
        self.t = 0.0

    @property
    def music_vol(self): return self._music_slider.value
    @property
    def sfx_vol(self):   return self._sfx_slider.value

    def update(self, dt): self.t += dt

    def handle_event(self, event):
        self._music_slider.handle_event(event)
        self._sfx_slider.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.resume_btn.collidepoint(event.pos): return "resume"
            if self.menu_btn.collidepoint(event.pos):   return "menu"
        return None

    def draw(self, surface, mouse_pos):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((4, 0, 18, 210)); surface.blit(ov, (0,0))

        panel = pygame.Rect(SCREEN_WIDTH//2 - 185, 228, 370, 400)
        glow_s = pygame.Surface((panel.w+24, panel.h+24), pygame.SRCALPHA)
        pygame.draw.rect(glow_s, (120,80,200,50), glow_s.get_rect(), border_radius=28)
        surface.blit(glow_s, (panel.x-12, panel.y-12))
        pygame.draw.rect(surface, (18, 10, 42), panel, border_radius=24)
        pygame.draw.rect(surface, (140, 90, 220), panel, width=3, border_radius=24)

        # Arcade 3D title — purple/violet gradient
        tf = _get_pixel_font(64)
        title = _render_arcade_title(
            tf, "PAUSED",
            top_color=(220, 180, 255), bot_color=(150,  70, 230),
            depth=9, extrude_color=( 70,  20, 110), outline_color=(25, 5, 45),
        )
        surface.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 12))

        hint = _get_font(16, bold=False).render("Press ESC to resume", True, (120, 110, 160))
        surface.blit(hint, (panel.centerx - hint.get_width()//2, panel.y + 82))

        lf = _get_font(18, bold=False)
        self._music_slider.draw(surface, (100, 180, 255), "MUSIC", lf)
        self._sfx_slider.draw(surface,   (255, 160,  60), "SFX",   lf)

        _btn(surface, "RESUME", self.resume_btn, self.resume_btn.collidepoint(mouse_pos))
        _btn(surface, "MENU",   self.menu_btn,   self.menu_btn.collidepoint(mouse_pos))


# ---------------------------------------------------------------------------
def _draw_star_icon(surface, cx, cy, r, color):
    pts = []
    for i in range(10):
        radius = r if i % 2 == 0 else r * 0.4
        a = math.radians(i * 36 - 90)
        pts.append((int(cx + radius * math.cos(a)), int(cy + radius * math.sin(a))))
    pygame.draw.polygon(surface, color, pts)


class LevelSelectScreen:
    # Màu chủ đề riêng cho từng loại màn
    _THEME = {
        "score":   {"top": (180, 130, 20),  "bg1": (60, 45, 10),  "bg2": (30, 22, 5),   "border": (255, 215, 60)},
        "collect": {"top": (20,  140, 60),  "bg1": (15, 50, 25),  "bg2": (8,  25, 12),  "border": (60,  220, 100)},
        "rescue":  {"top": (20,  130, 180), "bg1": (10, 45, 65),  "bg2": (5,  22, 35),  "border": (80,  210, 255)},
        "cage":    {"top": (160, 90,  20),  "bg1": (55, 30, 8),   "bg2": (28, 15, 4),   "border": (220, 150, 60)},
    }

    def __init__(self):
        self.t = 0.0
        self.particles = [_Particle() for _ in range(18)]

        card_w, card_h = 270, 295
        gap_x, gap_y = 60, 44
        start_x = (SCREEN_WIDTH - card_w * 2 - gap_x) // 2
        start_y = 148

        self.cards = []
        for i in range(4):
            row, col = divmod(i, 2)
            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)
            self.cards.append(pygame.Rect(x, y, card_w, card_h))

        self.back_btn = pygame.Rect(SCREEN_WIDTH // 2 - 110, 884, 220, 54)

    def update(self, dt):
        self.t += dt
        for p in self.particles:
            p.update(dt)

    def handle_click(self, pos):
        if self.back_btn.collidepoint(pos):
            return "menu"
        for i, rect in enumerate(self.cards):
            if rect.collidepoint(pos):
                return i + 1
        return None

    def draw(self, surface, mouse_pos):
        from game.level_config import LEVELS
        from ui.renderer import draw_candy

        draw_gradient_bg(surface, self.t)
        for p in self.particles:
            draw_candy(surface, p.ctype, p.x, p.y, scale=p.scale, alpha=p.alpha)

        # Arcade 3D title — gold/orange gradient
        tf = _get_pixel_font(78)
        title_surf = _render_arcade_title(
            tf, "SELECT LEVEL",
            top_color=(255, 235, 120), bot_color=(255, 145,  40),
            depth=10, extrude_color=(140,  55,  10), outline_color=(45, 15, 5),
        )
        tx = SCREEN_WIDTH // 2 - title_surf.get_width() // 2
        surface.blit(title_surf, (tx, 50))

        uw = title_surf.get_width() + 20
        ux = SCREEN_WIDTH // 2 - uw // 2
        title_bottom = 50 + title_surf.get_height() + 2
        pygame.draw.line(surface, ACCENT_GOLD, (ux, title_bottom), (ux + uw, title_bottom), 2)

        for i, (rect, cfg) in enumerate(zip(self.cards, LEVELS)):
            self._draw_card(surface, rect, cfg, i + 1, rect.collidepoint(mouse_pos))

        _btn(surface, "BACK", self.back_btn,
             self.back_btn.collidepoint(mouse_pos))

    # ------------------------------------------------------------------ card
    def _draw_card(self, surface, rect, cfg, level_num, hovered):
        from game.level_config import ScoreGoal, CollectGoal, RescueGoal, CageGoal

        goal  = cfg.goal
        theme = self._THEME[goal.type]
        pulse = (math.sin(self.t * 3.0 + level_num) + 1) * 0.5

        # --- Nền card ---
        card_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        for y in range(rect.h):
            ratio = y / rect.h
            bg = (int(_lerp(theme["bg1"][0], theme["bg2"][0], ratio)),
                  int(_lerp(theme["bg1"][1], theme["bg2"][1], ratio)),
                  int(_lerp(theme["bg1"][2], theme["bg2"][2], ratio)),
                  235)
            pygame.draw.line(card_surf, bg, (0, y), (rect.w, y))
        mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=20)
        card_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(card_surf, rect.topleft)

        # --- Header band màu ---
        HEADER_H = 46
        hdr = pygame.Surface((rect.w, HEADER_H), pygame.SRCALPHA)
        for y in range(HEADER_H):
            ratio = y / HEADER_H
            c = (int(_lerp(theme["top"][0], theme["bg1"][0], ratio)),
                 int(_lerp(theme["top"][1], theme["bg1"][1], ratio)),
                 int(_lerp(theme["top"][2], theme["bg1"][2], ratio)), 255)
            pygame.draw.line(hdr, c, (0, y), (rect.w, y))
        hdr_mask = pygame.Surface((rect.w, HEADER_H), pygame.SRCALPHA)
        pygame.draw.rect(hdr_mask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, rect.w, HEADER_H), border_radius=20)
        # Chỉ bo góc trên
        pygame.draw.rect(hdr_mask, (255, 255, 255, 255),
                         pygame.Rect(0, HEADER_H // 2, rect.w, HEADER_H // 2))
        hdr.blit(hdr_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(hdr, rect.topleft)

        # --- Viền ---
        bc = theme["border"]
        if hovered:
            alpha_border = int(200 + 55 * pulse)
            g_surf = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
            pygame.draw.rect(g_surf, (*bc, int(50 + 35 * pulse)),
                             g_surf.get_rect(), border_radius=26)
            surface.blit(g_surf, (rect.x - 10, rect.y - 10))
            pygame.draw.rect(surface, bc, rect, width=3, border_radius=20)
        else:
            pygame.draw.rect(surface, tuple(max(0, c - 60) for c in bc),
                             rect, width=2, border_radius=20)

        # --- Level number trong header ---
        lf = _get_pixel_font(30)
        lbl = _render_3d(lf, f"LEVEL {level_num}", (255, 255, 255), depth=3,
                         shadow_col=tuple(max(0, c - 80) for c in theme["top"]))
        surface.blit(lbl, (rect.x + 14, rect.y + (HEADER_H - lbl.get_height()) // 2))

        # --- Icon goal ---
        self._draw_goal_icon(surface, goal, rect.centerx, rect.y + HEADER_H + 68, self.t)

        # --- Đường kẻ phân cách ---
        sep_y = rect.y + HEADER_H + 118
        pygame.draw.line(surface, (*bc, 80),
                         (rect.x + 20, sep_y), (rect.x + rect.w - 20, sep_y), 1)

        # --- Goal description ---
        df = _get_pixel_font(22)
        if isinstance(goal, ScoreGoal):
            desc = f"Reach {goal.target:,} pts"
        elif isinstance(goal, CollectGoal):
            desc = f"Collect 20 {goal.color} candies"
        elif isinstance(goal, RescueGoal):
            desc = f"Rescue {goal.count} hostages"
        elif isinstance(goal, CageGoal):
            desc = "Break all 6 cages"
        else:
            desc = "???"

        ds = _render_3d(df, desc, (220, 210, 240), depth=3, shadow_col=(60, 50, 80))
        surface.blit(ds, (rect.centerx - ds.get_width() // 2, sep_y + 10))

        # --- Moves ---
        mf = _get_pixel_font(20)
        move_color = tuple(min(255, c + 40) for c in bc)
        ms = _render_3d(mf, f"{cfg.moves} moves", move_color, depth=2,
                        shadow_col=tuple(max(0, c - 60) for c in move_color))
        surface.blit(ms, (rect.centerx - ms.get_width() // 2, sep_y + 36))

        # --- Decorative stars ---
        for si in range(3):
            sx = rect.centerx + (si - 1) * 32
            _draw_star_icon(surface, sx, rect.y + rect.h - 28, 12,
                            tuple(c // 3 for c in bc))

    def _draw_goal_icon(self, surface, goal, cx, cy, t=0.0):
        from game.level_config import ScoreGoal, CollectGoal, RescueGoal, CageGoal
        from constants import CANDY_COLORS

        s = pygame.Surface((90, 90), pygame.SRCALPHA)
        bounce = int(math.sin(t * 4.0) * 3)

        if isinstance(goal, ScoreGoal):
            # Ngôi sao vàng lớn với vòng hào quang
            glow_r = 38 + int(4 * (math.sin(t * 3) + 1) * 0.5)
            pygame.draw.circle(s, (255, 210, 50, 40), (45, 45 + bounce), glow_r)
            pts = []
            for i in range(10):
                r = 34 if i % 2 == 0 else 14
                a = math.radians(i * 36 - 90)
                pts.append((45 + r * math.cos(a), 45 + bounce + r * math.sin(a)))
            pygame.draw.polygon(s, (255, 200, 30), pts)
            pygame.draw.polygon(s, (255, 245, 140), pts, 2)
            # Tia sáng
            for i in range(8):
                a = math.radians(i * 45 + t * 30)
                x1 = int(45 + 36 * math.cos(a))
                y1 = int(45 + bounce + 36 * math.sin(a))
                x2 = int(45 + 43 * math.cos(a))
                y2 = int(45 + bounce + 43 * math.sin(a))
                pygame.draw.line(s, (255, 240, 100, 160), (x1, y1), (x2, y2), 2)

        elif isinstance(goal, CollectGoal):
            color = CANDY_COLORS.get(goal.color, (200, 200, 200))
            light = tuple(min(255, c + 70) for c in color)
            # Viên kẹo tròn lớn
            pygame.draw.circle(s, color, (45, 45 + bounce), 30)
            pygame.draw.circle(s, light, (45, 45 + bounce), 30, 3)
            # Highlight
            hl = pygame.Surface((22, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(hl, (255, 255, 255, 140), hl.get_rect())
            s.blit(hl, (26, 28 + bounce))
            # Số lượng cần thu
            nf = _get_font(18)
            ns = nf.render("×20", True, (255, 255, 255))
            s.blit(ns, (45 - ns.get_width() // 2, 45 + bounce - ns.get_height() // 2))

        elif isinstance(goal, RescueGoal):
            # Stick figure + neon ring
            pygame.draw.circle(s, (0, 200, 255, 50), (45, 45), 36)
            pygame.draw.circle(s, (0, 200, 255, 120), (45, 45), 36, 2)
            # Đầu
            pygame.draw.circle(s, (130, 230, 255), (45, 18 + bounce), 13)
            pygame.draw.circle(s, (200, 245, 255), (45, 18 + bounce), 13, 2)
            # Thân
            pygame.draw.line(s, (100, 210, 255), (45, 31 + bounce), (45, 62 + bounce), 5)
            # Tay
            pygame.draw.line(s, (100, 210, 255), (45, 42 + bounce), (28, 54 + bounce), 3)
            pygame.draw.line(s, (100, 210, 255), (45, 42 + bounce), (62, 54 + bounce), 3)
            # Chân
            pygame.draw.line(s, (100, 210, 255), (45, 62 + bounce), (32, 76 + bounce), 3)
            pygame.draw.line(s, (100, 210, 255), (45, 62 + bounce), (58, 76 + bounce), 3)

        elif isinstance(goal, CageGoal):
            # Lồng sắt chi tiết
            pygame.draw.rect(s, (180, 130, 50, 60), (12, 12, 66, 66), border_radius=8)
            pygame.draw.rect(s, (200, 150, 60), (12, 12, 66, 66), 3, border_radius=8)
            for bx in [25, 45, 65]:
                pygame.draw.line(s, (160, 115, 45), (bx, 12), (bx, 78), 3)
                pygame.draw.line(s, (220, 175, 90), (bx + 1, 14), (bx + 1, 30), 1)
            for by in [30, 50, 70]:
                pygame.draw.line(s, (160, 115, 45), (12, by), (78, by), 3)
            # Khóa vàng
            pygame.draw.rect(s, (255, 200, 50), (35, 38, 20, 16), border_radius=3)
            pygame.draw.arc(s, (255, 200, 50),
                            pygame.Rect(38, 28, 14, 16), 0, math.pi, 3)
            pygame.draw.circle(s, (80, 50, 10), (45, 46), 3)

        surface.blit(s, (cx - 45, cy - 45))
