import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
	from pynput import mouse, keyboard
except Exception as e:
	mouse = None
	keyboard = None


class AutoClickerApp:
	def __init__(self, root: tk.Tk):
		self.root = root
		self.root.title("Auto Clicker")
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)

		self.running = threading.Event()
		self.exit_event = threading.Event()

		self._create_widgets()

		self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
		self.click_thread.start()

		self.hk_listener = None
		self._start_hotkeys()

		self._mouse_pos_job = None
		self._schedule_mouse_pos_update()

	def _create_widgets(self):
		frm = ttk.Frame(self.root, padding=12)
		frm.grid(row=0, column=0, sticky="nsew")

		ttk.Label(frm, text="Interval (ms):").grid(row=0, column=0, sticky="w")
		self.ms_var = tk.StringVar(value="100")
		self.ms_entry = ttk.Entry(frm, textvariable=self.ms_var, width=12)
		self.ms_entry.grid(row=0, column=1, sticky="w")

		self.clicks_unlimited_var = tk.BooleanVar(value=True)
		self.clicks_var = tk.StringVar(value="100")
		ttk.Label(frm, text="Clicks:").grid(row=1, column=0, sticky="w", pady=(6, 0))
		self.clicks_entry = ttk.Entry(frm, textvariable=self.clicks_var, width=12)
		self.clicks_entry.grid(row=1, column=1, sticky="w", pady=(6, 0))
		self.unlimited_chk = ttk.Checkbutton(frm, text="Unlimited", variable=self.clicks_unlimited_var, command=self._on_unlimited_toggle)
		self.unlimited_chk.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(6, 0))

		self.use_pos_var = tk.BooleanVar(value=False)
		self.x_var = tk.StringVar(value="0")
		self.y_var = tk.StringVar(value="0")
		self.use_pos_chk = ttk.Checkbutton(frm, text="Click at fixed position", variable=self.use_pos_var, command=self._on_fixed_toggle)
		self.use_pos_chk.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

		coords_frm = ttk.Frame(frm)
		coords_frm.grid(row=3, column=0, columnspan=3, sticky="w")
		self.x_label = ttk.Label(coords_frm, text="X:")
		self.x_label.grid(row=0, column=0, sticky="w")
		self.x_entry = ttk.Entry(coords_frm, textvariable=self.x_var, width=10)
		self.x_entry.grid(row=0, column=1, sticky="w", padx=(2, 8))
		self.y_label = ttk.Label(coords_frm, text="Y:")
		self.y_label.grid(row=0, column=2, sticky="w")
		self.y_entry = ttk.Entry(coords_frm, textvariable=self.y_var, width=10)
		self.y_entry.grid(row=0, column=3, sticky="w", padx=(2, 8))
		self.record_btn = ttk.Button(coords_frm, text="Record (F8)", command=self._record_and_add)
		self.record_btn.grid(row=0, column=4, sticky="w")

		self.coord_list_label = ttk.Label(frm, text="Coordinate list:")
		self.coord_list_label.grid(row=4, column=0, sticky="w", pady=(8, 0))
		list_frm = ttk.Frame(frm)
		list_frm.grid(row=5, column=0, columnspan=3, sticky="nsew")
		self.coord_listbox = tk.Listbox(list_frm, height=6, width=40, exportselection=False)
		self.coord_listbox.grid(row=0, column=0, sticky="nsew")
		self.coord_scroll = ttk.Scrollbar(list_frm, orient="vertical", command=self.coord_listbox.yview)
		self.coord_scroll.grid(row=0, column=1, sticky="ns")
		self.coord_listbox.configure(yscrollcommand=self.coord_scroll.set)
		list_frm.columnconfigure(0, weight=1)
		list_frm.rowconfigure(0, weight=1)

		list_btns = ttk.Frame(frm)
		list_btns.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))
		self.add_xy_btn = ttk.Button(list_btns, text="Add X,Y", command=self._add_current_xy)
		self.add_xy_btn.grid(row=0, column=0, padx=(0, 6))
		self.remove_btn = ttk.Button(list_btns, text="Remove Selected", command=self._remove_selected_coord)
		self.remove_btn.grid(row=0, column=1, padx=(0, 6))
		self.clear_btn = ttk.Button(list_btns, text="Clear", command=self._clear_coords)
		self.clear_btn.grid(row=0, column=2)

		ttk.Label(frm, text="(F7 = toggle, F8 = record & add to list, Ctrl+Alt+A = enable, Ctrl+Alt+D = disable)").grid(row=7, column=0, columnspan=3, sticky="w", pady=(6, 6))

		btn_frame = ttk.Frame(frm)
		btn_frame.grid(row=8, column=0, columnspan=3, pady=(6, 0))

		self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start)
		self.start_btn.grid(row=0, column=0, padx=(0, 8))
		self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop)
		self.stop_btn.grid(row=0, column=1)
		self.tester_btn = ttk.Button(btn_frame, text="TPS Tester", command=self._open_tester_window)
		self.tester_btn.grid(row=0, column=2, padx=(8, 0))

		self.mouse_pos_lbl = ttk.Label(frm, text="Mouse: x=?, y=?")
		self.mouse_pos_lbl.grid(row=9, column=0, columnspan=3, sticky="w", pady=(8, 0))

		ttk.Label(frm, text="Status:").grid(row=10, column=0, sticky="w", pady=(8, 0))
		self.status_lbl = ttk.Label(frm, text="Stopped", foreground="red")
		self.status_lbl.grid(row=10, column=1, sticky="w", pady=(8, 0))
		self.status_more_lbl = ttk.Label(frm, text="")
		self.status_more_lbl.grid(row=10, column=2, sticky="w", pady=(8, 0))

		vcmd = (self.root.register(self._validate_int), "%P")
		self.ms_entry.config(validate="key", validatecommand=vcmd)
		self.clicks_entry.config(validate="key", validatecommand=vcmd)
		self.x_entry.config(validate="key", validatecommand=vcmd)
		self.y_entry.config(validate="key", validatecommand=vcmd)

		self.coord_list = []

		self._on_unlimited_toggle()
		self._on_fixed_toggle()

		self.longpress_var = tk.StringVar(value="off")
		ttk.Label(frm, text="Long press:").grid(row=11, column=0, sticky="w", pady=(8, 0))
		lp_frm = ttk.Frame(frm)
		lp_frm.grid(row=11, column=1, columnspan=2, sticky="w", pady=(8, 0))
		self.lp_off = ttk.Radiobutton(lp_frm, text="Off", variable=self.longpress_var, value="off", command=self._on_longpress_toggle)
		self.lp_on = ttk.Radiobutton(lp_frm, text="On", variable=self.longpress_var, value="on", command=self._on_longpress_toggle)
		self.lp_off.grid(row=0, column=0, padx=(0, 8))
		self.lp_on.grid(row=0, column=1, padx=(0, 8))
		ttk.Label(lp_frm, text="Hold (ms):").grid(row=0, column=2, padx=(8, 2))
		self.hold_ms_var = tk.StringVar(value="200")
		self.hold_ms_entry = ttk.Entry(lp_frm, textvariable=self.hold_ms_var, width=8)
		self.hold_ms_entry.grid(row=0, column=3)
		self.hold_ms_entry.config(validate="key", validatecommand=vcmd)
		self._on_longpress_toggle()

	def _validate_int(self, proposed: str) -> bool:
		if proposed == "":
			return True
		try:
			v = int(proposed)
			return v >= 0
		except Exception:
			return False

	def start(self):
		try:
			ms = int(self.ms_var.get())
		except Exception:
			messagebox.showerror("Invalid interval", "Please enter a valid integer for milliseconds.")
			return

		if ms < 1:
			messagebox.showwarning("Interval too small", "Minimum interval is 1 ms. Using 1 ms.")
			ms = 1
			self.ms_var.set("1")

		unlimited = self.clicks_unlimited_var.get()
		clicks_count = None
		if not unlimited:
			try:
				clicks_count = int(self.clicks_var.get())
			except Exception:
				messagebox.showerror("Invalid clicks", "Please enter a valid integer for number of clicks.")
				return
			if clicks_count <= 0:
				messagebox.showerror("Invalid clicks", "Number of clicks must be greater than 0 or set Unlimited.")
				return

		use_fixed = self.use_pos_var.get()
		target_pos = None
		if use_fixed:
			coords = list(self.coord_list)
			if len(coords) == 0:
				try:
					x = int(self.x_var.get())
					y = int(self.y_var.get())
				except Exception:
					messagebox.showerror("Invalid position", "Please enter valid integers for X and Y or add coordinates to the list.")
					return
				if x < 0 or y < 0:
					messagebox.showerror("Invalid position", "X and Y must be zero or positive.")
					return
				target_pos = (x, y)
			else:
				target_pos = None
				self._coord_list_snapshot = coords
				self._coord_index = 0

		self.interval = ms / 1000.0
		self._unlimited = unlimited
		self._remaining_clicks = clicks_count
		self._use_fixed_pos = use_fixed
		self._target_pos = target_pos
		self._clicks_made = 0

		lp_on = self.longpress_var.get() == "on"
		self._longpress = lp_on
		self._hold_s = None
		if lp_on:
			try:
				hold_ms = int(self.hold_ms_var.get())
			except Exception:
				messagebox.showerror("Invalid hold", "Please enter a valid integer for Hold (ms).")
				return
			if hold_ms < 1:
				messagebox.showwarning("Hold too small", "Minimum hold is 1 ms. Using 1 ms.")
				hold_ms = 1
				self.hold_ms_var.set("1")
			self._hold_s = hold_ms / 1000.0

		try:
			if self._mouse_pos_job:
				self.root.after_cancel(self._mouse_pos_job)
				self._mouse_pos_job = None
		except Exception:
			pass

		self.running.set()
		self._update_status()

	def stop(self):
		self.running.clear()
		self._update_status()
		if not self.exit_event.is_set():
			self._schedule_mouse_pos_update()

	def toggle(self):
		if self.running.is_set():
			self.stop()
		else:
			self.start()

	def _update_status(self):
		if self.running.is_set():
			self.status_lbl.config(text="Running", foreground="green")
			if getattr(self, "_unlimited", True):
				self.status_more_lbl.config(text="(unlimited)")
			else:
				rem = getattr(self, "_remaining_clicks", None)
				self.status_more_lbl.config(text=f"({rem} left)" if rem is not None else "")
		else:
			self.status_lbl.config(text="Stopped", foreground="red")
			self.status_more_lbl.config(text="")

	def _click_loop(self):
		if mouse is None:
			return
		m = mouse.Controller()
		while not self.exit_event.is_set():
			if self.running.is_set():
				try:
					if getattr(self, "_use_fixed_pos", False):
						coords = getattr(self, "_coord_list_snapshot", None)
						if coords and len(coords) > 0:
							pos = coords[getattr(self, "_coord_index", 0) % len(coords)]
							try:
								m.position = pos
							except Exception:
								pass
							self._coord_index = (getattr(self, "_coord_index", 0) + 1) % len(coords)
						elif getattr(self, "_target_pos", None) is not None:
							try:
								m.position = self._target_pos
							except Exception:
								pass
					if getattr(self, "_longpress", False):
						try:
							m.press(mouse.Button.left)
						except Exception:
							pass
						hold_s = getattr(self, "_hold_s", 0.2)
						waited_h = 0.0
						step_h = 0.01
						while waited_h < hold_s and not self.exit_event.is_set() and self.running.is_set():
							time.sleep(min(step_h, hold_s - waited_h))
							waited_h += step_h
						try:
							m.release(mouse.Button.left)
						except Exception:
							pass
					else:
						m.click(mouse.Button.left, 1)
				except Exception:
					pass

				if not getattr(self, "_unlimited", True):
					if getattr(self, "_remaining_clicks", None) is not None and self._remaining_clicks > 0:
						self._remaining_clicks -= 1
						self._clicks_made += 1
						try:
							self.root.after(0, self._update_status)
						except Exception:
							pass
						if self._remaining_clicks <= 0:
							self.running.clear()
							try:
								self.root.after(0, self._update_status)
								self.root.after(0, self._schedule_mouse_pos_update)
							except Exception:
								pass
				interval = getattr(self, "interval", 0.1)
				waited = 0.0
				step = 0.01
				while waited < interval and not self.exit_event.is_set() and self.running.is_set():
					time.sleep(min(step, interval - waited))
					waited += step
			else:
				time.sleep(0.05)

	def _start_hotkeys(self):
		if keyboard is None:
			self.status_lbl.config(text="Stopped (pynput missing)", foreground="orange")
			return

		hotkey_map = {
			"<ctrl>+<alt>+a": self._hotkey_enable,
			"<ctrl>+<alt>+d": self._hotkey_disable,
			"<f7>": self._hotkey_toggle,
			"<f8>": self._hotkey_record,
		}

		try:
			self.hk_listener = keyboard.GlobalHotKeys(hotkey_map)
			self.hk_thread = threading.Thread(target=self._run_hotkey_listener, daemon=True)
			self.hk_thread.start()
			self.root.after(0, lambda: self.status_lbl.config(text="Stopped (hotkeys enabled)", foreground="orange"))
		except Exception:
			try:
				self._start_manual_listener()
				self.root.after(0, lambda: self.status_lbl.config(text="Stopped (hotkey listener)", foreground="orange"))
			except Exception:
				self.root.after(0, lambda: messagebox.showwarning("Hotkeys", "Failed to start global hotkeys."))


	def _start_manual_listener(self):
		self._pressed = set()

		def on_press(key):
			self._pressed.add(key)
			try:
				# detect 'a' or 'd' as character keys
				chars = {k.char for k in self._pressed if hasattr(k, 'char') and k.char is not None}
			except Exception:
				chars = set()

			mods = {str(k) for k in self._pressed if str(k).startswith('Key.')}
			ctrl = any(k in mods for k in ('Key.ctrl_l', 'Key.ctrl_r', 'Key.ctrl'))
			alt = any(k in mods for k in ('Key.alt_l', 'Key.alt_r', 'Key.alt'))

			if ctrl and alt and 'a' in chars:
				self.root.after(0, self.start)
			elif ctrl and alt and 'd' in chars:
				self.root.after(0, self.stop)
			# F7 toggle support
			mods_str = {str(k) for k in self._pressed if str(k).startswith('Key.')}
			if 'Key.f7' in mods_str:
				self.root.after(0, self.toggle)
			if 'Key.f8' in mods_str:
				self.root.after(0, self._record_and_add)

		def on_release(key):
			if key in self._pressed:
				self._pressed.remove(key)

		self._manual_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
		self._manual_listener.daemon = True
		self._manual_listener.start()

	def _run_hotkey_listener(self):
		try:
			if self.hk_listener:
				self.hk_listener.start()
				while not self.exit_event.is_set():
					time.sleep(0.1)
				try:
					self.hk_listener.stop()
				except Exception:
					pass
		except Exception:
			self.root.after(0, lambda: messagebox.showwarning("Hotkeys", "Failed to start global hotkeys."))

	def _hotkey_enable(self):
		def do_start():
			self.start()

		self.root.after(0, do_start)

	def _hotkey_disable(self):
		def do_stop():
			self.stop()

		self.root.after(0, do_stop)

	def _hotkey_toggle(self):
		self.root.after(0, self.toggle)

	def _hotkey_record(self):
		self.root.after(0, self._record_and_add)

	def _record_position(self):
		if mouse is None:
			messagebox.showwarning("Record position", "pynput is not available to read mouse position.")
			return
		try:
			m = mouse.Controller()
			x, y = m.position
			self.x_var.set(str(int(x)))
			self.y_var.set(str(int(y)))
		except Exception:
			messagebox.showwarning("Record position", "Failed to read mouse position.")

	def _record_and_add(self):
		self._record_position()
		self._add_current_xy()

	def _add_current_xy(self):
		try:
			x = int(self.x_var.get())
			y = int(self.y_var.get())
		except Exception:
			return
		if x < 0 or y < 0:
			return
		self.coord_list.append((x, y))
		self.coord_listbox.insert(tk.END, f"({x}, {y})")

	def _remove_selected_coord(self):
		# Remove selected entries from both listbox and list (from bottom up)
		try:
			selection = list(self.coord_listbox.curselection())
		except Exception:
			selection = []
		if not selection:
			return
		for idx in reversed(selection):
			try:
				self.coord_listbox.delete(idx)
			except Exception:
				pass
			try:
				if 0 <= idx < len(self.coord_list):
					self.coord_list.pop(idx)
			except Exception:
				pass

	def _clear_coords(self):
		self.coord_listbox.delete(0, tk.END)
		self.coord_list = []

	def _schedule_mouse_pos_update(self):
		if mouse is None:
			self.mouse_pos_lbl.config(text="Mouse: pynput missing")
			return
		try:
			m = mouse.Controller()
			x, y = m.position
			self.mouse_pos_lbl.config(text=f"Mouse: x={int(x)}, y={int(y)}")
		except Exception:
			pass
		if not self.exit_event.is_set() and self.root.winfo_exists():
			self._mouse_pos_job = self.root.after(100, self._schedule_mouse_pos_update)

	def _on_unlimited_toggle(self):
		if self.clicks_unlimited_var.get():
			self.clicks_entry.state(["disabled"])  # disable entry
		else:
			self.clicks_entry.state(["!disabled"])  # enable entry

	def _on_fixed_toggle(self):
		enabled = self.use_pos_var.get()
		for w in (self.x_label, self.x_entry, self.y_label, self.y_entry, self.record_btn):
			try:
				if enabled:
					w.state(["!disabled"]) if hasattr(w, 'state') else w.configure(state='normal')
				else:
					w.state(["disabled"]) if hasattr(w, 'state') else w.configure(state='disabled')
			except Exception:
				pass

	def _on_longpress_toggle(self):
		enabled = self.longpress_var.get() == "on"
		try:
			if enabled:
				self.hold_ms_entry.state(["!disabled"]) if hasattr(self.hold_ms_entry, 'state') else self.hold_ms_entry.configure(state='normal')
			else:
				self.hold_ms_entry.state(["disabled"]) if hasattr(self.hold_ms_entry, 'state') else self.hold_ms_entry.configure(state='disabled')
		except Exception:
			pass

	def _open_tester_window(self):
		if hasattr(self, 'tester_window') and self.tester_window.winfo_exists():
			self.tester_window.lift()
			return

		self.tester_window = tk.Toplevel(self.root)
		self.tester_window.title('TPS Tester')
		self.tester_window.protocol('WM_DELETE_WINDOW', self._close_tester_window)

		frm = ttk.Frame(self.tester_window, padding=10)
		frm.grid(row=0, column=0)

		self.tps_label = ttk.Label(frm, text='TPS: 0.00', font=('Segoe UI', 14))
		self.tps_label.grid(row=0, column=0, columnspan=3, pady=(0, 8))

		self.tester_start_btn = ttk.Button(frm, text='Start', command=self._start_tester)
		self.tester_start_btn.grid(row=1, column=0, padx=4)
		self.tester_stop_btn = ttk.Button(frm, text='Stop', command=self._stop_tester)
		self.tester_stop_btn.grid(row=1, column=1, padx=4)
		self.tester_reset_btn = ttk.Button(frm, text='Reset', command=self._reset_tester)
		self.tester_reset_btn.grid(row=1, column=2, padx=4)

		self._tester_timestamps = []
		self._tester_running = threading.Event()
		self._tester_listener = None
		self._tester_job = None

		if mouse is None:
			self.tester_start_btn.config(state='disabled')
			self.tps_label.config(text='TPS: pynput missing')


	def _start_tester(self):
		if mouse is None:
			return
		if self._tester_running.is_set():
			return
		self._tester_running.set()

		def on_click(x, y, button, pressed):
			if pressed:
				# record timestamp in seconds
				self._tester_timestamps.append(time.time())

		self._tester_listener = mouse.Listener(on_click=on_click)
		self._tester_listener.daemon = True
		self._tester_listener.start()

		self._update_tps()


	def _stop_tester(self):
		self._tester_running.clear()
		try:
			if self._tester_listener:
				self._tester_listener.stop()
		except Exception:
			pass
		self._tester_listener = None
		if getattr(self, '_tester_job', None):
			try:
				self.tester_window.after_cancel(self._tester_job)
			except Exception:
				pass
		self._tester_job = None


	def _reset_tester(self):
		self._tester_timestamps = []
		if getattr(self, 'tps_label', None):
			self.tps_label.config(text='TPS: 0.00')


	def _update_tps(self):
		now = time.time()
		cutoff = now - 1.0
		self._tester_timestamps = [t for t in self._tester_timestamps if t >= cutoff]
		count = len(self._tester_timestamps)
		if getattr(self, 'tps_label', None):
			self.tps_label.config(text=f'TPS: {count:.2f}')
		if self._tester_running.is_set() and getattr(self, 'tester_window', None) and self.tester_window.winfo_exists():
			self._tester_job = self.tester_window.after(150, self._update_tps)
		else:
			self._tester_job = None


	def _close_tester_window(self):
		self._stop_tester()
		try:
			if getattr(self, 'tester_window', None):
				self.tester_window.destroy()
		except Exception:
			pass

	def on_close(self):
		self.exit_event.set()
		self.running.clear()
		try:
			if self.hk_listener:
				self.hk_listener.stop()
		except Exception:
			pass
		try:
			if self._mouse_pos_job:
				self.root.after_cancel(self._mouse_pos_job)
		except Exception:
			pass
		time.sleep(0.05)
		self.root.destroy()


def main():
	root = tk.Tk()
	app = AutoClickerApp(root)
	root.mainloop()


if __name__ == "__main__":
	main()