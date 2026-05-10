from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union
import random


@dataclass
class ScoreGoal:
    target: int
    type: str = "score"


@dataclass
class CollectGoal:
    color: str
    count: int
    type: str = "collect"


@dataclass
class RescueGoal:
    count: int
    type: str = "rescue"


@dataclass
class CageGoal:
    type: str = "cage"


@dataclass
class LevelConfig:
    level: int
    moves: int
    goal: Union[ScoreGoal, CollectGoal, RescueGoal, CageGoal]
    hostage_positions: list = field(default_factory=list)   # [(row, col), ...]
    cage_positions: list = field(default_factory=list)      # [(row, col, hp), ...]


LEVELS: list[LevelConfig] = [
    LevelConfig(level=1, moves=30, goal=ScoreGoal(target=4000)),
    LevelConfig(level=2, moves=25, goal=CollectGoal(
        color=random.choice(["red", "orange", "green", "purple", "blue"]), count=20)),
    LevelConfig(level=3, moves=28,
        goal=RescueGoal(count=3),
        hostage_positions=[(0, 2), (0, 4), (0, 6)]),
    LevelConfig(level=4, moves=25,
        goal=CageGoal(),
        cage_positions=[
            (3, 3, 2), (3, 4, 1), (3, 5, 2),
            (4, 3, 1), (4, 4, 2), (4, 5, 1),
        ]),
]


def get_level(n: int) -> LevelConfig:
    idx = (n - 1) % len(LEVELS)
    return LEVELS[idx]
