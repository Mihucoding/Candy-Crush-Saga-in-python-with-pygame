"""
=============================================================
  GAME MODULE — TÀI LIỆU MÔ TẢ TOÀN BỘ (tiếng Việt)
  Cập nhật: 2026-05-10
=============================================================
"""

# ─── candy.py ────────────────────────────────────────────────────────────────

CANDY_MODULE = """
Module: game/candy.py
Mục đích: Định nghĩa thực thể Candy và các hằng số loại đặc biệt.
"""

CANDY_CONSTANTS = """
Hằng số loại đặc biệt:
    NORMAL      = "normal"      — Kẹo thông thường, không có hiệu ứng.
    STRIPED_H   = "striped_h"   — Tạo khi match 4 theo hàng ngang → xóa cả hàng.
    STRIPED_V   = "striped_v"   — Tạo khi match 4 theo cột dọc   → xóa cả cột.
    WRAPPED     = "wrapped"     — Tạo khi match hình L/T (≥5 ô)   → xóa vùng 3×3.
    COLOR_BOMB  = "color_bomb"  — Tạo khi match thẳng 5 ô         → xóa tất cả kẹo cùng màu.
"""

CANDY_CLASS = """
Lớp: Candy
    Đại diện cho một ô kẹo trên bảng.

    Thuộc tính:
        candy_type   (str)  — Màu sắc kẹo: "red" | "orange" | "yellow" | "green" | "blue" | "purple".
        special_type (str)  — Loại đặc biệt (mặc định NORMAL).
        is_matched   (bool) — Đánh dấu đã nằm trong một nhóm match.
        is_new       (bool) — Đánh dấu vừa được sinh ra (dùng cho animation fade-in).

    Candy.__init__(candy_type=None, special_type=NORMAL):
        Khởi tạo kẹo. Nếu candy_type=None thì chọn ngẫu nhiên từ CANDY_TYPES.

    Candy.activate(row, col, board, target=None) -> list[tuple]:
        Kích hoạt hiệu ứng đặc biệt của kẹo, trả về danh sách tọa độ (row, col) cần phá hủy.
            STRIPED_H  → tất cả ô trên hàng `row`                     — O(COLS)
            STRIPED_V  → tất cả ô trên cột `col`                      — O(ROWS)
            WRAPPED    → vùng 3×3 xung quanh (row, col)               — O(1)
            COLOR_BOMB → tất cả ô có candy_type == target.candy_type  — O(ROWS×COLS)
        Tham số `target` chỉ dùng khi special_type == COLOR_BOMB.

    Candy.combo_with(other, row, col, board) -> list[tuple]:
        Xử lý hiệu ứng khi kết hợp hai kẹo đặc biệt với nhau.
        Bảng combo:
            COLOR_BOMB + COLOR_BOMB  → xóa toàn bộ bảng               — O(ROWS×COLS)
            COLOR_BOMB + bất kỳ     → gán special của `other` lên tất cả kẹo cùng màu rồi xóa — O(ROWS×COLS)
            STRIPED    + STRIPED    → xóa hàng `row` + cột `col`      — O(ROWS + COLS)
            WRAPPED    + STRIPED    → xóa 3 hàng liền + 3 cột liền    — O(ROWS + COLS)
            WRAPPED    + WRAPPED    → xóa vùng 5×5                    — O(1)
"""

# ─── board.py ────────────────────────────────────────────────────────────────

BOARD_MODULE = """
Module: game/board.py
Mục đích: Cấu trúc dữ liệu chính — mảng 2 chiều 9×9 chứa các Candy.
Lưu ý:   Pure Python, KHÔNG import pygame.
"""

