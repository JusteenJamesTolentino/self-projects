import tkinter as tk
from tkinter import ttk
from .models import BG_COLOR, FG_COLOR, FONT_MAIN, FONT_TITLE


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
    return canvas.create_polygon([coord for p in points for coord in p], smooth=True, splinesteps=20, **kwargs)


def apply_dark_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except Exception:
        pass
    style.configure('TLabel', foreground=FG_COLOR, background=BG_COLOR, font=FONT_MAIN)
    style.configure('TFrame', background=BG_COLOR)
    style.configure('Card.TFrame', background='#262626')
    style.configure('TButton', foreground=FG_COLOR, background=BG_COLOR, font=FONT_MAIN, padding=6)
    style.map('TButton', background=[('active', '#005a9e'), ('disabled', '#444444')])
    style.configure('TEntry', fieldbackground='#1e1e1e', foreground=FG_COLOR, background='#1e1e1e')
    root.configure(bg=BG_COLOR)


class LoginView:
    def __init__(self, controller, root_cls=tk.Tk):
        self.controller = controller
        self.root = root_cls()
        self.root.title("Login")
        self.root.geometry("620x360")
        self.root.configure(bg=BG_COLOR)
        apply_dark_theme(self.root)
        self.build()

    def build(self):
        container = ttk.Frame(self.root)
        container.pack(expand=True, fill="both")

        canvas_card = tk.Canvas(container, width=360, height=240, bg=BG_COLOR, highlightthickness=0)
        canvas_card.pack(pady=10)
        draw_rounded_rect(canvas_card, 6, 6, 354, 234, r=16, fill=BG_COLOR, outline="#ffffff")

        card = ttk.Frame(container, padding=(24, 18), style="Card.TFrame")
        card.place(in_=canvas_card, x=12, y=12)

        ttk.Label(card, text="GROUP 1", font=("Segoe UI", 18, "bold"), foreground=FG_COLOR, background=BG_COLOR).pack()
        ttk.Label(card, text="Arduino System — Login", font=("Segoe UI", 10), foreground="#bfc7d6", background=BG_COLOR).pack(pady=(0, 12))

        form = ttk.Frame(card)
        form.pack(pady=(6, 4))

        self.username_entry = tk.Entry(form, width=28, bg=BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, relief='flat', highlightthickness=1, highlightbackground='#ffffff', highlightcolor='#ffffff')
        self.username_entry.grid(row=0, column=0, columnspan=2, pady=(6, 8))

        self.password_entry = tk.Entry(form, width=28, bg=BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, relief='flat', highlightthickness=1, highlightbackground='#ffffff', highlightcolor='#ffffff')
        self.password_entry.grid(row=1, column=0, columnspan=2, pady=(2, 6))

        self.show_state = {"visible": False}

        def toggle_show():
            self.show_state["visible"] = not self.show_state["visible"]
            if getattr(self.password_entry, '_placeholder', False):
                self.password_entry.config(show='')
            else:
                self.password_entry.config(show=("" if self.show_state["visible"] else "*"))

        eye_btn = ttk.Button(form, text="🙈", width=3, command=toggle_show)
        eye_btn.grid(row=1, column=2, padx=(8, 0))

        def _make_placeholder(entry, hint, is_password=False):
            def on_focus_in(event):
                if getattr(entry, '_placeholder', False):
                    entry.delete(0, tk.END)
                    entry._placeholder = False
                    if is_password and not self.show_state['visible']:
                        entry.config(show='*')

            def on_focus_out(event):
                if entry.get().strip() == '':
                    entry.insert(0, hint)
                    entry._placeholder = True
                    entry.config(show='')

            entry.insert(0, hint)
            entry._placeholder = True
            entry.bind('<FocusIn>', on_focus_in)
            entry.bind('<FocusOut>', on_focus_out)

        _make_placeholder(self.username_entry, 'Username', is_password=False)
        _make_placeholder(self.password_entry, 'Password', is_password=True)

        self.error_label = ttk.Label(card, text="", foreground="#ff6b6b", background=BG_COLOR)
        self.error_label.pack(pady=(4, 0))

        action_frame = ttk.Frame(card)
        action_frame.pack(pady=(14, 0), fill="x")

        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(anchor="center")

        login_btn = ttk.Button(btn_frame, text="Sign in", command=self.on_signin, width=10)
        login_btn.pack(side=tk.LEFT, padx=(0, 8))

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.root.destroy, width=10)
        cancel_btn.pack(side=tk.LEFT)

        self.username_entry.focus_set()

    def on_signin(self):
        self.controller.handle_login(self.username_entry.get().strip(), self.password_entry.get().strip(), self.error_label, self.root)


