import sys
import pygame

pygame.mixer.pre_init(22050, -16, 1, 512)

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR
from game.board import Board
from game.match_finder import MatchFinder
from game.score import ScoreTracker
from game.game_state import GameState, STATE_IDLE, STATE_GAMEOVER, STATE_WIN
from ui.renderer import draw_board
from ui.animations import AnimationManager
from ui.hud import HUD
from ui.screens import MenuScreen, GameOverScreen, LevelCompleteScreen
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
    
    # FIRST: Check for matches immediately (from the swap itself)
    groups = finder.find_matches(board)
    if groups:
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

        # Remove matches and collect activations
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
        anims.add(PopAnim(list(all_to_remove)))
        
        if has_special:
            snd.play("special")
        else:
            snd.play("pop")
    
    # THEN: Continue with gravity + fill chain until board settles
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

        # Remove matches and collect ALL recursive activations
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
        anims.add(PopAnim(list(all_to_remove)))
        
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


def run_game(screen: pygame.Surface, clock: pygame.time.Clock, snd: "SoundManager") -> str:
    """Run one game session. Returns 'menu' or 'quit'."""
    board    = Board()
    finder   = MatchFinder()
    scorer   = ScoreTracker()
    state    = GameState()
    anims    = AnimationManager()
    hud      = HUD()

    selected = None
    t = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "menu"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.is_input_locked or anims.is_busy:
                    continue
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
                        
                        valid, activations = board.swap(r1, c1, r2, c2)
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
                            _run_cascade(board, finder, scorer, anims, snd)
                            state.on_gravity_done(False)
                        else:
                            snd.play("invalid")
                    except NotImplementedError:

                        # DSA not yet implemented — show selection feedback only
                        selected = cell

        # --- Animate & update ---
        anims.update(dt)
        hud.update(dt, scorer.score)

        # --- Check game-over state ---
        if state.current_state == STATE_GAMEOVER:
            return "gameover"
        if state.current_state == STATE_WIN:
            return "win"

        # --- Draw ---
        screen.fill(BG_COLOR)
        draw_board(screen, board, anim_manager=anims, selected=selected, t=t)
        hud.draw(screen, scorer.score, state.moves_left, combo=scorer.combo)

        font = pygame.font.SysFont("Arial", 16)
        anims.draw_floating(screen, font)
        anims.draw_effects(screen, lambda sz: pygame.font.SysFont("Arial", sz, bold=True))

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
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Candy Crush — DSA Edition")
    clock = pygame.time.Clock()

    scene = "menu"
    menu  = MenuScreen()
    gameover_screen = None
    win_screen      = None
    last_score      = 0

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
                        scene = "game"
                    elif action == "quit":
                        snd.play("button")
                        pygame.quit()
                        sys.exit()
            screen.fill(BG_COLOR)
            menu.draw(screen, pygame.mouse.get_pos())
            pygame.display.flip()

        elif scene == "game":
            result = run_game(screen, clock, snd)
            if result == "quit":
                pygame.quit()
                sys.exit()
            elif result == "menu":
                scene = "menu"
            elif result == "gameover":
                snd.play("gameover")
                gameover_screen = GameOverScreen(last_score)
                scene = "gameover"
            elif result == "win":
                snd.play("win")
                win_screen = LevelCompleteScreen(last_score, stars=3)
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