BOARD_CLASS = """
Lớp: Board
    Quản lý toàn bộ trạng thái bảng: vị trí kẹo, lồng (cages), con tin (hostages).

    Thuộc tính:
        grid           (list[list[Candy|None]])  — Mảng 2D chứa các ô kẹo.
        removed_colors (list[str])               — Log màu các kẹo vừa bị xóa (dùng để tính CollectGoal).
        hostages       (set[tuple])              — Tập hợp (row, col) của các con tin còn trên bảng.
        rescued_count  (int)                     — Số con tin đã giải cứu thành công.
        cages          (dict[tuple, int])        — Map (row, col) → HP của lồng còn lại.

    Board.__init__(cage_positions=None, hostage_positions=None):
        Khởi tạo bảng ngẫu nhiên, đảm bảo không có match ngay từ đầu bằng cách loại trừ
        màu sắc tạo thành chuỗi 3 theo hàng hoặc cột.
        Độ phức tạp: O(ROWS × COLS).

    Board.get_candy(row, col) -> Candy | None:
        Trả về kẹo tại (row, col), hoặc None nếu ngoài phạm vi.
        Được UI gọi để đọc trạng thái bảng.

    Board.is_adjacent(r1, c1, r2, c2) -> bool:
        Kiểm tra khoảng cách Manhattan == 1 (hai ô kề nhau theo hàng hoặc cột).

    Board.swap(r1, c1, r2, c2) -> tuple[bool, list, list]:
        Thực hiện swap hai ô kẹo, xử lý theo thứ tự ưu tiên:
            1. Combo 2 kẹo đặc biệt (kích hoạt ngay, không cần match)
            2. Kẹo đặc biệt + kẹo thường (activate tại vị trí mới)
            3. Swap bình thường → kiểm tra match → hoàn tác nếu không có match
        Returns:
            (valid: bool, activations: list[(r,c,special)], initial_groups: list[set])
            valid=False nếu không kề nhau hoặc không tạo match.

    Board.remove_matches(positions) -> list[tuple[int, int, str]]:
        Xóa tất cả kẹo tại danh sách tọa độ đầu vào, xử lý dây chuyền:
            - Kẹo đặc biệt: kích hoạt hiệu ứng → thêm các ô mới vào hàng đợi xóa.
            - Con tin: bất tử, thêm ô phía dưới vào hàng đợi để con tin có chỗ rơi.
            - Lồng cạnh ô bị xóa: giảm 1 HP (mỗi lồng tối đa 1 lần/lượt remove).
        Returns: list[(r, c, special_type)] — các kẹo đặc biệt đã kích hoạt, dùng cho UI.
        Độ phức tạp: O(n) amortized (n = số ô bị xóa cuối cùng).

    Board.apply_gravity() -> list[tuple]:
        Áp dụng trọng lực: gom các ô không rỗng xuống phía dưới trong từng cột.
        Dùng counter `placed` thay vì index để tránh tạo lỗ trống ở đáy khi con tin được giải cứu.
        Giải cứu con tin: nếu con tin sẽ đổ xuống row cuối (GRID_ROWS-1), tăng rescued_count
        và không đặt vào grid, giữ ô đó trống để fill_empty xử lý tiếp.
        Returns: list[(from_row, col, to_row, col)] — danh sách di chuyển để UI render FallAnim.
        Độ phức tạp: O(ROWS × COLS).

    Board.fill_empty() -> list[tuple]:
        Điền kẹo mới vào các ô trống liên tiếp từ đầu mỗi cột (sau khi gravity đã chạy).
        Returns: list[(spawn_row, col, dest_row, col)] — spawn_row âm biểu thị vị trí ngoài màn hình.
        Độ phức tạp: O(ROWS × COLS).
"""

# ─── match_finder.py ─────────────────────────────────────────────────────────

MATCH_FINDER_MODULE = """
Module: game/match_finder.py
Mục đích: Phát hiện các nhóm kẹo khớp (match) trên bảng.
"""

