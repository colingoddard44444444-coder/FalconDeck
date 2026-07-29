import tkinter as tk

import config
from dashboard import Dashboard
from flights import FlightsScreen
from map import MapScreen
from radar import RadarScreen


class FalconDeck(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(config.APP_NAME)
        self.configure(bg=config.BACKGROUND, cursor="none")
        self.fullscreen = True

        self.container = tk.Frame(self, bg=config.BACKGROUND, cursor="none")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.dashboard = Dashboard(
            self.container,
            show_radar=self.show_radar,
            show_flights=self.show_flights,
            show_map=self.show_map,
            close_app=self.destroy,
        )
        self.radar = RadarScreen(self.container, show_dashboard=self.show_dashboard)
        self.flights = FlightsScreen(self.container, show_dashboard=self.show_dashboard)
        self.map_screen = MapScreen(self.container, show_dashboard=self.show_dashboard)

        for page in (self.dashboard, self.radar, self.flights, self.map_screen):
            page.grid(row=0, column=0, sticky="nsew")
            page.configure(cursor="none")

        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.leave_fullscreen)
        self.bind("<Control-Shift-q>", lambda event: self.destroy())

        self.show_dashboard()
        self.after(150, self.force_fullscreen)
        self.after(900, self.force_fullscreen)

    def force_fullscreen(self):
        self.update_idletasks()
        self.overrideredirect(True)
        self.geometry("800x480+0+0")
        try:
            self.attributes("-fullscreen", True)
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.lift()
        self.focus_force()

    def show_dashboard(self):
        self.dashboard.tkraise()
        self.dashboard.focus_set()

    def show_radar(self):
        self.radar.tkraise()
        self.radar.focus_set()

    def show_flights(self):
        self.flights.tkraise()
        self.flights.focus_set()

    def show_map(self):
        self.map_screen.tkraise()
        self.map_screen.focus_set()

    def leave_fullscreen(self, event=None):
        self.fullscreen = False
        try:
            self.attributes("-fullscreen", False)
            self.attributes("-topmost", False)
        except tk.TclError:
            pass
        self.overrideredirect(False)
        self.geometry("800x480+0+0")
        self.configure(cursor="")

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.configure(cursor="none")
            self.force_fullscreen()
        else:
            self.leave_fullscreen()


if __name__ == "__main__":
    FalconDeck().mainloop()
