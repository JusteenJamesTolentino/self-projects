
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sys
import time
import json
import threading
import asyncio

try:
    from data_logger import log_reading, load_entries, compute_stats, clear_log, export_csv
except Exception:
    def log_reading(kind, data):
        pass


    def load_entries(limit=None):
        return []


    def compute_stats(entries):
        return {"count": 0}


    def clear_log():
        return False


    def export_csv(dest):
        return False

try:

    import serial
    from serial.tools import list_ports

except Exception:
    messagebox.showerror("Error", "Failed to import serial libraries.")
    serial = None
    list_ports = None

# Optional Facebook integration
try:
    from fbchat_muqit import Client, Message, ThreadType, Mention
    FB_AVAILABLE = True
except Exception:
    Client = object  # placeholder
    Message = object
    ThreadType = object
    Mention = object
    FB_AVAILABLE = False

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
BTN_COLOR = "#007acc"
FONT_MAIN = ("Segoe UI", 12)
FONT_TITLE = ("Segoe UI", 16, "bold")
arduino = None
SERIAL_LOCK = threading.Lock()

# Facebook bridge (initialized later)
FB_MANAGER = None

# Persistent RFID authorization store
AUTH_FILE = "authorized_rfid.json"
ADMIN_UIDS = {"29:4C:62:12"}  # Predefined admin cards (normalized uppercase)
AUTH_NAMES_FILE = "authorized_users.json"  # UID -> display name mapping

# Simple current session store
CURRENT_USER = {"uid": None, "is_admin": False, "name": None}


def load_authorized_uids():
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(str(x).strip().upper() for x in data if x)
    except Exception:
        pass
    return set()


def save_authorized_uids(uids):
    try:
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(uids)), f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


authorized_uids = load_authorized_uids()


def load_authorized_names():
    try:
        with open(AUTH_NAMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k).strip().upper(): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_authorized_names(name_map):
    try:
        norm = {str(k).strip().upper(): str(v) for k, v in name_map.items()}
        with open(AUTH_NAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(norm, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


authorized_names = load_authorized_names()


def auto_detect_serial():
    if list_ports is None:
        return None
    ports = list_ports.comports()
    if not ports:
        return None

    plat = sys.platform.lower()

    def score(p):
        dev = getattr(p, 'device', '') or ''
        desc = (getattr(p, 'description', '') or '').lower()
        mfg = (getattr(p, 'manufacturer', '') or '').lower()
        pr = 100
        # Manufacturer/description hints
        if 'arduino' in desc or 'arduino' in mfg or 'genuino' in desc or 'genuino' in mfg:
            pr -= 20
        if 'ch340' in desc or 'wch' in desc or 'wch' in mfg or 'cp210' in desc or 'ftdi' in desc:
            pr -= 5

        if plat.startswith('linux'):
            if '/dev/ttyusb' in dev:
                pr = min(pr, 1)
            elif '/dev/ttyacm' in dev:
                pr = min(pr, 2)
            elif '/dev/tty' in dev:
                pr = min(pr, 50)
        elif plat.startswith('darwin'):
            if '/dev/tty.usbmodem' in dev:
                pr = min(pr, 1)
            elif '/dev/tty.usbserial' in dev:
                pr = min(pr, 2)
            elif '/dev/cu.' in dev:
                pr = min(pr, 20)
        elif plat.startswith('win'):
            if dev.upper().startswith('COM'):
                pr = min(pr, 10)
        else:
            # Unknown platform: prefer anything with tty/usb
            if 'usb' in dev.lower():
                pr = min(pr, 10)

        # Prefer ports with a valid VID/PID as a slight hint they are real USB serial
        vid = getattr(p, 'vid', None)
        pid = getattr(p, 'pid', None)
        if vid is not None and pid is not None:
            pr -= 2

        return pr

    best = None
    best_score = None
    for p in ports:
        s = score(p)
        if best is None or s < best_score:
            best = p
            best_score = s
    return best.device if best else None


def init_serial(port=None, baudrate=9600, timeout=1):
    global arduino
    if serial is None:
        return False
    try:
        if port is None:
            port = auto_detect_serial()
        if port is None:
            return False
        if arduino is not None and hasattr(arduino, 'is_open') and arduino.is_open:
            try:
                arduino.close()
            except Exception:
                pass
        arduino = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        print(f"[Serial] Connected to {port}")
        return True
    except Exception as e:
        print(f"[Serial] Could not open port {port}: {e}")
        arduino = None
        return False


def close_serial():
    global arduino
    try:
        if arduino is not None and hasattr(arduino, 'is_open') and arduino.is_open:
            arduino.close()
    except Exception:
        pass
    arduino = None


def is_serial_connected():
    return arduino is not None and hasattr(arduino, 'is_open') and arduino.is_open


def send_command(command):
    if is_serial_connected():
        try:
            # Ensure thread-safe serial writes if Facebook bot also sends commands
            try:
                lock = SERIAL_LOCK
            except Exception:
                lock = None
            if lock:
                with lock:
                    arduino.write(command.encode())
            else:
                arduino.write(command.encode())
            print(f"OUTPUT -> {command}")
        except Exception as e:
            print(f"[Serial] Write failed: {e}")
    else:
        print(f"[Serial] Not connected, would send: {command}")


# ---- Facebook Bot integration ----
if FB_AVAILABLE:
    class GuiBot(Client):
        # Defaults (use your values)
        TEST_THREAD_ID = "757293467310599"
        BOT_MODE = "TEST"  # TEST: only respond in TEST_THREAD_ID; GLOBAL: respond anywhere
        OWNER_ID = "100088164532775"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.gui_notify = None  # callable: (status_text, connected:bool) -> None
            self._name_cache = {}

        async def _get_name(self, uid: str) -> str:
            try:
                if uid in self._name_cache:
                    return self._name_cache[uid]
                info = await self.fetchUserInfo(uid)
                if isinstance(info, dict) and uid in info:
                    name = getattr(info[uid], "name", None) or getattr(info[uid], "full_name", None)
                    if name:
                        self._name_cache[uid] = name
                        return name
            except Exception:
                pass
            return uid

        async def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type=None, **kwargs):
            # Default thread type when available
            print(f"[FB] Message from {author_id} in {thread_id} ({thread_type}): {message}")
            if thread_type is None and FB_AVAILABLE:
                try:
                    thread_type = ThreadType.USER
                except Exception:
                    thread_type = None
            text = (message or getattr(message_object, 'text', '') or '').strip()
            if not text:
                return

            # Mode restriction
            if str(self.BOT_MODE).upper() == "TEST" and str(thread_id) != str(self.TEST_THREAD_ID):
                return

            parts = text.split()
            if len(parts) < 2:
                return
            if parts[0].lower() != "bot":
                return

            cmd = parts[1].lower()

            async def reply(msg: str):
                try:
                    await self.sendMessage(msg, thread_id=thread_id, thread_type=thread_type, reply_to_id=getattr(message_object, 'uid', None))
                except Exception:
                    pass

            # Basic help
            if cmd == "help":
                await reply(
                    "🤖 Bot Controls:\n"
                    "• bot tms <go|caution|stop|off> — control traffic lights\n"
                    "• bot led <green|yellow|red|off> — same as tms\n"
                    "• bot distance <once> — single ultrasonic read (logged)\n"
                    "• bot stream <on|off> — ultrasonic streaming toggle\n"
                    "• bot env — read humidity & temperature (logged)\n"
                    "• bot who — show current GUI user\n"
                    "• bot mode — show current bot mode\n"
                )
                return

            # Simple status
            if cmd == "mode":
                await reply(f"🧩 Mode: {self.BOT_MODE}")
                return

            # Hardware controls via Arduino serial (write-only; GUI handles reads/logging)
            if cmd in ("tms", "led") and len(parts) >= 3:
                arg = parts[2].lower()
                m = {"go": "G", "green": "G", "caution": "Y", "yellow": "Y", "stop": "R", "red": "R", "off": "C"}
                if arg in m:
                    send_command(m[arg])
                    await reply(f"✅ {cmd} -> {arg}")
                else:
                    await reply("Usage: bot tms <go|caution|stop|off>")
                return

            if cmd == "distance" and len(parts) >= 3:
                if parts[2].lower() == "once":
                    send_command('U')
                    await reply("📏 Requested one distance sample.")
                    return
                await reply("Usage: bot distance once")
                return

            if cmd == "stream" and len(parts) >= 3:
                arg = parts[2].lower()
                if arg in ("on", "start"):
                    send_command('L')
                    await reply("📡 Streaming ON")
                elif arg in ("off", "stop"):
                    send_command('S')
                    await reply("📡 Streaming OFF")
                else:
                    await reply("Usage: bot stream <on|off>")
                return

            if cmd == "env":
                # Trigger a fresh read; GUI will log it
                send_command('R')
                await reply("🌡️ Requested humidity & temperature.")
                return

            if cmd == "who":
                name = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "(no session)"
                role = "Admin" if CURRENT_USER.get("is_admin") else ("User" if CURRENT_USER.get("uid") else "-")
                await reply(f"👤 Current GUI user: {name} ({role})")
                return

            await reply("❓ Unknown command. Try `bot help`.")

    class FacebookManager:
        def __init__(self):
            self.thread = None
            self.loop = None
            self.bot = None
            self.connected = False
            self.name = None
            self.uid = None
            self._status_cb = None

        def start(self, status_cb=None, cookies_path: str = "./fbstate.json"):
            if self.thread and self.thread.is_alive():
                return
            self._status_cb = status_cb
            self.thread = threading.Thread(target=self._thread_main, args=(cookies_path,), daemon=True)
            self.thread.start()

        def _thread_main(self, cookies_path: str):
            asyncio.run(self._run(cookies_path))

        async def _run(self, cookies_path: str):
            try:
                if self._status_cb:
                    self._status_cb("FB: Connecting…", False)
                bot = await GuiBot.startSession(cookies_path)
                self.bot = bot
                self.loop = asyncio.get_running_loop()
                # Fetch self name
                if await bot.isLoggedIn():
                    info = await bot.fetchUserInfo(bot.uid)
                    display = None
                    if isinstance(info, dict) and bot.uid in info:
                        display = getattr(info[bot.uid], 'name', None) or getattr(info[bot.uid], 'full_name', None)
                    self.name = display or str(bot.uid)
                    self.uid = bot.uid
                    self.connected = True
                    if self._status_cb:
                        self._status_cb(f"FB: Connected as {self.name}", True)
                await bot.listen()
            except Exception as e:
                if self._status_cb:
                    self._status_cb("FB: Connection error", False)
            finally:
                self.connected = False
                if self._status_cb:
                    self._status_cb("FB: Disconnected", False)

        def notify_access(self, text: str):
            try:
                if not (self.bot and self.loop and self.connected):
                    return
                async def _send():
                    try:
                        await self.bot.sendMessage(text, thread_id=self.bot.TEST_THREAD_ID, thread_type=ThreadType.USER)
                    except Exception:
                        pass
                asyncio.run_coroutine_threadsafe(_send(), self.loop)
            except Exception:
                pass

        def stop(self):
            # Best-effort: no clean stop available without library hooks. User can leave it running.
            pass
else:
    class FacebookManager:
        def __init__(self):
            self.connected = False
            self.name = None
        def start(self, status_cb=None, cookies_path: str = "./fbstate.json"):
            if status_cb:
                status_cb("FB: Not available", False)
        def notify_access(self, text: str):
            pass
        def stop(self):
            pass


# Small helper to safely send Facebook notifications (if connected)
def fb_notify(text: str):
    try:
        global FB_MANAGER
        if FB_MANAGER is None:
            return
        FB_MANAGER.notify_access(text)
    except Exception:
        pass


def apply_dark_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG_COLOR)
    style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR, font=FONT_MAIN)
    style.configure("TButton", background=BTN_COLOR, foreground="white", font=FONT_MAIN, padding=6)
    style.map("TButton", background=[("active", "#005f87")], foreground=[("disabled", "#888888")])
    style.configure("TEntry", fieldbackground="#2d2d2d", foreground=FG_COLOR, padding=5)
    style.map("TEntry", fieldbackground=[("active", "#3c3c3c")])


