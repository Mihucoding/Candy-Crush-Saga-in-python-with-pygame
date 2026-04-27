from constants import SCORE_PER_CANDY, COMBO_MULTIPLIER


class ScoreTracker:

    def __init__(self):
        self.score: int = 0
        self.combo: int = 0
        self.high_score: int = 0

    def add_match(self, group_size: int) -> int:
        self.combo += 1
        multiplier = COMBO_MULTIPLIER ** (self.combo - 1)
        points = int(SCORE_PER_CANDY * group_size * multiplier)
        self.score += points
        if self.score > self.high_score:
            self.high_score = self.score
        return points

    def reset_combo(self) -> None:
        self.combo = 0

    def reset(self) -> None:
        self.reset_combo()
        self.score = 0 