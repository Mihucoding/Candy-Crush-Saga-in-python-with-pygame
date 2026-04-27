"""
=============================================================
  GAME MODULE — TÀI LIỆU MÔ TẢ (tổng hợp từ comment code)
=============================================================
"""

# ─── board.py ────────────────────────────────────────────────────────────────

Board = """
Board.__init__:
    Tạo 1 mảng 2 Chiều các viên kẹo ( bao gồm các loại bình thường và đặc biệt )

Board.get_candy:
    Check kẹo để sử dụng, có được sài trong phần UI

Board.is_adjacent:
    Check kẹo có cạnh nhau hay không

Board.swap:
    Thực hiện thao tác swap kẹo
    - Đảm bảo không lỗi
    - Không cạnh nhau thì sẽ không swap được
    - Check Combo đặc biệt trước ( 2 viên kẹo đặc biệt )
      + Nếu là Color Bomb thì phải activate trước
      + Nếu không thì áp dụng hiệu ứng combo 2 viên kẹo đặc biệt bình thường
    - Check combo 1 viên special và 1 thường
    - Check xem có matches
      + Nếu không trùng thì đổi lại vị trí và return False
      + Nếu matches thì check combo và trả về viên kẹo đặc biệt nếu có

Board.remove_matches:
    Xóa matches
    - Chạy từng viên kẹo
    - Nếu bình thường thì xóa và tiếp
    - Nếu có đặc biệt thì phải kích hoạt đặc biệt trước
    - Trả về các viên kẹo đặc biệt để kích hoạt hiệu ứng UI

Board.apply_gravity:
    Kích hoạt cơ chế trọng lực ( Viên kẹo rớt xuống )
    - Thu thập các candy không None, từ dưới lên trên
    - Ghi lại vị trí mới từ dưới lên
    - Các ô trống phía trên gán bằng None để có thể fill lại

Board.fill_empty:
    Fill các ô trống bằng kẹo mới
    - Record trả về ( from_row, col, to_row, col ) để UI chạy animation
"""

# ─── candy.py ────────────────────────────────────────────────────────────────

Candy = """
Candy.activate:
    Hàm activate được gọi khi board chọn candy đặc biệt
    ( Kích hoạt kỹ năng đặc biệt của candies )
    - STRIPED_H : Xóa toàn bộ hàng ngang
    - STRIPED_V : Xóa toàn bộ cột dọc
    - COLOR_BOMB: Xóa các viên kẹo trùng màu

Candy.combo_with:
    Combo khi kết hợp các viên kẹo có hiệu ứng đặc biệt với nhau
    - COLOR_BOMB + COLOR_BOMB  : xóa nguyên sàn
    - COLOR_BOMB + đặc biệt    : các viên kẹo cùng màu đều nhận hiệu ứng đặc biệt đó
    - STRIPED   + STRIPED      : xóa hàng và cột tại vị trí đó
    - WRAPPED   + STRIPED      : xóa 3 hàng + 3 cột
    - WRAPPED   + WRAPPED      : xóa vùng 5×5
"""

# ─── match_finder.py ─────────────────────────────────────────────────────────

MatchFinder = """
MatchFinder.find_matches:
    Gọi _scan_col và _scan_row để tìm matches — áp dụng OOP tính đóng gói

MatchFinder._scan_row / _scan_col:
    Quét tuyến tính O(n), duy trì streak liên tiếp cùng loại

MatchFinder._merge_overlapping:
    Gộp các nhóm match chồng lên nhau thành 1 nhóm duy nhất
    ( giữ nguyên nhóm straight-5 để classify đúng COLOR_BOMB )
"""

# ─── game_state.py ───────────────────────────────────────────────────────────

GameState = """
GameState.__init__:
    Khởi tạo trạng thái ban đầu của màn chơi
    ( IDLE, số lượt còn lại, ô đang chọn )

GameState.on_swap_attempted:
    Xử lý kết quả sau khi swap
    — thành công thì sang MATCHING, thất bại thì về IDLE

GameState.on_matches_cleared:
    Sau khi xóa matches
    — còn match thì tiếp tục MATCHING, không còn thì sang FALLING

GameState.on_gravity_done:
    Sau khi kẹo rơi xong
    — có match mới thì quay lại MATCHING, không thì về IDLE

GameState.use_move:
    Trừ 1 lượt đi, nếu hết lượt thì chuyển sang GAMEOVER

GameState.is_input_locked:
    Kiểm tra xem người chơi có được tương tác không
    ( chỉ được khi đang IDLE )
"""
