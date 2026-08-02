import tkinter as tk

import config


class NavigationBar(tk.Frame):
    def __init__(
        self,
        parent,
        show_home,
        show_radar,
        show_map,
        show_flights,
        show_airband,
        show_settings,
        show_developer,
        play_click=None,
    ):
        super().__init__(
            parent,
            bg=config.PANEL,
            height=52,
            cursor="none",
        )

        self.pack_propagate(False)
        self.play_click = play_click
        self.buttons = {}

        items = (
            ("HOME", show_home),
            ("RADAR", show_radar),
            ("MAP", show_map),
            ("FLIGHTS", show_flights),
            ("AIRBAND", show_airband),
            ("SETTINGS", show_settings),
            ("DEV", show_developer),
        )

        for name, command in items:
            button = tk.Button(
                self,
                text=name,
                command=lambda action=command: self.run_action(action),
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                activebackground=config.PANEL_LIGHT,
                activeforeground=config.ACCENT,
                relief="flat",
                bd=0,
                highlightthickness=0,
                font=("DejaVu Sans", 9, "bold"),
                cursor="none",
            )
            button.pack(
                side="left",
                fill="both",
                expand=True,
                padx=1,
                pady=4,
            )

            self.buttons[name] = button

    def run_action(self, action):
        if self.play_click:
            self.play_click()

        action()

    def set_active(self, name):
        for button_name, button in self.buttons.items():
            if button_name == name:
                button.configure(
                    bg=config.ACCENT,
                    fg="#000000",
                )
            else:
                button.configure(
                    bg=config.PANEL,
                    fg=config.DIM_TEXT,
                )
