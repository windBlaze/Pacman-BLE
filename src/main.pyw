import time
import tkinter as tk
from balance_board import BalanceBoard
from window import Window

CHAR_UUID = "2a57"
TARGET_MAC = "08:70:02:74:C1:DC"
START_HOLD_SEC = 6.0
THRESHOLD_DEG = 5.0
POLL_INTERVAL_MS = 50  # 20 Hz

def wait_for_forward(board: BalanceBoard, duration: float, threshold: float):
    print(f"Hold board forward (> {threshold}°) for {duration:.1f}s to start...")
    start_ts = None
    while True:
        pitch, _ = board.get_tilt()
        if pitch > threshold:
            start_ts = start_ts or time.monotonic()
            if time.monotonic() - start_ts >= duration:
                print("[INFO] Starting game!")
                return
        else:
            start_ts = None
        time.sleep(0.1)

def main():
    # 1) Start BLE sensor
    board = BalanceBoard(TARGET_MAC, CHAR_UUID)
    board.start()

    # 2) Wait for user to hold board forward for START_HOLD_SEC
    wait_for_forward(board, START_HOLD_SEC, THRESHOLD_DEG)

    # 3) Launch Pacman window
    root = tk.Tk()
    pacman = Window(root)

    # 4) Poll sensor, generate arrow-key events
    prev = {'dir': None}
    def poll_sensor():
        new_dir = board.get_direction()
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

if __name__ == "__main__":
    main()
