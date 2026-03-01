import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import requests


# ---------------------------------------------------------------------------
# Helpers (ported from nordnet_aktie_screener.py)
# ---------------------------------------------------------------------------

COUNTRIES = [
    ("Danmark",  "DDK"),
    ("Sverige",  "DSE"),
    ("Finland",  "DFI"),
    ("Norge",    "DNO"),
    ("Tyskland", "DDE"),
    ("USA",      "DUS"),
    ("Canada",   "DCA"),
]

EXCLUDE_FILE = "exclude_list.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/122.0.0.0 Safari/537.36")


def load_exclude_list():
    try:
        with open(EXCLUDE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"all_stocks": [{"my_stocks": []}, {"exclude_stocks": []}]}


def get_session_cookies():
    """Fetch cookies from the Nordnet landing page."""
    r = requests.get("https://www.nordnet.dk/markedet", headers={"User-Agent": UA}, timeout=15)
    return {c.name: c.value for c in r.cookies}


def login(session: requests.Session, username: str, password: str) -> bool:
    """
    Attempt to log in via Nordnet's API.
    Returns True on success, False otherwise.
    """
    # First visit landing page to pick up CSRF / session cookies
    session.get("https://www.nordnet.dk/markedet", headers={"User-Agent": UA}, timeout=15)

    login_url = "https://www.nordnet.dk/api/2/authentication/basic/login"
    payload = {"username": username, "password": password}
    headers = {
        "User-Agent": UA,
        "client-id": "NEXT",
        "Content-Type": "application/json",
    }
    r = session.post(login_url, json=payload, headers=headers, timeout=15)
    return r.status_code == 200


def fetch_stocks(cookies: dict, exchange_country: str,
                 headers: dict, log_fn) -> list:
    """Download all stocks for a given exchange country."""
    # Note: %3 (not %3A) matches the working original script's URL format
    url = (f"https://www.nordnet.dk/api/2/instrument_search/query/stocklist"
           f"?apply_filters=exchange_country%3{exchange_country}"
           f"&sort_order=desc&sort_attribute=dividend_yield&limit=100&offset=0")
    r = requests.get(url, cookies=cookies, headers=headers, timeout=15)
    if r.status_code != 200:
        log_fn(f"  [!] HTTP {r.status_code} for {exchange_country}")
        return []

    data = r.json()
    total = data.get("total_hits", 0)
    results = list(data.get("results", []))

    offset = 100
    batch = 100
    while offset < total:
        url = (f"https://www.nordnet.dk/api/2/instrument_search/query/stocklist"
               f"?apply_filters=exchange_country%3{exchange_country}"
               f"&sort_order=desc&sort_attribute=dividend_yield"
               f"&limit={batch}&offset={offset}")
        r = requests.get(url, cookies=cookies, headers=headers, timeout=15)
        if r.status_code != 200:
            break
        results += r.json().get("results", [])
        offset += batch

    return results