def draw_rounded_rect(canvas, x1, y1, x2, y2, r=20, **kwargs):
    points = [
        (x1 + r, y1),
        (x2 - r, y1),
        (x2, y1 + r),
        (x2, y2 - r),
        (x2 - r, y2),
        (x1 + r, y2),
        (x1, y2 - r),
        (x1, y1 + r)
    ]

    coords = []
    for p in points:
        for coord in p:
            coords.append(coord)

    return canvas.create_polygon(coords, smooth=True, splinesteps=20, **kwargs)


def login_window():
    login = tk.Tk()
    login.title("Login")
    login.geometry("620x460")
    login.configure(bg=BG_COLOR)
    apply_dark_theme(login)

    container = ttk.Frame(login)
    container.pack(expand=True, fill="both")

    canvas_card = tk.Canvas(container, width=360, height=240, bg=BG_COLOR, highlightthickness=0)
    canvas_card.pack(pady=10)

    draw_rounded_rect(canvas_card, 6, 6, 354, 234, r=16, fill="#262626", outline="#3a3a3a")

    card = ttk.Frame(container, padding=(24, 18), style="Card.TFrame")

    card.place(in_=canvas_card, x=12, y=12)

    ttk.Label(card, text="GROUP 1", font=("Segoe UI", 18, "bold"), foreground=FG_COLOR, background=BG_COLOR).pack()
    ttk.Label(card, text="Arduino System — Login", font=("Segoe UI", 10), foreground="#bfc7d6",
              background=BG_COLOR).pack(pady=(0, 12))

    form = ttk.Frame(card)
    form.pack(pady=(6, 4))

    username_entry = ttk.Entry(form, width=28, foreground="#bfc7d6")
    username_entry.grid(row=0, column=0, columnspan=2, pady=(6, 8))

    password_entry = ttk.Entry(form, width=28, foreground="#bfc7d6")
    password_entry.grid(row=1, column=0, columnspan=2, pady=(2, 6))

    def add_placeholder(entry, placeholder, is_password=False):
        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground=FG_COLOR)
                if is_password and not show_state["visible"]:
                    entry.config(show="*")

        def on_focus_out(event):
            if entry.get() == "":
                entry.insert(0, placeholder)
                entry.config(foreground="#bfc7d6")
                if is_password:
                    entry.config(show="")

        entry.insert(0, placeholder)
        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    add_placeholder(username_entry, "Username")
    add_placeholder(password_entry, "Password", is_password=True)

    show_state = {"visible": False}

    def toggle_show():
        show_state["visible"] = not show_state["visible"]

        if show_state["visible"]:
            password_entry.config(show="")
            eye_btn.config(text="👁️")
        else:
            password_entry.config(show="*")
            eye_btn.config(text="🙈")

    eye_btn = ttk.Button(form, text="🙈", width=3, command=toggle_show)
    eye_btn.grid(row=1, column=2, padx=(8, 0))

    error_label = ttk.Label(card, text="", foreground="#ff6b6b", background=BG_COLOR)
    error_label.pack(pady=(4, 0))

    try_count = {"count": 0}

    def verify_login(event=None):
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if username == "group1" and password == "group1":
            CURRENT_USER["name"] = username
            login.destroy()
            main_menu()
        else:
            try_count["count"] += 1
            remaining = max(0, 3 - try_count["count"])
            error_label.config(text=f"Invalid credentials. {remaining} attempts left.")
            if try_count["count"] >= 3:
                login.destroy()

    def close_window():
        login.destroy()

    action_frame = ttk.Frame(card)
    action_frame.pack(pady=(14, 0), fill="x")

    btn_frame = ttk.Frame(action_frame)
    btn_frame.pack(anchor="center")

    login_btn = ttk.Button(btn_frame, text="Sign in", command=verify_login, width=10)
    login_btn.pack(side=tk.LEFT, padx=(0, 8))

    cancel_btn = ttk.Button(btn_frame, text="Cancel", command=close_window, width=10)
    cancel_btn.pack(side=tk.LEFT)

    # --- RFID Login Section ---
    rfid_sep = ttk.Label(card, text="──────── or ────────", foreground="#6b7280", background=BG_COLOR)
    rfid_sep.pack(pady=(12, 6))

    rfid_status = ttk.Label(card, text="Scan your RFID to sign in", foreground="#bfc7d6", background=BG_COLOR)
    rfid_status.pack(pady=(0, 6))

    scan_state = {"active": False, "job": None}

    def extract_uid(line: str):
        try:
            if not line:
                return None
            text = line
            if isinstance(line, bytes):
                try:
                    text = line.decode(errors="ignore")
                except Exception:
                    text = str(line)
            text = text.strip()
            if not text:
                return None
            if "UID" in text:
                # support formats like 'UID: 29:4C:62:12' or 'Card UID: 12 34 56 78'
                part = text.split("UID:")[-1]
                raw = part.replace(" ", "").replace("-", ":").replace("::", ":").upper().strip()
                # normalize to colon-separated hex pairs if possible
                if raw and all(c in "0123456789ABCDEF:" for c in raw):
                    return raw
                return raw
        except Exception:
            return None
        return None

    def stop_rfid_login():
        scan_state["active"] = False
        if scan_state["job"]:
            try:
                login.after_cancel(scan_state["job"])
            except Exception:
                pass
            scan_state["job"] = None

    def rfid_tick():
        if not scan_state["active"]:
            return
        # Try connect if needed
        if not is_serial_connected():
            ok = init_serial(port=None)
            if not ok:
                rfid_status.config(text="No serial device found… retrying…")
                scan_state["job"] = login.after(600, rfid_tick)
                return
        # Read one line
        try:
            try:
                arduino.reset_input_buffer()
            except Exception:
                pass
            line = arduino.readline()
            if isinstance(line, bytes):
                line = line.decode(errors="ignore").strip()
            else:
                line = str(line).strip()
        except Exception:
            line = ""
        uid = extract_uid(line)
        if uid:
            stop_rfid_login()
            normalized = uid.upper()
            is_admin = normalized in ADMIN_UIDS
            if normalized in authorized_uids or is_admin:
                role = "Admin" if is_admin else "User"
                display_name = authorized_names.get(normalized, normalized)
                rfid_status.config(text=f"RFID recognized: {display_name} ({role})")
                CURRENT_USER["uid"] = normalized
                CURRENT_USER["is_admin"] = is_admin
                CURRENT_USER["name"] = display_name
                login.destroy()
                main_menu()
                return
            else:
                rfid_status.config(text=f"RFID not authorized: {normalized}")
                messagebox.showwarning("RFID", "Card not authorized.")
        else:
            rfid_status.config(text="Waiting for RFID…")
        scan_state["job"] = login.after(400, rfid_tick)

    def start_rfid_login():
        if scan_state["active"]:
            stop_rfid_login()
            rfid_status.config(text="Scan cancelled.")
            return
        scan_state["active"] = True
        rfid_status.config(text="Hold your RFID near the reader…")
        rfid_tick()

    scan_btn = ttk.Button(card, text="Scan RFID to Sign in", command=start_rfid_login, width=24)
    scan_btn.pack(pady=(0, 8))

    login.bind('<Return>', verify_login)

    username_entry.focus_set()

    login.mainloop()


