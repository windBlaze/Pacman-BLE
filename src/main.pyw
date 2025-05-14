import time
import tkinter as tk
from balance_board import BalanceBoard
from window import Window

CHAR_UUID = "2a57"
TARGET_MAC = "35:b1:96:1a:52:77"  # Unix
TARGET_MAC = "C2D3CF52-F199-E073-3987-A8935699F64D"  # Mac
START_HOLD_SEC = 5.0
VALIDATION_HOLD_SEC = 2.0
POLL_INTERVAL_MS = 50  # 20 Hz
DOT_RADIUS = 10

def validate_user_input_visual(root, board: BalanceBoard, on_complete):
    directions = ["Up", "Left", "Right", "Down"]
    canvas = tk.Canvas(root, bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    instruction_label = tk.Label(root, text="", font=("Arial", 24), fg="white", bg="black")
    instruction_label.pack(pady=20)

    progress_label = tk.Label(root, text="", font=("Arial", 18), fg="white", bg="black")
    progress_label.pack(pady=10)

    # Screen size (update lazily in case of resolution change)
    width  = root.winfo_screenwidth()
    height = root.winfo_screenheight()

    # Draw the dot in the middle of the screen
    dot_x, dot_y = width // 2, height // 2
    dot = canvas.create_oval(
        dot_x - DOT_RADIUS, dot_y - DOT_RADIUS,
        dot_x + DOT_RADIUS, dot_y + DOT_RADIUS,
        fill="green"
    )

    def move_dot(direction):
        """Move dot 20 px in the requested direction—but never off-screen."""
        nonlocal dot_x, dot_y, width, height
        # Ask the canvas for its *current* dimensions, so clamping still
        # works if the window is resized after start-up.
        width  = canvas.winfo_width()  or width
        height = canvas.winfo_height() or height

        step = 20
        if direction == "Up":
            dot_y = max(DOT_RADIUS, dot_y - step)
        elif direction == "Down":
            dot_y = min(height - DOT_RADIUS, dot_y + step)
        elif direction == "Left":
            dot_x = max(DOT_RADIUS, dot_x - step)
        elif direction == "Right":
            dot_x = min(width - DOT_RADIUS, dot_x + step)

        canvas.coords(
            dot,
            dot_x - DOT_RADIUS, dot_y - DOT_RADIUS,
            dot_x + DOT_RADIUS, dot_y + DOT_RADIUS,
        )

    def reset_dot_to_centre():
        """Re-centre the dot before starting a new validation direction."""
        nonlocal dot_x, dot_y
        dot_x, dot_y = width // 2, height // 2
        canvas.coords(
            dot,
            dot_x - DOT_RADIUS, dot_y - DOT_RADIUS,
            dot_x + DOT_RADIUS, dot_y + DOT_RADIUS,
        )

    def validate_direction(index: int):
        if index >= len(directions):
            instruction_label.config(
                text=f"Tip board forward for {START_HOLD_SEC:.0f} s to start the game."
            )
            wait_for_forward_visual(root, board, on_complete)
            return

        # Re-centre the dot for the next cue
        reset_dot_to_centre()

        direction = directions[index]
        direction_text = ""
        if direction == "Up":
            direction_text = "forward"
        elif direction == "Down":
            direction_text = "backward"
        else:
            direction_text = direction.lower()
        instruction_label.config(
            text=f"Tip the board {direction} for {VALIDATION_HOLD_SEC:.0f} s."
        )
        progress_label.config(text="")
        start_ts = None

        def poll():
            nonlocal start_ts
            current_direction = board.get_direction()

            # Show real-time dot feedback (but without letting it escape!)
            if current_direction:
                move_dot(current_direction)

            if current_direction == direction:
                start_ts = start_ts or time.monotonic()
                elapsed = time.monotonic() - start_ts
                progress_label.config(
                    text=f"{elapsed:.1f}/{VALIDATION_HOLD_SEC:.0f} s"
                )
                if elapsed >= VALIDATION_HOLD_SEC:
                    progress_label.config(text=f"{direction} ✓")
                    # Give the user a brief moment to see the confirmation
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
    progress_label = tk.Label(root, text="", font=("Arial", 18), fg="white", bg="black")
    progress_label.pack(pady=10)

    def check_forward():
        nonlocal start_ts
        current_direction = board.get_direction()
        if current_direction == "Up":
            start_ts = start_ts or time.monotonic()
            elapsed = time.monotonic() - start_ts
            progress_label.config(text=f"{elapsed:.1f}/{START_HOLD_SEC:.1f} seconds")
            if elapsed >= START_HOLD_SEC:
                progress_label.config(text="Starting game!")
                root.after(1000, on_complete)
                return
        else:
            start_ts = None
            progress_label.config(text="")
        root.after(POLL_INTERVAL_MS, check_forward)

    check_forward()

def main():
    # 1) Start BLE sensor
    balance_board = BalanceBoard(TARGET_MAC, CHAR_UUID)
    balance_board.start()

    # 2) Create tkinter root
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")

    # 3) Validate user input visually
    def start_game():
        for widget in root.winfo_children():
            widget.destroy()
        pacman = Window(root)

        # Poll sensor, generate arrow-key events
        prev = {'dir': None}
        def poll_sensor():
            new_dir = balance_board.get_direction()
            old_dir = prev['dir']
            if new_dir != old_dir:
                if old_dir:
                    root.event_generate(f"<KeyRelease-{old_dir}>")
                if new_dir:
                    root.event_generate(f"<KeyPress-{new_dir}>")
                prev['dir'] = new_dir
            root.after(POLL_INTERVAL_MS, poll_sensor)

        root.after(POLL_INTERVAL_MS, poll_sensor)
        pacman.run()

    validate_user_input_visual(root, balance_board, start_game)

    root.mainloop()

if __name__ == "__main__":
    main()
