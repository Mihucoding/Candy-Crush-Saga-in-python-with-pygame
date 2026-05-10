import sys
import os
import pygame

pygame.mixer.pre_init(22050, -16, 2, 512)  # 2 channels for stereo music support

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR
from game.board import Board
from game.match_finder import MatchFinder
from game.score import ScoreTracker
from game.game_state import GameState, STATE_IDLE, STATE_GAMEOVER, STATE_WIN
from ui.renderer import draw_board
from ui.animations import ScreenShake
from ui.animations import AnimationManager
from ui.hud import HUD
from ui.screens import MenuScreen, GameOverScreen, LevelCompleteScreen, PauseScreen, LevelSelectScreen
from ui.sounds import SoundManager


def _banner_for(match_size: int, combo: int, has_special: bool) -> tuple[str, tuple]:
    if has_special or combo >= 4:
        return 'AMAZING!!!', (255, 100, 50)
    if combo >= 3 or match_size >= 5:
        return 'EXCELLENT!!', (255, 160, 30)
    if combo >= 2 or match_size >= 4:
        return 'GREAT!', (255, 220, 50)
    return 'GOOD', (255, 255, 255)


def _run_cascade(board, finder, scorer, anims, snd) -> None:
    """Apply gravity + fill + detect chain matches until the board settles."""
    from ui.animations import FallAnim, PopAnim
    from game.candy import NORMAL, Candy
    
    # Cascade: gravity + fill chain until board settles
    while True:
        falls = board.apply_gravity()
        if falls:
            anims.add(FallAnim(falls))
        
        new_falls = board.fill_empty()
        if new_falls:
            anims.add(FallAnim(new_falls))
        
        groups = finder.find_matches(board)
        if not groups:
            break
            
        all_to_remove = set()
        total_activations = []
        has_special = False
        
        for group in groups:
            points = scorer.add_match(len(group))
            special_type = finder.classify_match(group)
            
            # Show floating text with score
            group_center_r = sum(r for r, c in group) // len(group)
            group_center_c = sum(c for r, c in group) // len(group)
            anims.add_floating(f"+{points}", group_center_r, group_center_c)
            
            # Spawn special candy if applicable
            if special_type != NORMAL:
                spawn_pos = next(iter(group))
                sr, sc = spawn_pos
                board.grid[sr][sc] = Candy(board.grid[sr][sc].candy_type, special_type)
                to_remove = [pos for pos in group if pos != spawn_pos]
                all_to_remove.update(to_remove)
            else:
                all_to_remove.update(group)

        # Lưu màu kẹo trước khi xóa để particle đúng màu
        colors_map = {(r, c): board.get_candy(r, c).candy_type
                      for r, c in all_to_remove if board.get_candy(r, c)}
        activations = board.remove_matches(list(all_to_remove))
        total_activations.extend(activations)

        # Visual feedback
        if total_activations:
            has_special = True
            for r, c, s_type in total_activations:
                anims.add_special_break(s_type, r, c)

        label, color = _banner_for(
            max(len(g) for g in groups), scorer.combo, has_special
        )
        anims.add_banner(label, color)
        anims.add(PopAnim(list(all_to_remove), colors_map))
        
        if has_special:
            snd.play("special")
        else:
            snd.play("pop")
        snd.play_combo(scorer.combo)



def cell_at(mx: int, my: int):
    from constants import GRID_OFFSET_X, GRID_OFFSET_Y, CELL_SIZE, GRID_ROWS, GRID_COLS
    col = (mx - GRID_OFFSET_X) // CELL_SIZE
    row = (my - GRID_OFFSET_Y) // CELL_SIZE
    if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
        return row, col
    return None