MATCH_FINDER_CLASS = """
Lớp: MatchFinder
    Không lưu trạng thái — tất cả phương thức là stateless scanner.

    MatchFinder.find_matches(board) -> list[set[tuple]]:
        Quét tất cả hàng và cột, gộp các nhóm chồng lên nhau.
        Returns: danh sách các nhóm tọa độ {(r,c), ...} đủ 3+ kẹo cùng màu.
        Độ phức tạp: O(ROWS × COLS).

    MatchFinder.classify_match(group) -> str:
        Xác định loại kẹo đặc biệt nên được sinh ra từ nhóm match.
        Logic phân loại theo kích thước và hình dạng nhóm:
            len ≤ 3                          → NORMAL
            len == 4 (cùng cột)              → STRIPED_V
            len == 4 (cùng hàng)             → STRIPED_H
            len == 5 (thẳng hàng hoặc cột)  → COLOR_BOMB
            len ≥ 5 (hình L/T)              → WRAPPED

    MatchFinder._scan_row(board, row) -> list[set]:
        Quét tuyến tính hàng ngang, thu thập chuỗi ≥3 kẹo cùng loại.
        Độ phức tạp: O(COLS).

    MatchFinder._scan_col(board, col) -> list[set]:
        Quét tuyến tính cột dọc, thu thập chuỗi ≥3 kẹo cùng loại.
        Độ phức tạp: O(ROWS).

    MatchFinder._is_straight_5(group) -> bool:
        Kiểm tra nhóm có đúng 5 ô và nằm thẳng trên một hàng hoặc một cột không.
        Dùng để phân biệt COLOR_BOMB với WRAPPED khi len==5.

    MatchFinder._merge_overlapping(groups) -> list[set]:
        Gộp các nhóm có phần tử chung thành một nhóm duy nhất.
        Ngoại lệ: hai nhóm straight-5 không bị gộp với nhau (bảo toàn hình dạng cho classify).
        Độ phức tạp: O(n²) với n = số nhóm (thực tế n nhỏ).
"""

# ─── score.py ────────────────────────────────────────────────────────────────

SCORE_MODULE = """
Module: game/score.py
Mục đích: Theo dõi điểm số, chuỗi combo và số kẹo đã thu thập.
"""

SCORE_CLASS = """
Lớp: ScoreTracker
    Theo dõi điểm, combo và thống kê kẹo đã xóa trong phiên chơi.

    Thuộc tính:
        score      (int)           — Điểm hiện tại.
        combo      (int)           — Bộ đếm combo liên tiếp.
        high_score (int)           — Điểm cao nhất trong phiên.
        collected  (dict[str,int]) — Số lượng kẹo mỗi màu đã bị xóa (cho CollectGoal).

    ScoreTracker.add_match(group_size) -> int:
        Tăng combo, tính điểm = SCORE_PER_CANDY × group_size × COMBO_MULTIPLIER^(combo-1).
        Returns: điểm vừa kiếm được (hiển thị dạng floating text trên UI).

    ScoreTracker.collect_batch(colors: list[str]) -> None:
        Cộng số lượng từng màu vào `collected`. Được gọi sau mỗi cascade để
        theo dõi tiến độ goal CollectGoal.

    ScoreTracker.reset_combo() -> None:
        Đặt combo về 0. Gọi khi bắt đầu lượt mới (sau khi người chơi thực hiện swap).

    ScoreTracker.reset() -> None:
        Reset toàn bộ về trạng thái ban đầu cho game session mới.
"""

# ─── game_state.py ───────────────────────────────────────────────────────────

GAME_STATE_MODULE = """
Module: game/game_state.py
Mục đích: Máy trạng thái hữu hạn (FSM) điều khiển luồng chơi.

Sơ đồ FSM:
    IDLE ──(swap valid)──> MATCHING ──(cleared)──> FALLING ──(done)──> IDLE
         \\─(swap invalid)─> IDLE
    Any ──(moves=0)──> GAMEOVER
    Any ──(score≥target / goal met)──> WIN
"""

GAME_STATE_CLASS = """
Lớp: GameState
    FSM với 6 trạng thái: IDLE, SWAPPING, MATCHING, FALLING, GAMEOVER, WIN.

    GameState.__init__(moves=INITIAL_MOVES):
        Khởi tạo ở trạng thái IDLE với số lượt cho phép.

    GameState.on_swap_attempted(valid: bool) -> None:
        Chuyển sang MATCHING nếu swap hợp lệ, về IDLE nếu không hợp lệ.

    GameState.on_matches_cleared(has_more_matches: bool) -> None:
        MATCHING nếu còn match cần xử lý, FALLING nếu bảng đã ổn định.

    GameState.on_gravity_done(new_matches_exist: bool) -> None:
        MATCHING nếu gravity tạo ra match mới, IDLE nếu không.
        Không ghi đè GAMEOVER hoặc WIN.

    GameState.use_move() -> None:
        Trừ 1 lượt đi. Khi moves_left == 0 → GAMEOVER.

    GameState.check_win(score, scorer=None, level_cfg=None, board=None) -> None:
        Kiểm tra điều kiện thắng theo loại goal của level:
            ScoreGoal  → score >= goal.target
            CollectGoal→ scorer.collected[color] >= goal.count
            RescueGoal → board.rescued_count >= goal.count
            CageGoal   → len(board.cages) == 0
        Không ghi đè GAMEOVER hoặc WIN đã có.

    GameState.is_input_locked (property) -> bool:
        True khi state != IDLE — ngăn người chơi tương tác trong lúc đang xử lý.
"""

