import asyncio
import struct
import threading
from collections import deque
from typing import Optional, Tuple

from bleak import BleakClient, BleakScanner


class BalanceBoard:
    """
    Connects to an Arduino-based balance board over BLE, receives raw pitch & roll floats,
    allows origin resetting, and provides current tilt and discrete arrow-key directions.
    """

    # --------------------------------------------
    #                CONSTANTS / TUNING
    # --------------------------------------------
    _AVG_SAMPLES = 5              # how many samples for the moving average
    _NOTIFY_FORMAT = "<ff"        # little-endian Pitch,Roll floats  (# NEW)
    _NOTIFY_SIZE   = struct.calcsize(_NOTIFY_FORMAT)

    def __init__(
        self,
        mac_address: str,
        char_uuid: str = "2a57",
        activate_thresh: float = 5.0,   # degrees needed to fire a direction
        release_thresh: float = 3.0,    # degrees back to centre to release
    ):
        self.mac_address = mac_address
        self.char_uuid = char_uuid

        # last raw reading
        self._raw_pitch: float = 0.0
        self._raw_roll: float = 0.0

        # origin offsets (set by reset_origin)
        self._origin_pitch: float = 0.0
        self._origin_roll: float = 0.0

        # circular buffers for a short moving average  (# NEW)
        self._pitch_hist = deque(maxlen=self._AVG_SAMPLES)
        self._roll_hist  = deque(maxlen=self._AVG_SAMPLES)

        self._activate = activate_thresh
        self._release  = release_thresh

        self._direction: Optional[str] = None      # last direction fired (# NEW)

        # thread-sync
        self._lock          = threading.Lock()
        self._connected_evt = threading.Event()
        self._calibrated    = False

    # ------------------------------------------------------------ #
    #                         Public API                           #
    # ------------------------------------------------------------ #
    def is_connected(self) -> bool:
        return self._connected_evt.is_set()

    def wait_until_connected(self, timeout: Optional[float] = None) -> bool:
        return self._connected_evt.wait(timeout)

    def reset_origin(self) -> None:
        """Call when the board lies flat to set a new zero."""
        with self._lock:
            self._origin_pitch = self._raw_pitch
            self._origin_roll  = self._raw_roll
        print(f"[INFO] Origin reset: pitch={self._origin_pitch:.2f}, roll={self._origin_roll:.2f}")

    # -----------------------  LIVE VALUES  ----------------------- #
    def get_tilt(self) -> Tuple[float, float]:
        """
        Return smoothed (pitch, roll) in degrees, after subtracting the origin
        and *properly* inverting the roll axis so “lean right” is positive.
        """
        with self._lock:
            if not self._pitch_hist:         # no data yet
                return 0.0, 0.0
            pitch = sum(self._pitch_hist) / len(self._pitch_hist)
            roll  = sum(self._roll_hist)  / len(self._roll_hist)

            # FIXED — correct order: (latest_raw − origin) then invert sign
            pitch -= self._origin_pitch
            roll  = -(roll - self._origin_roll)

        return pitch, roll

    def get_direction(self) -> Optional[str]:
        """
        Return 'Up', 'Down', 'Left', 'Right' or None.
        Uses hysteresis so the same key isn’t spammed while you hold a lean.
        """
        pitch, roll = self.get_tilt()

        # currently outside any gesture ─ look for activation
        if self._direction is None:
            if pitch > self._activate:
                self._direction = "Up"
            elif pitch < -self._activate:
                self._direction = "Down"
            elif roll > self._activate:
                self._direction = "Right"
            elif roll < -self._activate:
                self._direction = "Left"
            return self._direction

        # we are *inside* a gesture ─ wait for release back to dead-zone
        if (
            -self._release <= pitch <= self._release
            and -self._release <= roll  <= self._release
        ):
            self._direction = None            # released
        return self._direction

    # -----------------------  Life-cycle  ------------------------ #
    def start(self) -> None:
        """Start BLE scanning/connection in a background thread."""
        threading.Thread(
            target=lambda: asyncio.run(self._ble_main()), daemon=True
        ).start()

    # ------------------------------------------------------------ #
    #                    Internal / BLE helpers                    #
    # ------------------------------------------------------------ #
    async def _ble_main(self) -> None:
        print("[INFO] Scanning for BLE devices…")
        devices = await BleakScanner.discover()
        target = next((d for d in devices if d.address.lower() == self.mac_address.lower()), None)
        if not target:
            print(f"[ERROR] Device {self.mac_address} not found.")
            return

        async with BleakClient(target, timeout=20) as client:
            print(f"[INFO] Connected to {target.address}. Subscribing notifications…")
            await client.start_notify(self.char_uuid, self._notification_handler)
            self._connected_evt.set()
            await asyncio.Event().wait()       # keep task alive

    # -------------------  Notification handler  ------------------ #
    def _notification_handler(self, _: int, data: bytearray) -> None:
        """Decode a <float, float> packet and update state."""
        if len(data) != self._NOTIFY_SIZE:
            print(f"[WARN] Expected {self._NOTIFY_SIZE} bytes, got {len(data)}")
            return

        try:
            pitch, roll = struct.unpack(self._NOTIFY_FORMAT, data)  # FIXED: '<ff'
        except struct.error as exc:
            print(f"[ERROR] Unpack failed: {exc}")
            return

        with self._lock:
            self._raw_pitch = pitch
            self._raw_roll  = roll

            # add to smoothing buffers
            self._pitch_hist.append(pitch)
            self._roll_hist.append(roll)

            # first packet: auto-calibrate
            if not self._calibrated:
                self.reset_origin()
                self._calibrated = True
