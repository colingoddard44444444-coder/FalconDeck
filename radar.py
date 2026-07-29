import math
import tkinter as tk

import config
from adsb import load_aircraft


EARTH_RADIUS_NM = 3440.065


def distance_and_bearing(lat1, lon1, lat2, lon2):
    """Calculate distance in nautical miles and bearing in degrees."""

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    distance = (
        2
        * EARTH_RADIUS_NM
        * math.atan2(
            math.sqrt(value),
            math.sqrt(max(0, 1 - value)),
        )
    )

    y = math.sin(delta_lon) * math.cos(lat2_rad)

    x = (
        math.cos(lat1_rad) * math.sin(lat2_rad)
        - math.sin(lat1_rad)
        * math.cos(lat2_rad)
        * math.cos(delta_lon)
    )

    bearing = (
        math.degrees(math.atan2(y, x)) + 360
    ) % 360

    return distance, bearing


class RadarScreen(tk.Frame):
    def __init__(self, parent, show_dashboard):
        super().__init__(
            parent,
            bg=config.BACKGROUND,
            cursor="none",
        )

        self.show_dashboard = show_dashboard

        self.aircraft = []
        self.targets = []

        self.selected_hex = None
        self.selected_distance = None

        self.sweep_angle = 0
        self.range_nm = config.RADAR_RANGE_NM

        self.build_interface()

        self.after(150, self.refresh_aircraft)
        self.after(100, self.animate_sweep)

    def build_interface(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_radar()
        self.build_details_bar()

    def build_header(self):
        header = tk.Frame(
            self,
            bg=config.PANEL,
            height=52,
            cursor="none",
        )
        header.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        header.grid_propagate(False)

        header.grid_columnconfigure(1, weight=1)

        home_button = tk.Button(
            header,
            text="⌂ HOME",
            command=self.show_dashboard,
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            activebackground=config.ACCENT,
            activeforeground=config.BACKGROUND,
            relief="flat",
            borderwidth=0,
            font=("DejaVu Sans", 11, "bold"),
            padx=14,
            cursor="none",
        )
        home_button.grid(
            row=0,
            column=0,
            padx=8,
            pady=7,
            sticky="ns",
        )

        title = tk.Label(
            header,
            text="LIVE ADS-B RADAR",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 17, "bold"),
            cursor="none",
        )
        title.grid(
            row=0,
            column=1,
            sticky="w",
            padx=8,
        )

        self.count_label = tk.Label(
            header,
            text="0 TARGETS",
            bg=config.PANEL,
            fg=config.TEXT,
            font=("DejaVu Sans", 10, "bold"),
            cursor="none",
        )
        self.count_label.grid(
            row=0,
            column=2,
            padx=(6, 10),
        )

        range_button = tk.Button(
            header,
            text="RANGE",
            command=self.change_range,
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground=config.BACKGROUND,
            relief="flat",
            borderwidth=0,
            font=("DejaVu Sans", 9, "bold"),
            padx=10,
            cursor="none",
        )
        range_button.grid(
            row=0,
            column=3,
            padx=(0, 8),
            pady=7,
            sticky="ns",
        )

    def build_radar(self):
        self.canvas = tk.Canvas(
            self,
            bg="#030A0F",
            highlightthickness=0,
            cursor="none",
        )
        self.canvas.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        self.canvas.bind(
            "<Configure>",
            lambda event: self.draw_radar(),
        )

        self.canvas.bind(
            "<Button-1>",
            self.select_target,
        )

    def build_details_bar(self):
        details = tk.Frame(
            self,
            bg=config.PANEL,
            height=82,
            cursor="none",
        )
        details.grid(
            row=2,
            column=0,
            sticky="ew",
        )
        details.grid_propagate(False)

        for column in range(6):
            details.grid_columnconfigure(
                column,
                weight=1,
                uniform="details",
            )

        self.callsign_value = self.detail_cell(
            details,
            0,
            "CALLSIGN",
        )

        self.altitude_value = self.detail_cell(
            details,
            1,
            "ALTITUDE",
        )

        self.speed_value = self.detail_cell(
            details,
            2,
            "SPEED",
        )

        self.heading_value = self.detail_cell(
            details,
            3,
            "HEADING",
        )

        self.distance_value = self.detail_cell(
            details,
            4,
            "DISTANCE",
        )

        self.hex_value = self.detail_cell(
            details,
            5,
            "HEX",
        )

    def detail_cell(self, parent, column, heading):
        frame = tk.Frame(
            parent,
            bg=config.PANEL_LIGHT,
            cursor="none",
        )
        frame.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=3,
            pady=7,
        )

        tk.Label(
            frame,
            text=heading,
            bg=config.PANEL_LIGHT,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            cursor="none",
        ).pack(
            pady=(6, 0),
        )

        value = tk.Label(
            frame,
            text="---",
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            font=("DejaVu Sans", 10, "bold"),
            cursor="none",
        )
        value.pack(
            pady=(2, 4),
        )

        return value

    def change_range(self):
        ranges = (10, 25, 50, 100)

        try:
            current_index = ranges.index(self.range_nm)
        except ValueError:
            current_index = 1

        self.range_nm = ranges[
            (current_index + 1) % len(ranges)
        ]

        self.draw_radar()

    def refresh_aircraft(self):
        try:
            self.aircraft = [
                aircraft
                for aircraft in load_aircraft()
                if aircraft.has_position
            ]
        except Exception as error:
            print(f"ADS-B refresh error: {error}")
            self.aircraft = []

        visible_count = 0

        for aircraft in self.aircraft:
            distance, unused_bearing = distance_and_bearing(
                config.HOME_LAT,
                config.HOME_LON,
                aircraft.latitude,
                aircraft.longitude,
            )

            if distance <= self.range_nm:
                visible_count += 1

        self.count_label.config(
            text=f"{visible_count} TARGET"
            if visible_count == 1
            else f"{visible_count} TARGETS"
        )

        self.update_selected_aircraft()
        self.draw_radar()

        self.after(
            config.REFRESH_MS,
            self.refresh_aircraft,
        )

    def update_selected_aircraft(self):
        if not self.selected_hex:
            return

        selected = next(
            (
                aircraft
                for aircraft in self.aircraft
                if aircraft.hex == self.selected_hex
            ),
            None,
        )

        if selected is None:
            self.selected_hex = None
            self.selected_distance = None
            self.clear_details()
            return

        distance, unused_bearing = distance_and_bearing(
            config.HOME_LAT,
            config.HOME_LON,
            selected.latitude,
            selected.longitude,
        )

        self.selected_distance = distance
        self.show_details(selected, distance)

    def radar_geometry(self):
        width = max(
            self.canvas.winfo_width(),
            100,
        )

        height = max(
            self.canvas.winfo_height(),
            100,
        )

        centre_x = width / 2
        centre_y = height / 2

        radius = (
            min(width, height) / 2
        ) - 24

        return (
            width,
            height,
            centre_x,
            centre_y,
            radius,
        )

    def draw_radar(self):
        self.canvas.delete("all")
        self.targets = []

        (
            width,
            height,
            centre_x,
            centre_y,
            radius,
        ) = self.radar_geometry()

        self.draw_background_grid(
            centre_x,
            centre_y,
            radius,
        )

        self.draw_aircraft(
            centre_x,
            centre_y,
            radius,
        )

        self.draw_sweep()

    def draw_background_grid(
        self,
        centre_x,
        centre_y,
        radius,
    ):
        ring_colour = "#156075"
        grid_colour = "#0B3440"

        for fraction in (
            0.25,
            0.50,
            0.75,
            1.00,
        ):
            ring_radius = radius * fraction

            self.canvas.create_oval(
                centre_x - ring_radius,
                centre_y - ring_radius,
                centre_x + ring_radius,
                centre_y + ring_radius,
                outline=ring_colour,
                width=1,
                tags="radar",
            )

            distance = int(
                self.range_nm * fraction
            )

            self.canvas.create_text(
                centre_x + 6,
                centre_y - ring_radius + 10,
                text=f"{distance} NM",
                fill=config.DIM_TEXT,
                font=("DejaVu Sans", 8, "bold"),
                anchor="w",
                tags="radar",
            )

        for angle in range(0, 360, 45):
            angle_rad = math.radians(angle - 90)

            end_x = (
                centre_x
                + math.cos(angle_rad) * radius
            )

            end_y = (
                centre_y
                + math.sin(angle_rad) * radius
            )

            self.canvas.create_line(
                centre_x,
                centre_y,
                end_x,
                end_y,
                fill=grid_colour,
                width=1,
                tags="radar",
            )

        for label, angle in (
            ("N", 0),
            ("E", 90),
            ("S", 180),
            ("W", 270),
        ):
            angle_rad = math.radians(angle - 90)

            label_x = (
                centre_x
                + math.cos(angle_rad)
                * (radius + 13)
            )

            label_y = (
                centre_y
                + math.sin(angle_rad)
                * (radius + 13)
            )

            self.canvas.create_text(
                label_x,
                label_y,
                text=label,
                fill=config.ACCENT,
                font=("DejaVu Sans", 9, "bold"),
                tags="radar",
            )

        self.canvas.create_oval(
            centre_x - 5,
            centre_y - 5,
            centre_x + 5,
            centre_y + 5,
            fill=config.ACCENT,
            outline="white",
            width=1,
            tags="radar",
        )

    def draw_aircraft(
        self,
        centre_x,
        centre_y,
        radius,
    ):
        for aircraft in self.aircraft:
            distance, bearing = distance_and_bearing(
                config.HOME_LAT,
                config.HOME_LON,
                aircraft.latitude,
                aircraft.longitude,
            )

            if distance > self.range_nm:
                continue

            scaled_distance = (
                distance / self.range_nm
            ) * radius

            bearing_rad = math.radians(
                bearing - 90
            )

            x = (
                centre_x
                + math.cos(bearing_rad)
                * scaled_distance
            )

            y = (
                centre_y
                + math.sin(bearing_rad)
                * scaled_distance
            )

            selected = (
                aircraft.hex == self.selected_hex
            )

            colour = self.altitude_colour(
                aircraft.altitude
            )

            self.draw_aircraft_symbol(
                x,
                y,
                aircraft.heading,
                colour,
                selected,
            )

            label = (
                aircraft.callsign
                or aircraft.hex.upper()
            )

            altitude_text = ""

            if isinstance(
                aircraft.altitude,
                (int, float),
            ):
                altitude_text = (
                    f"\n{int(aircraft.altitude / 100):03d}"
                )

            self.canvas.create_text(
                x + 11,
                y - 10,
                text=f"{label}{altitude_text}",
                fill=config.TEXT,
                font=("DejaVu Sans", 8, "bold"),
                anchor="w",
            )

            self.targets.append(
                {
                    "aircraft": aircraft,
                    "x": x,
                    "y": y,
                    "distance": distance,
                }
            )

    def draw_aircraft_symbol(
        self,
        x,
        y,
        heading,
        colour,
        selected,
    ):
        if not isinstance(
            heading,
            (int, float),
        ):
            heading = 0

        size = 10 if selected else 8

        points = [
            (0, -size),
            (size * 0.45, size * 0.65),
            (0, size * 0.35),
            (-size * 0.45, size * 0.65),
        ]

        rotated = []

        heading_rad = math.radians(heading)

        for point_x, point_y in points:
            rotated_x = (
                point_x * math.cos(heading_rad)
                - point_y * math.sin(heading_rad)
            )

            rotated_y = (
                point_x * math.sin(heading_rad)
                + point_y * math.cos(heading_rad)
            )

            rotated.extend(
                (
                    x + rotated_x,
                    y + rotated_y,
                )
            )

        self.canvas.create_polygon(
            rotated,
            fill=colour,
            outline="white" if selected else colour,
            width=2 if selected else 1,
        )

        if selected:
            self.canvas.create_oval(
                x - 14,
                y - 14,
                x + 14,
                y + 14,
                outline=config.ACCENT,
                width=2,
            )

    def draw_sweep(self):
        self.canvas.delete("sweep")

        (
            unused_width,
            unused_height,
            centre_x,
            centre_y,
            radius,
        ) = self.radar_geometry()

        angle_rad = math.radians(
            self.sweep_angle - 90
        )

        end_x = (
            centre_x
            + math.cos(angle_rad) * radius
        )

        end_y = (
            centre_y
            + math.sin(angle_rad) * radius
        )

        self.canvas.create_line(
            centre_x,
            centre_y,
            end_x,
            end_y,
            fill=config.ACCENT,
            width=2,
            tags="sweep",
        )

    def animate_sweep(self):
        self.sweep_angle = (
            self.sweep_angle + 3
        ) % 360

        self.draw_sweep()

        self.after(
            75,
            self.animate_sweep,
        )

    def select_target(self, event):
        nearest = None
        nearest_pixels = 28

        for target in self.targets:
            pixel_distance = math.hypot(
                event.x - target["x"],
                event.y - target["y"],
            )

            if pixel_distance < nearest_pixels:
                nearest = target
                nearest_pixels = pixel_distance

        if nearest is None:
            self.selected_hex = None
            self.selected_distance = None
            self.clear_details()
            self.draw_radar()
            return

        aircraft = nearest["aircraft"]

        self.selected_hex = aircraft.hex
        self.selected_distance = nearest["distance"]

        self.show_details(
            aircraft,
            nearest["distance"],
        )

        self.draw_radar()

    def show_details(self, aircraft, distance):
        callsign = (
            aircraft.callsign or "UNKNOWN"
        )

        altitude = (
            f"{aircraft.altitude:,.0f} FT"
            if isinstance(
                aircraft.altitude,
                (int, float),
            )
            else "---"
        )

        speed = (
            f"{aircraft.speed:.0f} KT"
            if isinstance(
                aircraft.speed,
                (int, float),
            )
            else "---"
        )

        heading = (
            f"{aircraft.heading:.0f}°"
            if isinstance(
                aircraft.heading,
                (int, float),
            )
            else "---"
        )

        distance_text = (
            f"{distance:.1f} NM"
        )

        self.callsign_value.config(
            text=callsign,
            fg=config.ACCENT,
        )

        self.altitude_value.config(
            text=altitude,
        )

        self.speed_value.config(
            text=speed,
        )

        self.heading_value.config(
            text=heading,
        )

        self.distance_value.config(
            text=distance_text,
        )

        self.hex_value.config(
            text=aircraft.hex.upper(),
        )

    def clear_details(self):
        for label in (
            self.callsign_value,
            self.altitude_value,
            self.speed_value,
            self.heading_value,
            self.distance_value,
            self.hex_value,
        ):
            label.config(
                text="---",
                fg=config.TEXT,
            )

    @staticmethod
    def altitude_colour(altitude):
        if not isinstance(
            altitude,
            (int, float),
        ):
            return "#FFFFFF"

        if altitude < 5000:
            return "#57FF6A"

        if altitude < 15000:
            return "#00E5FF"

        if altitude < 30000:
            return "#FFD84D"

        return "#FF6FCF"
