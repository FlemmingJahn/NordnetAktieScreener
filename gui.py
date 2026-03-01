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


def save_exclude_list(data: dict):
    with open(EXCLUDE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def login(session: requests.Session, username: str, password: str) -> bool:
    session.get("https://www.nordnet.dk/markedet", headers={"User-Agent": UA}, timeout=15)
    login_url = "https://www.nordnet.dk/api/2/authentication/basic/login"
    payload = {"username": username, "password": password}
    headers = {"User-Agent": UA, "client-id": "NEXT", "Content-Type": "application/json"}
    r = session.post(login_url, json=payload, headers=headers, timeout=15)
    return r.status_code == 200


def fetch_stocks(session: requests.Session, exchange_country: str, headers: dict, log_fn) -> list:
    url = (f"https://www.nordnet.dk/api/2/instrument_search/query/stocklist"
           f"?apply_filters=exchange_country%3{exchange_country}"
           f"&sort_order=desc&sort_attribute=dividend_yield&limit=100&offset=0")
    r = session.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        log_fn(f"  [!] HTTP {r.status_code} for {exchange_country}")
        return []
    data = r.json()
    total = data.get("total_hits", 0)
    results = list(data.get("results", []))
    offset = 100
    while offset < total:
        url = (f"https://www.nordnet.dk/api/2/instrument_search/query/stocklist"
               f"?apply_filters=exchange_country%3{exchange_country}"
               f"&sort_order=desc&sort_attribute=dividend_yield&limit=100&offset={offset}")
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            break
        results += r.json().get("results", [])
        offset += 100
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
        self._session = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Tab 1 – Screening
        screening_tab = ttk.Frame(self.notebook)
        self.notebook.add(screening_tab, text="  Screening  ")
        self._build_screening_tab(screening_tab)

        # Tab 2 – Ekskluderingsliste
        exclude_tab = ttk.Frame(self.notebook)
        self.notebook.add(exclude_tab, text="  Ekskluderingsliste  ")
        self._build_exclude_tab(exclude_tab)

    # ── Tab 1: Screening ───────────────────────────────────────────────

    def _build_screening_tab(self, parent):
        top = ttk.Frame(parent, padding=10)
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
            ("P/E min:",              "pe_min",                         "1"),
            ("P/E max:",              "pe_max",                         "20"),
            ("Direkte Rente min %:",  "dividend_yield_min",             "1"),
            ("Direkte Rente max %:",  "dividend_yield_max",             "100"),
            ("Belåning min %:",       "instrument_pawn_percentage_min", "65"),
            ("Belåning max %:",       "instrument_pawn_percentage_max", "101"),
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

        # Button row
        btn_frame = ttk.Frame(parent, padding=(10, 0, 10, 6))
        btn_frame.pack(fill=tk.X)

        self.run_btn = ttk.Button(btn_frame, text="▶  Kør screening", command=self._start)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = ttk.Button(btn_frame, text="■  Stop", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Klar.")
        ttk.Label(btn_frame, textvariable=self.status_var, foreground="gray").pack(side=tk.LEFT, padx=12)

        # Results table
        table_frame = ttk.Frame(parent, padding=(10, 0, 10, 4))
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

        self.tree.tag_configure("odd",  background="#f5f5f5")
        self.tree.tag_configure("even", background="#ffffff")

        # Right-click context menu to add selected stock to an exclude list
        self._ctx_menu = tk.Menu(self, tearoff=0)
        self._ctx_menu.add_command(label="➕ Tilføj til 'Mine beholdninger'",
                                   command=lambda: self._add_selected_to_exclude("my_stocks"))
        self._ctx_menu.add_command(label="➕ Tilføj til 'Ekskluderede aktier'",
                                   command=lambda: self._add_selected_to_exclude("exclude_stocks"))
        self.tree.bind("<Button-3>", self._show_ctx_menu)

        # Log area
        log_frame = ttk.LabelFrame(parent, text="Log", padding=6)
        log_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(log_frame, height=5, state=tk.DISABLED,
                                                 font=("Consolas", 9))
        self.log_box.pack(fill=tk.X)

    # ── Tab 2: Exclude list editor ─────────────────────────────────────

    def _build_exclude_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # ── Left panel: Mine beholdninger ──
        left = ttk.LabelFrame(parent, text="Mine beholdninger (altid ekskluderet)", padding=8)
        left.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.my_stocks_lb = tk.Listbox(left, selectmode=tk.EXTENDED, font=("Segoe UI", 9))
        vsb_my = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.my_stocks_lb.yview)
        self.my_stocks_lb.configure(yscrollcommand=vsb_my.set)
        self.my_stocks_lb.grid(row=0, column=0, sticky="nsew")
        vsb_my.grid(row=0, column=1, sticky="ns")

        my_btn = ttk.Frame(left)
        my_btn.grid(row=1, column=0, columnspan=2, pady=(6, 0), sticky="ew")
        self.my_entry = ttk.Entry(my_btn)
        self.my_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.my_entry.bind("<Return>", lambda e: self._add_entry(self.my_entry, self.my_stocks_lb))
        ttk.Button(my_btn, text="Tilføj",
                   command=lambda: self._add_entry(self.my_entry, self.my_stocks_lb)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(my_btn, text="Fjern valgte",
                   command=lambda: self._remove_selected(self.my_stocks_lb)).pack(side=tk.LEFT)

        # ── Right panel: Ekskluderede aktier ──
        right = ttk.LabelFrame(parent, text="Ekskluderede aktier", padding=8)
        right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.excl_stocks_lb = tk.Listbox(right, selectmode=tk.EXTENDED, font=("Segoe UI", 9))
        vsb_ex = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.excl_stocks_lb.yview)
        self.excl_stocks_lb.configure(yscrollcommand=vsb_ex.set)
        self.excl_stocks_lb.grid(row=0, column=0, sticky="nsew")
        vsb_ex.grid(row=0, column=1, sticky="ns")

        ex_btn = ttk.Frame(right)
        ex_btn.grid(row=1, column=0, columnspan=2, pady=(6, 0), sticky="ew")
        self.excl_entry = ttk.Entry(ex_btn)
        self.excl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.excl_entry.bind("<Return>", lambda e: self._add_entry(self.excl_entry, self.excl_stocks_lb))
        ttk.Button(ex_btn, text="Tilføj",
                   command=lambda: self._add_entry(self.excl_entry, self.excl_stocks_lb)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(ex_btn, text="Fjern valgte",
                   command=lambda: self._remove_selected(self.excl_stocks_lb)).pack(side=tk.LEFT)

        # ── Save button ──
        save_frame = ttk.Frame(parent, padding=(10, 0, 10, 10))
        save_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Button(save_frame, text="💾  Gem ekskluderingsliste",
                   command=self._save_exclude_list).pack(side=tk.LEFT)
        self.excl_status_var = tk.StringVar()
        ttk.Label(save_frame, textvariable=self.excl_status_var, foreground="gray").pack(side=tk.LEFT, padx=10)

        # Populate listboxes from loaded data
        self._populate_exclude_listboxes()

    # ------------------------------------------------------------------
    # Exclude list helpers
    # ------------------------------------------------------------------

    def _populate_exclude_listboxes(self):
        self.my_stocks_lb.delete(0, tk.END)
        self.excl_stocks_lb.delete(0, tk.END)
        try:
            for name in sorted(self.exclude_list["all_stocks"][0]["my_stocks"]):
                self.my_stocks_lb.insert(tk.END, name)
            for name in sorted(self.exclude_list["all_stocks"][1]["exclude_stocks"]):
                self.excl_stocks_lb.insert(tk.END, name)
        except Exception:
            pass

    def _add_entry(self, entry: ttk.Entry, listbox: tk.Listbox):
        value = entry.get().strip()
        if not value:
            return
        existing = list(listbox.get(0, tk.END))
        if value not in existing:
            listbox.insert(tk.END, value)
            items = sorted(listbox.get(0, tk.END))
            listbox.delete(0, tk.END)
            for item in items:
                listbox.insert(tk.END, item)
        entry.delete(0, tk.END)

    def _remove_selected(self, listbox: tk.Listbox):
        for idx in reversed(listbox.curselection()):
            listbox.delete(idx)

    def _save_exclude_list(self):
        my_stocks    = list(self.my_stocks_lb.get(0, tk.END))
        excl_stocks  = list(self.excl_stocks_lb.get(0, tk.END))
        self.exclude_list = {
            "all_stocks": [
                {"my_stocks": my_stocks},
                {"exclude_stocks": excl_stocks},
            ]
        }
        try:
            save_exclude_list(self.exclude_list)
            self.excl_status_var.set("Gemt ✓")
            self.after(3000, lambda: self.excl_status_var.set(""))
        except Exception as e:
            messagebox.showerror("Fejl", f"Kunne ikke gemme filen:\n{e}")

    def _show_ctx_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _add_selected_to_exclude(self, list_key: str):
        sel = self.tree.selection()
        if not sel:
            return
        name = self.tree.set(sel[0], "Firma")
        if list_key == "my_stocks":
            lb = self.my_stocks_lb
        else:
            lb = self.excl_stocks_lb
        if name not in lb.get(0, tk.END):
            lb.insert(tk.END, name)
            items = sorted(lb.get(0, tk.END))
            lb.delete(0, tk.END)
            for item in items:
                lb.insert(tk.END, item)
        # Switch to exclude tab so user can see it was added
        self.notebook.select(1)
        self._save_exclude_list()

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
        # Reload exclude list from disk (picks up any saves)
        self.exclude_list = load_exclude_list()
        self._populate_exclude_listboxes()

        self._running = True
        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

        for row in self.tree.get_children():
            self.tree.delete(row)
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)

        self._thread = threading.Thread(target=self._run_screening, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        if self._session:
            self._session.close()
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

            self._session = requests.Session()
            self._session.headers.update({"User-Agent": UA})

            r0 = self._session.get("https://www.nordnet.dk/markedet", timeout=15)
            cookies = {c.name: c.value for c in r0.cookies}
            self._session.cookies.update(cookies)
            self.after(0, self._log, f"Cookies modtaget: {list(cookies.keys())}")

            username = self.username_var.get().strip()
            password = self.password_var.get().strip()

            if username and password:
                self.after(0, self._log, f"Logger ind som {username}…")
                ok = login(self._session, username, password)
                if ok:
                    self.after(0, self._log, "Login lykkedes ✓")
                else:
                    self.after(0, self._log, "Login mislykkedes — fortsætter uden login.")
            else:
                self.after(0, self._log, "Ingen login — henter offentlige data.")

            api_headers = {"client-id": "NEXT"}

            def fval(key, default):
                try:
                    return float(self.filter_vars[key].get())
                except ValueError:
                    return default

            pe_min = fval("pe_min", 1)
            pe_max = fval("pe_max", 20)
            dy_min = fval("dividend_yield_min", 1)
            dy_max = fval("dividend_yield_max", 100)
            bp_min = fval("instrument_pawn_percentage_min", 65)
            bp_max = fval("instrument_pawn_percentage_max", 101)

            selected_countries = [(name, code) for name, code in COUNTRIES
                                  if self.country_vars[code].get()]

            if not selected_countries:
                self.after(0, messagebox.showwarning, "Ingen markeder", "Vælg mindst ét marked.")
                self.after(0, self._finish)
                return

            try:
                my_stocks   = set(self.exclude_list["all_stocks"][0]["my_stocks"])
                excl_stocks = set(self.exclude_list["all_stocks"][1]["exclude_stocks"])
            except Exception:
                my_stocks = excl_stocks = set()

            row_count = 0

            for country_name, code in selected_countries:
                if not self._running:
                    break
                self.after(0, self._set_status, f"Henter {country_name}…")
                self.after(0, self._log, f"→ {country_name} ({code})")

                stocks = fetch_stocks(self._session, code, api_headers,
                                      lambda m: self.after(0, self._log, m))
                self.after(0, self._log, f"  {len(stocks)} aktier hentet.")

                for info in stocks:
                    if not self._running:
                        break

                    name = get_value(info, "instrument_info", "name")
                    if name is None:
                        continue
                    if name in my_stocks or name in excl_stocks:
                        continue
                    if "Fund" in name:
                        continue

                    pe = get_value(info, "key_ratios_info", "pe")
                    dy = get_value(info, "key_ratios_info", "dividend_yield")
                    bp = get_value(info, "instrument_info", "instrument_pawn_percentage")

                    if pe is None or dy is None or bp is None:
                        continue

                    try:
                        pe_f = float(pe)
                        dy_f = float(dy)
                        bp_f = float(bp)
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

        except requests.exceptions.ConnectionError:
            # Session was closed by _stop() — treat as a clean stop
            self.after(0, self._set_status, "Stoppet.")
            self.after(0, self._log, "Stoppet.")
        except Exception as e:
            if self._running:
                self.after(0, self._log, f"Fejl: {e}")
                self.after(0, self._set_status, "Fejl — se log.")
            else:
                self.after(0, self._set_status, "Stoppet.")
                self.after(0, self._log, "Stoppet.")
        finally:
            self._session = None
            self.after(0, self._finish)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()

