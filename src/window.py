import time
import tkinter as tk

from board   import Board
from gameImage import GameImage
from pacman  import Pacman
from enemy   import Enemy
from pickup  import Pickup
from wall    import Wall


# ──────────────────────────────────────────────────────────────────────────────
FRAME_MS = 16          # one frame every ≈16 ms  → ≈60 fps on any machine
# ──────────────────────────────────────────────────────────────────────────────


class Window:
    def __init__(self, master):
        # --- basic window -----------------------------------------------------
        self._master = master
        self._images = GameImage()

        # native, border-less fullscreen (Esc to leave)
        self._master.attributes('-fullscreen', True)

        self._canvas = tk.Canvas(self._master, background="black")
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # current screen geometry
        self._width  = self._master.winfo_width()  or self._master.winfo_screenwidth()
        self._height = self._master.winfo_height() or self._master.winfo_screenheight()

        # --- HUD --------------------------------------------------------------
        self._score_label = tk.Label(self._master, font=('Arial', 20),
                                     bg='black', fg='white')
        self._level_label = tk.Label(self._master, font=('Arial', 20),
                                     bg='black', fg='white')
        self._lives_label = tk.Label(self._master, font=('Arial', 20),
                                     bg='black', fg='white')

        self._score_label.place(relx=0.05, rely=0.97, anchor='sw')
        self._level_label.place(relx=0.50, rely=0.97, anchor='s')
        self._lives_label.place(relx=0.95, rely=0.97, anchor='se')

        self._master.title('Pacman')

        # --- game model -------------------------------------------------------
        self._bindings_enabled(True)
        self._pause    = False          # toggled with Esc
        self._running  = False          # becomes True in run()
        self.board     = Board(self._width, self._height, self._images)
        self.board.new_level()

    # ────────────────────────────────────────────────────────────────────────
    # drawing helpers
    # ────────────────────────────────────────────────────────────────────────
    def _draw_board(self) -> None:
        """
        Redraw every visible sprite.  All items get the tag 'sprite' so they can
        be wiped in one go next frame without nuking the whole canvas.
        """
        self._canvas.delete('sprite')

        cell_h = self.board.square_height()   # about 24
        cell_w = self.board.square_width()    # about 36

        for obj in self.board.game_objects:
            cx = obj.x * cell_w
            cy = obj.y * cell_h

            if isinstance(obj, Wall):
                self._canvas.create_rectangle(
                    cx, cy,
                    cx + cell_w, cy + cell_h,
                    fill='blue', width=0, tags='sprite'
                )

            elif isinstance(obj, (Pickup, Pacman, Enemy)):
                self._canvas.create_image(
                    cx + cell_w / 2,
                    cy + cell_h / 2,
                    image=obj._image,
                    tags='sprite'
                )

        # flush once, instead of per-item
        self._canvas.update_idletasks()

    def _draw_stats(self) -> None:
        self._score_label['text'] = self.board.pacman.display_score()
        self._level_label['text'] = self.board.pacman.display_level()
        self._lives_label['text'] = self.board.pacman.display_lives()

    def _adjust_board(self) -> None:
        self._draw_board()
        self._draw_stats()

    # ────────────────────────────────────────────────────────────────────────
    # level / state transitions
    # ────────────────────────────────────────────────────────────────────────
    def _check_for_completion(self) -> None:
        if self.board.level_complete():
            self.display_completed()
            self._canvas.after(5000, self.run)          # next level intro

        elif self.board.game_over:
            self._gameover_transition()

        elif self.board.pacman.is_respawning:
            self.board.pacman.is_respawning = False
            self._draw_board()
            # ⬇︎  FIX: pass the callback, do *not* call it now
            self._master.after(550, self._respawn_transition)

        # else: no timer here – the central _game_loop schedules frames

    def display_completed(self) -> None:
        self.board.pacman.direction = None
        self._bindings_enabled(False)
        self._canvas.after(750, self.loading_screen)

    def loading_screen(self) -> None:
        self._canvas.delete('sprite')
        self._canvas.create_image(
            self._width / 2, self._height / 2,
            image=self._images.return_image('loading_screen')
        )
        self._master.after(3500, self.level_advancement)

    def level_advancement(self) -> None:
        self.board.new_level()
        self._bindings_enabled(True)

    def gameover_screen(self) -> None:
        self._canvas.create_image(
            self._width / 2, self._height / 2,
            image=self._images.return_image('over')
        )

    def _gameover_transition(self) -> None:
        self._bindings_enabled(False)
        self.board.pacman._image = None
        self.gameover_screen()

    def _respawn_transition(self) -> None:
        self._adjust_board()
        self.delay_beginning()
        # after the 3-2-1 count-in let normal play resume
        self._master.after(2100, lambda: setattr(self, '_pause', False))

    def delay_beginning(self) -> None:
        def three(): self._canvas.create_image(
            self._width / 2, self._height / 2,
            image=self._images.return_image('three'))
        def two():  self._adjust_board(); self._canvas.create_image(
            self._width / 2, self._height / 2,
            image=self._images.return_image('two'))
        def one():  self._adjust_board(); self._canvas.create_image(
            self._width / 2, self._height / 2,
            image=self._images.return_image('one'))

        self._pause = True                       # freeze gameplay logic
        self._adjust_board()
        self._master.after(100,  three)
        self._master.after(700,  two)
        self._master.after(1300, one)

    # ────────────────────────────────────────────────────────────────────────
    # input
    # ────────────────────────────────────────────────────────────────────────
    def pacmans_direction(self, event: tk.Event) -> None:
        try:
            self.board.pacman.change_direction(event.keysym)

            if not self.board.validate_path(event.keysym):
                self.board.pacman.next_direction = event.keysym
                self.board.pacman.direction      = self.board.pacman.last_direction
            else:
                self.board.pacman.direction_image(self._images)
                self.board.pacman.next_direction = None
        except AttributeError:
            pass

    def check_pause(self) -> None:
        if self._pause:
            self._master.after(1, self.check_pause)

    def _pause_game(self, _event: tk.Event) -> None:
        self._pause = not self._pause
        if not self._pause:
            self.check_pause()          # continue immediately

    def _bindings_enabled(self, enabled: bool) -> None:
        if enabled:
            for key in ('<Left>', '<Right>', '<Up>', '<Down>'):
                self._master.bind(key, self.pacmans_direction)
            self._master.bind('<Escape>', self._pause_game)
        else:
            for key in ('<Left>', '<Right>', '<Up>', '<Down>', '<Escape>'):
                self._master.unbind(key)

    # ────────────────────────────────────────────────────────────────────────
    # main game logic
    # ────────────────────────────────────────────────────────────────────────
    def update(self) -> None:
        """
        Called every frame by _game_loop.
        Handles all gameplay unless the user pressed Esc.
        """
        if self._pause:
            self._canvas.create_image(
                self._width / 2, self._height / 2,
                image=self._images.return_image('game_paused')
            )
            return

        self.board.update_directions()
        self.board.update_board()
        self._check_for_completion()

        if not self.board.game_over:
            self._adjust_board()

    # ────────────────────────────────────────────────────────────────────────
    # frame-rate controlled master loop
    # ────────────────────────────────────────────────────────────────────────
    def _game_loop(self):
        if not self._running:
            return                      # allows clean exit if ever needed

        start = time.perf_counter()
        self.update()
        elapsed = (time.perf_counter() - start) * 1000         # ms
        self._canvas.after(max(0, FRAME_MS - int(elapsed)), self._game_loop)

    # ────────────────────────────────────────────────────────────────────────
    # entry point
    # ────────────────────────────────────────────────────────────────────────
    def run(self) -> None:
        """
        Start game after the opening 3-2-1 countdown.
        """
        self.delay_beginning()                          # visual intro
        self._running = True
        self._master.after(2000, self._game_loop)       # start logic loop
        self._master.mainloop()
