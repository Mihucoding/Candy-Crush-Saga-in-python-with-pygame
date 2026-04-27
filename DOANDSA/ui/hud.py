import pygame
from constants import (
    SCREEN_WIDTH, TEXT_COLOR, HUD_BG_COLOR,
    FONT_LARGE, FONT_MEDIUM, FONT_SMALL,
)


class HUD:
    def __init__(self):
        self._score_display = 0.0
        self._fonts: dict[str, pygame.font.Font] = {}

    def _get_font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            try:
                self._fonts[size] = pygame.font.SysFont("Arial Rounded MT Bold", size, bold=True)
            except Exception:
                self._fonts[size] = pygame.font.SysFont("Arial", size, bold=True)
        return self._fonts[size]

    def update(self, dt: float, target_score: int) -> None:
        diff = target_score - self._score_display
        self._score_display += diff * min(dt * 8, 1.0)

    def draw(self, surface: pygame.Surface, score: int, moves_left: int, level: int = 1, combo: int = 0) -> None:
        # HUD background panel
        panel = pygame.Rect(0, 0, SCREEN_WIDTH, 130)
        pygame.draw.rect(surface, HUD_BG_COLOR, panel)
        pygame.draw.line(surface, (60, 50, 90), (0, 130), (SCREEN_WIDTH, 130), 2)

        self._draw_level(surface, level)
        self._draw_score(surface, score)
        self._draw_moves(surface, moves_left)
        if combo > 1:
            self._draw_combo(surface, combo)

    def _draw_level(self, surface: pygame.Surface, level: int) -> None:
        font_s = self._get_font(FONT_SMALL)
        font_m = self._get_font(FONT_MEDIUM)

        lbl = font_s.render("LEVEL", True, (160, 140, 200))
        val = font_m.render(str(level), True, TEXT_COLOR)

        pill = pygame.Rect(10, 8, 80, 50)
        pygame.draw.rect(surface, (40, 30, 70), pill, border_radius=12)
        pygame.draw.rect(surface, (80, 60, 130), pill, width=2, border_radius=12)

        surface.blit(lbl, (pill.centerx - lbl.get_width() // 2, pill.y + 4))
        surface.blit(val, (pill.centerx - val.get_width() // 2, pill.y + 22))

    def _draw_score(self, surface: pygame.Surface, score: int) -> None:
        font_s = self._get_font(FONT_SMALL)
        font_l = self._get_font(FONT_LARGE)

        lbl = font_s.render("SCORE", True, (160, 140, 200))
        val = font_l.render(str(int(self._score_display)), True, (255, 220, 80))

        cx = SCREEN_WIDTH // 2
        surface.blit(lbl, (cx - lbl.get_width() // 2, 10))
        surface.blit(val, (cx - val.get_width() // 2, 30))

    def _draw_moves(self, surface: pygame.Surface, moves_left: int) -> None:
        font_s = self._get_font(FONT_SMALL)
        font_m = self._get_font(FONT_MEDIUM)

        color = (255, 80, 80) if moves_left <= 5 else TEXT_COLOR

        lbl = font_s.render("MOVES", True, (160, 140, 200))
        val = font_m.render(str(moves_left), True, color)

        pill = pygame.Rect(SCREEN_WIDTH - 90, 8, 80, 50)
        pygame.draw.rect(surface, (40, 30, 70), pill, border_radius=12)
        pygame.draw.rect(surface, (80, 60, 130), pill, width=2, border_radius=12)

        if moves_left <= 5:
            pygame.draw.rect(surface, (180, 40, 40), pill, width=2, border_radius=12)

        surface.blit(lbl, (pill.centerx - lbl.get_width() // 2, pill.y + 4))
        surface.blit(val, (pill.centerx - val.get_width() // 2, pill.y + 22))

    def _draw_combo(self, surface: pygame.Surface, combo: int) -> None:
        font = self._get_font(FONT_SMALL)
        text = font.render(f"COMBO x{combo}!", True, (255, 200, 50))
        cx = SCREEN_WIDTH // 2
        surface.blit(text, (cx - text.get_width() // 2, 88))

    def draw_goal_strip(self, surface: pygame.Surface, goals: dict, progress: dict) -> None:
        """
        goals:    {candy_type: target_count}
        progress: {candy_type: cleared_so_far}
        """
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
            count_text = font.render(f"{min(cleared,target)}/{target}", True, color)
            surface.blit(count_text, (x - count_text.get_width() // 2, strip_y + 14))

            from ui.renderer import draw_candy
            draw_candy(surface, ctype, x, strip_y + 8, scale=0.55, alpha=220)
