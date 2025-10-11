import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sys
import time

try:
    from data_logger import log_reading, load_entries, compute_stats, clear_log, export_csv
except Exception:
    # Fallback no-op implementations if logger import fails
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

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
BTN_COLOR = "#007acc"
FONT_MAIN = ("Segoe UI", 12)
FONT_TITLE = ("Segoe UI", 16, "bold")
arduino = None


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
            arduino.write(command.encode())
            print(f"OUTPUT -> {command}")
        except Exception as e:
            print(f"[Serial] Write failed: {e}")
    else:
        print(f"[Serial] Not connected, would send: {command}")

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
    ttk.Label(card, text="Arduino System — Login", font=("Segoe UI", 10), foreground="#bfc7d6", background=BG_COLOR).pack(pady=(0, 12))

   
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

    login.bind('<Return>', verify_login)

    username_entry.focus_set()

    login.mainloop()

def main_menu():
    menu = tk.Tk()
    menu.title("Main Menu")
    menu.geometry("650x550")
    menu.configure(bg=BG_COLOR)
    apply_dark_theme(menu)

    ttk.Label(menu, text="MAIN MENU", font=FONT_TITLE).pack(pady=20)

    
    status_frame = ttk.Frame(menu)
    status_frame.pack(pady=(0, 6))
    serial_status_var = tk.StringVar()
    if is_serial_connected():
        serial_status_var.set("Serial: Connected")
    else:
        serial_status_var.set("Serial: Disconnected")
    serial_label = ttk.Label(status_frame, textvariable=serial_status_var, font=("Segoe UI", 10))
    serial_label.pack(side=tk.LEFT, padx=(0, 12))

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
    menu_buttons.append(("LOCK / UNLOCK SYSTEM", open_lock))
    def open_item_detector():
        item_detector_window()
    menu_buttons.append(("ITEM DETECTOR SYSTEM", open_item_detector))
    def open_distance():
        distance_window()
    menu_buttons.append(("DISTANCE MEASURE SYSTEM", open_distance))
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

    red_circle = light_canvas.create_oval(red_x - radius, cy - radius, red_x + radius, cy + radius, fill="#4b0000", outline="#000000")
    yellow_circle = light_canvas.create_oval(yellow_x - radius, cy - radius, yellow_x + radius, cy + radius, fill="#4b2f00", outline="#000000")
    green_circle = light_canvas.create_oval(green_x - radius, cy - radius, green_x + radius, cy + radius, fill="#003d00", outline="#000000")


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
            status_label.config(text="LIGHT: GO")
            timer_label.config(text="TIMER: 15")
            send_command("G")
            set_light("GO")
            try:
                log_reading("traffic", {"event": "start_cycle", "phase": "GO", "cycle_id": cycle_counter["id"]})
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
        if current_phase["state"] == "GO":
            current_phase["state"] = "CAUTION"
            current_phase["time_left"] = 5
            status_label.config(text="LIGHT: CAUTION")
            timer_label.config(text="TIMER: 5")
            # Y = yellow / caution
            send_command("Y")
            set_light("CAUTION")
            try:
                log_reading("traffic", {"event": "phase", "phase": "CAUTION", "cycle_id": cycle_counter["id"]})
            except Exception:
                pass
        elif current_phase["state"] == "CAUTION":
            current_phase["state"] = "STOP"
            current_phase["time_left"] = 15
            status_label.config(text="LIGHT: STOP")
            timer_label.config(text="TIMER: 15")
            # R = red / stop
            send_command("R")
            set_light("STOP")
            try:
                log_reading("traffic", {"event": "phase", "phase": "STOP", "cycle_id": cycle_counter["id"]})
            except Exception:
                pass
        elif current_phase["state"] == "STOP":
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
        update_timer()

    def go_button():
        stop_traffic_cycle()
        current_phase["state"] = "GO"
        current_phase["time_left"] = 15
        status_label.config(text="LIGHT: GO")
        timer_label.config(text="TIMER: 15")
        send_command("G")
        set_light("GO")
        try:
            log_reading("traffic", {"event": "manual", "phase": "GO", "cycle_id": cycle_counter["id"]})
        except Exception:
            pass
        update_timer()

    def caution_button():
        stop_traffic_cycle()
        current_phase["state"] = "CAUTION"
        current_phase["time_left"] = 5
        status_label.config(text="LIGHT: CAUTION")
        timer_label.config(text="TIMER: 5")
        send_command("Y")
        set_light("CAUTION")
        try:
            log_reading("traffic", {"event": "manual", "phase": "CAUTION", "cycle_id": cycle_counter["id"]})
        except Exception:
            pass
        update_timer()

    def stop_button():
        stop_traffic_cycle()
        current_phase["state"] = "STOP"
        current_phase["time_left"] = 15
        status_label.config(text="LIGHT: STOP")
        timer_label.config(text="TIMER: 15")
        send_command("R")
        set_light("STOP")
        try:
            log_reading("traffic", {"event": "manual", "phase": "STOP", "cycle_id": cycle_counter["id"]})
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

    temp_arc = canvas.create_arc(t_cx - t_r, t_cy - t_r, t_cx + t_r, t_cy + t_r, start=180, extent=0, style='arc', outline='#ff6b6b', width=12)
    temp_text = canvas.create_text(t_cx, t_cy + 30, text="-- °C", fill=FG_COLOR, font=("Segoe UI", 12, "bold"))
    canvas.create_text(t_cx, t_cy - t_r - 10, text="Temperature", fill="#bfc7d6", font=("Segoe UI", 10))

    h_x, h_y = 340, 40
    h_w, h_h = 160, 160
    canvas.create_rectangle(h_x, h_y, h_x + h_w, h_y + h_h, outline="#3a3a3a", fill="#222222", width=2)
    humid_fill = canvas.create_rectangle(h_x + 6, h_y + 6 + h_h, h_x + h_w - 6, h_y + h_h - 6, outline="", fill="#00bcd4")
    humid_text = canvas.create_text(h_x + h_w / 2, h_y + h_h + 18, text="-- %", fill=FG_COLOR, font=("Segoe UI", 12, "bold"))
    canvas.create_text(h_x + h_w / 2, h_y - 10, text="Humidity", fill="#bfc7d6", font=("Segoe UI", 10))

    stats_frame = ttk.Frame(win)
    stats_frame.pack(pady=8)
    ttk.Label(stats_frame, text="", width=12).grid(row=0, column=0)
    ttk.Label(stats_frame, text="Current", width=12).grid(row=0, column=1)
    ttk.Label(stats_frame, text="Highest", width=12).grid(row=0, column=2)
    ttk.Label(stats_frame, text="Lowest", width=12).grid(row=0, column=3)
    ttk.Label(stats_frame, text="Temp (°C)", width=12).grid(row=1, column=0)
    temp_cur = ttk.Label(stats_frame, text="--", width=12); temp_cur.grid(row=1, column=1)
    temp_high = ttk.Label(stats_frame, text="--", width=12); temp_high.grid(row=1, column=2)
    temp_low = ttk.Label(stats_frame, text="--", width=12); temp_low.grid(row=1, column=3)
    ttk.Label(stats_frame, text="Humid (%)", width=12).grid(row=2, column=0)
    humid_cur = ttk.Label(stats_frame, text="--", width=12); humid_cur.grid(row=2, column=1)
    humid_high = ttk.Label(stats_frame, text="--", width=12); humid_high.grid(row=2, column=2)
    humid_low = ttk.Label(stats_frame, text="--", width=12); humid_low.grid(row=2, column=3)

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
            humidity = float(parts[hidx+1])
            tidx = parts.index("Temperature:")
            temp = float(parts[tidx+1])
            return temp, humidity
        except Exception:
            return None, None

    widgets = { 'temp_arc': temp_arc, 'temp_text': temp_text, 'humid_fill': humid_fill, 'humid_text': humid_text }
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
                temp = None; humid = None
            if temp is not None and humid is not None:
                temp_cur.config(text=f"{temp:.2f}")
                humid_cur.config(text=f"{humid:.2f}")
                extreme_events = update_stats(temp, humid)
                temp_high.config(text=f"{stats['temp_high']:.2f}")
                temp_low.config(text=f"{stats['temp_low']:.2f}")
                humid_high.config(text=f"{stats['humid_high']:.2f}")
                humid_low.config(text=f"{stats['humid_low']:.2f}")
                pct_t = max(0.0, min(1.0, (temp - MIN_TEMP)/(MAX_TEMP-MIN_TEMP)))
                extent = int(180 * pct_t)
                canvas.itemconfig(widgets['temp_arc'], extent=extent)
                canvas.itemconfig(widgets['temp_text'], text=f"{temp:.1f} °C")
                pct_h = max(0.0, min(1.0, (humid - MIN_HUM)/(MAX_HUM-MIN_HUM)))
                x1 = h_x + 6; x2 = h_x + h_w - 6
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
                temp_cur.config(text="--"); humid_cur.config(text="--")
        except Exception:
            temp_cur.config(text="--"); humid_cur.config(text="--")

    def auto_update():
        fetch_and_update()
        win.after(1000, auto_update)

    btn_frame = ttk.Frame(win); btn_frame.pack(pady=10)

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
    win = tk.Toplevel()
    win.title("Item Detector")
    win.geometry("420x260")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Item Detector System", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


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
    txt = tk.Text(log_frame, height=6, bg="#222222", fg=FG_COLOR, insertbackground=FG_COLOR, highlightthickness=0, relief=tk.FLAT, wrap="word")
    txt.pack(side=tk.LEFT, fill="both", expand=True)
    scroll = ttk.Scrollbar(log_frame, command=txt.yview)
    scroll.pack(side=tk.RIGHT, fill="y")
    txt.configure(yscrollcommand=scroll.set)

    controls = ttk.Frame(container)
    controls.pack(pady=4)

    auto_state = {"running": False, "job": None, "mode": "poll"}  # mode: 'stream' or 'poll'

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
                    reading_var.set("Out of range")
                    status_var.set("OOR")
                    append_log("[OK] Distance: -1 cm (out of range)")
                    try:
                        log_reading("distance", {"distance": -1.0})
                    except Exception:
                        pass
                else:
                    reading_var.set(f"{dist:.2f} cm")
                    status_var.set("OK")
                    append_log(f"[OK] {dist:.2f} cm")
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
            auto_state["job"] = win.after(125, auto_loop)
        else:
            # stream mode: read all available lines without blocking
            try:
                updated = False
                # Determine available bytes
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
                # Read lines while buffer has data
                loop_guard = 0
                while avail > 0 and loop_guard < 50:  # guard to avoid very long loops
                    loop_guard += 1
                    line = arduino.readline()
                    if not line:
                        break
                    if isinstance(line, bytes):
                        line = line.decode(errors="ignore").strip()
                    else:
                        line = str(line).strip()
                    dist = parse_distance_line(line)
                    if dist is not None:
                        updated = True
                        if dist < 0:
                            reading_var.set("Out of range")
                            status_var.set("OOR")
                            append_log("[OK] Distance: -1 cm (out of range)")
                            try:
                                log_reading("distance", {"distance": -1.0})
                            except Exception:
                                pass
                        else:
                            reading_var.set(f"{dist:.2f} cm")
                            status_var.set("OK")
                            append_log(f"[OK] {dist:.2f} cm")
                            try:
                                log_reading("distance", {"distance": float(dist)})
                            except Exception:
                                pass
                    # update avail for next iteration
                    try:
                        avail = getattr(arduino, 'in_waiting', 0)
                        if callable(avail):
                            avail = avail()
                    except Exception:
                        try:
                            avail = arduino.inWaiting()
                        except Exception:
                            avail = 0
                if not updated:
                    status_var.set("Waiting…")
            except Exception as e:
                status_var.set("Stream error")
                append_log(f"[EXC] {e}")
            auto_state["job"] = win.after(50, auto_loop)

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
                send_command('u')  # start streaming on device
                status_var.set("Streaming…")
            except Exception:
                auto_state["mode"] = "poll"
                status_var.set("Auto (poll)")
            auto_state["running"] = True
            btn_auto.config(text="Stop Auto")
            auto_loop()

    btn_read = ttk.Button(controls, text="Read Once", command=read_once, width=14)
    btn_read.pack(side=tk.LEFT, padx=6)
    btn_auto = ttk.Button(controls, text="Start Auto", command=toggle_auto, width=14)
    btn_auto.pack(side=tk.LEFT, padx=6)
    ttk.Button(controls, text="Close", command=win.destroy, width=10).pack(side=tk.LEFT, padx=6)

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

login_window()