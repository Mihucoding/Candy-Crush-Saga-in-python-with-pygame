# Function Map — `game/`

## candy.py

| Name | Type | Signature |
|------|------|-----------|
| `Candy` | class | — |
| `__init__` | method | `(self, candy_type: str = None)` |
| `activate` | method | `(self, row: int, col: int, board, target: "Candy \| None" = None) -> list[tuple]` |
| `combo_with` | method | `(self, other: "Candy", row: int, col: int, board) -> list[tuple]` |
| `__repr__` | method | `(self)` |

---

## board.py

| Name | Type | Signature |
|------|------|-----------|
| `Board` | class | — |
| `__init__` | method | `(self)` |
| `get_candy` | method | `(self, row: int, col: int) -> Optional[Candy]` |
| `is_adjacent` | method | `(self, r1: int, c1: int, r2: int, c2: int) -> bool` |
| `swap` | method | `(self, r1: int, c1: int, r2: int, c2: int) -> bool` |
| `remove_matches` | method | `(self, positions: list[tuple]) -> None` |
| `apply_gravity` | method | `(self) -> list[tuple]` |
| `fill_empty` | method | `(self) -> list[tuple]` |
| `__repr__` | method | `(self)` |

---

## game_state.py

| Name | Type | Signature |
|------|------|-----------|
| `GameState` | class | — |
| `__init__` | method | `(self)` |
| `on_swap_attempted` | method | `(self, valid: bool) -> None` |
| `on_matches_cleared` | method | `(self, has_more_matches: bool) -> None` |
| `on_gravity_done` | method | `(self, new_matches_exist: bool) -> None` |
| `use_move` | method | `(self) -> None` |
| `is_input_locked` | method | `(self) -> bool` |

---

## match_finder.py

| Name | Type | Signature |
|------|------|-----------|
| `MatchFinder` | class | — |
| `find_matches` | method | `(self, board: Board) -> list[set[tuple]]` |
| `classify_match` | method | `(self, group: set[tuple]) -> str` |
| `_scan_row` | method | `(self, board: Board, row: int) -> list[set[tuple]]` |
| `_scan_col` | method | `(self, board: Board, col: int) -> list[set[tuple]]` |
| `_merge_overlapping` | method | `(self, groups: list[set[tuple]]) -> list[set[tuple]]` |

---

## score.py

| Name | Type | Signature |
|------|------|-----------|
| `ScoreTracker` | class | — |
| `__init__` | method | `(self)` |
| `add_match` | method | `(self, group_size: int) -> int` |
| `reset_combo` | method | `(self) -> None` |
| `reset` | method | `(self) -> None` |
