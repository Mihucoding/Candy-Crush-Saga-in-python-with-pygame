from __future__ import annotations
from typing import TYPE_CHECKING
# Em hay nhập lộn nên thêm như vậy
if TYPE_CHECKING:
    from game.board import Board
from game.candy import NORMAL, STRIPED_H, STRIPED_V, WRAPPED, COLOR_BOMB
from constants import GRID_COLS, GRID_ROWS


class MatchFinder:
    # Gàn tìm matches gọi _scan_col và _scan_row ở đây e áp dụng OOP tính đóng gói
    def find_matches(self, board: Board) -> list[set[tuple]]:

        matched_candies = []
        for col in range(GRID_COLS):
            matched_candies += self._scan_col(board, col)
        for row in range(GRID_ROWS):
            matched_candies += self._scan_row(board,row)
        merge_match = self._merge_overlapping(matched_candies)
        return merge_match
        


    # Xác định loại kẹo trả về khi match  
    def classify_match(self, group: set[tuple]) -> str:
        cols = [c for r, c in group]
        rows = [r for r, c in group]
        if len(group) <= 3:
            return NORMAL
        elif len(group) == 4:
            if len(set(cols)) == 1:
                return STRIPED_V
            else:
                return STRIPED_H
        elif len(group) == 5 and (all(r == rows[0] for r in rows) or all(c == cols[0] for c in cols) )  :
            return COLOR_BOMB
        elif len(group) >= 5:
            return WRAPPED             


    # Caged cells coi như chướng ngại — không tham gia match, ngắt streak
    @staticmethod
    def _is_caged(board, r, c) -> bool:
        return (r, c) in getattr(board, "cages", {})

    # Hàm private để scan hàng
    def _scan_row(self, board, row):
        res = []
        streak = set()
        current_type = None
        for c in range(GRID_COLS):
            candy = board.grid[row][c]
            blocked = self._is_caged(board, row, c)
            if candy and not blocked and candy.candy_type == current_type:
                streak.add((row, c))
            else:
                if len(streak) >= 3:
                    res.append(streak)
                if candy and not blocked:
                    current_type = candy.candy_type
                    streak = {(row, c)}
                else:
                    current_type = None
                    streak = set()
        if len(streak) >= 3:
            res.append(streak)
        return res

    # Hàm private để scan cột
    def _scan_col(self, board, col):
        res = []
        streak = set()
        current_type = None
        for r in range(GRID_ROWS):
            candy = board.grid[r][col]
            blocked = self._is_caged(board, r, col)
            if candy and not blocked and candy.candy_type == current_type:
                streak.add((r, col))
            else:
                if len(streak) >= 3:
                    res.append(streak)
                if candy and not blocked:
                    current_type = candy.candy_type
                    streak = {(r, col)}
                else:
                    current_type = None
                    streak = set()
        if len(streak) >= 3:
            res.append(streak)
        return res
    # Hàm check có phải color Bomb
    def _is_straight_5(self, group: set[tuple]) -> bool:
        if len(group) != 5:
            return False
        rows = [r for r, c in group]
        cols = [c for r, c in group]
        return len(set(rows)) == 1 or len(set(cols)) == 1
    # Hàm gộp khi cần xác định
    def _merge_overlapping(self, groups):
        i = 0
        # Check từng phần tử trong nhóm 
        while i < len(groups):
            j = i + 1
            popped_i = False
            # chạy từng phần tử khác trong nhóm
            while j < len(groups):
                #Check 2 nhóm 
                if groups[i] & groups[j]:
                    # Nếu nhóm 5 thì không đụng
                    if self._is_straight_5(groups[i]) and self._is_straight_5(groups[j]):
                        j += 1
                    elif self._is_straight_5(groups[i]) or self._is_straight_5(groups[j]):
                        shared = groups[i] & groups[j]
                        if self._is_straight_5(groups[i]):
                            groups[j] -= shared
                        else:
                            groups[i] -= shared
                        # Nếu nhóm < 3 loại
                        if len(groups[j]) < 3:
                            groups.pop(j)
                        elif len(groups[i]) < 3:
                            groups.pop(i)
                            popped_i = True
                            break
                        else:
                            j += 1
                    else:
                        groups[i] |= groups[j]
                        groups.pop(j)
                else:
                    j += 1
            if not popped_i:
                i += 1
        return groups


