from constants import INITIAL_MOVES

# State constants — DO NOT rename (UI reads these)
STATE_IDLE      = "IDLE"
STATE_SWAPPING  = "SWAPPING"
STATE_MATCHING  = "MATCHING"
STATE_FALLING   = "FALLING"
STATE_GAMEOVER  = "GAMEOVER"
STATE_WIN       = "WIN"


class GameState:
    # Khởi tạo trạng thái ban đầu của màn chơi ( IDLE, số lượt còn lại, ô đang chọn )
    def __init__(self):
        self.current_state: str = STATE_IDLE
        self.moves_left: int = INITIAL_MOVES
        self.selected: tuple | None = None

    # Xử lý kết quả sau khi swap — thành công thì sang MATCHING, thất bại thì về IDLE
    def on_swap_attempted(self, valid: bool) -> None:
        if valid == True:
            self.current_state = STATE_MATCHING
        else:
            self.current_state = STATE_IDLE

    # Sau khi xóa matches — còn match thì tiếp tục MATCHING, không còn thì sang FALLING
    def on_matches_cleared(self, has_more_matches: bool) -> None:
        if has_more_matches :
            self.current_state = STATE_MATCHING
        else:
            self.current_state = STATE_FALLING

    # Sau khi kẹo rơi xong — có match mới thì quay lại MATCHING, không thì về IDLE
    def on_gravity_done(self, new_matches_exist: bool) -> None:
        if new_matches_exist:
            self.current_state = STATE_MATCHING
        else:
            self.current_state = STATE_IDLE

    # Trừ 1 lượt đi, nếu hết lượt thì chuyển sang GAMEOVER
    def use_move(self) -> None:
        self.moves_left -= 1
        if self.moves_left == 0:
            self.current_state = STATE_GAMEOVER

    # Kiểm tra xem người chơi có được tương tác không ( chỉ được khi đang IDLE )
    @property
    def is_input_locked(self) -> bool:
        return self.current_state != STATE_IDLE