def run_game(screen: pygame.Surface, clock: pygame.time.Clock, snd: "SoundManager", level_num: int = 1) -> tuple[str, int, int]:
    """Run one game session. Returns (result, score, level_num) where result is 'menu'|'quit'|'gameover'|'win'."""
    from game.hint_finder import HintFinder
    from game.level_config import get_level
    from constants import HINT_DELAY

    cfg      = get_level(level_num)
    board    = Board(cage_positions=cfg.cage_positions, hostage_positions=cfg.hostage_positions)
    finder   = MatchFinder()
    scorer   = ScoreTracker()
    state    = GameState(moves=cfg.moves)
    anims    = AnimationManager()
    hud      = HUD()
    hints    = HintFinder()

    selected     = None
    t            = 0.0
    idle_timer   = 0.0
    hint_pair    = None
    paused       = False
    shake        = None
    pause_screen = PauseScreen()

    while True:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit", scorer.score, level_num
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                paused = not paused
                if paused:
                    pygame.mixer.music.pause()
                    pause_screen = PauseScreen(snd.get_music_volume(), snd.get_sfx_volume())
                else:
                    pygame.mixer.music.unpause()
                continue

            # Tất cả event khi đang pause → giao cho pause_screen
            if paused:
                action = pause_screen.handle_event(event)
                snd.set_music_volume(pause_screen.music_vol)
                snd.set_sfx_volume(pause_screen.sfx_vol)
                if action == "resume":
                    paused = False
                    pygame.mixer.music.unpause()
                elif action == "menu":
                    pygame.mixer.music.unpause()
                    return "menu", scorer.score, level_num
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.is_input_locked or anims.is_busy:
                    continue
                # Bất kỳ click nào → reset hint timer
                idle_timer = 0.0
                hint_pair  = None
                cell = cell_at(*event.pos)
                if cell is None:
                    selected = None
                    continue

                if selected is None:
                    selected = cell
                    snd.play("select")
                else:
                    r1, c1 = selected
                    r2, c2 = cell
                    selected = None

                    # --- Delegate to board logic ---
                    try:
                        from game.candy import NORMAL as _NORMAL
                        from ui.animations import PopAnim, SwapAnim
                        
                        valid, activations, initial_groups = board.swap(r1, c1, r2, c2)
                        anims.add(SwapAnim(r1, c1, r2, c2, valid))
                        state.on_swap_attempted(valid)
                        
                        if valid:
                            snd.play("swap")
                            if activations:
                                snd.play("special")
                                for r, c, s_type in activations:
                                    anims.add_special_break(s_type, r, c)

                            state.use_move()
                            scorer.reset_combo()
                            if initial_groups:
                                has_special_init = bool(activations)
                                all_removed_init = []
                                for group in initial_groups:
                                    pts = scorer.add_match(len(group))
                                    gr = sum(r for r, c in group) // len(group)
                                    gc = sum(c for r, c in group) // len(group)
                                    anims.add_floating(f"+{pts}", gr, gc)
                                    all_removed_init.extend(group)
                                label, color = _banner_for(
                                    max(len(g) for g in initial_groups), scorer.combo, has_special_init
                                )
                                anims.add_banner(label, color)
                                anims.add(PopAnim(all_removed_init, {}))
                                snd.play("special" if has_special_init else "pop")
                            _run_cascade(board, finder, scorer, anims, snd)
                            scorer.collect_batch(board.removed_colors)
                            board.removed_colors.clear()
                            state.check_win(scorer.score, scorer, cfg, board)
                            state.on_gravity_done(False)
                            if scorer.combo >= 3:
                                shake = ScreenShake(intensity=7 + scorer.combo*1.5, duration=0.3)
                        else:
                            snd.play("invalid")
                    except NotImplementedError:

                        # DSA not yet implemented — show selection feedback only
                        selected = cell

        # --- Animate & update (đóng băng khi pause) ---
        if not paused:
            anims.update(dt)
            hud.update(dt, scorer.score, scorer.combo)
            if shake:
                shake.update(dt)
                if shake.done: shake = None

            # --- Hint timer: hiện gợi ý sau 30s không tương tác ---
            if not state.is_input_locked and not anims.is_busy:
                idle_timer += dt
                if idle_timer >= HINT_DELAY and hint_pair is None:
                    hint_pair = hints.find_hint(board)
            else:
                idle_timer = 0.0
        else:
            pause_screen.update(dt)

        # --- Check game-over state (wait for animations to finish first) ---
        if state.current_state == STATE_GAMEOVER and not anims.is_busy:
            return "gameover", scorer.score, level_num
        if state.current_state == STATE_WIN and not anims.is_busy:
            return "win", scorer.score, level_num

        # --- Draw ---
        screen.fill(BG_COLOR)
        sh_off = shake.get_offset() if shake else (0, 0)
        draw_board(screen, board, anim_manager=anims, selected=selected, t=t, hint=hint_pair, shake_offset=sh_off)
        hud.draw(screen, scorer.score, state.moves_left, combo=scorer.combo, t=t,
                 level=level_num, level_cfg=cfg, scorer=scorer, board=board)

        font = pygame.font.SysFont("Arial", 16)
        anims.draw_floating(screen, font)
        anims.draw_effects(screen, lambda sz: pygame.font.SysFont("Arial", sz, bold=True))

        if paused:
            pause_screen.draw(screen, pygame.mouse.get_pos())

        # Watermark when DSA not implemented
        try:
            board.swap(0, 0, 0, 0)
        except NotImplementedError:
            wm_font = pygame.font.SysFont("Arial", 14)
            wm = wm_font.render("⚠ Implement game/ DSA stubs to play", True, (255, 160, 60))
            screen.blit(wm, (SCREEN_WIDTH // 2 - wm.get_width() // 2, SCREEN_HEIGHT - 28))

        pygame.display.flip()


def main():
    pygame.init()
    snd = SoundManager()
    # Use absolute path for cross-platform compatibility
    music_path = os.path.join(os.path.dirname(__file__), "assets", "sounds", "bgm.ogg")
    snd.start_music(music_path)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Candy Crush — DSA Edition")
    clock = pygame.time.Clock()

    scene = "menu"
    menu  = MenuScreen()
    level_select_screen = None
    gameover_screen = None
    win_screen      = None
    last_score      = 0
    current_level   = 1

    while True:
        dt = clock.tick(FPS) / 1000.0

        if scene == "menu":
            menu.update(dt)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = menu.handle_click(event.pos)
                    if action == "play":
                        snd.play("button")
                        level_select_screen = LevelSelectScreen()
                        scene = "level_select"
                    elif action == "quit":
                        snd.play("button")
                        pygame.quit()
                        sys.exit()
            screen.fill(BG_COLOR)
            menu.draw(screen, pygame.mouse.get_pos())
            pygame.display.flip()

        elif scene == "level_select":
            level_select_screen.update(dt)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = level_select_screen.handle_click(event.pos)
                    if isinstance(action, int):
                        snd.play("button")
                        current_level = action
                        scene = "game"
                    elif action == "menu":
                        snd.play("button")
                        scene = "menu"
            screen.fill(BG_COLOR)
            level_select_screen.draw(screen, pygame.mouse.get_pos())
            pygame.display.flip()

        elif scene == "game":
            result, last_score, current_level = run_game(screen, clock, snd, current_level)
            if result == "quit":
                pygame.quit()
                sys.exit()
            elif result == "menu":
                current_level = 1
                scene = "menu"
            elif result == "gameover":
                snd.play("gameover")
                gameover_screen = GameOverScreen(last_score)
                scene = "gameover"
            elif result == "win":
                snd.play("win")
                win_screen = LevelCompleteScreen(last_score, stars=3)
                current_level += 1
                scene = "win"

        elif scene == "gameover":
            gameover_screen.update(dt)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = gameover_screen.handle_click(event.pos)
                    if action == "retry":
                        snd.play("button")
                        scene = "game"
                    elif action == "menu":
                        snd.play("button")
                        scene = "menu"
            screen.fill(BG_COLOR)
            gameover_screen.draw(screen, pygame.mouse.get_pos())
            pygame.display.flip()

        elif scene == "win":
            win_screen.update(dt)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    action = win_screen.handle_click(event.pos)
                    if action == "next":
                        snd.play("button")
                        scene = "game"
            screen.fill(BG_COLOR)
            win_screen.draw(screen, pygame.mouse.get_pos())
            pygame.display.flip()


if __name__ == "__main__":
    main()