def main_menu():
    menu = tk.Tk()
    menu.title("Main Menu")
    menu.geometry("650x550")
    menu.configure(bg=BG_COLOR)
    apply_dark_theme(menu)

    title = "MAIN MENU"
    if CURRENT_USER.get("uid"):
        role = "Admin" if CURRENT_USER.get("is_admin") else "User"
        display = CURRENT_USER.get("name") or CURRENT_USER.get("uid")
        title = f"MAIN MENU — {display} ({role})"
    ttk.Label(menu, text=title, font=FONT_TITLE).pack(pady=20)

    status_frame = ttk.Frame(menu)
    status_frame.pack(pady=(0, 6))
    serial_status_var = tk.StringVar()
    if is_serial_connected():
        serial_status_var.set("Serial: Connected")
    else:
        serial_status_var.set("Serial: Disconnected")
    serial_label = ttk.Label(status_frame, textvariable=serial_status_var, font=("Segoe UI", 10))
    serial_label.pack(side=tk.LEFT, padx=(0, 12))

    # Facebook status (optional)
    fb_status_var = tk.StringVar(value="FB: Not connected")
    fb_label = ttk.Label(status_frame, textvariable=fb_status_var, font=("Segoe UI", 10))
    fb_label.pack(side=tk.LEFT, padx=(0, 12))

    def toggle_serial():
        if is_serial_connected():
            close_serial()
            serial_status_var.set("Serial: Disconnected")
            toggle_btn.config(text="Connect")
        else:
            ok = init_serial(port=None)
            if ok:
                detected = getattr(arduino, 'port', None)
                if detected:
                    serial_status_var.set(f"Serial: Connected ({detected})")
                else:
                    serial_status_var.set("Serial: Connected")
                toggle_btn.config(text="Disconnect")
            else:
                candidate = auto_detect_serial()
                if candidate:
                    messagebox.showwarning("Serial", f"Could not connect to serial port: {candidate}")
                else:
                    messagebox.showwarning("Serial", "No serial ports found on this system.")

    if is_serial_connected():
        btn_text = "Disconnect"
    else:
        btn_text = "Connect"
    toggle_btn = ttk.Button(status_frame, text=btn_text, command=toggle_serial, width=10)
    toggle_btn.pack(side=tk.LEFT)

    # --- Facebook Controls ---
    def fb_status_update(text: str, ok: bool):
        try:
            # Ensure UI updates occur on Tk thread
            menu.after(0, lambda: fb_status_var.set(text))
        except Exception:
            pass

    def toggle_facebook():
        # Use a shared global manager
        global FB_MANAGER
        if FB_MANAGER is None:
            FB_MANAGER = FacebookManager()
        # Start only; stop is best-effort no-op
        FB_MANAGER.start(status_cb=fb_status_update, cookies_path="./fbstate.json")

    fb_btn = ttk.Button(status_frame, text="Connect FB", command=toggle_facebook, width=12)
    # Only enable if module available
    if not FB_AVAILABLE:
        fb_btn.config(state=tk.DISABLED)
        fb_status_var.set("FB: Not available")
    fb_btn.pack(side=tk.LEFT, padx=(8, 0))

    def open_tms():
        menu.destroy()
        traffic_light_control()

    btn_frame = ttk.Frame(menu)
    btn_frame.pack(pady=10)

    menu_buttons = []
    menu_buttons.append(("TMS APPLICATION", open_tms))

    def open_humidity():
        humidity_temperature_window()

    menu_buttons.append(("HUMIDITY & TEMPERATURE", open_humidity))

    def open_lock():
        lock_window()

    menu_buttons.append(("LOCK AND UNLOCK", open_lock))

    def open_item_detector():
        rfid_window()

    menu_buttons.append(("RFID SYSTEM", open_item_detector))

    def open_distance():
        distance_window()

    menu_buttons.append(("DISTANCE MEASURE SYSTEM", open_distance))

    def open_accounts():
        accounts_window()

    # Always show ACCOUNTS; the window itself requires an Admin scan to unlock actions
    menu_buttons.append(("ACCOUNTS", open_accounts))

    def open_other():
        other_window()

    menu_buttons.append(("OTHER", open_other))

    def open_analytics():
        analytics_window()

    menu_buttons.append(("ANALYTICS", open_analytics))

    for idx, (text, cmd) in enumerate(menu_buttons):
        row = idx // 2
        col = idx % 2
        btn = ttk.Button(btn_frame, text=text, command=cmd, width=25)
        btn.grid(row=row, column=col, padx=12, pady=10, ipadx=6, ipady=6)

    def sign_out():
        try:
            menu.destroy()
        except Exception:
            pass
        login_window()

    signout_btn = ttk.Button(menu, text="Sign Out", command=sign_out, width=12)
    signout_btn.pack(pady=(8, 12))

    # If a FB manager exists globally and is connected, notify of session
    try:
        global FB_MANAGER
    except Exception:
        FB_MANAGER = None

    def notify_login_once():
        try:
            # Initialize shared manager once per process
            global FB_MANAGER
            if FB_MANAGER is None:
                FB_MANAGER = FacebookManager()
            # Attach label updater; avoid starting twice
            def _cb(text, ok):
                try:
                    fb_status_var.set(text)
                except Exception:
                    pass
            # Do not autostart; user must press Connect FB
            name = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "(unknown)"
            role = "Admin" if CURRENT_USER.get("is_admin") else ("User" if CURRENT_USER.get("uid") else "-")
            FB_MANAGER.notify_access(f"🖥️ GUI session: {name} ({role}) logged in")
        except Exception:
            pass

    # Fire-and-forget: notify if already connected
    menu.after(500, notify_login_once)

    menu.mainloop()


