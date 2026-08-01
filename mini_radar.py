import math
import tkinter as tk

import config


class MiniRadar(tk.Canvas):
    def __init__(self, parent, range_nm=25):
        super().__init__(
            parent,
            width=245,
            height=135,
            bg="#08131c",
            highlightthickness=1,
            highlightbackground=config.ACCENT,
            cursor="none",
        )

        self.ranges = [10, 25, 50]
        self.range_nm = range_nm if range_nm in self.ranges else 25
        self.aircraft = []
        self.bind("<Configure>", lambda event: self.redraw())
        self.bind("<ButtonRelease-1>", self.change_range)

    def change_range(self, event=None):
        current = self.ranges.index(self.range_nm)
        self.range_nm = self.ranges[
            (current + 1) % len(self.ranges)
        ]
        self.redraw()

    @staticmethod
    def distance_and_bearing(lat1, lon1, lat2, lon2):
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

        distance = radius_nm * 2 * math.atan2(
            math.sqrt(value),
            math.sqrt(1 - value),
        )

        y = math.sin(dl) * math.cos(p2)
        x = (
            math.cos(p1) * math.sin(p2)
            - math.sin(p1) * math.cos(p2) * math.cos(dl)
        )

        bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
        return distance, bearing

    def update_aircraft(self, aircraft):
        self.aircraft = [
            plane
            for plane in aircraft
            if getattr(plane, "has_position", False)
        ]
        self.redraw()

    def redraw(self):
        self.delete("all")

        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())

        cx = width / 2
        cy = height / 2 + 4
        radius = min(width, height) * 0.40

        for fraction in (0.5, 1.0):
            ring = radius * fraction
            self.create_oval(
                cx - ring,
                cy - ring,
                cx + ring,
                cy + ring,
                outline="#21475a",
                width=1,
            )

        self.create_line(
            cx,
            cy - radius,
            cx,
            cy + radius,
            fill="#173747",
        )
        self.create_line(
            cx - radius,
            cy,
            cx + radius,
            cy,
            fill="#173747",
        )

        self.create_text(
            cx,
            cy - radius - 8,
            text="N",
            fill=config.ACCENT,
            font=("DejaVu Sans", 8, "bold"),
        )

        self.create_oval(
            cx - 4,
            cy - 4,
            cx + 4,
            cy + 4,
            fill=config.ACCENT,
            outline="white",
        )

        visible = 0

        for plane in self.aircraft:
            distance, bearing = self.distance_and_bearing(
                config.HOME_LAT,
                config.HOME_LON,
                plane.latitude,
                plane.longitude,
            )

            if distance > self.range_nm:
                continue

            angle = math.radians(bearing - 90)
            screen_radius = radius * (distance / self.range_nm)

            x = cx + math.cos(angle) * screen_radius
            y = cy + math.sin(angle) * screen_radius

            self.create_polygon(
                x,
                y - 4,
                x + 3,
                y + 3,
                x - 3,
                y + 3,
                fill="#00eaff",
                outline="black",
            )

            visible += 1

        self.create_text(
            7,
            height - 7,
            text=f"{visible} AIRCRAFT • {self.range_nm} NM",
            anchor="sw",
            fill="#9aa7b2",
            font=("DejaVu Sans", 7, "bold"),
        )

        self.create_text(
            width - 7,
            height - 7,
            text="TAP TO CHANGE RANGE",
            anchor="se",
            fill="#5f7f91",
            font=("DejaVu Sans", 6, "bold"),
        )
