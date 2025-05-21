import time
import tkinter as tk
from balance_board import BalanceBoard
from window import Window


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
#  BOILERPLATE  (unchanged from your original logic)
# ──────────────────────────────────────────────────────────────────────────
def main():
    # 1) Start BLE sensor
    balance_board = BalanceBoard(TARGET_MAC, CHAR_UUID)
    balance_board.start()

    print("Waiting for balance board…")
    while not balance_board.wait_until_connected(timeout=10):      # ← pick a timeout you like
        print("Could not connect within 10 s – retrying.") 
        balance_board = BalanceBoard(TARGET_MAC, CHAR_UUID) 
        balance_board.start()

    # 2) Tk root
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")

    # — NEW: press <space> anywhere in the window to recalibrate
    def on_space(event=None):
        print("[INFO] Spacebar pressed → resetting origin")
        balance_board.reset_origin()

    root.bind_all("<space>", on_space)

    # 3) Validate then launch Pac-Man-style window
    def start_game():
        def restart_game():
            """Restart the game from the calibration phase."""
            for widget in root.winfo_children():
                widget.destroy()
            validate_user_input_visual(root, balance_board, start_game)

        for widget in root.winfo_children():
            widget.destroy()

        pacman = Window(root)

        prev = {"dir": None}

        def poll_sensor():
            new_dir = balance_board.get_direction()
            old_dir = prev["dir"]

            if new_dir != old_dir:
                if old_dir:
                    root.event_generate(f"<KeyRelease-{old_dir}>")
                if new_dir:
                    root.event_generate(f"<KeyPress-{new_dir}>")
                prev["dir"] = new_dir

            if pacman.board.game_over:  # Check if the game is over
                print("[INFO] Game over! Restarting...")
                restart_game()
                return

            root.after(POLL_INTERVAL_MS, poll_sensor)

        root.after(POLL_INTERVAL_MS, poll_sensor)
        pacman.run()

    validate_user_input_visual(root, balance_board, start_game)
    root.mainloop()


if __name__ == "__main__":
    main()
