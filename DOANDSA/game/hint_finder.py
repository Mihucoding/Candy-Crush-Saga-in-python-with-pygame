from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.board import Board

from constants import GRID_ROWS, GRID_COLS
from game.match_finder import MatchFinder


class HintFinder:
    """Tìm cặp kẹo kề nhau đầu tiên mà khi swap sẽ tạo ra match."""

    def __init__(self):
        self._finder = MatchFinder()

    def find_hint(self, board: "Board") -> tuple[tuple, tuple] | None:
        """Trả về ((r1,c1), (r2,c2)) nếu tìm được nước đi hợp lệ, ngược lại None."""
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if c + 1 < GRID_COLS and self._try_swap(board, r, c, r, c + 1):
                    return (r, c), (r, c + 1)
                if r + 1 < GRID_ROWS and self._try_swap(board, r, c, r + 1, c):
                    return (r, c), (r + 1, c)
        return None

    def _try_swap(self, board: "Board", r1: int, c1: int, r2: int, c2: int) -> bool:
        """Swap tạm thời, kiểm tra match rồi hoàn tác — không thay đổi board."""
        board.grid[r1][c1], board.grid[r2][c2] = board.grid[r2][c2], board.grid[r1][c1]
        has_match = bool(self._finder.find_matches(board))
        board.grid[r1][c1], board.grid[r2][c2] = board.grid[r2][c2], board.grid[r1][c1]
        return has_match