def get_value(info, info_index, key):
    try:
        return info[info_index][key]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nordnet Aktie Screener")
        self.resizable(True, True)
        self.exclude_list = load_exclude_list()
        self._running = False
        self._thread = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── top frame: login + filters ──────────────────────────────────
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        # Login section
        login_frame = ttk.LabelFrame(top, text="Login (valgfrit — bedre data med login)", padding=8)
        login_frame.grid(row=0, column=0, padx=(0, 12), pady=4, sticky="nw")

        ttk.Label(login_frame, text="Brugernavn:").grid(row=0, column=0, sticky="w")
        self.username_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.username_var, width=22).grid(row=0, column=1, padx=4)

        ttk.Label(login_frame, text="Adgangskode:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.password_var = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=22).grid(row=1, column=1, padx=4, pady=(4, 0))

        # Filter section
        filter_frame = ttk.LabelFrame(top, text="Filtre", padding=8)
        filter_frame.grid(row=0, column=1, padx=4, pady=4, sticky="nw")

        filters = [
            ("P/E min:",          "pe_min",                    "1"),
            ("P/E max:",          "pe_max",                    "20"),
            ("Direkte Rente min %:", "dividend_yield_min",     "1"),
            ("Direkte Rente max %:", "dividend_yield_max",     "100"),
            ("Belåning min %:",   "instrument_pawn_percentage_min", "65"),
            ("Belåning max %:",   "instrument_pawn_percentage_max", "101"),
        ]
        self.filter_vars = {}
        for i, (label, key, default) in enumerate(filters):
            ttk.Label(filter_frame, text=label).grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=default)
            self.filter_vars[key] = var
            ttk.Entry(filter_frame, textvariable=var, width=8).grid(row=i, column=1, padx=6, pady=1)

        # Country checkboxes
        country_frame = ttk.LabelFrame(top, text="Markeder", padding=8)
        country_frame.grid(row=0, column=2, padx=4, pady=4, sticky="nw")

        self.country_vars = {}
        default_on = {"DDK", "DSE", "DFI", "DUS", "DCA"}
        for i, (name, code) in enumerate(COUNTRIES):
            var = tk.BooleanVar(value=code in default_on)
            self.country_vars[code] = var
            ttk.Checkbutton(country_frame, text=name, variable=var).grid(row=i, column=0, sticky="w")

        # ── button row ───────────────────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=(10, 0, 10, 6))
        btn_frame.pack(fill=tk.X)

        self.run_btn = ttk.Button(btn_frame, text="▶  Kør screening", command=self._start)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = ttk.Button(btn_frame, text="■  Stop", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Klar.")
        ttk.Label(btn_frame, textvariable=self.status_var, foreground="gray").pack(side=tk.LEFT, padx=12)

        # ── results table ────────────────────────────────────────────────
        table_frame = ttk.Frame(self, padding=(10, 0, 10, 4))
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("#", "Firma", "Marked", "P/E", "Direkte Rente %", "Belåning %")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        col_widths = [40, 280, 80, 80, 140, 100]
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=w, anchor=tk.E if col not in ("Firma", "Marked") else tk.W)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # alternating row colours
        self.tree.tag_configure("odd",  background="#f5f5f5")
        self.tree.tag_configure("even", background="#ffffff")

        # ── log area ─────────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self, text="Log", padding=6)
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(log_frame, height=5, state=tk.DISABLED,
                                                 font=("Consolas", 9))
        self.log_box.pack(fill=tk.X)

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def _sort_column(self, col):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]))
        except ValueError:
            data.sort()
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
            self.tree.item(k, tags=("even" if idx % 2 == 0 else "odd",))

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _set_status(self, msg: str):
        self.status_var.set(msg)

    # ------------------------------------------------------------------
    # Run / Stop
    # ------------------------------------------------------------------

    def _start(self):
        if self._running:
            return
        self._running = True
        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

        # clear previous results
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)

        self._thread = threading.Thread(target=self._run_screening, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self._set_status("Stopper…")

    def _finish(self):
        self._running = False
        self.run_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Screening logic (runs in background thread)
    # ------------------------------------------------------------------

    def _run_screening(self):
        try:
            self.after(0, self._set_status, "Forbinder til Nordnet…")
            self.after(0, self._log, "Henter session cookies…")

            # Fetch cookies exactly like the working original script
            r0 = requests.get(
                "https://www.nordnet.dk/markedet",
                headers={"User-Agent": UA},
                timeout=15,
            )
            cookies = {c.name: c.value for c in r0.cookies}
            self.after(0, self._log, f"Cookies modtaget: {list(cookies.keys())}")

            username = self.username_var.get().strip()
            password = self.password_var.get().strip()

            if username and password:
                self.after(0, self._log, f"Logger ind som {username}…")
                session = requests.Session()
                session.cookies.update(cookies)
                ok = login(session, username, password)
                if ok:
                    cookies = {c.name: c.value for c in session.cookies}
                    self.after(0, self._log, "Login lykkedes ✓")
                else:
                    self.after(0, self._log, "Login mislykkedes — fortsætter uden login.")
            else:
                self.after(0, self._log, "Ingen login — henter offentlige data.")

            api_headers = {"client-id": "NEXT"}

            # Read filter values
            def fval(key, default):
                try:
                    return float(self.filter_vars[key].get())
                except ValueError:
                    return default

            pe_min    = fval("pe_min", 1)
            pe_max    = fval("pe_max", 20)
            dy_min    = fval("dividend_yield_min", 1)
            dy_max    = fval("dividend_yield_max", 100)
            bp_min    = fval("instrument_pawn_percentage_min", 65)
            bp_max    = fval("instrument_pawn_percentage_max", 101)

            selected_countries = [(name, code) for name, code in COUNTRIES
                                  if self.country_vars[code].get()]

            if not selected_countries:
                self.after(0, messagebox.showwarning, "Ingen markeder", "Vælg mindst ét marked.")
                self.after(0, self._finish)
                return

            row_count = 0

            for country_name, code in selected_countries:
                if not self._running:
                    break
                self.after(0, self._set_status, f"Henter {country_name}…")
                self.after(0, self._log, f"→ {country_name} ({code})")

                stocks = fetch_stocks(cookies, code, api_headers, lambda m: self.after(0, self._log, m))

                self.after(0, self._log, f"  {len(stocks)} aktier hentet.")

                for info in stocks:
                    if not self._running:
                        break

                    name = get_value(info, "instrument_info", "name")
                    if name is None:
                        continue

                    # Exclude lists
                    try:
                        if name in self.exclude_list["all_stocks"][0]["my_stocks"]:
                            continue
                        if name in self.exclude_list["all_stocks"][1]["exclude_stocks"]:
                            continue
                    except Exception:
                        pass

                    if name and "Fund" in name:
                        continue

                    pe   = get_value(info, "key_ratios_info", "pe")
                    dy   = get_value(info, "key_ratios_info", "dividend_yield")
                    bp   = get_value(info, "instrument_info", "instrument_pawn_percentage")

                    if pe is None or dy is None or bp is None:
                        continue

                    try:
                        pe_f  = float(pe)
                        dy_f  = float(dy)
                        bp_f  = float(bp)
                    except (TypeError, ValueError):
                        continue

                    if not (pe_min < pe_f < pe_max):
                        continue
                    if not (dy_min < dy_f < dy_max):
                        continue
                    if not (bp_min < bp_f < bp_max):
                        continue

                    row_count += 1
                    tag = "even" if row_count % 2 == 0 else "odd"
                    values = (row_count, name, country_name,
                              f"{pe_f:.2f}", f"{dy_f:.2f}", f"{bp_f:.0f}")
                    self.after(0, lambda v=values, t=tag: self.tree.insert("", tk.END, values=v, tags=(t,)))

            msg = f"Færdig — {row_count} aktier fundet." if self._running else "Stoppet."
            self.after(0, self._set_status, msg)
            self.after(0, self._log, msg)

        except Exception as e:
            self.after(0, self._log, f"Fejl: {e}")
            self.after(0, self._set_status, "Fejl — se log.")

        finally:
            self.after(0, self._finish)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()

