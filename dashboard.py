import os
import tkinter as tk

import config
from adsb import load_aircraft


class Dashboard(tk.Frame):
    def __init__(self, parent, show_radar, show_flights, show_map, close_app):
        super().__init__(parent, bg=config.BACKGROUND, cursor="none")
        self.show_radar = show_radar
        self.show_flights = show_flights
        self.show_map = show_map
        self.close_app = close_app
        self.build_interface()
        self.update_status()

    def build_interface(self):
        header = tk.Frame(self, bg=config.PANEL, height=54, cursor="none")
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=config.APP_NAME,
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 21, "bold"),
        ).pack(side="left", padx=(16, 8), pady=8)

        tk.Label(
            header,
            text=f"v{config.VERSION}",
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 9, "bold"),
        ).pack(side="left", pady=(15, 0))

        tk.Button(
            header,
            text="EXIT",
            command=self.close_app,
            bg=config.DANGER,
            fg="white",
            activebackground="#B71C1C",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            padx=16,
            pady=5,
            cursor="none",
        ).pack(side="right", padx=12, pady=10)

        body = tk.Frame(self, bg=config.BACKGROUND, cursor="none")
        body.pack(fill="both", expand=True, padx=10, pady=9)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=7)

        status = tk.Frame(body, bg=config.PANEL, cursor="none")
        status.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            status,
            text="SYSTEM STATUS",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 5))

        self.aircraft_status = self.status_row(status, "AIRCRAFT")
        self.receiver_status = self.status_row(status, "ADS-B RECEIVER")
        self.location_status = self.status_row(status, "LOCATION")
        self.system_status = self.status_row(status, "SYSTEM")

        menu = tk.Frame(body, bg=config.BACKGROUND, cursor="none")
        menu.grid(row=0, column=1, sticky="nsew")
        for row in range(5):
            menu.grid_rowconfigure(row, weight=1, uniform="menu")
        menu.grid_columnconfigure(0, weight=1)

        self.menu_button(menu, 0, "LIVE RADAR", "View nearby aircraft", self.show_radar, True)
        self.menu_button(menu, 1, "LIVE FLIGHTS", "Browse received aircraft", self.show_flights, True)
        self.menu_button(menu, 2, "MOVING MAP", "Open the map screen", self.show_map, True)
        self.menu_button(menu, 3, "AIRBAND", "Radio controls coming next", None, False)
        self.menu_button(menu, 4, "SETTINGS", "Display options coming next", None, False)

    def status_row(self, parent, title):
        row = tk.Frame(parent, bg=config.PANEL_LIGHT, height=66, cursor="none")
        row.pack(fill="x", padx=9, pady=3)
        row.pack_propagate(False)

        tk.Label(
            row,
            text=title,
            bg=config.PANEL_LIGHT,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        ).pack(anchor="w", padx=9, pady=(6, 0))

        value = tk.Label(
            row,
            text="CHECKING",
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            font=("DejaVu Sans", 10, "bold"),
            wraplength=250,
            justify="left",
        )
        value.pack(anchor="w", padx=9, pady=(1, 0))
        return value

    def menu_button(self, parent, row, title, subtitle, command, enabled):
        frame = tk.Frame(
            parent,
            bg=config.PANEL,
            highlightthickness=2,
            highlightbackground=config.ACCENT if enabled else config.DIM_TEXT,
            cursor="none",
        )
        frame.grid(row=row, column=0, sticky="nsew", pady=3)

        button = tk.Button(
            frame,
            text=title,
            command=command if enabled else None,
            state="normal" if enabled else "disabled",
            bg=config.PANEL,
            fg=config.TEXT,
            disabledforeground=config.DIM_TEXT,
            activebackground=config.PANEL_LIGHT,
            activeforeground=config.ACCENT,
            relief="flat",
            bd=0,
            anchor="w",
            font=("DejaVu Sans", 12, "bold"),
            padx=12,
            pady=2,
            cursor="none",
        )
        button.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=subtitle,
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8),
            cursor="none",
        ).place(x=14, rely=0.68, anchor="w")

    def update_status(self):
        try:
            aircraft = load_aircraft()
        except Exception:
            aircraft = []

        positioned = sum(1 for plane in aircraft if plane.has_position)
        receiver_running = os.path.exists(config.AIRCRAFT_JSON)

        self.aircraft_status.config(text=f"{len(aircraft)} RECEIVED / {positioned} POSITIONED")
        self.receiver_status.config(
            text="ONLINE" if receiver_running else "OFFLINE",
            fg=config.SUCCESS if receiver_running else config.DANGER,
        )
        self.location_status.config(text="BLETCHLEY, MILTON KEYNES")
        self.system_status.config(text="READY", fg=config.SUCCESS)
        self.after(config.REFRESH_MS, self.update_status)
