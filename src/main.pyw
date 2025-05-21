import time
import tkinter as tk
from balance_board import BalanceBoard
from window import Window
import threading, queue


LANG = "FR"          # ← switch to "EN" for English UI texts
# ──────────────────────────────────────────────────────────────────────────

# English ↔︎ French resources -------------------------------------------------
TEXT = {
    "EN": {
        "dirs": {
            "Up":    "forward",
            "Down":  "backward",
            "Left":  "left",
            "Right": "right",
        },
        "tip_to_start":    "Tip board forward for {sec:.0f} s to start the game.",
        "tip_direction":   "Tip the board {dir} for {sec:.0f} s.",
        "progress":        "{elapsed:.1f}/{total:.1f} seconds",
        "starting_game":   "Starting game!",
        "validated_tick":  "{dir} ✓",
    },
    "FR": {
        "dirs": {
            "Up":    "vers l'avant",
            "Down":  "vers l'arrière",
            "Left":  "à gauche",
            "Right": "à droite",
        },
        "tip_to_start":    "Inclinez la planche vers l'avant pendant {sec:.0f} s pour démarrer le jeu.",
        "tip_direction":   "Inclinez la planche {dir} pendant {sec:.0f} s.",
        "progress":        "{elapsed:.1f}/{total:.1f} secondes",
        "starting_game":   "Démarrage du jeu !",
        "validated_tick":  "{dir} ✓",
    },
}

# BLE / game-play constants ---------------------------------------------------
CHAR_UUID           = "2a57"
TARGET_MAC = "08:70:02:74:C1:DC"  # Unix
#TARGET_MAC          = "C2D3CF52-F199-E073-3987-A8935699F64D"  # macOS example
START_HOLD_SEC      = 5.0
VALIDATION_HOLD_SEC = 3.0
POLL_INTERVAL_MS    = 300           # 20 Hz
DOT_RADIUS          = 10