def traffic_light_control():
    app = tk.Tk()
    app.title("Traffic Light Control")
    app.geometry("400x500")
    app.configure(bg=BG_COLOR)
    apply_dark_theme(app)

    current_phase = {"state": "OFF", "time_left": 0}
    cycle_running = {"active": False}
    timer_job = {"job": None}
    cycle_counter = {"id": 0}
    # After entering CAUTION, this indicates which phase comes next ("STOP" or "GO").
    cycle_meta = {"after_caution": "STOP"}

    def back_to_menu():
        try:
            app.destroy()
        except Exception:
            pass
        main_menu()

    top_bar = ttk.Frame(app)
    top_bar.pack(fill="x", pady=(8, 0), padx=8)
    back_btn = ttk.Button(top_bar, text="← Back", command=back_to_menu, width=8)
    back_btn.pack(side=tk.LEFT)

    status_label = ttk.Label(app, text="LIGHT: OFF", font=("Segoe UI", 14, "bold"))
    status_label.pack(pady=15)

    timer_label = ttk.Label(app, text="TIMER: 0", font=("Segoe UI", 20, "bold"))
    timer_label.pack(pady=10)

    light_frame = ttk.Frame(app)
    light_frame.pack(pady=10)

    light_canvas_container = tk.Canvas(light_frame, width=340, height=140, bg=BG_COLOR, highlightthickness=0)
    light_canvas_container.pack()

    draw_rounded_rect(light_canvas_container, 6, 6, 334, 134, r=12, fill="#252525", outline="#3a3a3a")
    light_canvas = tk.Canvas(light_canvas_container, width=320, height=120, bg="#2b2b2b", highlightthickness=0)
    light_canvas.place(x=10, y=10)

    padding = 20
    radius = 40
    cy = 60
    red_x = padding + radius
    yellow_x = red_x + radius * 2 + 20
    green_x = yellow_x + radius * 2 + 20

    red_circle = light_canvas.create_oval(red_x - radius, cy - radius, red_x + radius, cy + radius, fill="#4b0000",
                                          outline="#000000")
    yellow_circle = light_canvas.create_oval(yellow_x - radius, cy - radius, yellow_x + radius, cy + radius,
                                             fill="#4b2f00", outline="#000000")
    green_circle = light_canvas.create_oval(green_x - radius, cy - radius, green_x + radius, cy + radius,
                                            fill="#003d00", outline="#000000")

    def set_light(phase):
        if phase == "GO":
            light_canvas.itemconfig(green_circle, fill="#00c853")
            light_canvas.itemconfig(yellow_circle, fill="#4b2f00")
            light_canvas.itemconfig(red_circle, fill="#4b0000")
        elif phase == "CAUTION":
            light_canvas.itemconfig(green_circle, fill="#003d00")
            light_canvas.itemconfig(yellow_circle, fill="#ffd600")
            light_canvas.itemconfig(red_circle, fill="#4b0000")
        elif phase == "STOP":
            light_canvas.itemconfig(green_circle, fill="#003d00")
            light_canvas.itemconfig(yellow_circle, fill="#4b2f00")
            light_canvas.itemconfig(red_circle, fill="#ff1744")
        else:
            light_canvas.itemconfig(green_circle, fill="#003d00")
            light_canvas.itemconfig(yellow_circle, fill="#4b2f00")
            light_canvas.itemconfig(red_circle, fill="#4b0000")
        try:
            if phase in ("GO", "CAUTION", "STOP"):
                log_reading("traffic", {"event": "phase_visual", "phase": phase, "cycle_id": cycle_counter["id"]})
        except Exception:
            pass

    def update_timer():

        if not cycle_running["active"]:
            if current_phase["time_left"] > 0:
                current_phase["time_left"] -= 1
                timer_label.config(text=f"TIMER: {current_phase['time_left']}")
                timer_job["job"] = app.after(1000, update_timer)
            else:
                current_phase["state"] = "OFF"
                status_label.config(text="LIGHT: OFF")
                timer_label.config(text="TIMER: 0")
                send_command("C")
        else:
            if current_phase["time_left"] > 0:
                current_phase["time_left"] -= 1
                timer_label.config(text=f"TIMER: {current_phase['time_left']}")
                timer_job["job"] = app.after(1000, update_timer)
            else:
                next_phase()

    def start_traffic_cycle():
        if not cycle_running["active"]:
            cycle_running["active"] = True
            cycle_counter["id"] += 1
            current_phase["state"] = "GO"
            current_phase["time_left"] = 15
            cycle_meta["after_caution"] = "STOP"
            status_label.config(text="LIGHT: GO")
            timer_label.config(text="TIMER: 15")
            send_command("G")
            set_light("GO")
            try:
                log_reading("traffic", {"event": "start_cycle", "phase": "GO", "cycle_id": cycle_counter["id"]})
            except Exception:
                pass
            # Notify via Facebook who used TMS
            try:
                actor = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "Unknown"
                fb_notify(f"{actor} used TMS (start cycle -> GO)")
            except Exception:
                pass
            update_timer()

    def stop_traffic_cycle():
        cycle_running["active"] = False
        if timer_job["job"]:
            app.after_cancel(timer_job["job"])
            timer_job["job"] = None
        current_phase["state"] = "OFF"
        current_phase["time_left"] = 0
        status_label.config(text="LIGHT: OFF")
        timer_label.config(text="TIMER: 0")

        send_command("C")
        set_light("OFF")
        try:
            log_reading("traffic", {"event": "stop_cycle", "cycle_id": cycle_counter["id"]})
        except Exception:
            pass

    def next_phase():
        if not cycle_running["active"]:
            return
        # Desired cycle: GO -> CAUTION -> STOP -> CAUTION -> GO -> ...
        if current_phase["state"] == "GO":
            # Enter CAUTION; next after caution will be STOP
            current_phase["state"] = "CAUTION"
            current_phase["time_left"] = 5
            cycle_meta["after_caution"] = "STOP"
            status_label.config(text="LIGHT: CAUTION")
            timer_label.config(text="TIMER: 5")
            send_command("Y")
            set_light("CAUTION")
            try:
                log_reading("traffic", {"event": "phase", "phase": "CAUTION", "cycle_id": cycle_counter["id"]})
            except Exception:
                pass
        elif current_phase["state"] == "CAUTION":
            if cycle_meta.get("after_caution") == "STOP":
                # Move to STOP
                current_phase["state"] = "STOP"
                current_phase["time_left"] = 15
                status_label.config(text="LIGHT: STOP")
                timer_label.config(text="TIMER: 15")
                send_command("R")
                set_light("STOP")
                try:
                    log_reading("traffic", {"event": "phase", "phase": "STOP", "cycle_id": cycle_counter["id"]})
                except Exception:
                    pass
            else:
                # Move to GO
                current_phase["state"] = "GO"
                current_phase["time_left"] = 15
                status_label.config(text="LIGHT: GO")
                timer_label.config(text="TIMER: 15")
                send_command("G")
                set_light("GO")
                try:
                    log_reading("traffic", {"event": "phase", "phase": "GO", "cycle_id": cycle_counter["id"]})
                except Exception:
                    pass
        elif current_phase["state"] == "STOP":
            # Insert CAUTION before GO; next after caution will be GO
            current_phase["state"] = "CAUTION"
            current_phase["time_left"] = 5
            cycle_meta["after_caution"] = "GO"
            status_label.config(text="LIGHT: CAUTION")
            timer_label.config(text="TIMER: 5")
            send_command("Y")
            set_light("CAUTION")
            try:
                log_reading("traffic", {"event": "phase", "phase": "CAUTION", "cycle_id": cycle_counter["id"]})
            except Exception:
                pass
        update_timer()

    def go_button():
        stop_traffic_cycle()
        current_phase["state"] = "GO"
        current_phase["time_left"] = 15
        cycle_meta["after_caution"] = "STOP"  # after yellow from GO, go to STOP
        status_label.config(text="LIGHT: GO")
        timer_label.config(text="TIMER: 15")
        send_command("G")
        set_light("GO")
        try:
            log_reading("traffic", {"event": "manual", "phase": "GO", "cycle_id": cycle_counter["id"]})
        except Exception:
            pass
        try:
            actor = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "Unknown"
            fb_notify(f"{actor} used TMS (GO)")
        except Exception:
            pass
        update_timer()

    def caution_button():
        # Preserve the sequence intent based on prior phase
        prev = current_phase["state"]
        stop_traffic_cycle()
        current_phase["state"] = "CAUTION"
        current_phase["time_left"] = 5
        if prev == "STOP":
            cycle_meta["after_caution"] = "GO"
        else:
            cycle_meta["after_caution"] = "STOP"
        status_label.config(text="LIGHT: CAUTION")
        timer_label.config(text="TIMER: 5")
        send_command("Y")
        set_light("CAUTION")
        try:
            log_reading("traffic", {"event": "manual", "phase": "CAUTION", "cycle_id": cycle_counter["id"]})
        except Exception:
            pass
        try:
            actor = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "Unknown"
            fb_notify(f"{actor} used TMS (YELLOW)")
        except Exception:
            pass
        update_timer()

    def stop_button():
        stop_traffic_cycle()
        current_phase["state"] = "STOP"
        current_phase["time_left"] = 15
        cycle_meta["after_caution"] = "GO"  # after yellow from STOP, go to GO
        status_label.config(text="LIGHT: STOP")
        timer_label.config(text="TIMER: 15")
        send_command("R")
        set_light("STOP")
        try:
            log_reading("traffic", {"event": "manual", "phase": "STOP", "cycle_id": cycle_counter["id"]})
        except Exception:
            pass
        try:
            actor = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "Unknown"
            fb_notify(f"{actor} used TMS (RED)")
        except Exception:
            pass
        update_timer()

    control_frame = ttk.Frame(app)
    control_frame.pack(pady=12)

    start_btn = ttk.Button(control_frame, text="Start Cycle", command=start_traffic_cycle, width=14)
    start_btn.pack(side=tk.LEFT, padx=8, pady=6)
    stop_btn = ttk.Button(control_frame, text="Stop Cycle", command=stop_traffic_cycle, width=14)
    stop_btn.pack(side=tk.LEFT, padx=8, pady=6)

    button_frame = ttk.Frame(app)
    button_frame.pack(pady=30)

    ttk.Button(button_frame, text="GO", command=go_button).pack(side=tk.LEFT, padx=10)
    ttk.Button(button_frame, text="CAUTION", command=caution_button).pack(side=tk.LEFT, padx=10)
    ttk.Button(button_frame, text="STOP", command=stop_button).pack(side=tk.LEFT, padx=10)

    app.mainloop()


