from __future__ import annotations
import random
from constants import CANDY_TYPES, GRID_ROWS, GRID_COLS

# ─── Special type constants ────────────────────────────────────────────────
NORMAL      = "normal"
STRIPED_H   = "striped_h"   # match 4 in a row  → clears whole row
STRIPED_V   = "striped_v"   # match 4 in a col  → clears whole column
WRAPPED     = "wrapped"     # L/T shape (5)      → clears 3×3 twice
COLOR_BOMB  = "color_bomb"  # 5 in a line        → clears all of one color
class Candy:
    """Single candy tile on the board."""

    def __init__(self, candy_type: str = None, special_type = NORMAL):
        self.candy_type:   str  = candy_type or random.choice(CANDY_TYPES)
        self.special_type: str  = special_type 
        self.is_matched:   bool = False
        self.is_new:       bool = True

   
    # Hàm activate được gọi khi board chọn candy đặc biệt (Kích hoạt kỹ năng đặc biệt của candies)
    def activate(self, row: int, col: int, board, target: "Candy | None" = None) -> list[tuple]:

        if self.special_type == STRIPED_H:
            # Xóa toàn bộ hàng ngang
            return [(row, c) for c in range(GRID_COLS)]
        elif self.special_type == STRIPED_V:
            # Xóa toàn bộ cột dọc
            return [(r, col) for r in range(GRID_ROWS)]
        elif self.special_type == WRAPPED:
            temp = []
            for r in range(max(0, row - 1), min(GRID_ROWS, row + 2)):
                for c in range(max(0, col - 1), min(GRID_COLS, col + 2)):
                    temp.append((r, c))
            return temp
        elif self.special_type == COLOR_BOMB:
            if target is None:
                return []
            temp = []
            # Xóa cacs viên kẹo trùng màu
            for r in range(GRID_ROWS):
                for c in range(GRID_COLS):
                    if board.get_candy(r, c) and board.get_candy(r, c).candy_type == target.candy_type:
                        temp.append((r, c))
            return temp
        else:
            return []

    # Combo khi kết hợp các viên kẹo có hiệu ứng đặc biệt với nhau
    def combo_with(self, other: "Candy", row: int, col: int, board) -> list[tuple]:
        dele = []
        Strip = [STRIPED_H, STRIPED_V]
        # Nếu combo Đặc biệt 2 color Bomb thì xóa nguyên sàn
        if self.special_type == COLOR_BOMB:
            if other.special_type == COLOR_BOMB:
                dele += [(r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)]
                return dele
            else:
                target_type = other.candy_type
                #Nếu kết hợp color_bomb với các hiệu ứng đặc biệt thì các viên kẹo trên toàn 
                special_to_apply = other.special_type
                for r in range(GRID_ROWS):
                    for c in range(GRID_COLS):
                        candy = board.get_candy(r, c)
                        if candy and candy.candy_type == target_type:
                            if special_to_apply != NORMAL:
                                candy.special_type = special_to_apply
                            dele.append((r, c))
                return list(set(dele))

        elif self.special_type in Strip and other.special_type in Strip:
            # Nếu Strip thì xóa trên hàng cột ấy
            dele += [(row, c) for c in range(GRID_COLS)]
            dele += [(r, col) for r in range(GRID_ROWS)]
            
            return list(set(dele))

        elif self.special_type == WRAPPED or other.special_type == WRAPPED:
            if self.special_type in Strip or other.special_type in Strip:
                # WRAPPED + STRIPED = 3 cột + 3 hàng
                for r in range(max(0, row - 1), min(GRID_ROWS, row + 2)):
                    dele += [(r, c) for c in range(GRID_COLS)]
                for c in range(max(0, col - 1), min(GRID_COLS, col + 2)):
                    dele += [(r, c) for r in range(GRID_ROWS)]
                return list(set(dele))
            else:
                # WRAPPED + WRAPPED = 5 X 5 hàng
                for r in range(max(0, row - 2), min(GRID_ROWS, row + 3)):
                    for c in range(max(0, col - 2), min(GRID_COLS, col + 3)):
                        dele.append((r, c))
                return list(set(dele))

        return []



    def __repr__(self):
        return f"Candy({self.candy_type[:2]},{self.special_type[:2]})"