class MainMenuView:
    def __init__(self, controller, root_cls=tk.Tk):
        self.controller = controller
        self.root = root_cls()
        self.root.title("Main Menu")
        self.root.geometry("650x350")
        self.root.configure(bg=BG_COLOR)
        apply_dark_theme(self.root)
        self.build()

    def build(self):
        ttk.Label(self.root, text="MAIN MENU", font=FONT_TITLE).pack(pady=20)
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        menu_buttons = [
            ("TMS APPLICATION", self.controller.open_tms),
            ("HUMIDITY & TEMPERATURE", self.controller.open_humidity),
            ("LOCK / UNLOCK SYSTEM", self.controller.open_lock),
            ("ITEM DETECTOR SYSTEM", self.controller.open_item_detector),
            ("DISTANCE MEASURE SYSTEM", self.controller.open_distance),
            ("OTHER", self.controller.open_other)
        ]

        for idx, (text, cmd) in enumerate(menu_buttons):
            row = idx // 2
            col = idx % 2
            btn = ttk.Button(btn_frame, text=text, command=cmd, width=25)
            btn.grid(row=row, column=col, padx=12, pady=10, ipadx=6, ipady=6)

        signout_btn = ttk.Button(self.root, text="Sign Out", command=self.controller.sign_out, width=12)
        signout_btn.pack(pady=(8, 12))


class TrafficView:
    def __init__(self, controller, root_cls=tk.Tk):
        self.controller = controller
        self.root = root_cls()
        self.root.title("Traffic Light Control")
        self.root.geometry("400x500")
        self.root.configure(bg=BG_COLOR)
        apply_dark_theme(self.root)
        self.build()

    def build(self):
        top_bar = ttk.Frame(self.root)
        top_bar.pack(fill="x", pady=(8, 0), padx=8)
        back_btn = ttk.Button(top_bar, text="← Back", command=self.controller.back_to_menu, width=8)
        back_btn.pack(side=tk.LEFT)

        self.status_label = ttk.Label(self.root, text="LIGHT: OFF", font=("Segoe UI", 14, "bold"))
        self.status_label.pack(pady=15)

        self.timer_label = ttk.Label(self.root, text="TIMER: 0", font=("Segoe UI", 20, "bold"))
        self.timer_label.pack(pady=10)

        light_frame = ttk.Frame(self.root)
        light_frame.pack(pady=10)

        light_canvas_container = tk.Canvas(light_frame, width=340, height=140, bg=BG_COLOR, highlightthickness=0)
        light_canvas_container.pack()
        draw_rounded_rect(light_canvas_container, 6, 6, 334, 134, r=12, fill="#252525", outline="#3a3a3a")
        self.light_canvas = tk.Canvas(light_canvas_container, width=320, height=120, bg="#2b2b2b", highlightthickness=0)
        self.light_canvas.place(x=10, y=10)

        padding = 20
        radius = 40
        cy = 60
        red_x = padding + radius
        yellow_x = red_x + radius * 2 + 20
        green_x = yellow_x + radius * 2 + 20

        self.red_circle = self.light_canvas.create_oval(red_x - radius, cy - radius, red_x + radius, cy + radius, fill="#4b0000", outline="#000000")
        self.yellow_circle = self.light_canvas.create_oval(yellow_x - radius, cy - radius, yellow_x + radius, cy + radius, fill="#4b2f00", outline="#000000")
        self.green_circle = self.light_canvas.create_oval(green_x - radius, cy - radius, green_x + radius, cy + radius, fill="#003d00", outline="#000000")

        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=12)

        start_btn = ttk.Button(control_frame, text="Start Cycle", command=self.controller.start_traffic_cycle, width=14)
        start_btn.pack(side=tk.LEFT, padx=8, pady=6)
        stop_btn = ttk.Button(control_frame, text="Stop Cycle", command=self.controller.stop_traffic_cycle, width=14)
        stop_btn.pack(side=tk.LEFT, padx=8, pady=6)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=30)

        ttk.Button(button_frame, text="GO", command=self.controller.go_button).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="CAUTION", command=self.controller.caution_button).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="STOP", command=self.controller.stop_button).pack(side=tk.LEFT, padx=10)
