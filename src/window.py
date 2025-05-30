import tkinter as tk
from board import Board
from gameImage import GameImage
from pacman import Pacman
from enemy import Enemy
from pickup import Pickup
from wall import Wall

class Window:

    def __init__(self, master):
        '''
        Initializes a Window Object that is the GUI for Pacman. The Window updates
        the GUI accordingly to the progression of the game, by the use of the Board
        object attribute initialized here. '''
        self._master = master
        self._images = GameImage()

        # 1) NATIVE FULLSCREEN MODE (macOS, Windows, Linux)
        # -------------------------------------------------
        # This makes your window truly fullscreen (no titlebar).
        # You can exit with Esc or by toggling this attribute.
        TARGET_W, TARGET_H = 1280, 720          # pick any 4:3 or 16:9 size
        self._master.geometry(f"{TARGET_W}x{TARGET_H}")

        x = (self._master.winfo_screenwidth()  - TARGET_W) // 2
        y = (self._master.winfo_screenheight() - TARGET_H) // 2
        self._master.geometry(f"+{x}+{y}")

        # lock the window so the user can’t drag-resize it
        self._master.resizable(False, False)

        self._canvas = tk.Canvas(
            self._master,
            background="black"
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # You can still track width/height if you need them:
        self._width = self._master.winfo_width() or self._master.winfo_screenwidth()
        self._height = self._master.winfo_height() or self._master.winfo_screenheight()

        self._master.update_idletasks()        # forces a geometry calculation
        self._width  = self._master.winfo_width()
        self._height = self._master.winfo_height()

        # Stats labels (you’ll likely want to overlay or place them differently in fullscreen):
        self._score_label = tk.Label(self._master, text='0', font=('Arial', 20), bg='black', fg='white')
        self._level_label = tk.Label(self._master, text='0', font=('Arial', 20), bg='black', fg='white')
        self._lives_label = tk.Label(self._master, text='0', font=('Arial', 20), bg='black', fg='white')

        # Place them in the same row—but you can adjust x/y coordinates for fullscreen:
        self._score_label.place(relx=0.05, rely=0.97, anchor='sw')
        self._level_label.place(relx=0.50, rely=0.97, anchor='s')
        self._lives_label.place(relx=0.95, rely=0.97, anchor='se')

        self._master.title('Pacman')

        # Bindings, game init, etc., stay the same…
        self._bindings_enabled(True)
        self._pause = False

        self.board = Board(self._width, self._height, self._images)
        self.board.new_level()

    # Drawing Functions #
    def _draw_board(self) -> None:
        ''' Draws the board given the game_objs in the board's set. '''
        total_height = self.board.square_height() # Approximately ~24
        total_width = self.board.square_width()   # Approximately ~36
        
        for game_obj in self.board.game_objects:
            if type(game_obj) == Wall:
                self._canvas.create_rectangle(game_obj.x * total_width,
                                              game_obj.y * total_height,
                                              (game_obj.x * total_width / total_width + 1) * total_width,
                                              (game_obj.y * total_height / total_height + 1) * total_height,
                                              fill = 'blue', width = 0)
        
            elif type(game_obj) == Pickup or type(game_obj) == Pacman or type(game_obj) == Enemy:
                self._canvas.create_image( game_obj.x * total_width + (total_width / 2),
                                           game_obj.y * total_height + (total_height / 2), image = game_obj._image)


    def _draw_stats(self) -> None:
        ''' Draws the statistics of Pacman for the player to see. '''
        self._score_label['text'] = self.board.pacman.display_score()
        self._level_label['text'] = self.board.pacman.display_level()
        self._lives_label['text'] = self.board.pacman.display_lives()

    def _adjust_board(self) -> None:
        ''' Deletes the board and then redraws to prevent animation overlapping. '''
        self._canvas.delete(tk.ALL)
        self._draw_board()
        self._draw_stats()

    # Level Completion / Transitioning Functions #
    def _check_for_completion(self) -> None:
        ''' Checks for completion of the level. If so, then displayCompleted is called
            to assist in the transition of the level change and loading screen. If not,
            then update the game as normal. '''
        # Completed Level GUI #
        if self.board.level_complete():
            self.display_completed()
            self._canvas.after(5000, self.run)

        # Gameover -> Stops Updating / Transitions to Gameover Screen #
        elif self.board.game_over:
            self._gameover_transition()

        elif self.board.pacman.is_respawning:
            self.board.pacman.is_respawning = False
            self._draw_board()
            self._master.after(550, self._respawn_transition())
            
        # Game Progress #
        else:
            self._canvas.after(400, self.update)
    
    def display_completed(self) -> None:
        ''' This functions is to add a proper transition between the completed
            level and the loading screen. Mainly for visual purposes to appear nicer. '''
        self.board.pacman.direction = None
        self._bindings_enabled(False)       # bindings are disabled during loading screen
        self._canvas.after(750, self.loading_screen)

    def loading_screen(self) -> None:
        ''' Adds a loading screen transition in between levels. '''
        self._canvas.delete(tk.ALL)
        self._canvas.create_image( self._width / 2, self._height / 2,
                                   image = self._images.return_image('loading_screen') )
        
        self._master.after(3500, self.level_advancement)

    def level_advancement(self) -> None:
        ''' Board loads up a new level once the previous level is completed. '''
        self.board.new_level()
        self._bindings_enabled(True)

    def gameover_screen(self) -> None:
        ''' Creates an image to display to the User when it is Game Over. '''
        self._canvas.create_image( self._width / 2, self._height / 2,
                                   image = self._images.return_image('over') )

    def _gameover_transition(self) -> None:
        self._bindings_enabled(False)       # bindings are disabled when game is over
        self.board.pacman._image = None     # pacman is no longer on the board, so no image required
        self.gameover_screen()

        
    def _respawn_transition(self) -> None:
        ''' Allows a transition to be in between respawning so that the game does not
            continue too quickly. '''
        self._adjust_board()
        self.delay_beginning()
        
        self._master.after(2100, self.update)
        
    def delay_beginning(self) -> None:
        ''' Delays the game by a short amount of time with GUI to
            inform the player when the game is going to start. This is
            in order to prevent the game starting immediately and affecting
            gameplay. '''
        def three():
            self._canvas.create_image(self._width / 2, self._height / 2,
                                                  image = self._images.return_image('three') )

        def two():
            self._adjust_board()
            self._canvas.create_image(self._width / 2, self._height / 2,
                                                  image = self._images.return_image('two') )

        def one():
            self._adjust_board()
            self._canvas.create_image(self._width / 2, self._height / 2,
                                                  image = self._images.return_image('one') )
        
        self._adjust_board()
        self._master.after(1300, three)
        self._master.after(1300, two)
        self._master.after(1300, one)
        
    # (Player) Binding Functions #
    def pacmans_direction(self, event: tk.Event) -> None:
        ''' Function that allows the player to move Pacman. Directions have
            to be validated in order to avoid stopped movement. nextDirection
            and lastDirection allow smoother control of Pacman. '''
        try:
            self.board.pacman.change_direction(event.keysym)

            if not self.board.validate_path( event.keysym ):
                self.board.pacman.next_direction = event.keysym
                self.board.pacman.direction = self.board.pacman.last_direction

            else:
                self.board.pacman.direction_image( self._images )
                self.board.pacman.next_direction = None

        except AttributeError:
            pass

    def check_pause(self) -> None:
        ''' Check_pause constantly calls itself to check when the player
            no longer wants the game to be paused. If so, then calls the
            update() function which will continue the game. '''
        if self._pause:
            self._master.after(1, self.check_pause)
        else:
            self.update()
    
    def _pause_game(self, event: tk.Event) -> None:
        ''' Pauses or unpauses the game by pressing the esc key. '''
        self._pause = not self._pause

    def _bindings_enabled(self, enabled: bool) -> None:
        ''' The boolean argument is what decides if the bindings are enabled or
            disabled. The bindings are enabled during play, but disabled in betwene
            level transition, specifically during the loading screen. '''
        if enabled:
            self._master.bind('<Left>', self.pacmans_direction)
            self._master.bind('<Right>', self.pacmans_direction)
            self._master.bind('<Up>', self.pacmans_direction)
            self._master.bind('<Down>', self.pacmans_direction)
            self._master.bind('<Escape>', self._pause_game)

        else:
            self._master.unbind('<Left>')
            self._master.unbind('<Right>')
            self._master.unbind('<Up>')
            self._master.unbind('<Down>')
            self._master.unbind('<Escape>')

    # Main Functions #
    def update(self) -> None:
        '''
        Updates the game consistently throughout the game. Also, updates the
        directions of the player, and the objects that are on the board as objects
        are removed from the board by the player.
        '''

        if not self._pause:
            self.board.update_directions()
            self.board.update_board()
            self._check_for_completion()

            if not self.board.game_over:
                self._adjust_board()
            
        else:
            self._canvas.create_image(self._width / 2, self._height / 2,
                                      image = self._images.return_image('game_paused') )
            self.check_pause()

    def run(self) -> None:
        self.delay_beginning()
        self._master.after(2000, self.update) # put again here to allow mainloop() to still occur and also call gameloop
        self._master.mainloop()

