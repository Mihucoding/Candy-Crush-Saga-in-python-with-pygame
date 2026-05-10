from __future__ import annotations
import random
from typing import Optional
from constants import GRID_ROWS, GRID_COLS, CANDY_TYPES
from game.candy import Candy, NORMAL, COLOR_BOMB , STRIPED_H, STRIPED_V
from game.match_finder import MatchFinder

class Board:

    # Tạo 1 mảng 2 Chiều các viên kẹo, tránh matches ngay từ đầu
    def __init__(self, cage_positions=None, hostage_positions=None):
        self.grid: list[list[Optional[Candy]]] = [[None] * GRID_COLS for _ in range(GRID_ROWS)]
        self.removed_colors: list[str] = []
        self.hostages: set[tuple] = set(hostage_positions or [])
        self.rescued_count: int = 0
        self.cages: dict[tuple, int] = {(r, c): hp for r, c, hp in (cage_positions or [])}
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                forbidden = set()
                # Kiểm tra 2 ô bên trái
                if c >= 2:
                    left1 = self.grid[r][c - 1]
                    left2 = self.grid[r][c - 2]
                    if left1 and left2 and left1.candy_type == left2.candy_type:
                        forbidden.add(left1.candy_type)
                # Kiểm tra 2 ô phía trên
                if r >= 2:
                    up1 = self.grid[r - 1][c]
                    up2 = self.grid[r - 2][c]
                    if up1 and up2 and up1.candy_type == up2.candy_type:
                        forbidden.add(up1.candy_type)
                available = [t for t in CANDY_TYPES if t not in forbidden] or list(CANDY_TYPES)
                self.grid[r][c] = Candy(random.choice(available))

    
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
            return False, [], []
        #Không cạnh nhau thì sẽ không swap được
        if not self.is_adjacent(r1,c1,r2,c2) :
            return False, [], []
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
            return True, activations, [set(dele)] if dele else []

        self.grid[r1][c1] , self.grid[r2][c2] =  self.grid[r2][c2] , self.grid[r1][c1]
        
        #Check combo 1 viên special và 1 thường
        if candy1.special_type != NORMAL or candy2.special_type != NORMAL:
            if candy1.special_type != NORMAL:
                dele = candy1.activate(r2,c2,self,candy2) # Đổi vị trí của 1 và 2
                activations = self.remove_matches(dele)
            else:
                dele = candy2.activate(r1,c1,self,candy1)
                activations = self.remove_matches(dele)
            return True, activations, [set(dele)] if dele else []
        #Check xem có matches
        finder = MatchFinder()
        check = finder.find_matches(self)
        if not check:
            #Nếu không trùng thì đổi lại vị trí và return False
            self.grid[r1][c1] , self.grid[r2][c2] =  self.grid[r2][c2] , self.grid[r1][c1]
            return False, [], []
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
            return True, activations, check


    # Xóa matches
    def remove_matches(self, positions: list[tuple]) -> list[tuple[int, int, str]]:
        activations = []
        to_clear = set(positions)
        processed = set()
        _cages_hit: set[tuple] = set()
        #Chạy từng viên kẹo
        while to_clear:
            r, c = to_clear.pop()
            if (r, c) in processed:
                continue
            candy = self.get_candy(r, c)
            if candy is None:
                continue
            # Con tin bất tử — xóa kẹo ngay bên dưới để con tin có chỗ rơi
            if (r, c) in self.hostages:
                processed.add((r, c))
                nr = r + 1
                if nr < GRID_ROWS and (nr, c) not in self.hostages:
                    to_clear.add((nr, c))
                continue
            #Nếu có đặc biệt thì phải kích hoạt đặc biệt trước
            if candy.special_type != NORMAL:
                activations.append((r, c, candy.special_type))
                extra = candy.activate(r, c, self)
                to_clear.update(extra)

            # Phá lồng cạnh ô bị xóa (mỗi lồng chỉ nhận 1 damage / lần remove)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) in self.cages and (nr, nc) not in _cages_hit:
                    _cages_hit.add((nr, nc))
                    self.cages[(nr, nc)] -= 1
                    if self.cages[(nr, nc)] <= 0:
                        del self.cages[(nr, nc)]

            self.removed_colors.append(candy.candy_type)
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

            # Dùng `placed` thay vì `i` để tính to_row
            # — tránh tạo hole ở đáy khi rescue con tin
            placed = 0
            for from_row, candy in stack:
                to_row = GRID_ROWS - 1 - placed
                # Con tin chạm đáy → giải cứu, không đặt vào grid
                if (from_row, col) in self.hostages and to_row == GRID_ROWS - 1:
                    self.hostages.discard((from_row, col))
                    self.rescued_count += 1
                    continue  # không tăng placed → các kẹo phía trên fill xuống
                self.grid[to_row][col] = candy
                if (from_row, col) in self.hostages:
                    self.hostages.discard((from_row, col))
                    self.hostages.add((to_row, col))
                if from_row != to_row:
                    moves.append((from_row, col, to_row, col))
                placed += 1

            # Các ô trống phía trên set None để fill_empty xử lý đúng
            for row in range(GRID_ROWS - placed):
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
