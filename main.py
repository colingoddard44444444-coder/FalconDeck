import tkinter as tk

import config
from airband import AirbandScreen
from audio import AudioController
from bootscreen import BootScreen
from dashboard import Dashboard
from developer import DeveloperScreen
from flights import FlightsScreen
from homescreen import HomeScreen
from map import MapScreen
from navbar import NavigationBar
from radar import RadarScreen
from settings import SettingsScreen


class FalconDeck(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(config.APP_NAME)
        self.configure(bg=config.BACKGROUND, cursor="none")
        self.fullscreen = True

        self.audio = AudioController()
        self.container = None

        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.leave_fullscreen)
        self.bind("<Control-Shift-q>", lambda event: self.close_app())

        self.protocol("WM_DELETE_WINDOW", self.close_app)

        self.after(100, self.force_fullscreen)
        self.after(800, self.force_fullscreen)

        self.show_boot_screen()

    def show_boot_screen(self):
        BootScreen(
            self,
            finished_callback=self.show_home_screen,
        )

    def show_home_screen(self):
        self.home_screen = HomeScreen(
            self,
            enter_callback=self.build_main_menu,
            start_heartbeat=self.audio.start_heartbeat,
            stop_heartbeat=self.audio.stop_heartbeat,
        )

    def build_main_menu(self):
        self.audio.stop_heartbeat()

        self.container = tk.Frame(
            self,
            bg=config.BACKGROUND,
            cursor="none",
        )
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.dashboard = Dashboard(
            self.container,
            show_radar=self.show_radar,
            show_flights=self.show_flights,
            show_map=self.show_map,
            show_airband=self.show_airband,
            show_settings=self.show_settings,
            show_developer=self.show_developer,
            close_app=self.close_app,
            tune_airband=self.tune_airband,
            play_click=self.audio.play_click,
        )

        self.radar = RadarScreen(
            self.container,
            show_dashboard=self.show_dashboard,
        )

        self.flights = FlightsScreen(
            self.container,
            show_dashboard=self.show_dashboard,
        )

        self.map_screen = MapScreen(
            self.container,
            show_dashboard=self.show_dashboard,
        )

        self.airband = AirbandScreen(
            self.container,
            show_dashboard=self.show_dashboard,
        )

        self.settings = SettingsScreen(
            self.container,
            show_dashboard=self.show_dashboard,
        )

        self.developer = DeveloperScreen(
            self.container,
            show_dashboard=self.show_dashboard,
        )

        for page in (
            self.dashboard,
            self.radar,
            self.flights,
            self.map_screen,
            self.airband,
            self.settings,
            self.developer,
        ):
            page.grid(row=0, column=0, sticky="nsew")
            page.configure(cursor="none")


        self.navbar = NavigationBar(
            self,
            show_home=self.show_dashboard,
            show_radar=self.show_radar,
            show_map=self.show_map,
            show_flights=self.show_flights,
            show_airband=self.show_airband,
            show_settings=self.show_settings,
            show_developer=self.show_developer,
            play_click=self.audio.play_click,
        )
        # Repack both widgets so the navbar always reserves
        # the bottom 52 pixels of the display.
        self.container.pack_forget()

        self.navbar.pack(
            side="bottom",
            fill="x",
        )

        self.container.pack(
            side="top",
            fill="both",
            expand=True,
        )

        self.navbar.lift()
        self.show_dashboard()

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
        self.airband.stop_listening()
        self.airband.start_adsb()
        self.dashboard.tkraise()
        self.dashboard.focus_set()

        if hasattr(self, "navbar"):
            self.navbar.set_active("HOME")

    def show_radar(self):
        self.airband.stop_listening()
        self.airband.start_adsb()
        self.radar.tkraise()
        self.radar.focus_set()

        if hasattr(self, "navbar"):
            self.navbar.set_active("RADAR")

    def show_flights(self):
        self.airband.stop_listening()
        self.airband.start_adsb()
        self.flights.tkraise()
        self.flights.focus_set()

        if hasattr(self, "navbar"):
            self.navbar.set_active("FLIGHTS")

    def show_map(self):
        self.airband.stop_listening()
        self.airband.start_adsb()
        self.map_screen.tkraise()
        self.map_screen.focus_set()

        if hasattr(self, "navbar"):
            self.navbar.set_active("MAP")

    def tune_airband(self, frequency):
        self.show_airband()
        self.airband.set_frequency(frequency)

        # Allow the Airband page to appear before starting.
        self.after(
            300,
            self.airband.start_listening,
        )

    def show_airband(self):
        self.airband.tkraise()
        self.airband.focus_set()

        if hasattr(self, "navbar"):
            self.navbar.set_active("AIRBAND")

    def show_settings(self):
        self.airband.stop_listening()
        self.airband.start_adsb()
        self.settings.tkraise()
        self.settings.focus_set()

        if hasattr(self, "navbar"):
            self.navbar.set_active("SETTINGS")

    def show_developer(self):
        self.airband.stop_listening()
        self.airband.start_adsb()
        self.developer.tkraise()
        self.developer.focus_set()
        self.developer.update_status()

        if hasattr(self, "navbar"):
            self.navbar.set_active("DEV")

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

    def close_app(self):
        self.audio.close()
        self.destroy()


if __name__ == "__main__":
    FalconDeck().mainloop()