# ─── level_config.py ─────────────────────────────────────────────────────────

LEVEL_CONFIG_MODULE = """
Module: game/level_config.py
Mục đích: Định nghĩa cấu hình cho từng màn chơi và các loại mục tiêu (goal).
"""

LEVEL_CONFIG_CLASSES = """
Các dataclass mục tiêu (Goal):

    ScoreGoal(target: int):
        Mục tiêu tích điểm — thắng khi score >= target.
        Ví dụ: ScoreGoal(target=4000)

    CollectGoal(color: str, count: int):
        Mục tiêu thu thập kẹo theo màu — thắng khi collected[color] >= count.
        Ví dụ: CollectGoal(color="red", count=20)

    RescueGoal(count: int):
        Mục tiêu giải cứu con tin — thắng khi board.rescued_count >= count.
        Con tin rơi theo trọng lực, bất tử trước special candy, giải cứu khi chạm đáy.
        Ví dụ: RescueGoal(count=3)

    CageGoal():
        Mục tiêu phá lồng — thắng khi len(board.cages) == 0.
        Lồng nhận damage khi match xảy ra ở ô cạnh nó (mỗi match tối đa 1 damage/lồng).
        Ví dụ: CageGoal()

Lớp: LevelConfig
    Đóng gói toàn bộ thông số của một màn chơi.

    Thuộc tính:
        level             (int)        — Số thứ tự màn.
        moves             (int)        — Số lượt tối đa.
        goal              (Goal)       — Loại mục tiêu cần đạt.
        hostage_positions (list)       — [(row, col)] — vị trí khởi đầu của con tin.
        cage_positions    (list)       — [(row, col, hp)] — vị trí và HP của các lồng.

Hàm: get_level(n: int) -> LevelConfig:
    Trả về cấu hình màn thứ n (1-based). Tự động lặp vòng nếu n > len(LEVELS).

Danh sách LEVELS (4 màn):
    Level 1 — ScoreGoal(4000),  30 lượt
    Level 2 — CollectGoal(random_color, 20),  25 lượt
    Level 3 — RescueGoal(3),  28 lượt, 3 con tin tại (0,2),(0,4),(0,6)
    Level 4 — CageGoal(),  25 lượt, 6 lồng cụm giữa bảng (3-4, 3-5)
"""

# ─── hint_finder.py ──────────────────────────────────────────────────────────

HINT_FINDER_MODULE = """
Module: game/hint_finder.py
Mục đích: Tìm gợi ý nước đi hợp lệ cho người chơi sau 30 giây không tương tác.
"""

HINT_FINDER_CLASS = """
Lớp: HintFinder
    Tìm cặp kẹo kề nhau đầu tiên mà khi swap sẽ tạo ra ít nhất 1 match.

    HintFinder.find_hint(board) -> tuple[tuple, tuple] | None:
        Duyệt toàn bộ bảng O(ROWS×COLS), thử swap từng cặp kề theo hàng và cột.
        Trả về ((r1,c1), (r2,c2)) của cặp đầu tiên tìm được, hoặc None nếu không còn nước đi.

    HintFinder._try_swap(board, r1, c1, r2, c2) -> bool:
        Swap tạm thời → kiểm tra match → hoàn tác. Không làm thay đổi trạng thái board.
        Độ phức tạp: O(ROWS×COLS) mỗi lần gọi (do find_matches quét toàn bảng).
"""
