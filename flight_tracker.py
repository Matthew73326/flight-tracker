"""
Flight Tracker - ADS-B Exchange military aircraft notifier
GitHub: https://github.com/Matthew73326/flight-tracker
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import json, os, math, time, threading, queue, webbrowser, sys, shutil, tempfile
from datetime import datetime

# ── Version ───────────────────────────────────────────────────────────────────
VERSION = "1.1.0"
GITHUB_USER = "Matthew73326"
GITHUB_REPO = "flight-tracker"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/version.json"
RAW_BASE    = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main"

# ── Startup log ───────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(BASE_DIR, "startup_log.txt")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def _write_log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception:
        pass

_write_log(f"=== Flight Tracker v{VERSION} starting ===")

# ── requests ──────────────────────────────────────────────────────────────────
try:
    import requests
    _write_log("requests: OK")
except ImportError:
    requests = None
    _write_log("requests: MISSING")

# ── Notification backends ─────────────────────────────────────────────────────
TOAST_OK = False
WINOTIFY  = False
toaster   = None

try:
    from windows_toasts import Toast, WindowsToaster, ToastDuration
    try:
        from windows_toasts import ToastActivatedEventArgs
    except ImportError:
        ToastActivatedEventArgs = None
    toaster  = WindowsToaster("Flight Tracker")
    TOAST_OK = True
    _write_log("windows_toasts: OK")
except Exception as e:
    _write_log(f"windows_toasts: FAILED ({e})")

if not TOAST_OK:
    try:
        from winotify import Notification, audio as winaudio
        WINOTIFY = True
        _write_log("winotify: OK")
    except Exception as e:
        _write_log(f"winotify: FAILED ({e})")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "location_name":             "London",
    "latitude":                   51.5074,
    "longitude":                 -0.1278,
    "radius_km":                  50,
    "poll_interval_sec":          60,
    "monitor_mode":               "military",
    "aircraft_types":             [],
    "registrations":              [],
    "notification_cooldown_sec":  300,
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
    except Exception as e:
        _write_log(f"Config load error: {e}")
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        _write_log(f"Config save error: {e}")

# ── Geo ───────────────────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

# ── ADS-B fetch ───────────────────────────────────────────────────────────────
def fetch_aircraft(lat, lon, radius_km, military_only=False):
    if military_only:
        url = "https://api.adsb.lol/v2/mil"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        all_ac = r.json().get("ac", [])
        in_range = []
        for ac in all_ac:
            try:
                dist = haversine_km(lat, lon, float(ac["lat"]), float(ac["lon"]))
                if dist <= radius_km:
                    ac["_dist_km"] = round(dist, 1)
                    in_range.append(ac)
            except (KeyError, TypeError, ValueError):
                continue
        return in_range
    else:
        radius_nm = radius_km / 1.852
        url = f"https://api.adsb.lol/v2/lat/{lat:.4f}/lon/{lon:.4f}/dist/{radius_nm:.1f}"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json().get("ac", [])

def aircraft_matches(ac, cfg):
    mode = cfg.get("monitor_mode", "all")
    if mode in ("all", "military"):
        return True
    if mode == "types":
        t = (ac.get("t") or "").upper()
        return any(x.upper() in t for x in cfg.get("aircraft_types", []))
    if mode == "registrations":
        reg = (ac.get("r") or "").upper()
        return reg in [x.upper() for x in cfg.get("registrations", [])]
    return False

# ── Notifications ─────────────────────────────────────────────────────────────
_notif_q = queue.Queue()

def send_notification(title, body, url=None):
    if TOAST_OK:
        try:
            toast = Toast()
            toast.text_fields = [title, body]
            toast.duration = ToastDuration.Short
            if url:
                if ToastActivatedEventArgs is not None:
                    def on_activated(e):
                        webbrowser.open(url)
                    toast.on_activated = on_activated
                else:
                    toast.launch_action = url
            toaster.show_toast(toast)
            return
        except Exception as e:
            _write_log(f"windows_toasts send error: {e}")
    if WINOTIFY:
        try:
            n = Notification(app_id="Flight Tracker", title=title, msg=body, duration="short")
            n.set_audio(winaudio.Default, loop=False)
            if url:
                n.add_actions(label="Track on map", launch=url)
            n.show()
            return
        except Exception as e:
            _write_log(f"winotify send error: {e}")
    _notif_q.put((title, body, url))

# ── Auto updater ──────────────────────────────────────────────────────────────
def parse_version(v):
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0, 0, 0)

def check_for_updates(silent=False):
    """Returns (latest_version, changelog) or (None, None) if up to date / error."""
    if requests is None:
        return None, None
    try:
        r = requests.get(VERSION_URL, timeout=8)
        r.raise_for_status()
        data = r.json()
        latest  = data.get("version", VERSION)
        changelog = data.get("changelog", "No changelog provided.")
        if parse_version(latest) > parse_version(VERSION):
            return latest, changelog
        return None, None
    except Exception as e:
        _write_log(f"Update check failed: {e}")
        return None, None

def download_update():
    """Downloads the latest flight_tracker.py and replaces the current one."""
    try:
        url = f"{RAW_BASE}/flight_tracker.py"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        new_code = r.text

        # Write to a temp file first, then replace
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8")
        tmp.write(new_code)
        tmp.close()

        current = os.path.abspath(__file__)
        backup  = current + ".bak"
        shutil.copy2(current, backup)       # keep a backup
        shutil.move(tmp.name, current)
        return True, None
    except Exception as e:
        _write_log(f"Update download failed: {e}")
        return False, str(e)

def restart_app():
    """Restart the application."""
    python = sys.executable
    os.execl(python, python, *sys.argv)

# ── Monitor thread ────────────────────────────────────────────────────────────
class FlightMonitor:
    def __init__(self, log_cb):
        self.log_cb  = log_cb
        self.running = False
        self._seen   = {}

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_cb(f"[{ts}] {msg}")

    def start(self, cfg):
        if self.running:
            return
        self.cfg     = cfg
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _loop(self):
        cfg      = self.cfg
        mode     = cfg.get("monitor_mode", "military")
        mil_only = (mode == "military")
        self.log(f"Started | {cfg['location_name']} ({cfg['latitude']}, {cfg['longitude']}) | "
                 f"Radius: {cfg['radius_km']} km | Mode: {mode}")

        while self.running:
            try:
                if requests is None:
                    self.log("WARNING: 'requests' not installed. Run setup_install.bat first!")
                else:
                    aircraft = fetch_aircraft(
                        cfg["latitude"], cfg["longitude"], cfg["radius_km"],
                        military_only=mil_only)
                    self.log(f"Polled ({mode}) - {len(aircraft)} aircraft in range")
                    now      = time.time()
                    cooldown = cfg.get("notification_cooldown_sec", 300)

                    for ac in aircraft:
                        if not aircraft_matches(ac, cfg):
                            continue
                        icao = ac.get("hex") or "unknown"
                        if now - self._seen.get(icao, 0) < cooldown:
                            continue
                        self._seen[icao] = now

                        reg      = (ac.get("r")      or "?").strip()
                        callsign = (ac.get("flight")  or "?").strip()
                        actype   = (ac.get("t")       or "?").strip()
                        alt      = ac.get("alt_baro") or ac.get("alt_geom") or "?"
                        spd      = ac.get("gs")       or "?"
                        dist     = ac.get("_dist_km") or "?"

                        if dist == "?":
                            try:
                                dist = round(haversine_km(
                                    cfg["latitude"], cfg["longitude"],
                                    float(ac["lat"]), float(ac["lon"])), 1)
                            except Exception:
                                dist = "?"

                        title   = f"[MIL] {callsign} ({reg})" if mil_only else f"{callsign} ({reg})"
                        body    = (f"Type: {actype}  |  Alt: {alt} ft  |  "
                                   f"Speed: {spd} kts  |  ~{dist} km away")
                        map_url = f"https://globe.adsbexchange.com/?icao={icao}" if icao != "unknown" else None

                        self.log(f"  NOTIFY -> {title} | {body}")
                        send_notification(title, body, url=map_url)

            except Exception as e:
                self.log(f"Error: {e}")
                _write_log(f"Monitor loop error: {e}")

            for _ in range(cfg.get("poll_interval_sec", 60)):
                if not self.running:
                    break
                time.sleep(1)

        self.log("Monitoring stopped.")


# ── Colours / fonts ───────────────────────────────────────────────────────────
BG     = "#0d1117"
PANEL  = "#161b22"
BORDER = "#30363d"
ACCENT = "#58a6ff"
GREEN  = "#3fb950"
RED    = "#f85149"
YELLOW = "#d29922"
TEXT   = "#e6edf3"
MUTED  = "#8b949e"

FONT_BODY  = ("Consolas", 10)
FONT_LABEL = ("Segoe UI", 10)
FONT_HEAD  = ("Segoe UI Semibold", 11)
FONT_BIG   = ("Segoe UI Semibold", 14)


# ── Update dialog ─────────────────────────────────────────────────────────────
class UpdateDialog(tk.Toplevel):
    def __init__(self, parent, latest_version, changelog):
        super().__init__(parent)
        self.parent  = parent
        self.title("Update Available")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("460x320")
        self.grab_set()  # modal

        tk.Label(self, text="Update Available!", font=FONT_BIG,
                 bg=BG, fg=YELLOW).pack(pady=(20, 4))
        tk.Label(self, text=f"Version {latest_version} is available  (you have {VERSION})",
                 font=FONT_LABEL, bg=BG, fg=MUTED).pack()

        tk.Label(self, text="What's new:", font=("Segoe UI Semibold", 10),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=20, pady=(16, 4))

        txt = tk.Text(self, bg=PANEL, fg=TEXT, font=FONT_BODY,
                      relief="flat", height=6, wrap="word")
        txt.insert("1.0", changelog)
        txt.config(state="disabled")
        txt.pack(fill="x", padx=20)

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(pady=16)

        tk.Button(btn_row, text="Update Now", command=self._do_update,
                  font=FONT_HEAD, bg=GREEN, fg="#000", activebackground="#2ea043",
                  relief="flat", padx=16, pady=8, cursor="hand2").pack(side="left", padx=8)

        tk.Button(btn_row, text="Not Now", command=self.destroy,
                  font=FONT_HEAD, bg=BORDER, fg=MUTED, activebackground=BORDER,
                  relief="flat", padx=16, pady=8, cursor="hand2").pack(side="left", padx=8)

        tk.Button(btn_row, text="View on GitHub",
                  command=lambda: webbrowser.open(f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}"),
                  font=FONT_HEAD, bg=PANEL, fg=TEXT, activebackground=BORDER,
                  relief="flat", padx=16, pady=8, cursor="hand2").pack(side="left", padx=8)

    def _do_update(self):
        self.destroy()
        # Show progress
        prog = tk.Toplevel(self.parent)
        prog.title("Updating...")
        prog.configure(bg=BG)
        prog.geometry("340x120")
        prog.resizable(False, False)
        tk.Label(prog, text="Downloading update...", font=FONT_HEAD,
                 bg=BG, fg=TEXT).pack(pady=20)
        tk.Label(prog, text="The app will restart automatically.",
                 font=FONT_LABEL, bg=BG, fg=MUTED).pack()
        prog.update()

        def _run():
            ok, err = download_update()
            prog.destroy()
            if ok:
                messagebox.showinfo("Updated!",
                    f"Successfully updated to the latest version.\nThe app will now restart.")
                restart_app()
            else:
                messagebox.showerror("Update Failed",
                    f"Could not download update:\n{err}\n\nYou can update manually from GitHub.")

        threading.Thread(target=_run, daemon=True).start()


# ── Main GUI ──────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        _write_log("GUI init started")
        self.title("Flight Tracker")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.geometry("720x720")
        self.cfg     = load_config()
        self.monitor = FlightMonitor(log_cb=self._log)
        self._build_ui()
        self._poll_notif_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        _write_log("GUI init complete")
        # Check for updates in background after 2 seconds
        self.after(2000, self._check_updates_bg)

    def _check_updates_bg(self):
        def _run():
            latest, changelog = check_for_updates()
            if latest:
                self.after(0, lambda: self._show_update_dialog(latest, changelog))
            else:
                self._log(f"v{VERSION} - App is up to date.")
        threading.Thread(target=_run, daemon=True).start()

    def _show_update_dialog(self, latest, changelog):
        self._log(f"Update available: v{latest}")
        UpdateDialog(self, latest, changelog)

    def _build_ui(self):
        # Header with version
        hdr = tk.Frame(self, bg=PANEL, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="FLIGHT TRACKER", font=FONT_BIG, bg=PANEL, fg=ACCENT).pack()
        tk.Label(hdr, text=f"Live ADS-B  -  Windows Notifications  -  v{VERSION}",
                 font=("Segoe UI", 9), bg=PANEL, fg=MUTED).pack()
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=14)

        # Location
        self._section(body, "Location")
        row1 = tk.Frame(body, bg=BG)
        row1.pack(fill="x", pady=(2, 10))
        self.e_name = self._entry(row1, "Name",        self.cfg["location_name"],  col=0, width=16)
        self.e_lat  = self._entry(row1, "Latitude",    str(self.cfg["latitude"]),  col=2, width=12)
        self.e_lon  = self._entry(row1, "Longitude",   str(self.cfg["longitude"]), col=4, width=12)
        self.e_rad  = self._entry(row1, "Radius (km)", str(self.cfg["radius_km"]), col=6, width=8)

        # Monitor mode
        self._section(body, "What to Monitor")
        mode_row = tk.Frame(body, bg=BG)
        mode_row.pack(fill="x", pady=(2, 6))
        self.mode_var = tk.StringVar(value=self.cfg["monitor_mode"])
        for val, lbl in [
            ("military",      "Military only  (uses /mil endpoint - no false positives)"),
            ("all",           "All aircraft"),
            ("types",         "Specific types"),
            ("registrations", "Specific registrations"),
        ]:
            tk.Radiobutton(
                mode_row, text=lbl, variable=self.mode_var, value=val,
                bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                font=FONT_LABEL, command=self._on_mode_change
            ).pack(anchor="w", padx=(0, 14))

        filters = tk.Frame(body, bg=BG)
        filters.pack(fill="x", pady=(4, 10))
        tk.Label(filters, text="Aircraft types (e.g. A400, C17, EUFI, CH47):",
                 bg=BG, fg=MUTED, font=FONT_LABEL).grid(row=0, column=0, sticky="w")
        self.e_types = self._flat_entry(filters, ",".join(self.cfg.get("aircraft_types", [])), col=1, row=0)
        tk.Label(filters, text="Registrations (e.g. ZM413, ZZ333):",
                 bg=BG, fg=MUTED, font=FONT_LABEL).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.e_regs = self._flat_entry(filters, ",".join(self.cfg.get("registrations", [])), col=1, row=1)
        filters.columnconfigure(1, weight=1)
        self._on_mode_change()

        # Timing
        self._section(body, "Timing")
        row2 = tk.Frame(body, bg=BG)
        row2.pack(fill="x", pady=(2, 12))
        self.e_poll     = self._entry(row2, "Poll every (sec)",         str(self.cfg["poll_interval_sec"]),         col=0, width=8)
        self.e_cooldown = self._entry(row2, "Re-notify cooldown (sec)", str(self.cfg["notification_cooldown_sec"]), col=2, width=8)

        # Buttons
        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(pady=4)

        self.btn_start = tk.Button(
            btn_row, text="Start Monitoring", command=self._start,
            font=FONT_HEAD, bg=GREEN, fg="#000", activebackground="#2ea043",
            relief="flat", padx=18, pady=8, cursor="hand2")
        self.btn_start.pack(side="left", padx=6)

        self.btn_stop = tk.Button(
            btn_row, text="Stop", command=self._stop,
            font=FONT_HEAD, bg=BORDER, fg=MUTED, activebackground=BORDER,
            relief="flat", padx=18, pady=8, cursor="hand2", state="disabled")
        self.btn_stop.pack(side="left", padx=6)

        tk.Button(
            btn_row, text="Save Config", command=self._save_cfg,
            font=FONT_HEAD, bg=PANEL, fg=TEXT, activebackground=BORDER,
            relief="flat", padx=18, pady=8, cursor="hand2"
        ).pack(side="left", padx=6)

        tk.Button(
            btn_row, text="Test Notification", command=self._test_notif,
            font=FONT_HEAD, bg=PANEL, fg=TEXT, activebackground=BORDER,
            relief="flat", padx=18, pady=8, cursor="hand2"
        ).pack(side="left", padx=6)

        tk.Button(
            btn_row, text="Check for Updates", command=self._manual_update_check,
            font=FONT_HEAD, bg=PANEL, fg=TEXT, activebackground=BORDER,
            relief="flat", padx=18, pady=8, cursor="hand2"
        ).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="Idle")
        tk.Label(body, textvariable=self.status_var,
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        # Log
        self._section(body, "Activity Log")
        self.log_box = scrolledtext.ScrolledText(
            body, bg=PANEL, fg=TEXT, font=FONT_BODY,
            relief="flat", height=12, state="disabled", insertbackground=TEXT)
        self.log_box.pack(fill="both", expand=True)

        self._log(f"Flight Tracker v{VERSION} ready. Press Start Monitoring.")
        if TOAST_OK:
            self._log("OK: Toast notifications ready. Click notification to open aircraft on map.")
        elif WINOTIFY:
            self._log("OK: winotify notifications ready.")
        else:
            self._log("WARNING: No toast library - run setup_install.bat.")
        if requests is None:
            self._log("WARNING: 'requests' not installed - run setup_install.bat first.")

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(10, 2))
        tk.Label(f, text=title, bg=BG, fg=ACCENT, font=FONT_HEAD).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=8, pady=6)

    def _entry(self, parent, label, value, col=0, width=14):
        tk.Label(parent, text=label, bg=BG, fg=MUTED, font=FONT_LABEL).grid(
            row=0, column=col, sticky="w", padx=(0 if col == 0 else 16, 4))
        e = tk.Entry(parent, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                     font=FONT_BODY, relief="flat", bd=6, width=width)
        e.insert(0, value)
        e.grid(row=0, column=col+1, sticky="ew")
        return e

    def _flat_entry(self, parent, value, col=1, row=0):
        e = tk.Entry(parent, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                     font=FONT_BODY, relief="flat", bd=6)
        e.insert(0, value)
        e.grid(row=row, column=col, padx=(12, 0), sticky="ew",
               pady=(0 if row == 0 else 6, 0))
        return e

    def _on_mode_change(self):
        mode = self.mode_var.get()
        self.e_types.config(state="normal" if mode == "types"         else "disabled",
                            fg=TEXT        if mode == "types"         else MUTED)
        self.e_regs.config( state="normal" if mode == "registrations" else "disabled",
                            fg=TEXT        if mode == "registrations" else MUTED)

    def _read_ui(self):
        try:
            self.cfg["location_name"]             = self.e_name.get().strip()
            self.cfg["latitude"]                  = float(self.e_lat.get())
            self.cfg["longitude"]                 = float(self.e_lon.get())
            self.cfg["radius_km"]                 = float(self.e_rad.get())
            self.cfg["poll_interval_sec"]         = int(self.e_poll.get())
            self.cfg["notification_cooldown_sec"] = int(self.e_cooldown.get())
            self.cfg["monitor_mode"]              = self.mode_var.get()
            self.cfg["aircraft_types"]            = [x.strip().upper() for x in self.e_types.get().split(",") if x.strip()]
            self.cfg["registrations"]             = [x.strip().upper() for x in self.e_regs.get().split(",") if x.strip()]
            return True
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return False

    def _save_cfg(self):
        if self._read_ui():
            save_config(self.cfg)
            self._log("Config saved.")

    def _test_notif(self):
        send_notification(
            "Flight Tracker Test",
            "Click this notification to open ADS-B Exchange map.",
            url="https://globe.adsbexchange.com"
        )
        self._log("Test notification sent.")

    def _manual_update_check(self):
        self._log("Checking for updates...")
        def _run():
            latest, changelog = check_for_updates()
            if latest:
                self.after(0, lambda: self._show_update_dialog(latest, changelog))
            else:
                self.after(0, lambda: self._log("Already on the latest version."))
        threading.Thread(target=_run, daemon=True).start()

    def _start(self):
        if not self._read_ui():
            return
        save_config(self.cfg)
        self.monitor.start(self.cfg)
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal", bg=RED, fg="#fff", activebackground="#c93728")
        self.status_var.set("Monitoring...")

    def _stop(self):
        self.monitor.stop()
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled", bg=BORDER, fg=MUTED)
        self.status_var.set("Idle")

    def _log(self, msg):
        def _do():
            self.log_box.config(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _do)

    def _poll_notif_queue(self):
        try:
            while True:
                item = _notif_q.get_nowait()
                title, body, url = item
                messagebox.showinfo(title, body)
                if url:
                    webbrowser.open(url)
        except queue.Empty:
            pass
        self.after(1000, self._poll_notif_queue)

    def _on_close(self):
        self.monitor.stop()
        self.destroy()


if __name__ == "__main__":
    try:
        _write_log("Launching App()")
        app = App()
        app.mainloop()
        _write_log("App exited normally")
    except Exception as e:
        _write_log(f"FATAL ERROR: {e}")
        import traceback
        _write_log(traceback.format_exc())
        try:
            root = tk.Tk()
            root.title("Flight Tracker - Error")
            root.geometry("600x300")
            tk.Label(root, text="Flight Tracker failed to start:", fg="red",
                     font=("Segoe UI", 11)).pack(pady=10)
            txt = tk.Text(root, wrap="word", height=10)
            txt.insert("1.0", traceback.format_exc())
            txt.pack(fill="both", expand=True, padx=10)
            tk.Label(root, text=f"Full log: {LOG_FILE}",
                     font=("Segoe UI", 9)).pack(pady=5)
            root.mainloop()
        except Exception:
            pass
