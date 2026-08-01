import os
import socket
import tkinter as tk
from datetime import datetime, timezone

import config
from adsb import load_aircraft


class Dashboard(tk.Frame):
    def __init__(self, parent, show_radar, show_flights, show_map, close_app):
        super().__init__(parent, bg=config.BACKGROUND, cursor="none")

        self.show_radar = show_radar
        self.show_flights = show_flights
        self.show_map = show_map
        self.close_app = close_app
        self.menu_cards = []

        self.build_interface()
        self.animate_menu()
        self.update_status()
        self.update_clock()

    def build_interface(self):
        header = tk.Frame(
            self,
            bg=config.PANEL,
            height=62,
            cursor="none",
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title_area = tk.Frame(header, bg=config.PANEL)
        title_area.pack(side="left", padx=(16, 8), pady=6)

        tk.Label(
            title_area,
            text="FALCONDECK MK V",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 19, "bold"),
        ).pack(anchor="w")

        self.header_status = tk.Label(
            title_area,
            text="INITIALISING SYSTEMS",
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        )
        self.header_status.pack(anchor="w")

        self.clock_label = tk.Label(
            header,
            text="--:--:-- UTC",
            bg=config.PANEL,
            fg=config.TEXT,
            font=("DejaVu Sans Mono", 13, "bold"),
        )
        self.clock_label.pack(side="right", padx=(5, 14))

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
            padx=14,
            pady=5,
            cursor="none",
        ).pack(side="right", padx=5, pady=12)

        body = tk.Frame(
            self,
            bg=config.BACKGROUND,
            cursor="none",
        )
        body.pack(fill="both", expand=True, padx=10, pady=9)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=7)

        status_panel = tk.Frame(
            body,
            bg=config.PANEL,
            cursor="none",
        )
        status_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8),
        )

        tk.Label(
            status_panel,
            text="SYSTEM STATUS",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 4))

        self.aircraft_status = self.status_row(status_panel, "AIRCRAFT")
        self.receiver_status = self.status_row(status_panel, "ADS-B RECEIVER")
        self.network_status = self.status_row(status_panel, "NETWORK")
        self.location_status = self.status_row(status_panel, "LOCATION")
        self.system_status = self.status_row(status_panel, "SYSTEM")

        menu = tk.Frame(
            body,
            bg=config.BACKGROUND,
            cursor="none",
        )
        menu.grid(row=0, column=1, sticky="nsew")

        for row in range(5):
            menu.grid_rowconfigure(row, weight=1, uniform="menu")

        menu.grid_columnconfigure(0, weight=1)

        self.menu_button(
            menu, 0,
            "LIVE RADAR",
            "Track nearby aircraft in real time",
            self.show_radar,
            True,
        )
        self.menu_button(
            menu, 1,
            "LIVE FLIGHTS",
            "Browse received aircraft and flight details",
            self.show_flights,
            True,
        )
        self.menu_button(
            menu, 2,
            "MOVING MAP",
            "Open the live aircraft map",
            self.show_map,
            True,
        )
        self.menu_button(
            menu, 3,
            "AIRBAND",
            "Radio controls coming soon",
            None,
            False,
        )
        self.menu_button(
            menu, 4,
            "SETTINGS",
            "System controls coming soon",
            None,
            False,
        )

    def status_row(self, parent, title):
        row = tk.Frame(
            parent,
            bg=config.PANEL_LIGHT,
            height=57,
            cursor="none",
        )
        row.pack(fill="x", padx=9, pady=2)
        row.pack_propagate(False)

        indicator = tk.Label(
            row,
            text="●",
            bg=config.PANEL_LIGHT,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 10, "bold"),
        )
        indicator.pack(side="left", padx=(8, 5))

        text_area = tk.Frame(row, bg=config.PANEL_LIGHT)
        text_area.pack(side="left", fill="both", expand=True)

        tk.Label(
            text_area,
            text=title,
            bg=config.PANEL_LIGHT,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        ).pack(anchor="w", pady=(5, 0))

        value = tk.Label(
            text_area,
            text="CHECKING",
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            font=("DejaVu Sans", 9, "bold"),
            wraplength=225,
            justify="left",
        )
        value.pack(anchor="w")

        value.indicator = indicator
        return value

    def menu_button(self, parent, row, title, subtitle, command, enabled):
        frame = tk.Frame(
            parent,
            bg=config.PANEL,
            highlightthickness=2,
            highlightbackground=(
                config.ACCENT if enabled else config.DIM_TEXT
            ),
            cursor="none",
        )
        frame.grid(
            row=row,
            column=0,
            sticky="nsew",
            pady=3,
        )

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
            padx=14,
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
        ).place(x=16, rely=0.69, anchor="w")

        self.menu_cards.append(frame)
        frame.grid_remove()

    def animate_menu(self):
        for index, card in enumerate(self.menu_cards):
            self.after(
                140 + (index * 135),
                card.grid,
            )

    def update_clock(self):
        now = datetime.now(timezone.utc)
        self.clock_label.config(
            text=now.strftime("%H:%M:%S UTC")
        )
        self.after(1000, self.update_clock)

    def wifi_connected(self):
        wireless_path = "/proc/net/wireless"

        try:
            with open(wireless_path, "r", encoding="utf-8") as wireless:
                lines = wireless.readlines()[2:]

            return any(
                ":" in line and float(line.split()[2].rstrip(".")) > 0
                for line in lines
            )
        except (OSError, ValueError, IndexError):
            return False

    def cpu_temperature(self):
        path = "/sys/class/thermal/thermal_zone0/temp"

        try:
            with open(path, "r", encoding="utf-8") as temperature:
                value = int(temperature.read().strip()) / 1000

            return f"{value:.0f}°C"
        except (OSError, ValueError):
            return "--"

    def update_status(self):
        try:
            aircraft = load_aircraft()
        except Exception:
            aircraft = []

        positioned = sum(
            1 for plane in aircraft
            if plane.has_position
        )

        receiver_running = os.path.exists(config.AIRCRAFT_JSON)
        network_online = self.wifi_connected()

        self.aircraft_status.config(
            text=f"{len(aircraft)} RECEIVED / {positioned} POSITIONED"
        )
        self.aircraft_status.indicator.config(
            fg=config.SUCCESS if aircraft else config.DIM_TEXT
        )

        self.receiver_status.config(
            text="ONLINE" if receiver_running else "OFFLINE",
            fg=config.SUCCESS if receiver_running else config.DANGER,
        )
        self.receiver_status.indicator.config(
            fg=config.SUCCESS if receiver_running else config.DANGER
        )

        self.network_status.config(
            text=(
                f"WI-FI CONNECTED • {socket.gethostname()}"
                if network_online
                else "WI-FI OFFLINE"
            ),
            fg=config.SUCCESS if network_online else config.DANGER,
        )
        self.network_status.indicator.config(
            fg=config.SUCCESS if network_online else config.DANGER
        )

        self.location_status.config(
            text="BLETCHLEY, MILTON KEYNES"
        )
        self.location_status.indicator.config(
            fg=config.ACCENT
        )

        self.system_status.config(
            text=f"READY • CPU {self.cpu_temperature()}",
            fg=config.SUCCESS,
        )
        self.system_status.indicator.config(
            fg=config.SUCCESS
        )

        self.header_status.config(
            text=(
                f"ADS-B {'ONLINE' if receiver_running else 'OFFLINE'}"
                f"  •  {positioned} AIRCRAFT"
                f"  •  WI-FI {'ONLINE' if network_online else 'OFFLINE'}"
            )
        )

        self.after(config.REFRESH_MS, self.update_status)
