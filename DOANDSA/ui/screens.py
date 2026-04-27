import math
import random
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, CANDY_TYPES, CANDY_COLORS, BG_COLOR, TEXT_COLOR


def _get_font(size: int, bold: bool = True) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("Arial Rounded MT Bold", size, bold=bold)
    except Exception:
        return pygame.font.SysFont("Arial", size, bold=bold)


def draw_gradient_bg(surface: pygame.Surface, t: float = 0.0) -> None:
    top    = (20 + int(10 * math.sin(t * 0.3)),  8,  50)
    bottom = (10,  5, int(60 + 20 * math.sin(t * 0.2 + 1)))
    for y in range(SCREEN_HEIGHT):
        ratio = y / SCREEN_HEIGHT
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))


def _pill_button(surface, text, rect, hovered=False):
    base  = (100, 60, 180) if not hovered else (140, 90, 220)
    glow  = (160, 110, 255) if hovered else (120, 80, 200)
    font  = _get_font(26)
    pygame.draw.rect(surface, base, rect, border_radius=rect.height // 2)
    pygame.draw.rect(surface, glow, rect, width=3, border_radius=rect.height // 2)
    lbl = font.render(text, True, TEXT_COLOR)
    surface.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                        rect.centery - lbl.get_height() // 2))


# ---------------------------------------------------------------------------
# Floating candy particles (menu background)
# ---------------------------------------------------------------------------

class _Particle:
    def __init__(self):
        self.reset(spawn=True)

    def reset(self, spawn=False):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT) if spawn else -30
        self.vy = random.uniform(40, 100)
        self.vx = random.uniform(-20, 20)
        self.ctype = random.choice(CANDY_TYPES)
        self.scale = random.uniform(0.4, 0.8)
        self.alpha = random.randint(120, 200)
        self.rot = 0.0
        self.rot_speed = random.uniform(-60, 60)

    def update(self, dt):
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.rot += self.rot_speed * dt
        if self.y > SCREEN_HEIGHT + 40:
            self.reset()


# ---------------------------------------------------------------------------
# Menu Screen
# ---------------------------------------------------------------------------

class MenuScreen:
    def __init__(self):
        self.particles = [_Particle() for _ in range(18)]
        self.t = 0.0
        self.buttons = {
            "play":   pygame.Rect(SCREEN_WIDTH // 2 - 100, 370, 200, 52),
            "quit":   pygame.Rect(SCREEN_WIDTH // 2 - 100, 440, 200, 52),
        }

    def update(self, dt: float) -> None:
        self.t += dt
        for p in self.particles:
            p.update(dt)

    def draw(self, surface: pygame.Surface, mouse_pos: tuple) -> None:
        draw_gradient_bg(surface, self.t)

        # Particles
        from ui.renderer import draw_candy
        for p in self.particles:
            draw_candy(surface, p.ctype, p.x, p.y, scale=p.scale, alpha=p.alpha)

        # Title
        title_font = _get_font(52)
        title = "CANDY CRUSH"
        colors = list(CANDY_COLORS.values())
        x = SCREEN_WIDTH // 2 - title_font.size(title)[0] // 2
        for i, ch in enumerate(title):
            color_idx = (i + int(self.t * 3)) % len(colors)
            ch_surf = title_font.render(ch, True, colors[color_idx])
            surface.blit(ch_surf, (x, 200))
            x += title_font.size(ch)[0]

        sub_font = _get_font(20, bold=False)
        sub = sub_font.render("DSA Edition", True, (180, 160, 220))
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 262))

        for key, rect in self.buttons.items():
            _pill_button(surface, key.upper(), rect, hovered=rect.collidepoint(mouse_pos))

    def handle_click(self, pos: tuple) -> str | None:
        for key, rect in self.buttons.items():
            if rect.collidepoint(pos):
                return key
        return None


# ---------------------------------------------------------------------------
# Game Over Screen
# ---------------------------------------------------------------------------

class GameOverScreen:
    def __init__(self, final_score: int):
        self.final_score = final_score
        self.t = 0.0
        self.retry_btn = pygame.Rect(SCREEN_WIDTH // 2 - 110, 420, 100, 48)
        self.menu_btn  = pygame.Rect(SCREEN_WIDTH // 2 + 10,  420, 100, 48)

    def update(self, dt: float) -> None:
        self.t += dt

    def draw(self, surface: pygame.Surface, mouse_pos: tuple) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 190))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 160, 200, 320, 280)
        pygame.draw.rect(surface, (25, 15, 50), panel, border_radius=20)
        pygame.draw.rect(surface, (100, 60, 180), panel, width=3, border_radius=20)

        title_font = _get_font(40)
        score_font = _get_font(32)
        lbl_font   = _get_font(18, bold=False)

        t_surf = title_font.render("GAME OVER", True, (255, 80, 80))
        surface.blit(t_surf, (panel.centerx - t_surf.get_width() // 2, panel.y + 20))

        lbl = lbl_font.render("Final Score", True, (160, 140, 200))
        surface.blit(lbl, (panel.centerx - lbl.get_width() // 2, panel.y + 90))

        sc = score_font.render(str(self.final_score), True, (255, 220, 80))
        surface.blit(sc, (panel.centerx - sc.get_width() // 2, panel.y + 115))

        _pill_button(surface, "RETRY", self.retry_btn, self.retry_btn.collidepoint(mouse_pos))
        _pill_button(surface, "MENU",  self.menu_btn,  self.menu_btn.collidepoint(mouse_pos))

    def handle_click(self, pos: tuple) -> str | None:
        if self.retry_btn.collidepoint(pos):
            return "retry"
        if self.menu_btn.collidepoint(pos):
            return "menu"
        return None


# ---------------------------------------------------------------------------
# Level Complete Screen
# ---------------------------------------------------------------------------

class LevelCompleteScreen:
    def __init__(self, score: int, stars: int = 2):
        self.score = score
        self.stars = min(max(stars, 0), 3)
        self.t = 0.0
        self.confetti = [
            {
                "x": random.randint(0, SCREEN_WIDTH),
                "y": random.uniform(-200, 0),
                "vy": random.uniform(120, 260),
                "vx": random.uniform(-30, 30),
                "color": random.choice(list(CANDY_COLORS.values())),
                "w": random.randint(6, 14),
                "h": random.randint(4, 8),
            }
            for _ in range(60)
        ]
        self.next_btn = pygame.Rect(SCREEN_WIDTH // 2 - 100, 450, 200, 52)
        self.score_display = 0.0

    def update(self, dt: float) -> None:
        self.t += dt
        self.score_display = min(self.score_display + self.score * dt * 2, self.score)
        for c in self.confetti:
            c["y"] += c["vy"] * dt
            c["x"] += c["vx"] * dt
            if c["y"] > SCREEN_HEIGHT + 20:
                c["y"] = random.uniform(-60, -10)
                c["x"] = random.randint(0, SCREEN_WIDTH)

    def draw(self, surface: pygame.Surface, mouse_pos: tuple) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 180))
        surface.blit(overlay, (0, 0))

        for c in self.confetti:
            pygame.draw.rect(surface, c["color"],
                             (int(c["x"]), int(c["y"]), c["w"], c["h"]))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 170, 170, 340, 300)
        pygame.draw.rect(surface, (25, 15, 50), panel, border_radius=20)
        pygame.draw.rect(surface, (255, 200, 50), panel, width=3, border_radius=20)

        title_font = _get_font(38)
        t_surf = title_font.render("LEVEL COMPLETE!", True, (255, 220, 80))
        surface.blit(t_surf, (panel.centerx - t_surf.get_width() // 2, panel.y + 18))

        # Stars
        star_font = _get_font(36)
        star_x = panel.centerx - 60
        for i in range(3):
            pop = max(0.0, min(1.0, (self.t - i * 0.25) / 0.2))
            scale = 0.5 + 0.5 * pop
            color = (255, 210, 30) if i < self.stars else (60, 50, 80)
            star = star_font.render("★", True, color)
            s = pygame.transform.scale(
                star, (int(star.get_width() * scale), int(star.get_height() * scale))
            )
            surface.blit(s, (star_x + i * 44 - s.get_width() // 2, panel.y + 78))

        lbl_font = _get_font(18, bold=False)
        lbl = lbl_font.render("Score", True, (160, 140, 200))
        surface.blit(lbl, (panel.centerx - lbl.get_width() // 2, panel.y + 140))

        sc_font = _get_font(34)
        sc = sc_font.render(str(int(self.score_display)), True, TEXT_COLOR)
        surface.blit(sc, (panel.centerx - sc.get_width() // 2, panel.y + 162))

        _pill_button(surface, "NEXT LEVEL", self.next_btn, self.next_btn.collidepoint(mouse_pos))

    def handle_click(self, pos: tuple) -> str | None:
        if self.next_btn.collidepoint(pos):
            return "next"
        return None