def humidity_temperature_window():
    win = tk.Toplevel()
    win.title("Humidity & Temperature")
    win.geometry("560x560")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)

    ttk.Label(win, text="Humidity & Temperature", font=("Segoe UI", 14, "bold")).pack(pady=10)

    gauge_frame = ttk.Frame(win)
    gauge_frame.pack(pady=6, padx=8, fill="x")

    canvas = tk.Canvas(gauge_frame, width=520, height=200, bg=BG_COLOR, highlightthickness=0)
    canvas.pack()

    t_cx, t_cy, t_r = 140, 110, 80
    canvas.create_oval(t_cx - t_r, t_cy - t_r, t_cx + t_r, t_cy + t_r, fill="#222222", outline="#3a3a3a", width=2)

    if hasattr(tk, 'math'):
        _cos = tk.math.cos
        _sin = tk.math.sin
    else:
        import math
        _cos = math.cos
        _sin = math.sin

    for i in range(0, 11):
        angle = 180 + (i * 18)
        rad = angle * 3.14159 / 180
        x1 = t_cx + (t_r - 8) * _cos(rad)
        y1 = t_cy + (t_r - 8) * _sin(rad)
        x2 = t_cx + (t_r - 2) * _cos(rad)
        y2 = t_cy + (t_r - 2) * _sin(rad)
        canvas.create_line(x1, y1, x2, y2, fill="#555555")

    temp_arc = canvas.create_arc(t_cx - t_r, t_cy - t_r, t_cx + t_r, t_cy + t_r, start=180, extent=0, style='arc',
                                 outline='#ff6b6b', width=12)
    temp_text = canvas.create_text(t_cx, t_cy + 30, text="-- °C", fill=FG_COLOR, font=("Segoe UI", 12, "bold"))
    canvas.create_text(t_cx, t_cy - t_r - 10, text="Temperature", fill="#bfc7d6", font=("Segoe UI", 10))

    h_x, h_y = 340, 40
    h_w, h_h = 160, 160
    canvas.create_rectangle(h_x, h_y, h_x + h_w, h_y + h_h, outline="#3a3a3a", fill="#222222", width=2)
    humid_fill = canvas.create_rectangle(h_x + 6, h_y + 6 + h_h, h_x + h_w - 6, h_y + h_h - 6, outline="",
                                         fill="#00bcd4")
    humid_text = canvas.create_text(h_x + h_w / 2, h_y + h_h + 18, text="-- %", fill=FG_COLOR,
                                    font=("Segoe UI", 12, "bold"))
    canvas.create_text(h_x + h_w / 2, h_y - 10, text="Humidity", fill="#bfc7d6", font=("Segoe UI", 10))

    stats_frame = ttk.Frame(win)
    stats_frame.pack(pady=8)
    ttk.Label(stats_frame, text="", width=12).grid(row=0, column=0)
    ttk.Label(stats_frame, text="Current", width=12).grid(row=0, column=1)
    ttk.Label(stats_frame, text="Highest", width=12).grid(row=0, column=2)
    ttk.Label(stats_frame, text="Lowest", width=12).grid(row=0, column=3)
    ttk.Label(stats_frame, text="Temp (°C)", width=12).grid(row=1, column=0)
    temp_cur = ttk.Label(stats_frame, text="--", width=12);
    temp_cur.grid(row=1, column=1)
    temp_high = ttk.Label(stats_frame, text="--", width=12);
    temp_high.grid(row=1, column=2)
    temp_low = ttk.Label(stats_frame, text="--", width=12);
    temp_low.grid(row=1, column=3)
    ttk.Label(stats_frame, text="Humid (%)", width=12).grid(row=2, column=0)
    humid_cur = ttk.Label(stats_frame, text="--", width=12);
    humid_cur.grid(row=2, column=1)
    humid_high = ttk.Label(stats_frame, text="--", width=12);
    humid_high.grid(row=2, column=2)
    humid_low = ttk.Label(stats_frame, text="--", width=12);
    humid_low.grid(row=2, column=3)

    stats = {"temp_high": None, "temp_low": None, "humid_high": None, "humid_low": None}
    simulation = {"active": False, "temp": 25.0, "humid": 55.0}

    def update_stats(temp_val, humid_val):
        events = []
        if temp_val is not None:
            if stats["temp_high"] is None or temp_val > stats["temp_high"]:
                stats["temp_high"] = temp_val
                events.append("new_high_temp")
            if stats["temp_low"] is None or temp_val < stats["temp_low"]:
                stats["temp_low"] = temp_val
                events.append("new_low_temp")
        if humid_val is not None:
            if stats["humid_high"] is None or humid_val > stats["humid_high"]:
                stats["humid_high"] = humid_val
                events.append("new_high_humid")
            if stats["humid_low"] is None or humid_val < stats["humid_low"]:
                stats["humid_low"] = humid_val
                events.append("new_low_humid")
        return events

    def parse_arduino_line(line):
        try:
            parts = line.strip().split()
            hidx = parts.index("Humidity:")
            humidity = float(parts[hidx + 1])
            tidx = parts.index("Temperature:")
            temp = float(parts[tidx + 1])
            return temp, humidity
        except Exception:
            return None, None

    widgets = {'temp_arc': temp_arc, 'temp_text': temp_text, 'humid_fill': humid_fill, 'humid_text': humid_text}
    MIN_TEMP, MAX_TEMP = 0.0, 50.0
    MIN_HUM, MAX_HUM = 0.0, 100.0

    def fetch_and_update():
        try:
            # If user connects serial while simulating, auto-stop simulation
            if simulation["active"] and is_serial_connected():
                simulation["active"] = False
                try:
                    sim_btn.config(text="Start Simulation")
                except Exception:
                    pass

            if simulation["active"] and not is_serial_connected():
                import random
                # Random walk with gentle drift
                simulation["temp"] += random.uniform(-0.35, 0.45)
                simulation["humid"] += random.uniform(-0.9, 1.0)
                # Clamp ranges
                simulation["temp"] = max(MIN_TEMP, min(MAX_TEMP, simulation["temp"]))
                simulation["humid"] = max(MIN_HUM, min(MAX_HUM, simulation["humid"]))
                temp, humid = simulation["temp"], simulation["humid"]
            elif is_serial_connected():
                try:
                    try:
                        arduino.reset_input_buffer()
                    except Exception:
                        pass
                    send_command('R')
                    win.update_idletasks()
                    win.after(150)
                    line = b""
                    try:
                        line = arduino.readline()
                        if isinstance(line, bytes):
                            line = line.decode(errors="ignore").strip()
                        else:
                            line = str(line).strip()
                    except Exception:
                        line = ""
                    temp, humid = parse_arduino_line(line)
                except Exception:
                    temp, humid = None, None
            else:
                temp = None;
                humid = None
            if temp is not None and humid is not None:
                temp_cur.config(text=f"{temp:.2f}")
                humid_cur.config(text=f"{humid:.2f}")
                extreme_events = update_stats(temp, humid)
                temp_high.config(text=f"{stats['temp_high']:.2f}")
                temp_low.config(text=f"{stats['temp_low']:.2f}")
                humid_high.config(text=f"{stats['humid_high']:.2f}")
                humid_low.config(text=f"{stats['humid_low']:.2f}")
                pct_t = max(0.0, min(1.0, (temp - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)))
                extent = int(180 * pct_t)
                canvas.itemconfig(widgets['temp_arc'], extent=extent)
                canvas.itemconfig(widgets['temp_text'], text=f"{temp:.1f} °C")
                pct_h = max(0.0, min(1.0, (humid - MIN_HUM) / (MAX_HUM - MIN_HUM)))
                x1 = h_x + 6;
                x2 = h_x + h_w - 6
                y_bottom = h_y + h_h - 6
                y_top = h_y + 6 + (1 - pct_h) * (h_h - 12)
                canvas.coords(widgets['humid_fill'], x1, y_top, x2, y_bottom)
                canvas.itemconfig(widgets['humid_text'], text=f"{humid:.1f} %")
                try:
                    meta = {"temperature": float(temp), "humidity": float(humid)}
                    if simulation["active"] and not is_serial_connected():
                        meta["sim"] = True
                    log_reading("env", meta)
                    for ev in extreme_events:
                        ext_meta = {"event": ev, "temperature": float(temp), "humidity": float(humid)}
                        if simulation["active"] and not is_serial_connected():
                            ext_meta["sim"] = True
                        log_reading("env_extreme", ext_meta)
                except Exception:
                    pass
            else:
                temp_cur.config(text="--");
                humid_cur.config(text="--")
        except Exception:
            temp_cur.config(text="--");
            humid_cur.config(text="--")

    def auto_update():
        fetch_and_update()
        win.after(1000, auto_update)

    btn_frame = ttk.Frame(win);
    btn_frame.pack(pady=10)

    def toggle_simulation():
        if is_serial_connected() and not simulation["active"]:
            messagebox.showinfo("Simulation", "Disconnect serial to use simulation mode.")
            return
        simulation["active"] = not simulation["active"]
        if simulation["active"]:
            sim_btn.config(text="Stop Simulation")
        else:
            sim_btn.config(text="Start Simulation")

    sim_btn = ttk.Button(btn_frame, text="Start Simulation", command=toggle_simulation)
    sim_btn.pack(side=tk.LEFT, padx=8)
    ttk.Button(btn_frame, text="Close", command=win.destroy).pack(side=tk.LEFT, padx=8)
    auto_update()


