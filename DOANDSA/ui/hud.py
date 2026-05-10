import math
import pygame
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR, HUD_BG_COLOR,
    FONT_LARGE, FONT_MEDIUM, FONT_SMALL,
    TARGET_SCORE, CANDY_COLORS,
    ACCENT_GOLD,
)


class HUD:
    def __init__(self):
        self._score_display = 0.0
        self._fonts: dict = {}
        self._combo_t    = 0.0
        self._last_combo = 0
        self._combo_particles: list = []

    # ------------------------------------------------------------------ fonts
    def _get_font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            try:
                self._fonts[size] = pygame.font.SysFont("Arial Rounded MT Bold", size, bold=True)
            except Exception:
                self._fonts[size] = pygame.font.SysFont("Arial", size, bold=True)
        return self._fonts[size]

    # ------------------------------------------------------------------ update
    def update(self, dt: float, target_score: int, combo: int = 0) -> None:
        diff = target_score - self._score_display
        self._score_display += diff * min(dt * 8, 1.0)

        if combo != self._last_combo:
            self._combo_t    = 0.0
            self._last_combo = combo
            # Spawn combo burst particles when combo rises
            if combo > 1:
                import random
                cx = SCREEN_WIDTH // 2
                for _ in range(12):
                    ang = random.uniform(0, 2 * math.pi)
                    spd = random.uniform(60, 160)
                    colors = list(CANDY_COLORS.values())
                    self._combo_particles.append({
                        'x': cx, 'y': 170,
                        'vx': math.cos(ang)*spd, 'vy': math.sin(ang)*spd,
                        'life': 1.0, 'size': random.randint(3, 6),
                        'color': random.choice(colors),
                    })
        if combo > 1:
            self._combo_t += dt

        # Update combo particles
        still = []
        for p in self._combo_particles:
            p['x']  += p['vx'] * dt
            p['y']  += p['vy'] * dt
            p['vy'] += 180 * dt
            p['life'] -= dt * 1.6
            if p['life'] > 0:
                still.append(p)
        self._combo_particles = still

    # ------------------------------------------------------------------ draw
    def draw(
        self, surface: pygame.Surface,
        score: int, moves_left: int,
        level: int = 1, combo: int = 0, t: float = 0.0,
        level_cfg=None, scorer=None, board=None,
    ) -> None:
        self._draw_hud_background(surface, t)
        self._draw_level(surface, level)
        self._draw_score(surface, score, t)
        self._draw_moves(surface, moves_left, t)
        self._draw_goal(surface, score, level_cfg, scorer, board)
        if combo > 1:
            self._draw_combo(surface, combo)
        self._draw_combo_particles(surface)

    # ------------------------------------------------------------------ background
    def _draw_hud_background(self, surface: pygame.Surface, t: float) -> None:
        # Glass panel — semi-transparent layered look
        panel = pygame.Rect(0, 0, SCREEN_WIDTH, 132)
        bg_surf = pygame.Surface((SCREEN_WIDTH, 132), pygame.SRCALPHA)
        bg_surf.fill((10, 5, 30, 195))
        surface.blit(bg_surf, (0, 0))

        # Animated shimmer line across the bottom of HUD
        shimmer_x = int((t * 200) % (SCREEN_WIDTH + 60)) - 30
        sh = pygame.Surface((60, 2), pygame.SRCALPHA)
        for i in range(60):
            a = int(180 * math.sin(math.pi * i / 60))
            pygame.draw.line(sh, (255, 230, 100, a), (i, 0), (i, 1))
        surface.blit(sh, (shimmer_x, 130))

        # Gradient bottom border line
        for x in range(0, SCREEN_WIDTH, 2):
            ratio = x / SCREEN_WIDTH
            r = int(255 * ratio)
            g = int(100 + 100 * math.sin(ratio * math.pi))
            b = int(255 * (1 - ratio))
            pygame.draw.line(surface, (r, g, b), (x, 131), (x+2, 131))

    # ------------------------------------------------------------------ level
    def _draw_level(self, surface: pygame.Surface, level: int) -> None:
        font_s = self._get_font(FONT_SMALL)
        font_m = self._get_font(FONT_MEDIUM)

        pill = pygame.Rect(10, 8, 86, 54)
        # Draw gradient on SRCALPHA surface, then mask to rounded rect
        pill_surf = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
        for i in range(pill.h):
            ratio = i / pill.h
            c = (int(50 - 10*ratio), int(30 - 10*ratio), int(90 + 20*ratio), 255)
            pygame.draw.line(pill_surf, c, (0, i), (pill.w, i))
        mask = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=14)
        pill_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(pill_surf, (pill.x, pill.y))
        pygame.draw.rect(surface, (255, 215, 80), pill, width=2, border_radius=14)

        lbl = font_s.render("LEVEL", True, (255, 220, 130))
        val = font_m.render(str(level), True, TEXT_COLOR)
        surface.blit(lbl, (pill.centerx - lbl.get_width()//2, pill.y + 4))
        surface.blit(val, (pill.centerx - val.get_width()//2, pill.y + 22))

    # ------------------------------------------------------------------ score
    def _draw_score(self, surface: pygame.Surface, score: int, t: float) -> None:
        font_s = self._get_font(FONT_SMALL)
        font_l = self._get_font(FONT_LARGE)

        cx = SCREEN_WIDTH // 2
        lbl = font_s.render("SCORE", True, (200, 180, 255))
        surface.blit(lbl, (cx - lbl.get_width()//2, 8))

        # Gold text with drop shadow
        num_str = str(int(self._score_display))
        shadow = font_l.render(num_str, True, (80, 50, 0))
        val    = font_l.render(num_str, True, ACCENT_GOLD)
        surface.blit(shadow, (cx - shadow.get_width()//2 + 2, 28 + 2))
        surface.blit(val,    (cx - val.get_width()//2,        28))

    # ------------------------------------------------------------------ goal (score or collect or rescue or cage)
    def _draw_goal(self, surface: pygame.Surface, score: int, level_cfg, scorer, board=None) -> None:
        from game.level_config import CollectGoal, ScoreGoal, RescueGoal, CageGoal
        if level_cfg is None:
            self._draw_progress_bar(surface, score, TARGET_SCORE)
            return
        goal = level_cfg.goal
        if isinstance(goal, ScoreGoal):
            self._draw_progress_bar(surface, score, goal.target)
        elif isinstance(goal, CollectGoal):
            collected = scorer.collected.get(goal.color, 0) if scorer else 0
            self.draw_goal_strip(surface, {goal.color: goal.count}, {goal.color: collected})
        elif isinstance(goal, RescueGoal):
            rescued = board.rescued_count if board else 0
            self._draw_counter_goal(surface, rescued, goal.count, label="RESCUE", color=(100, 200, 255))
        elif isinstance(goal, CageGoal):
            cages_left = len(board.cages) if board else 0
            self._draw_counter_goal(surface, cages_left, 0, label="CAGES LEFT", color=(200, 150, 60), invert=True)

    def _draw_progress_bar(self, surface: pygame.Surface, score: int, target: int = TARGET_SCORE) -> None:
        bar_rect = pygame.Rect(SCREEN_WIDTH//2 - 140, 100, 280, 14)
        progress  = min(1.0, score / max(target, 1))

        # Track
        track_s = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(track_s, (255, 255, 255, 40), track_s.get_rect(), border_radius=7)
        surface.blit(track_s, bar_rect.topleft)

        # Fill gradient: cyan → gold → red
        if progress > 0:
            fill_w = max(4, int(bar_rect.w * progress))
            fill_s = pygame.Surface((fill_w, bar_rect.h), pygame.SRCALPHA)
            for x in range(fill_w):
                ratio = x / max(fill_w - 1, 1)
                if ratio < 0.5:
                    c = (int(_lerp(80, 255, ratio*2)),
                         int(_lerp(220, 220, ratio*2)),
                         int(_lerp(255, 50, ratio*2)),
                         220)
                else:
                    c = (255, int(_lerp(220, 80, (ratio-0.5)*2)), 50, 220)
                pygame.draw.line(fill_s, c, (x, 0), (x, bar_rect.h - 1))
            mask = pygame.Surface((fill_w, bar_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=7)
            fill_s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(fill_s, bar_rect.topleft)

        # Border
        pygame.draw.rect(surface, (255, 255, 255, 80),
                         bar_rect, width=1, border_radius=7)

        # Star goal icon at end
        if progress >= 1.0:
            sf = self._get_font(16)
            done = sf.render("★ GOAL!", True, (255, 215, 80))
            surface.blit(done, (bar_rect.right + 6, bar_rect.centery - done.get_height()//2))

    # ------------------------------------------------------------------ moves
    def _draw_moves(self, surface: pygame.Surface, moves_left: int, t: float) -> None:
        font_s = self._get_font(FONT_SMALL)
        font_m = self._get_font(FONT_MEDIUM)

        low = moves_left <= 5
        color = (255, 80, 80) if low else TEXT_COLOR

        pill = pygame.Rect(SCREEN_WIDTH - 96, 8, 86, 54)
        # Draw gradient on SRCALPHA surface, mask to rounded rect
        pill_surf = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
        for i in range(pill.h):
            ratio = i / pill.h
            c = (int(50 - 10*ratio), int(30 - 10*ratio), int(90 + 20*ratio), 255)
            pygame.draw.line(pill_surf, c, (0, i), (pill.w, i))
        mask = pygame.Surface((pill.w, pill.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=14)
        pill_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(pill_surf, (pill.x, pill.y))

        if low:
            pulse = (math.sin(t * 6) + 1) * 0.5
            border_c = (int(180 + 75*pulse), int(20 + 20*pulse), int(20 + 20*pulse))
            pygame.draw.rect(surface, border_c, pill, width=2, border_radius=14)
        else:
            pygame.draw.rect(surface, (255, 215, 80), pill, width=2, border_radius=14)

        lbl = font_s.render("MOVES", True, (200, 180, 255))
        val = font_m.render(str(moves_left), True, color)
        surface.blit(lbl, (pill.centerx - lbl.get_width()//2, pill.y + 4))
        surface.blit(val, (pill.centerx - val.get_width()//2, pill.y + 22))

    # ------------------------------------------------------------------ combo
    def _draw_combo(self, surface: pygame.Surface, combo: int) -> None:
        base_size = min(FONT_SMALL + (combo - 2) * 6, 56)
        pop = 1.0 + 0.4 * math.exp(-6 * self._combo_t) * abs(math.sin(self._combo_t * 15))
        draw_size = max(20, int(base_size * pop))
        font = self._get_font(draw_size)

        if combo >= 5:
            hue = (pygame.time.get_ticks() // 3) % 360
            c = pygame.Color(0)
            c.hsva = (hue, 90, 100, 100)
            color = (c.r, c.g, c.b)
        elif combo == 4:
            color = (255, 80, 80)
        elif combo == 3:
            color = (255, 150, 40)
        else:
            color = (255, 220, 50)

        text_surf = font.render(f"x{combo}  COMBO!", True, color)
        tw, th = text_surf.get_size()
        cx = SCREEN_WIDTH // 2
        pill_w, pill_h = tw + 36, th + 16
        pill_y = 134

        pulse = (math.sin(self._combo_t * 7) + 1) * 0.5
        pill_surf = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pygame.draw.rect(pill_surf, (*color, int(35 + 25*pulse)),
                         pill_surf.get_rect(), border_radius=pill_h // 2)
        pygame.draw.rect(pill_surf, (*color, int(170 + 85*pulse)),
                         pill_surf.get_rect(), width=2, border_radius=pill_h // 2)
        surface.blit(pill_surf, (cx - pill_w//2, pill_y))
        surface.blit(text_surf, (cx - tw//2, pill_y + 8))

    # ------------------------------------------------------------------ particles
    def _draw_combo_particles(self, surface: pygame.Surface) -> None:
        if not self._combo_particles:
            return
        p_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for p in self._combo_particles:
            a = int(255 * max(0, p['life']))
            pygame.draw.circle(p_surf, (*p['color'][:3], a),
                               (int(p['x']), int(p['y'])), p['size'])
        surface.blit(p_surf, (0, 0))

    # ------------------------------------------------------------------ counter goal (rescue / cage)
    def _draw_counter_goal(
        self, surface: pygame.Surface,
        current: int, target: int,
        label: str, color: tuple, invert: bool = False,
    ) -> None:
        """
        invert=False (rescue): progress = current/target, done when current >= target
        invert=True  (cage):   shows count remaining, done when current == 0
        """
        font_s = self._get_font(FONT_SMALL)
        bar_y  = 100
        bar_rect = pygame.Rect(SCREEN_WIDTH // 2 - 140, bar_y, 280, 14)

        if invert:
            text = f"{label}: {current}"
            done = current == 0
            progress = 0.0  # no bar for invert mode
        else:
            text = f"{label}  {current}/{target}"
            done = current >= target
            progress = min(1.0, current / max(target, 1))

        # Label
        lbl_color = (80, 240, 80) if done else color
        lbl = font_s.render(text, True, lbl_color)
        surface.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, bar_y - 18))

        if not invert:
            # Track
            track_s = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
            pygame.draw.rect(track_s, (255, 255, 255, 40), track_s.get_rect(), border_radius=7)
            surface.blit(track_s, bar_rect.topleft)

            if progress > 0:
                fill_w = max(4, int(bar_rect.w * progress))
                fill_s = pygame.Surface((fill_w, bar_rect.h), pygame.SRCALPHA)
                for x in range(fill_w):
                    ratio = x / max(fill_w - 1, 1)
                    r = int(_lerp(color[0] * 0.4, color[0], ratio))
                    g = int(_lerp(color[1] * 0.4, color[1], ratio))
                    b = int(_lerp(color[2] * 0.4, color[2], ratio))
                    pygame.draw.line(fill_s, (r, g, b, 210), (x, 0), (x, bar_rect.h - 1))
                mask = pygame.Surface((fill_w, bar_rect.h), pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=7)
                fill_s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(fill_s, bar_rect.topleft)

            pygame.draw.rect(surface, (255, 255, 255, 80), bar_rect, width=1, border_radius=7)

        if done:
            sf = self._get_font(16)
            done_lbl = sf.render("★ DONE!", True, (255, 215, 80))
            surface.blit(done_lbl, (bar_rect.right + 6, bar_y - done_lbl.get_height() // 2))

    # ------------------------------------------------------------------ goal strip
    def draw_goal_strip(self, surface: pygame.Surface, goals: dict, progress: dict) -> None:
        font = self._get_font(FONT_SMALL)
        strip_y = 72
        total = len(goals)
        if total == 0:
            return
        item_w = 70
        start_x = SCREEN_WIDTH // 2 - (total * item_w) // 2
        for i, (ctype, target) in enumerate(goals.items()):
            cleared = progress.get(ctype, 0)
            done = cleared >= target
            x = start_x + i * item_w + item_w // 2
            color = (80, 200, 80) if done else (180, 160, 220)
            count_text = font.render(f"{min(cleared, target)}/{target}", True, color)
            surface.blit(count_text, (x - count_text.get_width()//2, strip_y + 14))
            from ui.renderer import draw_candy
            draw_candy(surface, ctype, x, strip_y + 8, scale=0.55, alpha=220)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
