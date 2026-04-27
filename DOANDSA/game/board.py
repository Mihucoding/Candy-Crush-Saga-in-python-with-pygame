from __future__ import annotations
from typing import Optional
from constants import GRID_ROWS, GRID_COLS
from game.candy import Candy, NORMAL, COLOR_BOMB , STRIPED_H, STRIPED_V
from game.match_finder import MatchFinder 

class Board:
    """2D grid of Candy objects. Pure data — no pygame imports."""
    # Tạo 1 mảng 2 Chiều các viên kẹo ( bao gồm các loại bình thường và đặc biệt)
    def __init__(self):
        self.grid: list[list[Optional[Candy]]] = [
            [Candy() for _ in range(GRID_COLS)]
            for _ in range(GRID_ROWS)
        ]

    
    # Check kẹo để sử dụng , có được sài trong phần UI
    def get_candy(self, row: int, col: int) -> Optional[Candy]:
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return self.grid[row][col]
        return None
    # Check kẹo có cạnh nhau hay không
    def is_adjacent(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        if (abs(c1-c2)+ abs(r1 - r2) == 1) :
            return True
        else:
            return False

    #Thực hiện thao tác swap kẹo
    def swap(self, r1: int, c1: int, r2: int, c2: int) -> tuple[bool, list[tuple[int, int, str]]]:
        candy1 = self.get_candy(r1,c1)
        candy2 = self.get_candy(r2,c2)
        # Đảm bảo không lỗi
        if not candy1 or not candy2 :
            return False, []
        #Không cạnh nhau thì sẽ không swap được
        if not self.is_adjacent(r1,c1,r2,c2) :
            return False, []
        activations = []
        # Check Combo đặc biệt trước
        # Check Combo 2 viên kẹo dặc biệt
        if candy1.special_type != NORMAL and candy2.special_type != NORMAL:
            #Nếu là Color Bomb Thì phải activate trước
            if candy1.special_type == COLOR_BOMB :
                dele = candy1.combo_with(candy2,r1,c1,self)
                activations = self.remove_matches(dele)
            elif candy2.special_type == COLOR_BOMB:
                dele = candy2.combo_with(candy1,r2,c2,self)
                activations = self.remove_matches(dele)
            else:
            #Nếu không thì áp dụng hiệu ứng combo 2 viên kẹo đặc biệt bình thường
                dele = candy1.combo_with(candy2,r2,c2,self)
                activations = self.remove_matches(dele)
            return True, activations
            
        self.grid[r1][c1] , self.grid[r2][c2] =  self.grid[r2][c2] , self.grid[r1][c1] 
        
        #Check combo 1 viên special và 1 thường
        if candy1.special_type != NORMAL or candy2.special_type != NORMAL:
            if candy1.special_type != NORMAL:
                dele = candy1.activate(r2,c2,self,candy2) # Đổi vị trí của 1 và 2
                activations = self.remove_matches(dele)
            else:
                dele = candy2.activate(r1,c1,self,candy1)
                activations = self.remove_matches(dele)
            return True, activations
        #Check xem có matches
        finder = MatchFinder()
        check = finder.find_matches(self)
        if not check:
            #Nếu không trùng thì đổi lại vị trí và return False
            self.grid[r1][c1] , self.grid[r2][c2] =  self.grid[r2][c2] , self.grid[r1][c1] 
            return False, []
        else:
            #Nếu matches thì check combo và trả về viên kẹo đặc biệt nếu có
            dele = []
            for can in check:
                special = finder.classify_match(can)
                if special != NORMAL:
                    # Tìm vị trí swapped nào nằm trong match
                    if (r1, c1) in can:
                        spawn = (r1, c1)
                    elif (r2, c2) in can:
                        spawn = (r2, c2)
                    else:
                        spawn = next(iter(can))  # fallback nếu cascade
                    sr, sc = spawn
                    self.grid[sr][sc] = Candy(self.grid[sr][sc].candy_type, special)
                    dele += [pos for pos in can if pos != spawn]
                else:
                    dele += list(can)
            activations = self.remove_matches(dele)
            return True, activations


    # Xóa matches
    def remove_matches(self, positions: list[tuple]) -> list[tuple[int, int, str]]:
        activations = []
        to_clear = set(positions)
        processed = set()
        #Chạy từng viên kẹo
        while to_clear:
            r, c = to_clear.pop()
            if (r, c) in processed:
                continue
            #Nếu bình thường thì xóa và tiếp
            candy = self.get_candy(r, c)
            if candy is None:
                continue
            #Nếu có đặc biệt thì phải kích hoạt đặc biệt trước
            if candy.special_type != NORMAL:
                activations.append((r, c, candy.special_type))
                extra = candy.activate(r, c, self)
                to_clear.update(extra)

            self.grid[r][c] = None
            processed.add((r, c))
        #Trả về các viên kẹo đặc biệt để kích hoạt hiệu ứng UI
        return activations

    # Kích hoạt cơ chế trọng lực ( Viên kẹo rớt xuống )
    def apply_gravity(self) -> list[tuple]:
        moves = []
        for col in range(GRID_COLS):
            #Thu thập các candy không None, từ dưới lên trên
            stack = []
            for row in range(GRID_ROWS - 1, -1, -1):
                if self.grid[row][col] is not None:
                    stack.append((row, self.grid[row][col]))

            # Ghi lại vị trí mới từ dưới lên
            for i, (from_row, candy) in enumerate(stack):
                to_row = GRID_ROWS - 1 - i
                self.grid[to_row][col] = candy
                if from_row != to_row:
                    moves.append((from_row, col, to_row, col))

            # Các ô trống phía trên gàn bằng None để có thể fill lại
            for row in range(GRID_ROWS - len(stack)):
                self.grid[row][col] = None
        return moves

    def fill_empty(self) -> list[tuple[int, int, int, int]]:
        record = []
        for c in range(GRID_COLS):
            # Đếm số None cần được fill
            empty_count = 0
            for r in range(GRID_ROWS):
                if self.grid[r][c] is None:
                    empty_count += 1
            
            # FIll từ cao xuống thấp
            for i in range(empty_count):
                row = empty_count - 1 - i
                self.grid[row][c] = Candy()
                self.grid[row][c].is_new = True
                #Record trả về danh sách kẹo để UI làm việc 
                record.append((row - empty_count, c, row, c))
        return record

    def __repr__(self):
        return "\n".join(" ".join(str(c) for c in row) for row in self.grid)