def lock_window():
    win = tk.Toplevel()
    win.title("Lock / Unlock")
    win.geometry("420x260")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Lock / Unlock System", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

def rfid_window():
    import tkinter as tk, threading, time

    win = tk.Toplevel()
    win.title("RFID SYSTEM")
    win.geometry("700x480")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)

    tk.Label(win, text="RFID TAG READER", font=("Segoe UI", 18, "bold"),
             bg=BG_COLOR, fg="white").pack(fill="x", pady=(12, 8))

    status = tk.Label(win, text="Status: Waiting for tag...", font=("Segoe UI", 11, "bold"),
                      fg="white", bg=BG_COLOR)
    status.pack(pady=6)

    log = tk.Text(win, width=80, height=18, bg="#0f0f0f", fg="#00ff99",
                  font=("Consolas", 10), bd=2, relief="ridge")
    log.pack(padx=16, pady=8)
    log.insert(tk.END, "🔷 RFID System Ready.\n\n")

    btn_frame = tk.Frame(win, bg=BG_COLOR); btn_frame.pack(pady=6)
    last, stop_flag = {"uid": None}, {"stop": False}

    def log_msg(s, color=None):
        log.insert(tk.END, s + "\n"); log.see(tk.END)
        if color: status.config(fg=color)

    # ✅ Grant Access button
    def grant():
        uid = last["uid"]
        if uid:
            authorized_uids.add(uid)
            save_authorized_uids(authorized_uids)
            log_msg(f"✅ ACCESS GRANTED — {uid}", "lime")
            status.config(text=f"Access Granted: {uid}", fg="lime")
            # --- LED: GREEN ---
            if is_serial_connected():
                arduino.write(b"GREEN\n")
                time.sleep(2)
                arduino.write(b"OFF\n")

    # ❌ Deny Access button
    def deny():
        uid = last["uid"]
        if uid:
            if uid in ADMIN_UIDS:
                log_msg("⛔ Cannot deny an ADMIN card.", "red")
                status.config(text=f"Admin Card: {uid}", fg="red")
                return
            if uid in authorized_uids:
                authorized_uids.discard(uid)
                save_authorized_uids(authorized_uids)
            log_msg(f"❌ ACCESS DENIED — {uid}", "red")
            status.config(text=f"Access Denied: {uid}", fg="red")
            # --- LED: RED ---
            if is_serial_connected():
                arduino.write(b"RED\n")
                time.sleep(2)
                arduino.write(b"OFF\n")

    tk.Button(btn_frame, text="Grant", width=12, bg="#00b347", fg="white",
              font=("Segoe UI", 10, "bold"), command=grant).pack(side="left", padx=8)
    tk.Button(btn_frame, text="Deny", width=12, bg="#d11a2a", fg="white",
              font=("Segoe UI", 10, "bold"), command=deny).pack(side="left", padx=8)

    # --- RFID reader thread ---
    def reader():
        not_connected_displayed = False
        while not stop_flag["stop"]:
            try:
                if not is_serial_connected():
                    if not not_connected_displayed:
                        log_msg("⚠️ Arduino not connected — please connect first.", "red")
                        status.config(text="Arduino not connected", fg="red")
                        not_connected_displayed = True
                    time.sleep(0.5)
                    continue
                else:
                    if not_connected_displayed:
                        log_msg("✅ Arduino reconnected. Ready to read tags.", "lime")
                        status.config(text="Connected — waiting for tag...", fg="white")
                        not_connected_displayed = False

                raw = arduino.readline()
                if not raw:
                    time.sleep(0.05)
                    continue

                line = raw.decode(errors="ignore").strip()
                if not line:
                    continue

                if "UID" in line or "Card UID" in line:
                    # ✅ Capture the full UID (e.g., 29:4C:62:12)
                    uid_raw = line.split("UID:")[-1].strip().replace(" ", "").upper()
                    last["uid"] = uid_raw
                    log_msg(f"🔍 Detected Tag UID: {uid_raw}")

                    # --- LED: YELLOW (tag detected) ---
                    if is_serial_connected():
                        arduino.write(b"YELLOW\n")

                    if uid_raw in authorized_uids or uid_raw in ADMIN_UIDS:
                        role = "ADMIN" if uid_raw in ADMIN_UIDS else "GRANTED"
                        log_msg(f"✅ Recognized — Access {role}", "lime")
                        status.config(text=f"Recognized: {uid_raw}", fg="lime")
                    else:
                        log_msg("⚠️ Unrecognized — Awaiting Decision", "yellow")
                        status.config(text=f"New Tag Detected: {uid_raw}", fg="yellow")
            except Exception as e:
                log_msg(f"⚠️ RFID read error: {e}", "red")
                status.config(text="Error reading RFID", fg="red")
                time.sleep(0.3)

    threading.Thread(target=reader, daemon=True).start()

    def close():
        stop_flag["stop"] = True
        win.destroy()

    tk.Button(win, text="Close", width=12, bg="#444", fg="white",
              font=("Segoe UI", 10, "bold"), command=close).pack(pady=8)
    win.protocol("WM_DELETE_WINDOW", close)

