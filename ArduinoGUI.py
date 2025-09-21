import serial
import tkinter as tk
from tkinter import ttk, messagebox

BG_COLOR = "#1e1e1e"
FG_COLOR = "#ffffff"
BTN_COLOR = "#007acc"
FONT_MAIN = ("Segoe UI", 12)
FONT_TITLE = ("Segoe UI", 16, "bold")

COM = "/dev/ttyUSB0"
arduino = serial.Serial(port=COM, baudrate=9600, timeout=1)

def send_command(command):
    arduino.write(command.encode())
    print(f"OUTPUT:  {command}")

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
    """Draw a rounded rectangle on `canvas`. Returns the created object ids."""
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
   
    return canvas.create_polygon(
        [coord for p in points for coord in p], smooth=True, splinesteps=20, **kwargs
    )

def login_window():
    login = tk.Tk()
    login.title("Login")
    login.geometry("620x360")
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
        password_entry.config(show=("" if show_state["visible"] else "*"))
        eye_btn.config(text=("👁️" if show_state["visible"] else "🙈"))

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
    menu.geometry("650x450")
    menu.configure(bg=BG_COLOR)
    apply_dark_theme(menu)

    ttk.Label(menu, text="MAIN MENU", font=FONT_TITLE).pack(pady=20)

    def open_tms():
        menu.destroy()
        traffic_light_control()

    btn_frame = ttk.Frame(menu)
    btn_frame.pack(pady=10)

    menu_buttons = [
        ("TMS APPLICATION", open_tms),
        ("HUMIDITY & TEMPERATURE", lambda: humidity_window()),
        ("LOCK / UNLOCK SYSTEM", lambda: lock_window()),
        ("ITEM DETECTOR SYSTEM", lambda: item_detector_window()),
        ("DISTANCE MEASURE SYSTEM", lambda: distance_window()),
        ("OTHER", lambda: other_window())
    ]

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
            current_phase["state"] = "GO"
            current_phase["time_left"] = 15
            status_label.config(text="LIGHT: GO")
            timer_label.config(text="TIMER: 15")
            send_command("G")
            set_light("GO")
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

    def next_phase():
        if not cycle_running["active"]:
            return
        if current_phase["state"] == "GO":
            current_phase["state"] = "CAUTION"
            current_phase["time_left"] = 5
            status_label.config(text="LIGHT: CAUTION")
            timer_label.config(text="TIMER: 5")
            send_command("Y")
            set_light("CAUTION")
        elif current_phase["state"] == "CAUTION":
            current_phase["state"] = "STOP"
            current_phase["time_left"] = 15
            status_label.config(text="LIGHT: STOP")
            timer_label.config(text="TIMER: 15")
            send_command("R")
            set_light("STOP")
        elif current_phase["state"] == "STOP":
            current_phase["state"] = "GO"
            current_phase["time_left"] = 15
            status_label.config(text="LIGHT: GO")
            timer_label.config(text="TIMER: 15")
            send_command("G")
            set_light("GO")
        update_timer()

    def go_button():
        stop_traffic_cycle()
        current_phase["state"] = "GO"
        current_phase["time_left"] = 15
        status_label.config(text="LIGHT: GO")
        timer_label.config(text="TIMER: 15")
        send_command("G")
        set_light("GO")
        update_timer()

    def caution_button():
        stop_traffic_cycle()
        current_phase["state"] = "CAUTION"
        current_phase["time_left"] = 5
        status_label.config(text="LIGHT: CAUTION")
        timer_label.config(text="TIMER: 5")
        send_command("Y")
        set_light("CAUTION")
        update_timer()

    def stop_button():
        stop_traffic_cycle()
        current_phase["state"] = "STOP"
        current_phase["time_left"] = 15
        status_label.config(text="LIGHT: STOP")
        timer_label.config(text="TIMER: 15")
        send_command("R")
        set_light("STOP")
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


def humidity_window():
    win = tk.Toplevel()
    win.title("Humidity & Temperature")
    win.geometry("420x300")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Humidity & Temperature", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


def lock_window():
    win = tk.Toplevel()
    win.title("Lock / Unlock")
    win.geometry("420x260")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Lock / Unlock System", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


def item_detector_window():
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
    win.geometry("420x260")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Distance Measure System", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)


def other_window():
    win = tk.Toplevel()
    win.title("Other")
    win.geometry("420x260")
    win.configure(bg=BG_COLOR)
    apply_dark_theme(win)
    ttk.Label(win, text="Other", font=("Segoe UI", 14, "bold")).pack(pady=12)
    ttk.Label(win, text="(Placeholder)").pack(pady=20)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)

login_window()