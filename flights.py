import tkinter as tk

import config
from adsb import load_aircraft


class FlightsScreen(tk.Frame):
    def __init__(self, parent, show_dashboard):
        super().__init__(parent, bg=config.BACKGROUND)

        self.show_dashboard = show_dashboard

        header = tk.Frame(self, bg=config.PANEL, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Button(
            header,
            text="← Dashboard",
            command=self.show_dashboard,
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            relief="flat",
        ).pack(side="left", padx=10, pady=10)

        tk.Label(
            header,
            text="LIVE FLIGHTS",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 18, "bold"),
        ).pack(side="left", padx=20)

        self.listbox = tk.Listbox(
            self,
            bg=config.PANEL,
            fg=config.TEXT,
            font=("DejaVu Sans Mono", 11),
            relief="flat",
        )

        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.update_list()

    def update_list(self):
        self.listbox.delete(0, tk.END)

        aircraft = sorted(
            load_aircraft(),
            key=lambda a: a.callsign or a.hex,
        )

        for plane in aircraft:

            callsign = plane.callsign or "UNKNOWN"
            altitude = plane.altitude or 0
            speed = plane.speed or 0

            self.listbox.insert(
                tk.END,
                f"{callsign:10}  {altitude:>6} ft   {speed:>3} kt",
            )

        self.after(config.REFRESH_MS, self.update_list)
