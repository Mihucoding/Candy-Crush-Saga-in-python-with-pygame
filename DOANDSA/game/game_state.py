from constants import INITIAL_MOVES, TARGET_SCORE

# State constants — DO NOT rename (UI reads these)
STATE_IDLE      = "IDLE"
STATE_SWAPPING  = "SWAPPING"
STATE_MATCHING  = "MATCHING"
STATE_FALLING   = "FALLING"
STATE_GAMEOVER  = "GAMEOVER"
STATE_WIN       = "WIN"


class GameState:
    # Khởi tạo trạng thái ban đầu của màn chơi ( IDLE, số lượt còn lại, ô đang chọn )
    def __init__(self, moves: int = INITIAL_MOVES):
        self.current_state: str = STATE_IDLE
        self.moves_left: int = moves
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

    # Trừ 1 lượt đi, nếu hết lượt thì chuyển sang GAMEOVER
    def use_move(self) -> None:
        self.moves_left -= 1
        if self.moves_left <= 0:
            self.moves_left = 0
            self.current_state = STATE_GAMEOVER

    # Sau khi kẹo rơi xong — có match mới thì quay lại MATCHING, không thì về IDLE
    # Không ghi đè GAMEOVER hoặc WIN
    def on_gravity_done(self, new_matches_exist: bool) -> None:
        if self.current_state in (STATE_GAMEOVER, STATE_WIN):
            return
        if new_matches_exist:
            self.current_state = STATE_MATCHING
        else:
            self.current_state = STATE_IDLE

    # Kiểm tra điều kiện thắng dựa trên level config
    def check_win(self, score: int, scorer=None, level_cfg=None, board=None) -> None:
        if self.current_state in (STATE_GAMEOVER, STATE_WIN):
            return
        if level_cfg is None:
            if score >= TARGET_SCORE:
                self.current_state = STATE_WIN
            return
        from game.level_config import ScoreGoal, CollectGoal, RescueGoal, CageGoal
        goal = level_cfg.goal
        if isinstance(goal, ScoreGoal):
            if score >= goal.target:
                self.current_state = STATE_WIN
        elif isinstance(goal, CollectGoal):
            if scorer and scorer.collected.get(goal.color, 0) >= goal.count:
                self.current_state = STATE_WIN
        elif isinstance(goal, RescueGoal):
            if board and board.rescued_count >= goal.count:
                self.current_state = STATE_WIN
        elif isinstance(goal, CageGoal):
            if board and len(board.cages) == 0:
                self.current_state = STATE_WIN

    # Kiểm tra xem người chơi có được tương tác không ( chỉ được khi đang IDLE )
    @property
    def is_input_locked(self) -> bool:
        return self.current_state != STATE_IDLE
