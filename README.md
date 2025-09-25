# Python Projects Collection

This folder contains a few small, related projects used for Arduino integration and a browser-based multiplayer Snake game prototype. It aims to be a convenient workspace for development and demos.

## Contents

- `ArduinoGUI.py` — A Tkinter desktop GUI that communicates with an Arduino over serial. Features include:

  - Traffic light control interface (Start/Stop/GO/CAUTION/STOP).
  - Humidity & Temperature viewer that polls the Arduino and shows current/high/low stats.
  - Placeholder windows for lock, item detector, and distance measure systems.
  - Uses the `arduino` serial object inside the script; edit the `COM` constant at top to match your system (e.g. `/dev/ttyUSB0`, `/dev/ttyACM0`).

- `server.py` — A Flask web server that serves static templates and runs an asyncio WebSocket server for a simple multiplayer Snake game. The project hosts pages under:

  - `/` — index page (`templates/index.html`)
  - `/game` — game page (`templates/game.html`)
  - `/snake` — multiplayer snake page (`templates/snake.html`) which connects to the WebSocket server started by `server.py`.

- `arduino/Temperature.ino` — Arduino sketch that (presumably) reads temperature and humidity and prints lines expected by `ArduinoGUI.py`. Open and upload this sketch from the Arduino IDE.

- `templates/` — HTML files used by `server.py` (`index.html`, `game.html`, `snake.html`).

## Quick Start

Note: commands below assume a Linux environment (this workspace was developed on Linux). Adjust as needed for Windows/macOS.

1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install --upgrade pip
pip install flask websockets pyserial
```

(If you prefer, create a `requirements.txt` with `flask`, `websockets`, `pyserial` and install from it.)

### Running the Flask + WebSocket server

```bash
python server.py
```

- The Flask app will be available at: http://localhost:5000
- The WebSocket server port is chosen at runtime (preferred 6789/6790); `server.py` prints which port it uses and `server.py` exposes an endpoint `/ws-port` if you need to fetch it programmatically.

### Running the Arduino GUI

Before running:

- Make sure the Arduino is connected and the sketch (`arduino/Temperature.ino`) is uploaded.
- Verify the serial device path (e.g. `/dev/ttyUSB0`, `/dev/ttyACM0`) and update the `COM` constant near the top of `ArduinoGUI.py`.
- On Linux you may need permission to access serial ports. Either run with `sudo` (not recommended) or add your user to the `dialout` group:

```bash
sudo usermod -a -G dialout $USER
# then log out and log back in (or restart your session)
```

Run the GUI:

```bash
python ArduinoGUI.py
```

- The GUI will open a login window (default credentials in the script: `group1` / `group1`).
- The Humidity & Temperature window polls the Arduino and updates a gauge (temperature arc) and a humidity fill bar.

## Arduino sketch

Open `arduino/Temperature.ino` in the Arduino IDE and upload to your board. The GUI expects the Arduino to print humidity and temperature in a line containing tokens like `Humidity:` and `Temperature:` so that the GUI can parse numeric values.

If the Arduino sketch prints different text, update the parser in `ArduinoGUI.py` (`parse_arduino_line`) to match the serial output format.

## Troubleshooting

- Serial port errors: ensure the correct device path and permissions. Use `dmesg` or `ls /dev/tty*` to find the device.
- Dependency errors: ensure your virtualenv is activated and dependencies installed.
- WebSocket connections failing: check that `server.py` prints the selected WebSocket port and that the firewall/port is open locally.

## Next improvements (ideas)

- Add a `requirements.txt` and make a small install script.
- Add command-line options to `ArduinoGUI.py` to select serial port and baud rate.
- Improve the GUI layout and add graphs/history for sensors.
- Add unit tests for server logic and parsing functions.

## License & Contact

This folder contains personal/demo projects. Use freely for learning and prototyping. If you'd like help extending any part, open an issue or contact the author.

---

Created to summarize and document the small projects in this directory.
