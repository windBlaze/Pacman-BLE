import asyncio
import struct
import threading
from bleak import BleakClient, BleakScanner

class BalanceBoard:
    """
    Connects to an Arduino-based balance board over BLE, receives raw pitch & roll floats,
    allows origin resetting, and provides current tilt and discrete arrow-key directions.
    """
    def __init__(
        self,
        mac_address: str,
        char_uuid: str = "2a57",
        forward_thresh: float = 5.0,
        release_thresh: float = 3.0,
    ):
        self.mac_address = mac_address
        self.char_uuid = char_uuid
        self.latest_pitch = 0.0
        self.latest_roll = 0.0
        self.origin_pitch = 0.0
        self.origin_roll = 0.0
        self.forward_thresh = forward_thresh
        self.release_thresh = release_thresh

    def reset_origin(self):  # call this to recalibrate flat board
        self.origin_pitch = self.latest_pitch
        self.origin_roll = self.latest_roll
        print("[INFO] Origin reset to pitch=%.2f, roll=%.2f" % (self.origin_pitch, self.origin_roll))

    def get_tilt(self) -> tuple[float, float]:
        """Return (pitch, roll) after subtracting origin and inverting roll axis."""
        pitch = self.latest_pitch - self.origin_pitch
        roll = -self.latest_roll - self.origin_roll
        return pitch, roll

    def get_direction(self) -> str | None:
        """Map tilt to one of the arrow-key directions or None."""
        pitch, roll = self.get_tilt()
        if pitch > self.forward_thresh:
            return 'Up'
        if pitch < -self.forward_thresh:
            return 'Down'
        if roll > self.forward_thresh:
            return 'Right'
        if roll < -self.forward_thresh:
            return 'Left'
        return None

    def start(self):
        """Scan, connect, and subscribe in a background thread."""
        thread = threading.Thread(target=lambda: asyncio.run(self._ble_main()), daemon=True)
        thread.start()

    async def _ble_main(self):
        print("[INFO] Scanning for BLE devices...")
        devices = await BleakScanner.discover()
        target = next((d for d in devices if d.address.lower() == self.mac_address.lower()), None)
        if not target:
            print(f"[ERROR] Device {self.mac_address} not found.")
            return
        async with BleakClient(target.address) as client:
            print(f"[INFO] Connected to {target.address}. Subscribing...")
            await client.start_notify(self.char_uuid, self._notification_handler)
            await asyncio.Event().wait()  # keep running

    def _notification_handler(self, _: int, data: bytearray):
        """Unpack two floats (pitch, roll) from the incoming bytes."""
        try:
            pitch, roll = struct.unpack('ff', data)
            self.latest_pitch = pitch
            self.latest_roll = roll
        except Exception as e:
            print(f"[ERROR] Failed to unpack data: {e}")