# ──────────────────────────────────────────────────────────────────────────
#  UI FLOW
# ──────────────────────────────────────────────────────────────────────────
def validate_user_input_visual(root, board: BalanceBoard, on_complete):
    directions = ["Up", "Left", "Right", "Down"]

    canvas = tk.Canvas(root, bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    instruction_label = tk.Label(root, font=("Arial", 24), fg="white", bg="black")
    instruction_label.pack(pady=20)

    progress_label = tk.Label(root, font=("Arial", 18), fg="white", bg="black")
    progress_label.pack(pady=10)

    # current screen size
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()

    # draw the green dot in the centre
    dot_x, dot_y = width // 2, height // 2
    dot = canvas.create_oval(
        dot_x - DOT_RADIUS, dot_y - DOT_RADIUS,
        dot_x + DOT_RADIUS, dot_y + DOT_RADIUS,
        fill="green"
    )

    # ────────────────────────────────────────────────────────────── helpers
    def move_dot(direction: str):
        """Move dot 20 px without letting it leave the canvas."""
        nonlocal dot_x, dot_y, width, height

        # refresh canvas dimensions in case of resize
        width  = canvas.winfo_width()  or width
        height = canvas.winfo_height() or height

        step = 30
        if direction == "Up":
            dot_y = max(DOT_RADIUS, dot_y - step)
        elif direction == "Down":
            dot_y = min(height - DOT_RADIUS, dot_y + step)
        elif direction == "Left":
            dot_x = max(DOT_RADIUS, dot_x - step)
        elif direction == "Right":
            dot_x = min(width - DOT_RADIUS, dot_x + step)

        canvas.coords(dot,
            dot_x - DOT_RADIUS, dot_y - DOT_RADIUS,
            dot_x + DOT_RADIUS, dot_y + DOT_RADIUS
        )

    def reset_dot():
        """Re-centre the dot before each new direction cue."""
        nonlocal dot_x, dot_y
        dot_x, dot_y = width // 2, height // 2
        canvas.coords(dot,
            dot_x - DOT_RADIUS, dot_y - DOT_RADIUS,
            dot_x + DOT_RADIUS, dot_y + DOT_RADIUS
        )

    # ─────────────────────────────────────────────────────────── main loop
    def validate_direction(index: int):
        if index >= len(directions):
            # all four done → ask user to hold forward to start
            instruction_label.config(
                text=TEXT[LANG]["tip_to_start"].format(sec=START_HOLD_SEC)
            )
            wait_for_forward_visual(root, board, on_complete)
            return

        reset_dot()
        direction = directions[index]
        dir_text  = TEXT[LANG]["dirs"][direction]

        instruction_label.config(
            text=TEXT[LANG]["tip_direction"].format(dir=dir_text, sec=VALIDATION_HOLD_SEC)
        )
        progress_label.config(text="")
        start_ts = None

        def poll():
            nonlocal start_ts
            current_dir = board.get_direction()

            if current_dir:
                move_dot(current_dir)

            if current_dir == direction:
                start_ts = start_ts or time.monotonic()
                elapsed  = time.monotonic() - start_ts
                progress_label.config(
                    text=TEXT[LANG]["progress"].format(elapsed=elapsed,
                                                       total=VALIDATION_HOLD_SEC)
                )
                if elapsed >= VALIDATION_HOLD_SEC:
                    progress_label.config(
                        text=TEXT[LANG]["validated_tick"].format(dir=dir_text)
                    )
                    root.after(600, lambda: validate_direction(index + 1))
                    return
            else:
                start_ts = None
                progress_label.config(text="")

            root.after(POLL_INTERVAL_MS, poll)

        poll()

    validate_direction(0)


def wait_for_forward_visual(root, board: BalanceBoard, on_complete):
    start_ts = None
    progress_label = tk.Label(root, font=("Arial", 18), fg="white", bg="black")
    progress_label.pack(pady=10)

    def check_forward():
        nonlocal start_ts
        current_dir = board.get_direction()

        if current_dir == "Up":
            start_ts = start_ts or time.monotonic()
            elapsed  = time.monotonic() - start_ts
            progress_label.config(
                text=TEXT[LANG]["progress"].format(elapsed=elapsed,
                                                   total=START_HOLD_SEC)
            )
            if elapsed >= START_HOLD_SEC:
                progress_label.config(text=TEXT[LANG]["starting_game"])
                root.after(1000, on_complete)
                return
        else:
            start_ts = None
            progress_label.config(text="")

        root.after(POLL_INTERVAL_MS, check_forward)

    check_forward()


# ──────────────────────────────────────────────────────────────────────────
#  GAME LAUNCH
# ──────────────────────────────────────────────────────────────────────────
def main():
    # 1) BLE balance board (already runs its own asyncio thread)
    balance_board = BalanceBoard(TARGET_MAC)
    balance_board.start()

    # 2) Tk root
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")

    # press <space> anywhere to recalibrate
    root.bind_all("<space>", lambda e=None: balance_board.reset_origin())

    # ————————————————————————————————————————————
    # 3) thread-safe sensor polling infrastructure
    # ————————————————————————————————————————————
    class SensorPoller(threading.Thread):
        """
        Polls BalanceBoard.get_direction() in the background and
        drops (“old_dir”, “new_dir”) tuples into a queue.
        """
        def __init__(self, board, out_q, poll_ms):
            super().__init__(daemon=True)
            self.board = board
            self.q     = out_q
            self.poll  = poll_ms / 1000.0
            self.prev  = None
            self.stop  = threading.Event()

        def run(self):
            while not self.stop.is_set():
                new = self.board.get_direction()
                if new != self.prev:
                    self.q.put((self.prev, new))
                    self.prev = new
                time.sleep(self.poll)

    # ————————————————————————————————————————————
    # 4) calibration screen then Pac-Man
    # ————————————————————————————————————————————
    def start_game():
        """
        Builds the game window, starts the background
        Bluetooth poller, and wires the queue into Tk.
        """
        # clear calibration widgets
        for w in root.winfo_children():
            w.destroy()

        pacman  = Window(root)
        msg_q   = queue.Queue()
        poller  = SensorPoller(balance_board, msg_q, POLL_INTERVAL_MS)
        poller.start()

        def restart_game():
            """Kill the poller, reset GUI, and re-enter calibration."""
            poller.stop()
            for w in root.winfo_children():
                w.destroy()
            validate_user_input_visual(root, balance_board, start_game)

        def pump_queue():
            """
            Runs in the **Tk thread**, consuming events produced by the
            SensorPoller and converting them to Tk <KeyPress>/<KeyRelease>.
            """
            try:
                while True:
                    old_dir, new_dir = msg_q.get_nowait()
                    if old_dir:
                        root.event_generate(f"<KeyRelease-{old_dir}>")
                    if new_dir:
                        root.event_generate(f"<KeyPress-{new_dir}>")
            except queue.Empty:
                pass

            # watch for game-over
            if pacman.board.game_over:
                restart_game()
                return

            root.after(10, pump_queue)      # keep looping

        pump_queue()    # prime the first call
        pacman.run()    # starts the game (internally calls mainloop)

    # 5) first show the direction-validation screen
    validate_user_input_visual(root, balance_board, start_game)
    root.mainloop()


if __name__ == "__main__":
    main()