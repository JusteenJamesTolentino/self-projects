import serial

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
BTN_COLOR = "#007acc"
FONT_MAIN = ("Segoe UI", 12)
FONT_TITLE = ("Segoe UI", 16, "bold")


class SerialModel:
    def __init__(self, port="/dev/ttyUSB0", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = None
        try:
            self._serial = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        except Exception:
            self._serial = None

    def send(self, data: str):
        if self._serial:
            try:
                self._serial.write(data.encode())
            except Exception:
                pass
        else:
            print(f"[SerialModel mock] send: {data}")


class AppState:
    def __init__(self):
        self.current_phase = {"state": "OFF", "time_left": 0}
        self.cycle_running = {"active": False}
        self.timer_job = {"job": None}
        self.try_count = {"count": 0}
