import tkinter as tk
from .models import SerialModel, AppState
from .views import LoginView, MainMenuView, TrafficView


class AppController:
    def __init__(self, config=None):
        """config: dict with optional keys 'serial' and 'durations'
        serial: {port, baudrate, timeout}
        durations: {go, caution, stop} in seconds
        """
        self.config = config or {}
        serial_cfg = self.config.get('serial', {})
        port = serial_cfg.get('port', '/dev/ttyUSB0')
        baudrate = serial_cfg.get('baudrate', 9600)
        timeout = serial_cfg.get('timeout', 1)
        self.serial = SerialModel(port=port, baudrate=baudrate, timeout=timeout)
        self.state = AppState()
        durations = self.config.get('durations', {})
        # default durations (seconds)
        self.t_go = durations.get('go', 15)
        self.t_caution = durations.get('caution', 5)
        self.t_stop = durations.get('stop', 15)

    def start(self):
        # launch login
        self.show_login()

    def show_login(self):
        self.login_view = LoginView(self)
        self.login_view.root.mainloop()

    def handle_login(self, username, password, error_label, root_window):
        if username == "group1" and password == "group1":
            try:
                root_window.destroy()
            except Exception:
                pass
            self.show_main_menu()
        else:
            self.state.try_count["count"] += 1
            remaining = max(0, 3 - self.state.try_count["count"])
            error_label.config(text=f"Invalid credentials. {remaining} attempts left.")
            if self.state.try_count["count"] >= 3:
                try:
                    root_window.destroy()
                except Exception:
                    pass

    def show_main_menu(self):
        self.main_view = MainMenuView(self)
        self.main_view.root.mainloop()

    def sign_out(self):
        try:
            self.main_view.root.destroy()
        except Exception:
            pass
        self.show_login()

    # Placeholder openers
    def open_tms(self):
        try:
            self.main_view.root.destroy()
        except Exception:
            pass
        self.traffic_view = TrafficView(self)
        self.traffic_view.root.mainloop()

    def open_humidity(self):
        win = tk.Toplevel()
        win.title("Humidity & Temperature")
        win.geometry("420x300")
        ttk = tk.ttk if hasattr(tk, 'ttk') else None
        lbl = tk.Label(win, text="Humidity & Temperature", font=("Segoe UI", 14, "bold"))
        lbl.pack(pady=12)
        tk.Label(win, text="(Placeholder)").pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def open_lock(self):
        win = tk.Toplevel()
        win.title("Lock / Unlock")
        win.geometry("420x260")
        tk.Label(win, text="Lock / Unlock System", font=("Segoe UI", 14, "bold")).pack(pady=12)
        tk.Label(win, text="(Placeholder)").pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def open_item_detector(self):
        win = tk.Toplevel()
        win.title("Item Detector")
        win.geometry("420x260")
        tk.Label(win, text="Item Detector System", font=("Segoe UI", 14, "bold")).pack(pady=12)
        tk.Label(win, text="(Placeholder)").pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def open_distance(self):
        win = tk.Toplevel()
        win.title("Distance Measure")
        win.geometry("420x260")
        tk.Label(win, text="Distance Measure System", font=("Segoe UI", 14, "bold")).pack(pady=12)
        tk.Label(win, text="(Placeholder)").pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    def open_other(self):
        win = tk.Toplevel()
        win.title("Other")
        win.geometry("420x260")
        tk.Label(win, text="Other", font=("Segoe UI", 14, "bold")).pack(pady=12)
        tk.Label(win, text="(Placeholder)").pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    # Traffic control methods
    def send_command(self, cmd):
        self.serial.send(cmd)

    def back_to_menu(self):
        try:
            self.traffic_view.root.destroy()
        except Exception:
            pass
        self.show_main_menu()

    def start_traffic_cycle(self):
        if not self.state.cycle_running["active"]:
            self.state.cycle_running["active"] = True
            self.state.current_phase["state"] = "GO"
            self.state.current_phase["time_left"] = self.t_go
            self.send_command("G")
            self.update_traffic_view()
            self._schedule_timer()

    def stop_traffic_cycle(self):
        self.state.cycle_running["active"] = False
        try:
            if self.state.timer_job["job"]:
                self.traffic_view.root.after_cancel(self.state.timer_job["job"])
                self.state.timer_job["job"] = None
        except Exception:
            pass
        self.state.current_phase["state"] = "OFF"
        self.state.current_phase["time_left"] = 0
        self.send_command("C")
        self.update_traffic_view()

    def next_phase(self):
        if not self.state.cycle_running["active"]:
            return
        st = self.state.current_phase["state"]
        if st == "GO":
            self.state.current_phase["state"] = "CAUTION"
            self.state.current_phase["time_left"] = self.t_caution
            self.send_command("Y")
        elif st == "CAUTION":
            self.state.current_phase["state"] = "STOP"
            self.state.current_phase["time_left"] = self.t_stop
            self.send_command("R")
        elif st == "STOP":
            self.state.current_phase["state"] = "GO"
            self.state.current_phase["time_left"] = self.t_go
            self.send_command("G")
        self.update_traffic_view()
        self._schedule_timer()

    def _schedule_timer(self):
        try:
            self.state.timer_job["job"] = self.traffic_view.root.after(1000, self._timer_tick)
        except Exception:
            pass

    def _timer_tick(self):
        if not self.state.cycle_running["active"]:
            # countdown only when stopped
            if self.state.current_phase["time_left"] > 0:
                self.state.current_phase["time_left"] -= 1
                self.update_traffic_view()
                self._schedule_timer()
            else:
                self.state.current_phase["state"] = "OFF"
                self.state.current_phase["time_left"] = 0
                self.send_command("C")
                self.update_traffic_view()
        else:
            if self.state.current_phase["time_left"] > 0:
                self.state.current_phase["time_left"] -= 1
                self.update_traffic_view()
                self._schedule_timer()
            else:
                self.next_phase()

    def update_traffic_view(self):
        if not hasattr(self, 'traffic_view'):
            return
        tv = self.traffic_view
        st = self.state.current_phase["state"]
        tv.status_label.config(text=f"LIGHT: {st}")
        tv.timer_label.config(text=f"TIMER: {self.state.current_phase['time_left']}")
        # set lights
        if st == "GO":
            tv.light_canvas.itemconfig(tv.green_circle, fill="#00c853")
            tv.light_canvas.itemconfig(tv.yellow_circle, fill="#4b2f00")
            tv.light_canvas.itemconfig(tv.red_circle, fill="#4b0000")
        elif st == "CAUTION":
            tv.light_canvas.itemconfig(tv.green_circle, fill="#003d00")
            tv.light_canvas.itemconfig(tv.yellow_circle, fill="#ffd600")
            tv.light_canvas.itemconfig(tv.red_circle, fill="#4b0000")
        elif st == "STOP":
            tv.light_canvas.itemconfig(tv.green_circle, fill="#003d00")
            tv.light_canvas.itemconfig(tv.yellow_circle, fill="#4b2f00")
            tv.light_canvas.itemconfig(tv.red_circle, fill="#ff1744")
        else:
            tv.light_canvas.itemconfig(tv.green_circle, fill="#003d00")
            tv.light_canvas.itemconfig(tv.yellow_circle, fill="#4b2f00")
            tv.light_canvas.itemconfig(tv.red_circle, fill="#4b0000")

    # Manual controls
    def go_button(self):
        self.stop_traffic_cycle()
        self.state.current_phase["state"] = "GO"
        self.state.current_phase["time_left"] = self.t_go
        self.send_command("G")
        self.update_traffic_view()
        self._schedule_timer()

    def caution_button(self):
        self.stop_traffic_cycle()
        self.state.current_phase["state"] = "CAUTION"
        self.state.current_phase["time_left"] = self.t_caution
        self.send_command("Y")
        self.update_traffic_view()
        self._schedule_timer()

    def stop_button(self):
        self.stop_traffic_cycle()
        self.state.current_phase["state"] = "STOP"
        self.state.current_phase["time_left"] = self.t_stop
        self.send_command("R")
        self.update_traffic_view()
        self._schedule_timer()
