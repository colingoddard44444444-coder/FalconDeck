import math
import os
import socket
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path

import config
from adsb import load_aircraft
from aircraft_intelligence import AircraftIntelligence
from airports import AIRPORTS
from event_engine import EventEngine
from mini_radar import MiniRadar


class Dashboard(tk.Frame):
    def __init__(self, parent, show_radar, show_flights, show_map, show_airband, show_settings, show_developer, close_app, tune_airband=None, play_click=None):
        super().__init__(parent, bg=config.BACKGROUND, cursor="none")

        self.show_radar = show_radar
        self.show_flights = show_flights
        self.show_map = show_map
        self.show_airband = show_airband
        self.tune_airband = tune_airband
        self.show_settings = show_settings
        self.show_developer = show_developer
        self.close_app = close_app
        self.play_click = play_click
        self.menu_cards = []
        self.menu_status_labels = {}
        self.activity_log_file = (
            Path(__file__).resolve().parent
            / "logs"
            / "mission_activity.log"
        )

        self.event_engine = EventEngine(
            self.activity_log_file,
            maximum_events=100,
        )
        self.event_engine.subscribe(
            self.receive_event,
        )

        self.activity_events = [
            self.event_engine.format_event(event)
            for event in self.event_engine.recent(20)
        ]
        self.spotlight_aircraft_hex = None
        self.selected_aircraft_hex = None
        self.current_target = None
        self.target_previous_distance = None
        self.target_motion = "CALCULATING"
        self.current_target_airport = None
        self.current_target_airport_distance = None
        self.alerted_emergency_hexes = set()
        self.suggested_radio_service = None
        self.suggested_radio_frequency = None
        self.close_target_panel()
        self.current_nearest_airport = None
        self.current_airport_distance = None

        self.aircraft_intelligence = AircraftIntelligence(
            home_lat=config.HOME_LAT,
            home_lon=config.HOME_LON,
            distance_function=self.distance_nm,
            bearing_function=self.bearing_degrees,
            airport_value_function=self.airport_value,
            nearest_airport_function=self.nearest_airport_to_position,
            airport_frequencies_function=self.airport_frequencies,
        )
        self.current_spotlight_insight = None

        self.activity_visible = False
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

        self.health_strip = tk.Frame(
            header,
            bg=config.PANEL,
            cursor="none",
        )
        self.health_strip.pack(
            side="right",
            padx=(4, 8),
            pady=8,
        )

        self.health_labels = {}

        for name in ("ADS-B", "WI-FI", "TARGET"):
            item = tk.Frame(
                self.health_strip,
                bg=config.PANEL,
            )
            item.pack(side="left", padx=4)

            indicator = tk.Label(
                item,
                text="●",
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 9, "bold"),
            )
            indicator.pack(side="left", padx=(0, 2))

            tk.Label(
                item,
                text=name,
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 7, "bold"),
            ).pack(side="left")

            self.health_labels[name] = indicator

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
        self.menu_panel = menu

        for row in range(5):
            menu.grid_rowconfigure(
                row,
                weight=1,
                uniform="menu",
                minsize=47,
            )

        menu.grid_rowconfigure(
            5,
            weight=0,
            minsize=32,
        )

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

        self.activity_panel = tk.Frame(
            menu,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.DIM_TEXT,
            cursor="none",
        )
        self.activity_panel.grid(
            row=5,
            column=0,
            sticky="nsew",
            pady=(3, 0),
        )

        activity_header = tk.Frame(
            self.activity_panel,
            bg=config.PANEL_LIGHT,
            height=25,
        )
        activity_header.pack(fill="x")
        activity_header.pack_propagate(False)

        self.activity_toggle = tk.Button(
            activity_header,
            text="▼ LOG",
            command=self.toggle_activity_panel,
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            relief="flat",
            bd=0,
            font=("DejaVu Sans",8,"bold"),
            cursor="none",
        )
        self.activity_toggle.pack(side="right", padx=6)

        self.activity_header_label = tk.Label(
            activity_header,
            text="MISSION ACTIVITY",
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            font=("DejaVu Sans", 8, "bold"),
            anchor="w",
        )
        self.activity_header_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=9,
            pady=4,
        )

        self.activity_label = tk.Label(
            self.activity_panel,
            text="SYSTEM INITIALISING",
            bg=config.PANEL,
            fg=config.TEXT,
            font=("DejaVu Sans Mono", 7, "bold"),
            justify="left",
            anchor="nw",
            wraplength=390,
        )
        self.activity_label.pack(
            fill="both",
            expand=True,
            padx=9,
            pady=5,
        )

        if (
            not self.activity_events
            or "FALCONDECK MISSION CONTROL READY"
            not in self.activity_events[0]
        ):
            self.log_activity(
                "FALCONDECK MISSION CONTROL READY"
            )
        else:
            self.activity_label.config(
                text="\n".join(self.activity_events[:4])
            )

        self.update_activity_header()


    def toggle_activity_panel(self):
        self.activity_visible = not self.activity_visible

        if self.activity_visible:
            self.menu_panel.grid_rowconfigure(
                5,
                weight=0,
                minsize=88,
            )
            self.activity_label.pack(
                fill="both",
                expand=True,
                padx=9,
                pady=5,
            )
            self.activity_toggle.config(text="▲ HIDE")
        else:
            self.activity_label.pack_forget()
            self.menu_panel.grid_rowconfigure(
                5,
                weight=0,
                minsize=32,
            )
            self.activity_toggle.config(text="▼ LOG")

    def update_activity_header(self):
        if not hasattr(self, "activity_header_label"):
            return

        recent = self.event_engine.recent(1)

        if not recent:
            text = "MISSION ACTIVITY"
        else:
            message = str(
                recent[0].get("message", "")
            ).strip()

            if len(message) > 42:
                message = message[:39] + "..."

            text = f"MISSION ACTIVITY  •  {message}"

        self.activity_header_label.config(text=text)

    def refresh_activity_feed(self):
        self.activity_events = [
            self.event_engine.format_event(event)
            for event in self.event_engine.recent(20)
        ]

        if hasattr(self, "activity_label"):
            self.activity_label.config(
                text="\n".join(
                    self.activity_events[:4]
                )
            )

        self.update_activity_header()

    def receive_event(self, event):
        self.refresh_activity_feed()

    def log_activity(
        self,
        message,
        category="SYSTEM",
        importance="normal",
        data=None,
    ):
        return self.event_engine.publish(
            message=message,
            category=category,
            importance=importance,
            data=data,
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
            font=("DejaVu Sans", 10, "bold"),
            padx=14,
            pady=2,
            cursor="none",
        )
        button.pack(
            fill="x",
            expand=False,
            pady=(2, 0),
        )

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

        subtitle_label = tk.Label(
            frame,
            text=subtitle,
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 7),
            cursor="none",
            anchor="w",
        )
        subtitle_label.pack(
            fill="x",
            padx=16,
            pady=(0, 2),
        )

        self.menu_status_labels[title] = subtitle_label

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
            new_hex = aircraft_hex.lower()

            if new_hex != self.selected_aircraft_hex:
                self.target_previous_distance = None
                self.target_motion = "CALCULATING"

            self.selected_aircraft_hex = new_hex
            self.current_target = aircraft

            identity = (
                getattr(aircraft, "callsign", None)
                or getattr(aircraft, "registration", None)
                or str(
                    getattr(aircraft, "hex", "UNKNOWN")
                ).upper()
            )

            self.log_activity(
                f"TARGET SELECTED  {identity}"
            )
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
        self.target_identity.pack(pady=(7, 2))

        self.sky_pointer = tk.Label(
            self.target_panel,
            text="LOOK  •  --  •  ELEVATION --",
            bg="#08131c",
            fg="#ffb000",
            font=("DejaVu Sans", 11, "bold"),
            pady=6,
            cursor="none",
        )
        self.sky_pointer.pack(
            fill="x",
            padx=8,
            pady=(1, 2),
        )

        self.target_motion_label = tk.Label(
            self.target_panel,
            text="MOTION  •  CALCULATING",
            bg=config.BACKGROUND,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            cursor="none",
        )
        self.target_motion_label.pack(
            fill="x",
            padx=8,
            pady=(0, 2),
        )

        self.target_airport_label = tk.Label(
            self.target_panel,
            text="NEAREST AIRPORT  •  CALCULATING",
            bg=config.BACKGROUND,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            cursor="none",
        )
        self.target_airport_label.pack(
            fill="x",
            padx=8,
            pady=(0, 2),
        )

        self.target_airport_label.bind(
            "<ButtonRelease-1>",
            self.open_target_airport,
        )

        self.frequency_suggestion_button = tk.Button(
            self.target_panel,
            text="SUGGESTED RADIO  •  CALCULATING",
            command=self.tune_suggested_frequency,
            bg="#10202c",
            fg="#ffb000",
            activebackground="#ffb000",
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 8, "bold"),
            pady=5,
            cursor="none",
            state="disabled",
        )
        self.frequency_suggestion_button.pack(
            fill="x",
            padx=8,
            pady=(0, 2),
        )

        self.flight_phase_label = tk.Label(
            self.target_panel,
            text="FLIGHT PHASE  •  CALCULATING",
            bg=config.BACKGROUND,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            cursor="none",
        )
        self.flight_phase_label.pack(
            fill="x",
            padx=8,
            pady=(0, 3),
        )

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

    @staticmethod
    def compass_direction(bearing):
        directions = (
            "NORTH",
            "NORTH EAST",
            "EAST",
            "SOUTH EAST",
            "SOUTH",
            "SOUTH WEST",
            "WEST",
            "NORTH WEST",
        )

        index = int((bearing + 22.5) // 45) % 8
        return directions[index]

    @staticmethod
    def elevation_angle(altitude_ft, distance_nm):
        if (
            not isinstance(altitude_ft, (int, float))
            or not isinstance(distance_nm, (int, float))
            or distance_nm <= 0
        ):
            return None

        horizontal_distance_ft = distance_nm * 6076.12

        return math.degrees(
            math.atan2(
                max(0, altitude_ft),
                horizontal_distance_ft,
            )
        )

    @staticmethod
    def airport_value(airport, *names):
        for name in names:
            if isinstance(airport, dict) and name in airport:
                return airport[name]

            if hasattr(airport, name):
                return getattr(airport, name)

        return None

    def nearest_airport_to_position(self, latitude, longitude):
        nearest = None
        nearest_distance = None

        for airport in AIRPORTS:
            airport_lat = self.airport_value(
                airport,
                "lat",
                "latitude",
            )
            airport_lon = self.airport_value(
                airport,
                "lon",
                "longitude",
            )

            if not isinstance(airport_lat, (int, float)):
                continue

            if not isinstance(airport_lon, (int, float)):
                continue

            distance = self.distance_nm(
                latitude,
                longitude,
                airport_lat,
                airport_lon,
            )

            if (
                nearest_distance is None
                or distance < nearest_distance
            ):
                nearest = airport
                nearest_distance = distance

        return nearest, nearest_distance

    def suggest_airport_frequency(
        self,
        airport,
        altitude,
        vertical_rate,
    ):
        if airport is None:
            return None, None

        icao = self.airport_value(
            airport,
            "icao",
            "ident",
            "code",
        )

        frequencies = self.airport_frequencies(icao)

        if not frequencies:
            return None, None

        available = {
            str(service).upper(): frequency
            for service, frequency in frequencies
        }

        if not isinstance(altitude, (int, float)):
            preferred = (
                "APPROACH",
                "TOWER",
                "GROUND",
                "ATIS",
            )
        elif altitude <= 1500:
            preferred = (
                "GROUND",
                "TOWER",
                "APPROACH",
                "ATIS",
            )
        elif altitude <= 3500:
            preferred = (
                "TOWER",
                "APPROACH",
                "GROUND",
                "ATIS",
            )
        elif altitude <= 12000:
            # Descending aircraft are more likely to be on approach.
            if (
                isinstance(vertical_rate, (int, float))
                and vertical_rate < -200
            ):
                preferred = (
                    "APPROACH",
                    "TOWER",
                    "ATIS",
                    "GROUND",
                )
            else:
                preferred = (
                    "APPROACH",
                    "TOWER",
                    "GROUND",
                    "ATIS",
                )
        else:
            preferred = (
                "APPROACH",
                "TOWER",
                "ATIS",
                "GROUND",
            )

        for service in preferred:
            if service in available:
                return service, available[service]

        service, frequency = frequencies[0]
        return service, frequency

    def update_frequency_suggestion(
        self,
        airport,
        altitude,
        vertical_rate,
    ):
        (
            service,
            frequency,
        ) = self.suggest_airport_frequency(
            airport,
            altitude,
            vertical_rate,
        )

        self.suggested_radio_service = service
        self.suggested_radio_frequency = frequency

        if not hasattr(
            self,
            "frequency_suggestion_button",
        ):
            return

        if service is None or frequency is None:
            self.frequency_suggestion_button.config(
                text="SUGGESTED RADIO  •  NO FREQUENCY DATA",
                state="disabled",
                fg=config.DIM_TEXT,
            )
            return

        self.frequency_suggestion_button.config(
            text=(
                f"SUGGESTED RADIO  •  "
                f"{service}  {frequency:.3f} MHz  •  TAP TO TUNE"
            ),
            state="normal",
            fg="#ffb000",
        )

    def tune_suggested_frequency(self):
        frequency = self.suggested_radio_frequency

        if not isinstance(frequency, (int, float)):
            return

        service = (
            self.suggested_radio_service
            or "RADIO"
        )

        self.log_activity(
            f"TUNING {service}  {frequency:.3f} MHz"
        )

        self.close_target_panel()

        if self.tune_airband:
            self.tune_airband(frequency)
        else:
            self.run_action(self.show_airband)

    @staticmethod
    def estimate_flight_phase(
        altitude,
        speed,
        vertical_rate,
        airport_distance,
    ):
        altitude_ok = isinstance(
            altitude,
            (int, float),
        )
        speed_ok = isinstance(
            speed,
            (int, float),
        )
        vertical_ok = isinstance(
            vertical_rate,
            (int, float),
        )
        distance_ok = isinstance(
            airport_distance,
            (int, float),
        )

        if speed_ok and speed < 45:
            return "TAXI / GROUND"

        if altitude_ok and altitude < 1500:
            if vertical_ok and vertical_rate > 500:
                return "TAKEOFF / INITIAL CLIMB"

            if (
                distance_ok
                and airport_distance < 4
                and vertical_ok
                and vertical_rate < -250
            ):
                return "FINAL APPROACH"

            if distance_ok and airport_distance < 6:
                return "AIRPORT CIRCUIT"

        if altitude_ok and altitude < 5000:
            if vertical_ok and vertical_rate > 400:
                return "CLIMBING"

            if vertical_ok and vertical_rate < -400:
                if distance_ok and airport_distance < 12:
                    return "APPROACH"

                return "DESCENDING"

        if altitude_ok and altitude < 12000:
            if vertical_ok and vertical_rate > 400:
                return "CLIMBING"

            if vertical_ok and vertical_rate < -400:
                if distance_ok and airport_distance < 20:
                    return "APPROACH"

                return "DESCENDING"

            return "LEVEL FLIGHT"

        if altitude_ok and altitude >= 12000:
            if vertical_ok and vertical_rate > 500:
                return "CLIMBING"

            if vertical_ok and vertical_rate < -500:
                return "DESCENDING"

            return "CRUISE"

        if vertical_ok:
            if vertical_rate > 400:
                return "CLIMBING"

            if vertical_rate < -400:
                return "DESCENDING"

        return "UNKNOWN"

    def update_flight_phase(
        self,
        altitude,
        speed,
        vertical_rate,
        airport_distance,
    ):
        phase = self.estimate_flight_phase(
            altitude,
            speed,
            vertical_rate,
            airport_distance,
        )

        if not hasattr(self, "flight_phase_label"):
            return

        colours = {
            "TAXI / GROUND": "#ffb000",
            "TAKEOFF / INITIAL CLIMB": config.SUCCESS,
            "CLIMBING": config.SUCCESS,
            "CRUISE": config.ACCENT,
            "LEVEL FLIGHT": config.ACCENT,
            "DESCENDING": "#ffb000",
            "APPROACH": "#ffb000",
            "FINAL APPROACH": config.DANGER,
            "AIRPORT CIRCUIT": "#ffb000",
            "UNKNOWN": config.DIM_TEXT,
        }

        self.flight_phase_label.config(
            text=f"FLIGHT PHASE  •  {phase}",
            fg=colours.get(
                phase,
                config.DIM_TEXT,
            ),
        )

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

            (
                nearest_airport,
                nearest_airport_distance,
            ) = self.nearest_airport_to_position(
                latitude,
                longitude,
            )

            self.current_target_airport = nearest_airport
            self.current_target_airport_distance = (
                nearest_airport_distance
            )

        if distance is not None:
            if self.target_previous_distance is None:
                self.target_motion = "CALCULATING"
            else:
                difference = (
                    distance - self.target_previous_distance
                )

                if difference < -0.08:
                    self.target_motion = "APPROACHING"
                elif difference > 0.08:
                    self.target_motion = "MOVING AWAY"
                else:
                    self.target_motion = "STEADY"

            self.target_previous_distance = distance

        altitude = getattr(aircraft, "altitude", None)

        direction = (
            self.compass_direction(bearing)
            if bearing is not None
            else "--"
        )

        elevation = self.elevation_angle(
            altitude,
            distance,
        )

        elevation_text = (
            f"{elevation:.0f}°"
            if elevation is not None
            else "--"
        )

        if hasattr(self, "sky_pointer"):
            self.sky_pointer.config(
                text=(
                    f"LOOK  •  {direction}  •  "
                    f"ELEVATION {elevation_text}"
                )
            )

        if hasattr(self, "target_airport_label"):
            if nearest_airport is not None:
                icao = self.airport_value(
                    nearest_airport,
                    "icao",
                    "ident",
                    "code",
                ) or "----"

                name = self.airport_value(
                    nearest_airport,
                    "name",
                    "airport",
                    "title",
                ) or "UNKNOWN AIRPORT"

                self.target_airport_label.config(
                    text=(
                        f"NEAREST AIRPORT  •  {icao}  "
                        f"{name}  •  "
                        f"{nearest_airport_distance:.1f} NM"
                    ),
                    fg=config.ACCENT,
                )
            else:
                self.target_airport_label.config(
                    text="NEAREST AIRPORT  •  NO DATA",
                    fg=config.DIM_TEXT,
                )

        if hasattr(self, "target_motion_label"):
            motion_colours = {
                "APPROACHING": config.SUCCESS,
                "MOVING AWAY": "#ffb000",
                "STEADY": config.ACCENT,
                "CALCULATING": config.DIM_TEXT,
            }

            self.target_motion_label.config(
                text=f"MOTION  •  {self.target_motion}",
                fg=motion_colours.get(
                    self.target_motion,
                    config.DIM_TEXT,
                ),
            )
        speed = getattr(aircraft, "speed", None)
        heading = getattr(aircraft, "heading", None)
        vertical_rate = getattr(aircraft, "vertical_rate", None)

        self.update_frequency_suggestion(
            nearest_airport,
            altitude,
            vertical_rate,
        )

        self.update_flight_phase(
            altitude,
            speed,
            vertical_rate,
            nearest_airport_distance,
        )

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

    @staticmethod
    def airport_frequencies(icao):
        frequencies = {
            "EGGW": (
                ("TOWER", 129.550),
                ("APPROACH", 129.025),
                ("GROUND", 121.805),
                ("ATIS", 120.575),
            ),
            "EGLL": (
                ("TOWER", 118.500),
                ("APPROACH", 119.725),
            ),
            "EGKK": (
                ("TOWER", 124.225),
                ("APPROACH", 126.825),
            ),
            "EGSS": (
                ("TOWER", 123.800),
                ("APPROACH", 120.625),
            ),
        }

        return frequencies.get(str(icao).upper(), ())

    def tune_airport_frequency(self, window, frequency):
        try:
            window.destroy()
        except tk.TclError:
            pass

        self.close_target_panel()

        if self.tune_airband:
            self.tune_airband(frequency)
        else:
            self.run_action(self.show_airband)

    def open_target_airport(self, event=None):
        airport = self.current_target_airport
        distance = self.current_target_airport_distance

        if airport is None:
            return

        icao = self.airport_value(
            airport,
            "icao",
            "ident",
            "code",
        ) or "----"

        name = self.airport_value(
            airport,
            "name",
            "airport",
            "title",
        ) or "UNKNOWN AIRPORT"

        latitude = self.airport_value(
            airport,
            "lat",
            "latitude",
        )

        longitude = self.airport_value(
            airport,
            "lon",
            "longitude",
        )

        window = tk.Toplevel(self)
        window.configure(bg=config.BACKGROUND)
        window.geometry("560x330+120+70")
        window.overrideredirect(True)
        window.attributes("-topmost", True)

        header = tk.Frame(
            window,
            bg=config.PANEL,
            height=52,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"AIRPORT  •  {icao}",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 16, "bold"),
        ).pack(side="left", padx=14, pady=10)

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
            padx=14,
            pady=5,
            cursor="none",
        ).pack(side="right", padx=9, pady=8)

        body = tk.Frame(
            window,
            bg=config.BACKGROUND,
        )
        body.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=10,
        )

        tk.Label(
            body,
            text=name,
            bg=config.BACKGROUND,
            fg=config.TEXT,
            font=("DejaVu Sans", 17, "bold"),
            wraplength=520,
        ).pack(pady=(4, 12))

        details = (
            (
                "DISTANCE FROM AIRCRAFT",
                f"{distance:.1f} NM"
                if isinstance(distance, (int, float))
                else "--",
            ),
            (
                "ICAO",
                str(icao),
            ),
            (
                "LATITUDE",
                f"{latitude:.5f}"
                if isinstance(latitude, (int, float))
                else "--",
            ),
            (
                "LONGITUDE",
                f"{longitude:.5f}"
                if isinstance(longitude, (int, float))
                else "--",
            ),
        )

        cards = tk.Frame(
            body,
            bg=config.BACKGROUND,
        )
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
                padx=4,
                pady=4,
            )

            tk.Label(
                card,
                text=title,
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 7, "bold"),
            ).pack(anchor="w", padx=9, pady=(7, 0))

            tk.Label(
                card,
                text=value,
                bg=config.PANEL,
                fg=config.TEXT,
                font=("DejaVu Sans", 11, "bold"),
            ).pack(anchor="w", padx=9, pady=(1, 7))

        for column in range(2):
            cards.grid_columnconfigure(column, weight=1)

        for row in range(2):
            cards.grid_rowconfigure(row, weight=1)

        frequency_list = self.airport_frequencies(icao)

        if frequency_list:
            frequency_panel = tk.Frame(
                body,
                bg=config.BACKGROUND,
            )
            frequency_panel.pack(fill="x", pady=(8, 0))

            for index, (service, frequency) in enumerate(
                frequency_list
            ):
                button = tk.Button(
                    frequency_panel,
                    text=f"{service}\n{frequency:.3f}",
                    command=lambda value=frequency: (
                        self.tune_airport_frequency(
                            window,
                            value,
                        )
                    ),
                    bg=config.PANEL_LIGHT,
                    fg=config.ACCENT,
                    activebackground=config.ACCENT,
                    activeforeground="#000000",
                    relief="flat",
                    bd=0,
                    font=("DejaVu Sans", 8, "bold"),
                    pady=6,
                    cursor="none",
                )
                button.grid(
                    row=0,
                    column=index,
                    sticky="nsew",
                    padx=2,
                )
                frequency_panel.grid_columnconfigure(
                    index,
                    weight=1,
                )
        else:
            tk.Button(
                body,
                text="OPEN AIRBAND",
                command=lambda: self.open_airport_airband(
                    window
                ),
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
                activebackground=config.ACCENT,
                activeforeground="#000000",
                relief="flat",
                bd=0,
                font=("DejaVu Sans", 10, "bold"),
                pady=8,
                cursor="none",
            ).pack(fill="x", pady=(8, 0))

    def open_airport_airband(self, window):
        try:
            window.destroy()
        except tk.TclError:
            pass

        self.close_target_panel()
        self.run_action(self.show_airband)

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

    @staticmethod
    def emergency_description(squawk):
        descriptions = {
            "7500": "UNLAWFUL INTERFERENCE",
            "7600": "RADIO COMMUNICATION FAILURE",
            "7700": "GENERAL EMERGENCY",
        }
        return descriptions.get(str(squawk), "EMERGENCY")

    def track_emergency_aircraft(self, window, aircraft):
        try:
            window.destroy()
        except tk.TclError:
            pass

        self.show_aircraft_details(aircraft)

    def show_emergency_alert(self, aircraft):
        squawk = str(
            getattr(aircraft, "squawk", "")
        ).strip()

        identity = (
            getattr(aircraft, "callsign", None)
            or getattr(aircraft, "registration", None)
            or str(
                getattr(aircraft, "hex", "UNKNOWN")
            ).upper()
        )

        description = self.emergency_description(squawk)

        self.log_activity(
            f"ALERT  SQUAWK {squawk}  {identity}"
        )

        window = tk.Toplevel(self)
        window.configure(bg="#240506")
        window.geometry("650x190+75+100")
        window.overrideredirect(True)
        window.attributes("-topmost", True)

        header = tk.Frame(
            window,
            bg=config.DANGER,
            height=48,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"EMERGENCY SQUAWK {squawk}",
            bg=config.DANGER,
            fg="white",
            font=("DejaVu Sans", 16, "bold"),
        ).pack(side="left", padx=14, pady=9)

        tk.Button(
            header,
            text="CLOSE",
            command=window.destroy,
            bg="#7a1014",
            fg="white",
            activebackground="#a5151b",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            padx=14,
            pady=5,
            cursor="none",
        ).pack(side="right", padx=8, pady=7)

        tk.Label(
            window,
            text=f"{identity}  •  {description}",
            bg="#240506",
            fg="white",
            font=("DejaVu Sans", 14, "bold"),
        ).pack(pady=(18, 5))

        altitude = getattr(aircraft, "altitude", None)

        altitude_text = (
            f"{altitude:,.0f} FT"
            if isinstance(altitude, (int, float))
            else "ALTITUDE UNKNOWN"
        )

        tk.Label(
            window,
            text=altitude_text,
            bg="#240506",
            fg="#ffb0b0",
            font=("DejaVu Sans", 10, "bold"),
        ).pack(pady=(0, 12))

        tk.Button(
            window,
            text="TRACK AIRCRAFT",
            command=lambda: self.track_emergency_aircraft(
                window,
                aircraft,
            ),
            bg=config.DANGER,
            fg="white",
            activebackground="white",
            activeforeground=config.DANGER,
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 11, "bold"),
            padx=35,
            pady=8,
            cursor="none",
        ).pack()

        # Close automatically after 15 seconds.
        window.after(
            15000,
            lambda: (
                window.destroy()
                if window.winfo_exists()
                else None
            ),
        )

    def check_emergency_squawks(self, aircraft):
        current_emergencies = set()

        for plane in aircraft:
            squawk = str(
                getattr(plane, "squawk", "")
            ).strip()

            if squawk not in ("7500", "7600", "7700"):
                continue

            aircraft_hex = str(
                getattr(plane, "hex", "")
            ).lower()

            if not aircraft_hex:
                continue

            current_emergencies.add(aircraft_hex)

            if aircraft_hex not in self.alerted_emergency_hexes:
                self.alerted_emergency_hexes.add(
                    aircraft_hex
                )
                self.show_emergency_alert(plane)

        # Allow a new alert if the aircraft disappears and returns.
        self.alerted_emergency_hexes.intersection_update(
            current_emergencies
        )

    @staticmethod
    def aircraft_identity(aircraft):
        return (
            getattr(aircraft, "callsign", None)
            or getattr(aircraft, "registration", None)
            or str(
                getattr(aircraft, "hex", "UNKNOWN")
            ).upper()
        )

    def choose_spotlight_aircraft(
        self,
        aircraft,
        positioned_aircraft,
        nearest,
    ):
        # Highest priority: emergency squawks.
        for plane in aircraft:
            squawk = str(
                getattr(plane, "squawk", "")
            ).strip()

            if squawk in ("7500", "7600", "7700"):
                return plane, f"EMERGENCY SQUAWK {squawk}"

        # Next: low aircraft, prioritising the closest.
        low_aircraft = []

        for plane in positioned_aircraft:
            altitude = getattr(plane, "altitude", None)

            if (
                isinstance(altitude, (int, float))
                and altitude <= 2000
            ):
                distance = self.distance_nm(
                    config.HOME_LAT,
                    config.HOME_LON,
                    plane.latitude,
                    plane.longitude,
                )
                low_aircraft.append((distance, plane))

        if low_aircraft:
            low_aircraft.sort(key=lambda item: item[0])
            return low_aircraft[0][1], "LOW ALTITUDE"

        if nearest is not None:
            return nearest, "NEAREST AIRCRAFT"

        return None, None

    def update_aircraft_spotlight(
        self,
        aircraft,
        positioned_aircraft,
        nearest,
    ):
        spotlight, reason = self.choose_spotlight_aircraft(
            aircraft,
            positioned_aircraft,
            nearest,
        )

        if spotlight is None:
            self.spotlight_aircraft_hex = None
            return

        aircraft_hex = str(
            getattr(spotlight, "hex", "")
        ).lower()

        if not aircraft_hex:
            return

        if aircraft_hex == self.spotlight_aircraft_hex:
            return

        self.spotlight_aircraft_hex = aircraft_hex

        identity = self.aircraft_identity(spotlight)
        altitude = getattr(spotlight, "altitude", None)

        altitude_text = (
            f"{altitude:,.0f} FT"
            if isinstance(altitude, (int, float))
            else "ALT --"
        )

        self.log_activity(
            f"SPOTLIGHT  {identity}  {altitude_text}  {reason}"
        )

    def update_health_strip(
        self,
        receiver_running,
        network_online,
    ):
        if not hasattr(self, "health_labels"):
            return

        adsb_colour = (
            config.SUCCESS
            if receiver_running
            else config.DANGER
        )

        wifi_colour = (
            config.SUCCESS
            if network_online
            else config.DANGER
        )

        target_colour = (
            config.SUCCESS
            if self.current_target is not None
            else "#ffb000"
        )

        self.health_labels["ADS-B"].config(
            fg=adsb_colour,
        )
        self.health_labels["WI-FI"].config(
            fg=wifi_colour,
        )
        self.health_labels["TARGET"].config(
            fg=target_colour,
        )

    def update_live_menu_cards(
        self,
        aircraft,
        positioned,
        nearest,
        nearest_distance,
        receiver_running,
        network_online,
    ):
        radar_text = (
            f"{len(aircraft)} aircraft • "
            f"{positioned} positioned"
        )

        if nearest is not None:
            nearest_identity = (
                getattr(nearest, "callsign", None)
                or getattr(nearest, "registration", None)
                or str(
                    getattr(nearest, "hex", "UNKNOWN")
                ).upper()
            )

            nearest_text = (
                f"Nearest {nearest_identity} • "
                f"{nearest_distance:.1f} NM"
            )
        else:
            nearest_text = "No positioned aircraft"

        if self.current_target is not None:
            target_identity = (
                getattr(self.current_target, "callsign", None)
                or getattr(
                    self.current_target,
                    "registration",
                    None,
                )
                or str(
                    getattr(
                        self.current_target,
                        "hex",
                        "UNKNOWN",
                    )
                ).upper()
            )
            map_text = f"Tracking {target_identity}"
        else:
            map_text = "Tap an aircraft to begin tracking"

        airband_text = (
            "One-touch airport and suggested tuning"
        )

        adsb_text = (
            "ADS-B online"
            if receiver_running
            else "ADS-B offline"
        )

        wifi_text = (
            "Wi-Fi online"
            if network_online
            else "Wi-Fi offline"
        )

        status_values = {
            "LIVE RADAR": radar_text,
            "LIVE FLIGHTS": nearest_text,
            "MOVING MAP": map_text,
            "AIRBAND": airband_text,
            "SETTINGS": f"{adsb_text} • {wifi_text}",
        }

        for title, value in status_values.items():
            label = self.menu_status_labels.get(title)

            if label is not None:
                label.config(text=value)

    def update_status(self):
        try:
            aircraft = load_aircraft()
        except Exception:
            aircraft = []

        self.mini_radar.update_aircraft(aircraft)
        self.check_emergency_squawks(aircraft)

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

        self.update_aircraft_spotlight(
            aircraft,
            positioned_aircraft,
            nearest,
        )

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

        # Treat ADS-B as active whenever fresh aircraft data is
        # successfully available. This keeps the health indicator
        # consistent with the radar and aircraft counters.
        receiver_running = (
            bool(aircraft)
            or os.path.exists(config.AIRCRAFT_JSON)
        )
        network_online = self.wifi_connected()

        self.update_live_menu_cards(
            aircraft,
            positioned,
            nearest,
            nearest_distance,
            receiver_running,
            network_online,
        )

        self.update_health_strip(
            receiver_running,
            network_online,
        )

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
