import math
import os
import socket
import tkinter as tk
from datetime import datetime, timezone

import config
from adsb import load_aircraft
from airports import AIRPORTS
from mini_radar import MiniRadar


class Dashboard(tk.Frame):
    def __init__(self, parent, show_radar, show_flights, show_map, show_airband, show_settings, show_developer, close_app, play_click=None):
        super().__init__(parent, bg=config.BACKGROUND, cursor="none")

        self.show_radar = show_radar
        self.show_flights = show_flights
        self.show_map = show_map
        self.show_airband = show_airband
        self.show_settings = show_settings
        self.show_developer = show_developer
        self.close_app = close_app
        self.play_click = play_click
        self.menu_cards = []
        self.selected_aircraft_hex = None
        self.current_target = None
        self.close_target_panel()
        self.current_nearest_airport = None
        self.current_airport_distance = None

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

        self.mini_radar = MiniRadar(
            status_panel,
            range_nm=25,
            on_aircraft_selected=self.show_aircraft_details,
        )
        self.mini_radar.pack(
            fill="x",
            padx=9,
            pady=(0, 3),
        )

        self.open_radar_button = tk.Button(
            status_panel,
            text="OPEN LIVE RADAR",
            command=lambda: self.run_action(self.show_radar),
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            cursor="none",
        )
        self.open_radar_button.pack(
            fill="x",
            padx=9,
            pady=(0, 4),
        )

        self.open_radar_button.bind(
            "<ButtonPress-1>",
            lambda event: self.open_radar_button.configure(
                bg=config.ACCENT,
                fg="#000000",
            ),
        )

        self.open_radar_button.bind(
            "<ButtonRelease-1>",
            lambda event: self.open_radar_button.configure(
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
            ),
        )

        self.open_map_button = tk.Button(
            status_panel,
            text="OPEN MOVING MAP",
            command=lambda: self.run_action(self.show_map),
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            cursor="none",
        )
        self.open_map_button.pack(
            fill="x",
            padx=9,
            pady=(0, 4),
        )

        self.open_map_button.bind(
            "<ButtonPress-1>",
            lambda event: self.open_map_button.configure(
                bg=config.ACCENT,
                fg="#000000",
            ),
        )

        self.open_map_button.bind(
            "<ButtonRelease-1>",
            lambda event: self.open_map_button.configure(
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
            ),
        )

        self.aircraft_status = self.status_row(status_panel, "AIRCRAFT")
        self.nearest_status = self.status_row(
            status_panel,
            "NEAREST AIRCRAFT",
        )
        self.nearest_status.bind(
            "<ButtonRelease-1>",
            self.clear_target,
        )
        self.nearest_status.master.bind(
            "<ButtonRelease-1>",
            self.clear_target,
        )
        self.receiver_status = self.status_row(status_panel, "ADS-B RECEIVER")
        self.network_status = self.status_row(status_panel, "NETWORK")
        self.location_status = self.status_row(status_panel, "LOCATION")
        self.location_status.bind(
            "<ButtonRelease-1>",
            self.open_nearest_airport,
        )
        self.location_status.master.bind(
            "<ButtonRelease-1>",
            self.open_nearest_airport,
        )

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
            "Open RTL-SDR airband controls",
            self.show_airband,
            True,
        )
        self.menu_button(
            menu, 4,
            "SETTINGS",
            "Audio and system controls",
            self.show_settings,
            True,
        )

    def status_row(self, parent, title):
        row = tk.Frame(
            parent,
            bg=config.PANEL_LIGHT,
            height=42,
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
            command=(
                lambda action=command: self.run_action(action)
            ) if enabled else None,
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

        if enabled:
            button.bind(
                "<ButtonPress-1>",
                lambda event, card=frame: card.configure(
                    highlightbackground="#FFFFFF",
                    bg=config.PANEL_LIGHT,
                ),
            )
            button.bind(
                "<ButtonRelease-1>",
                lambda event, card=frame: card.configure(
                    highlightbackground=config.ACCENT,
                    bg=config.PANEL,
                ),
            )

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

    def run_action(self, action):
        if self.play_click:
            self.play_click()

        if action:
            self.after(70, action)

    def open_nearest_airport(self, event=None):
        airport = self.current_nearest_airport
        distance = self.current_airport_distance

        if airport is None:
            return

        bearing = self.bearing_degrees(
            config.HOME_LAT,
            config.HOME_LON,
            airport["lat"],
            airport["lon"],
        )

        window = tk.Toplevel(self)
        window.configure(bg=config.BACKGROUND)
        window.geometry("540x340+130+70")
        window.overrideredirect(True)
        window.attributes("-topmost", True)

        header = tk.Frame(
            window,
            bg=config.PANEL,
            height=54,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=airport["icao"],
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 19, "bold"),
        ).pack(side="left", padx=15, pady=10)

        tk.Button(
            header,
            text="CLOSE",
            command=window.destroy,
            bg=config.DANGER,
            fg="white",
            activebackground="#B71C1C",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            padx=15,
            pady=5,
        ).pack(side="right", padx=10, pady=9)

        body = tk.Frame(
            window,
            bg=config.BACKGROUND,
        )
        body.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(
            body,
            text=airport["name"],
            bg=config.BACKGROUND,
            fg=config.TEXT,
            font=("DejaVu Sans", 17, "bold"),
            wraplength=500,
        ).pack(pady=(2, 12))

        details = (
            ("DISTANCE", f"{distance:.1f} NM"),
            ("BEARING", f"{bearing:.0f}°"),
            ("LATITUDE", f'{airport["lat"]:.5f}'),
            ("LONGITUDE", f'{airport["lon"]:.5f}'),
        )

        cards = tk.Frame(body, bg=config.BACKGROUND)
        cards.pack(fill="both", expand=True)

        for index, (title, value) in enumerate(details):
            card = tk.Frame(
                cards,
                bg=config.PANEL,
                highlightthickness=1,
                highlightbackground=config.DIM_TEXT,
            )
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=5,
                pady=5,
            )

            tk.Label(
                card,
                text=title,
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 8, "bold"),
            ).pack(anchor="w", padx=10, pady=(9, 1))

            tk.Label(
                card,
                text=value,
                bg=config.PANEL,
                fg=config.TEXT,
                font=("DejaVu Sans", 13, "bold"),
            ).pack(anchor="w", padx=10, pady=(0, 9))

        for column in range(2):
            cards.grid_columnconfigure(column, weight=1)

        for row in range(2):
            cards.grid_rowconfigure(row, weight=1)

    def select_target(self, aircraft):
        aircraft_hex = getattr(aircraft, "hex", None)

        if aircraft_hex:
            self.selected_aircraft_hex = aircraft_hex.lower()
            self.current_target = aircraft
            self.update_target_display()

    def clear_target(self, event=None):
        if self.selected_aircraft_hex is None:
            return

        self.selected_aircraft_hex = None
        self.current_target = None
        self.nearest_status.indicator.config(
            fg=config.DIM_TEXT,
        )
        self.update_status()

    def show_aircraft_details(self, aircraft):
        self.select_target(aircraft)
        self.show_target_panel()

    def show_target_panel(self):
        aircraft = self.current_target

        if aircraft is None:
            return

        if hasattr(self, "target_panel"):
            try:
                self.target_panel.destroy()
            except tk.TclError:
                pass

        self.target_panel = tk.Frame(
            self,
            bg=config.BACKGROUND,
            highlightthickness=2,
            highlightbackground=config.ACCENT,
            cursor="none",
        )

        self.target_panel.place(
            relx=0.51,
            rely=0.12,
            relwidth=0.47,
            relheight=0.82,
        )
        self.target_panel.lift()

        header = tk.Frame(
            self.target_panel,
            bg=config.PANEL,
            height=46,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="TARGET AIRCRAFT",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 13, "bold"),
        ).pack(side="left", padx=12, pady=9)

        tk.Button(
            header,
            text="CLOSE",
            command=self.close_target_panel,
            bg=config.DANGER,
            fg="white",
            activebackground="#B71C1C",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 8, "bold"),
            padx=12,
            pady=4,
            cursor="none",
        ).pack(side="right", padx=7, pady=7)

        self.target_identity = tk.Label(
            self.target_panel,
            text="--",
            bg=config.BACKGROUND,
            fg=config.TEXT,
            font=("DejaVu Sans", 17, "bold"),
        )
        self.target_identity.pack(pady=(9, 5))

        grid = tk.Frame(
            self.target_panel,
            bg=config.BACKGROUND,
        )
        grid.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=4,
        )

        self.target_values = {}

        fields = (
            "ALTITUDE",
            "SPEED",
            "HEADING",
            "VERTICAL RATE",
            "DISTANCE",
            "BEARING",
            "SQUAWK",
            "HEX",
        )

        for index, title in enumerate(fields):
            card = tk.Frame(
                grid,
                bg=config.PANEL,
                highlightthickness=1,
                highlightbackground=config.DIM_TEXT,
            )
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="nsew",
                padx=3,
                pady=3,
            )

            tk.Label(
                card,
                text=title,
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 7, "bold"),
            ).pack(anchor="w", padx=8, pady=(5, 0))

            value = tk.Label(
                card,
                text="--",
                bg=config.PANEL,
                fg=config.TEXT,
                font=("DejaVu Sans", 10, "bold"),
            )
            value.pack(anchor="w", padx=8, pady=(0, 5))

            self.target_values[title] = value

        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)

        for row in range(4):
            grid.grid_rowconfigure(row, weight=1)

        actions = tk.Frame(
            self.target_panel,
            bg=config.BACKGROUND,
        )
        actions.pack(fill="x", padx=8, pady=(3, 8))

        tk.Button(
            actions,
            text="MAP",
            command=self.open_target_map,
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            pady=7,
            cursor="none",
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 3),
        )

        tk.Button(
            actions,
            text="AIRBAND",
            command=self.open_target_airband,
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            pady=7,
            cursor="none",
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=3,
        )

        tk.Button(
            actions,
            text="CLEAR",
            command=self.clear_target,
            bg=config.PANEL_LIGHT,
            fg=config.DANGER,
            activebackground=config.DANGER,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            pady=7,
            cursor="none",
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(3, 0),
        )

        self.update_target_panel()

    def update_target_panel(self):
        if not hasattr(self, "target_panel"):
            return

        try:
            if not self.target_panel.winfo_exists():
                return
        except tk.TclError:
            return

        aircraft = self.current_target

        if aircraft is None:
            return

        identity = (
            getattr(aircraft, "callsign", None)
            or getattr(aircraft, "registration", None)
            or getattr(aircraft, "hex", "UNKNOWN").upper()
        )

        latitude = getattr(aircraft, "latitude", None)
        longitude = getattr(aircraft, "longitude", None)

        distance = None
        bearing = None

        if (
            isinstance(latitude, (int, float))
            and isinstance(longitude, (int, float))
        ):
            distance = self.distance_nm(
                config.HOME_LAT,
                config.HOME_LON,
                latitude,
                longitude,
            )

            bearing = self.bearing_degrees(
                config.HOME_LAT,
                config.HOME_LON,
                latitude,
                longitude,
            )

        altitude = getattr(aircraft, "altitude", None)
        speed = getattr(aircraft, "speed", None)
        heading = getattr(aircraft, "heading", None)
        vertical_rate = getattr(aircraft, "vertical_rate", None)

        values = {
            "ALTITUDE": (
                f"{altitude:,.0f} FT"
                if isinstance(altitude, (int, float))
                else "--"
            ),
            "SPEED": (
                f"{speed:.0f} KT"
                if isinstance(speed, (int, float))
                else "--"
            ),
            "HEADING": (
                f"{heading:.0f}°"
                if isinstance(heading, (int, float))
                else "--"
            ),
            "VERTICAL RATE": (
                f"{vertical_rate:+.0f} FT/MIN"
                if isinstance(vertical_rate, (int, float))
                else "--"
            ),
            "DISTANCE": (
                f"{distance:.1f} NM"
                if distance is not None
                else "--"
            ),
            "BEARING": (
                f"{bearing:.0f}°"
                if bearing is not None
                else "--"
            ),
            "SQUAWK": str(
                getattr(aircraft, "squawk", None) or "--"
            ),
            "HEX": str(
                getattr(aircraft, "hex", "--")
            ).upper(),
        }

        self.target_identity.config(text=identity)

        for title, value in values.items():
            if title in self.target_values:
                self.target_values[title].config(text=value)

    def close_target_panel(self):
        if hasattr(self, "target_panel"):
            try:
                self.target_panel.destroy()
            except tk.TclError:
                pass

            del self.target_panel

    def open_target_map(self):
        self.close_target_panel()
        self.run_action(self.show_map)

    def open_target_airband(self):
        self.close_target_panel()
        self.run_action(self.show_airband)

    def update_target_display(self):
        aircraft = self.current_target

        if aircraft is None:
            return

        identity = (
            getattr(aircraft, "callsign", None)
            or getattr(aircraft, "registration", None)
            or getattr(aircraft, "hex", "UNKNOWN").upper()
        )

        altitude = getattr(aircraft, "altitude", None)
        speed = getattr(aircraft, "speed", None)
        heading = getattr(aircraft, "heading", None)
        latitude = getattr(aircraft, "latitude", None)
        longitude = getattr(aircraft, "longitude", None)

        altitude_text = (
            f"{altitude:,.0f} FT"
            if isinstance(altitude, (int, float))
            else "ALT --"
        )

        speed_text = (
            f"{speed:.0f} KT"
            if isinstance(speed, (int, float))
            else "SPD --"
        )

        heading_text = (
            f"{heading:.0f}°"
            if isinstance(heading, (int, float))
            else "--"
        )

        distance_text = "--"
        bearing_text = "--"

        if (
            isinstance(latitude, (int, float))
            and isinstance(longitude, (int, float))
        ):
            distance = self.distance_nm(
                config.HOME_LAT,
                config.HOME_LON,
                latitude,
                longitude,
            )
            bearing = self.bearing_degrees(
                config.HOME_LAT,
                config.HOME_LON,
                latitude,
                longitude,
            )

            distance_text = f"{distance:.1f} NM"
            bearing_text = f"{bearing:.0f}°"

        self.nearest_status.config(
            text=(
                f"TARGET • {identity} • {distance_text}\n"
                f"{altitude_text} • {speed_text} • "
                f"BRG {bearing_text} • HDG {heading_text}"
            ),
            fg=config.TEXT,
        )
        self.nearest_status.indicator.config(
            fg="#ffb000",
        )

        self.update_target_panel()

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

    @staticmethod
    def bearing_degrees(lat1, lon1, lat2, lon2):
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dl = math.radians(lon2 - lon1)

        y = math.sin(dl) * math.cos(p2)
        x = (
            math.cos(p1) * math.sin(p2)
            - math.sin(p1) * math.cos(p2) * math.cos(dl)
        )

        return (math.degrees(math.atan2(y, x)) + 360) % 360

    @staticmethod
    def distance_nm(lat1, lon1, lat2, lon2):
        radius_nm = 3440.065
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)

        value = (
            math.sin(dp / 2) ** 2
            + math.cos(p1)
            * math.cos(p2)
            * math.sin(dl / 2) ** 2
        )

        return radius_nm * 2 * math.atan2(
            math.sqrt(value),
            math.sqrt(1 - value),
        )

    def update_status(self):
        try:
            aircraft = load_aircraft()
        except Exception:
            aircraft = []

        self.mini_radar.update_aircraft(aircraft)

        if self.selected_aircraft_hex is not None:
            refreshed_target = next(
                (
                    plane
                    for plane in aircraft
                    if str(
                        getattr(plane, "hex", "")
                    ).lower() == self.selected_aircraft_hex
                ),
                None,
            )

            if refreshed_target is not None:
                self.current_target = refreshed_target
                self.update_target_display()
            else:
                self.nearest_status.config(
                    text="TARGET • LOST CONTACT\nTAP TO CLEAR",
                    fg=config.DANGER,
                )
                self.nearest_status.indicator.config(
                    fg=config.DANGER,
                )


        positioned_aircraft = [
            plane for plane in aircraft
            if plane.has_position
        ]
        positioned = len(positioned_aircraft)

        nearest = None
        nearest_distance = None

        for plane in positioned_aircraft:
            distance = self.distance_nm(
                config.HOME_LAT,
                config.HOME_LON,
                plane.latitude,
                plane.longitude,
            )

            if nearest_distance is None or distance < nearest_distance:
                nearest = plane
                nearest_distance = distance


        nearest_airport = None
        nearest_airport_distance = None

        for airport in AIRPORTS:
            distance = self.distance_nm(
                config.HOME_LAT,
                config.HOME_LON,
                airport["lat"],
                airport["lon"],
            )

            if (
                nearest_airport_distance is None
                or distance < nearest_airport_distance
            ):
                nearest_airport = airport
                nearest_airport_distance = distance

        self.current_nearest_airport = nearest_airport
        self.current_airport_distance = nearest_airport_distance

        receiver_running = os.path.exists(config.AIRCRAFT_JSON)
        network_online = self.wifi_connected()

        self.aircraft_status.config(
            text=f"{len(aircraft)} RECEIVED / {positioned} POSITIONED"
        )
        self.aircraft_status.indicator.config(
            fg=config.SUCCESS if aircraft else config.DIM_TEXT
        )

        if self.selected_aircraft_hex is not None:
            pass
        elif nearest is not None:
            identity = (
                nearest.callsign
                or nearest.registration
                or nearest.hex.upper()
            )

            altitude = (
                f"{nearest.altitude:,.0f} FT"
                if isinstance(nearest.altitude, (int, float))
                else "ALT --"
            )

            aircraft_bearing = self.bearing_degrees(
                config.HOME_LAT,
                config.HOME_LON,
                nearest.latitude,
                nearest.longitude,
            )

            heading = (
                f"{nearest.heading:.0f}°"
                if isinstance(nearest.heading, (int, float))
                else "--"
            )

            self.nearest_status.config(
                text=(
                    f"{identity} • {nearest_distance:.1f} NM\n"
                    f"{altitude} • BRG {aircraft_bearing:.0f}° • HDG {heading}"
                ),
                fg=config.TEXT,
            )
            self.nearest_status.indicator.config(fg=config.ACCENT)
        else:
            self.nearest_status.config(
                text="NO POSITIONED AIRCRAFT",
                fg=config.DIM_TEXT,
            )
            self.nearest_status.indicator.config(fg=config.DIM_TEXT)

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

        if nearest_airport is not None:
            airport_bearing = self.bearing_degrees(
                config.HOME_LAT,
                config.HOME_LON,
                nearest_airport["lat"],
                nearest_airport["lon"],
            )

            self.location_status.config(
                text=(
                    f'{nearest_airport["icao"]} • '
                    f'{nearest_airport["name"]}\n'
                    f'{nearest_airport_distance:.1f} NM • '
                    f'BRG {airport_bearing:.0f}°'
                ),
                fg=config.TEXT,
            )
            self.location_status.indicator.config(
                fg=config.ACCENT
            )
        else:
            self.location_status.config(
                text="NO AIRPORT DATA",
                fg=config.DIM_TEXT,
            )
            self.location_status.indicator.config(
                fg=config.DIM_TEXT
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