def distance_window():
    win = tk.Toplevel()
    win.title("Distance Measure")
    win.geometry("460x300")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)

    ttk.Label(win, text="Distance Measure System", font=("Segoe UI", 14, "bold")).pack(pady=12)

    container = ttk.Frame(win)
    container.pack(pady=4, padx=10, fill="both", expand=True)

    reading_var = tk.StringVar(value="-- cm")
    status_var = tk.StringVar(value="Idle")

    reading_label = ttk.Label(container, textvariable=reading_var, font=("Segoe UI", 28, "bold"))
    reading_label.pack(pady=6)
    ttk.Label(container, textvariable=status_var, font=("Segoe UI", 10)).pack(pady=(0, 10))

    log_frame = ttk.Frame(container)
    log_frame.pack(fill="both", expand=True, pady=(4, 6))
    txt = tk.Text(log_frame, height=6, bg="#222222", fg=FG_COLOR, insertbackground=FG_COLOR, highlightthickness=0,
                  relief=tk.FLAT, wrap="word")
    txt.pack(side=tk.LEFT, fill="both", expand=True)
    scroll = ttk.Scrollbar(log_frame, command=txt.yview)
    scroll.pack(side=tk.RIGHT, fill="y")
    txt.configure(yscrollcommand=scroll.set)

    controls = ttk.Frame(container)
    controls.pack(pady=4)

    # Unit selection and formatting helpers
    unit_var = tk.StringVar(value="cm")  # 'cm' or 'inch'
    last = {"cm": None}
    AUTO_INTERVAL_MS = 200  # real-time refresh period for auto mode

    def format_distance(cm):
        try:
            if cm is None:
                return "--"
            if cm < 0:
                return "Out of range"
            if unit_var.get() == "inch":
                return f"{(cm / 2.54):.2f} in"
            return f"{cm:.2f} cm"
        except Exception:
            return "--"

    def refresh_display():
        reading_var.set(format_distance(last["cm"]))

    def on_unit_change(*_):
        refresh_display()

    # Unit selector UI
    unit_box = ttk.Combobox(controls, textvariable=unit_var, values=["cm", "inch"], width=6, state="readonly")
    unit_box.pack(side=tk.LEFT, padx=6)
    try:
        unit_var.trace_add("write", lambda *_: on_unit_change())
    except Exception:
        unit_var.trace("w", lambda *_: on_unit_change())

    auto_state = {"running": False, "job": None, "mode": "poll"}  # mode: 'stream' or 'poll'
    stream_buf = {"buf": ""}

    def parse_distance_line(line):
        # Expected formats: 'Distance: 123.45 cm' or 'Distance: -1 cm'
        try:
            if not line:
                return None
            # accept bytes and str
            if isinstance(line, bytes):
                try:
                    line = line.decode(errors="ignore")
                except Exception:
                    return None
            parts = line.strip().split()
            # e.g. ["Distance:", "123.45", "cm"] or ["Distance:", "-1", "cm"]
            if len(parts) >= 2 and parts[0] == 'Distance:':
                raw = parts[1].replace(',', '')
                if raw.replace('.', '', 1).replace('-', '', 1).isdigit():
                    try:
                        return float(raw)
                    except Exception:
                        return None
        except Exception:
            return None
        return None

    def append_log(msg):
        try:
            txt.insert(tk.END, msg + "\n")
            txt.see(tk.END)
        except Exception:
            pass

    def read_once():
        if not is_serial_connected():
            status_var.set("Not connected")
            append_log("[WARN] Not connected to serial.")
            return
        status_var.set("Querying...")
        try:
            try:
                arduino.reset_input_buffer()
            except Exception:
                pass
            send_command('U')
            # Read response line (Arduino responds quickly; try twice if first is empty)
            line = b""
            try:
                line = arduino.readline() or arduino.readline()
                if isinstance(line, bytes):
                    line = line.decode(errors="ignore").strip()
                else:
                    line = str(line).strip()
            except Exception:
                line = ""
            dist = parse_distance_line(line)
            if dist is not None:
                if dist < 0:
                    last["cm"] = -1.0
                    refresh_display()
                    status_var.set("OOR")
                    append_log("[OK] Distance: -1 cm (out of range)")
                    try:
                        log_reading("distance", {"distance": -1.0})
                    except Exception:
                        pass
                else:
                    last["cm"] = float(dist)
                    refresh_display()
                    status_var.set("OK")
                    append_log(f"[OK] {dist:.2f} cm ({(dist/2.54):.2f} in)")
                    try:
                        log_reading("distance", {"distance": float(dist)})
                    except Exception:
                        pass
            else:
                status_var.set("No valid reading")
                append_log(f"[ERR] Invalid line: {line}")
        except Exception as e:
            status_var.set("Error")
            append_log(f"[EXC] {e}")

    def auto_loop():
        if not auto_state["running"]:
            return
        if not is_serial_connected():
            status_var.set("Disconnected")
            append_log("[WARN] Serial disconnected; stopping auto.")
            auto_state["running"] = False
            if auto_state["job"]:
                try:
                    win.after_cancel(auto_state["job"])
                except Exception:
                    pass
                auto_state["job"] = None
            # ensure device stops streaming
            try:
                send_command('S')
            except Exception:
                pass
            btn_auto.config(text="Start Auto")
            return
        if auto_state["mode"] == "poll":
            read_once()
            auto_state["job"] = win.after(AUTO_INTERVAL_MS, auto_loop)
        else:
            # stream mode: non-blocking buffered read
            try:
                updated = False
                # Read all currently available bytes
                avail = 0
                try:
                    avail = getattr(arduino, 'in_waiting', 0)
                    if callable(avail):
                        avail = avail()
                except Exception:
                    try:
                        avail = arduino.inWaiting()
                    except Exception:
                        avail = 0
                if avail > 0:
                    try:
                        chunk = arduino.read(avail)
                        if isinstance(chunk, bytes):
                            chunk = chunk.decode(errors="ignore")
                        else:
                            chunk = str(chunk)
                    except Exception:
                        chunk = ""
                    if chunk:
                        stream_buf["buf"] += chunk
                        # Process complete lines
                        while True:
                            nl = stream_buf["buf"].find('\n')
                            if nl < 0:
                                break
                            raw_line = stream_buf["buf"][:nl]
                            stream_buf["buf"] = stream_buf["buf"][nl+1:]
                            line = raw_line.strip()
                            if not line:
                                continue
                            dist = parse_distance_line(line)
                            if dist is not None:
                                updated = True
                                if dist < 0:
                                    last["cm"] = -1.0
                                    refresh_display()
                                    status_var.set("OOR")
                                    append_log("[OK] Distance: -1 cm (out of range)")
                                    try:
                                        log_reading("distance", {"distance": -1.0})
                                    except Exception:
                                        pass
                                else:
                                    last["cm"] = float(dist)
                                    refresh_display()
                                    status_var.set("OK")
                                    append_log(f"[OK] {dist:.2f} cm ({(dist/2.54):.2f} in)")
                                    try:
                                        log_reading("distance", {"distance": float(dist)})
                                    except Exception:
                                        pass
                if not updated:
                    status_var.set("Waiting…")
            except Exception as e:
                status_var.set("Stream error")
                append_log(f"[EXC] {e}")
            auto_state["job"] = win.after(AUTO_INTERVAL_MS, auto_loop)

    def toggle_auto():
        if auto_state["running"]:
            auto_state["running"] = False
            btn_auto.config(text="Start Auto")
            if auto_state["job"]:
                try:
                    win.after_cancel(auto_state["job"])
                except Exception:
                    pass
                auto_state["job"] = None
            # send stop stream if we were streaming
            if auto_state["mode"] == "stream":
                try:
                    send_command('S')
                except Exception:
                    pass
            status_var.set("Auto stopped")
            try:
                btn_read.config(state=tk.NORMAL)
            except Exception:
                pass
        else:
            if not is_serial_connected():
                status_var.set("Not connected")
                append_log("[WARN] Cannot start auto without serial.")
                return
            # Prefer stream mode; fall back to poll if something fails
            auto_state["mode"] = "stream"
            try:
                try:
                    arduino.reset_input_buffer()
                except Exception:
                    pass
                send_command('L')  # start streaming on device (lowercase L)
                status_var.set("Streaming…")
            except Exception:
                auto_state["mode"] = "poll"
                status_var.set("Auto (poll)")
            auto_state["running"] = True
            btn_auto.config(text="Stop Auto")
            try:
                btn_read.config(state=tk.DISABLED)
            except Exception:
                pass
            auto_loop()

    btn_read = ttk.Button(controls, text="Read Once", command=read_once, width=14)
    btn_read.pack(side=tk.LEFT, padx=6)
    btn_auto = ttk.Button(controls, text="Start Auto", command=toggle_auto, width=14)
    btn_auto.pack(side=tk.LEFT, padx=6)
    ttk.Button(controls, text="Close", command=win.destroy, width=10).pack(side=tk.LEFT, padx=6)

    # Auto-start real-time streaming on open. Tries to connect if needed.
    def start_realtime(attempt=0):
        try:
            if not is_serial_connected():
                ok = init_serial(port=None)
                if not ok:
                    status_var.set("Waiting for serial…")
                    # Retry with gentle backoff (max ~2s)
                    delay = 500 if attempt < 3 else 1000 if attempt < 6 else 2000
                    auto_state["job"] = win.after(delay, lambda: start_realtime(min(attempt + 1, 10)))
                    return
            # Connected: start device streaming
            try:
                arduino.reset_input_buffer()
            except Exception:
                pass
            auto_state["mode"] = "stream"
            send_command('L')  # start streaming on device (lowercase L)
            status_var.set("Streaming…")
            auto_state["running"] = True
            try:
                btn_auto.config(text="Stop Auto")
                btn_read.config(state=tk.DISABLED)
            except Exception:
                pass
            auto_loop()
        except Exception:
            # Fallback to polling if something unexpected happens
            auto_state["mode"] = "poll"
            auto_state["running"] = True
            try:
                btn_auto.config(text="Stop Auto")
                btn_read.config(state=tk.DISABLED)
            except Exception:
                pass
            status_var.set("Auto (poll)")
            auto_loop()

    # Kick off real-time streaming immediately
    start_realtime()

    def on_close():
        auto_state["running"] = False
        if auto_state["job"]:
            try:
                win.after_cancel(auto_state["job"])
            except Exception:
                pass
            auto_state["job"] = None
        # Ensure device stream is stopped
        try:
            if is_serial_connected():
                send_command('S')
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)


def other_window():
    win = tk.Toplevel()
    win.title("Other")
    win.geometry("420x260")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Other", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


def analytics_window():
    win = tk.Toplevel()
    win.title("Analytics / Data Log")
    win.geometry("780x520")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)

    ttk.Label(win, text="System Analytics", font=("Segoe UI", 14, "bold")).pack(pady=10)

    top_frame = ttk.Frame(win)
    top_frame.pack(fill="x", padx=8)

    summary_var = tk.StringVar(value="Loading...")
    ttk.Label(top_frame, textvariable=summary_var, font=("Segoe UI", 10)).pack(anchor="w")

    table_frame = ttk.Frame(win)
    table_frame.pack(fill="both", expand=True, padx=8, pady=6)

    cols = ("ts", "kind", "temperature", "humidity", "distance")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)
    for c in cols:
        tree.heading(c, text=c.upper())
        tree.column(c, width=120, anchor="center")
    tree.pack(side=tk.LEFT, fill="both", expand=True)
    scroll = ttk.Scrollbar(table_frame, command=tree.yview)
    scroll.pack(side=tk.RIGHT, fill="y")
    tree.configure(yscrollcommand=scroll.set)

    def human_time(ts):
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        except Exception:
            return "?"

    def refresh():
        entries = load_entries()
        for i in tree.get_children():
            tree.delete(i)
        # Show only latest 300 entries
        for e in entries[-300:]:
            tree.insert("", tk.END, values=(
                human_time(e.get("ts")),
                e.get("kind"),
                e.get("temperature", ""),
                e.get("humidity", ""),
                e.get("distance", ""),
            ))
        stats = compute_stats(entries)
        if stats.get("count", 0) == 0:
            summary_var.set("No data yet.")
            return
        kinds = ", ".join(f"{k}:{v}" for k, v in stats.get("kinds", {}).items())

        def fmt_block(name):
            blk = stats.get(name, {})
            if blk.get("avg") is None:
                return f"{name[:4]} -"
            return f"{name[:4]} min:{blk['min']:.2f} max:{blk['max']:.2f} avg:{blk['avg']:.2f}"

        summary_var.set(
            f"Entries: {stats['count']} | Kinds: {kinds} | "
            f"{fmt_block('temperature')} | {fmt_block('humidity')} | {fmt_block('distance')}"
        )

    btn_frame = ttk.Frame(win)
    btn_frame.pack(pady=6)

    def do_export():
        dest = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Export CSV")
        if not dest:
            return
        ok = export_csv(dest)
        if ok:
            messagebox.showinfo("Export", f"Exported to {dest}")
        else:
            messagebox.showerror("Export", "Failed to export (maybe no data)")

    def do_clear():
        if not messagebox.askyesno("Confirm", "Clear the entire log? This cannot be undone."):
            return
        if clear_log():
            refresh()
            messagebox.showinfo("Log", "Log cleared.")
        else:
            messagebox.showerror("Log", "Failed to clear log.")

    ttk.Button(btn_frame, text="Refresh", command=refresh, width=12).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Export CSV", command=do_export, width=12).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Clear Log", command=do_clear, width=12).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Close", command=win.destroy, width=12).pack(side=tk.LEFT, padx=6)

    refresh()


def accounts_window():
    win = tk.Toplevel()
    win.title("Accounts (Admin)")
    win.geometry("600x480")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)

    ttk.Label(win, text="Accounts Management", font=("Segoe UI", 14, "bold")).pack(pady=10)
    info = ttk.Label(win, text="Step 1: Scan ADMIN card to unlock", font=("Segoe UI", 10))
    info.pack(pady=(0, 6))

    status = ttk.Label(win, text="Waiting for admin…", font=("Segoe UI", 10))
    status.pack(pady=(0, 8))

    # List current authorized UIDs
    list_frame = ttk.Frame(win)
    list_frame.pack(fill="both", expand=True, padx=10, pady=6)
    listbox = tk.Listbox(list_frame, bg="#222", fg=FG_COLOR, height=12)
    listbox.pack(side=tk.LEFT, fill="both", expand=True)
    sb = ttk.Scrollbar(list_frame, command=listbox.yview)
    sb.pack(side=tk.RIGHT, fill="y")
    listbox.configure(yscrollcommand=sb.set)

    def refresh_list():
        listbox.delete(0, tk.END)
        # Admin UIDs shown with [ADMIN]
        for uid in sorted(authorized_uids.union(ADMIN_UIDS)):
            tag = " [ADMIN]" if uid in ADMIN_UIDS else ""
            label = authorized_names.get(uid, uid)
            listbox.insert(tk.END, f"{label} ({uid}){tag}")

    refresh_list()

    # Controls
    btns = ttk.Frame(win)
    btns.pack(pady=6)

    state = {"unlocked": False, "stop": False, "mode": "admin"}  # admin -> add_user

    def parse_uid_line(raw):
        try:
            if not raw:
                return None
            if isinstance(raw, bytes):
                try:
                    raw = raw.decode(errors="ignore")
                except Exception:
                    raw = str(raw)
            text = raw.strip()
            if not text:
                return None
            if "UID" in text:
                part = text.split("UID:")[-1]
                uid = part.replace(" ", "").replace("-", ":").replace("::", ":").upper().strip()
                return uid if uid else None
        except Exception:
            return None
        return None

    def listen_loop():
        # Runs on the Tk thread via after()
        if state["stop"]:
            return
        # Ensure serial
        if not is_serial_connected():
            status.config(text="Not connected. Connect serial to proceed.")
            win.after(600, listen_loop)
            return
        # Try read one line (non-blocking-ish)
        line = b""
        try:
            line = arduino.readline()
        except Exception:
            line = b""
        uid = parse_uid_line(line)
        if state["mode"] == "admin":
            if uid:
                if uid in ADMIN_UIDS:
                    state["unlocked"] = True
                    state["mode"] = "add_user"
                    info.config(text="Step 2: Scan USER card to add")
                    status.config(text=f"Admin OK: {uid}")
                else:
                    status.config(text=f"Not an admin card: {uid}")
        else:  # add_user
            if uid:
                if uid in ADMIN_UIDS:
                    status.config(text="That is an admin card. Present a user card.")
                else:
                    if uid in authorized_uids:
                        messagebox.showinfo("Accounts", f"User already authorized: {uid}")
                    else:
                        # Prompt for friendly name
                        name = simpledialog.askstring("User Name", "Enter display name for this card:", parent=win)
                        if name is None:
                            name = ""
                        authorized_uids.add(uid)
                        if name.strip():
                            authorized_names[uid] = name.strip()
                            save_authorized_names(authorized_names)
                        if save_authorized_uids(authorized_uids):
                            shown = f"{authorized_names.get(uid, uid)} ({uid})"
                            messagebox.showinfo("Accounts", f"User added: {shown}")
                            # Notify via Facebook: admin added <name> "<tag>"
                            try:
                                admin_actor = CURRENT_USER.get("name") or CURRENT_USER.get("uid") or "Admin"
                                display = authorized_names.get(uid, name.strip() or uid)
                                fb_notify(f"{admin_actor} added {display} \"{uid}\"")
                            except Exception:
                                pass
                        else:
                            messagebox.showerror("Accounts", "Failed to save list.")
                    refresh_list()
                    # Continue listening for more user cards until admin relock or close
        win.after(250, listen_loop)

    def start_listening():
        state["stop"] = False
        state["mode"] = "admin"
        state["unlocked"] = False
        info.config(text="Step 1: Scan ADMIN card to unlock")
        status.config(text="Waiting for admin…")
        listen_loop()

    def relock():
        state["mode"] = "admin"
        state["unlocked"] = False
        info.config(text="Step 1: Scan ADMIN card to unlock")
        status.config(text="Locked")

    def remove_selected():
        idx = listbox.curselection()
        if not idx:
            messagebox.showinfo("Remove", "Select a UID to remove.")
            return
        entry = listbox.get(idx[0])
        # entry is like: "Name (UID) [ADMIN]?" — extract UID between parentheses if present
        uid = entry
        try:
            l = entry.index("(")
            r = entry.index(")", l+1)
            uid = entry[l+1:r]
        except Exception:
            uid = entry.split()[0]
        if uid in ADMIN_UIDS:
            messagebox.showwarning("Remove", "Cannot remove an ADMIN card here.")
            return
        if not state["unlocked"]:
            messagebox.showwarning("Locked", "Scan ADMIN card first to unlock.")
            return
        if uid in authorized_uids:
            authorized_uids.discard(uid)
            if save_authorized_uids(authorized_uids):
                messagebox.showinfo("Remove", f"Removed: {uid}")
            else:
                messagebox.showerror("Remove", "Failed to save list.")
            # Also remove name mapping if exists
            if uid in authorized_names:
                authorized_names.pop(uid, None)
                save_authorized_names(authorized_names)
            refresh_list()

    ttk.Button(btns, text="Start (Scan Admin)", command=start_listening, width=18).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="Relock", command=relock, width=10).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="Remove Selected", command=remove_selected, width=16).pack(side=tk.LEFT, padx=6)
    ttk.Button(btns, text="Close", command=win.destroy, width=10).pack(side=tk.LEFT, padx=6)

    def on_close():
        state["stop"] = True
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)


login_window()
