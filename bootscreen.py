import tkinter as tk
from tkinter import ttk


class BootScreen:
    def __init__(self, root, finished_callback):
        self.root = root
        self.finished_callback = finished_callback
        self.value = 0

        self.frame = tk.Frame(root, bg="black", cursor="none")
        self.frame.pack(fill="both", expand=True)

        self.logo = tk.Label(
            self.frame,
            text="FALCONDECK",
            fg="#00eaff",
            bg="black",
            font=("DejaVu Sans", 36, "bold"),
            cursor="none",
        )
        self.logo.pack(pady=(120, 20))

        self.status = tk.Label(
            self.frame,
            text="INITIALISING SYSTEMS...",
            fg="white",
            bg="black",
            font=("DejaVu Sans", 14, "bold"),
            cursor="none",
        )
        self.status.pack()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Falcon.Horizontal.TProgressbar",
            troughcolor="#10202c",
            background="#00eaff",
            bordercolor="#10202c",
            lightcolor="#00eaff",
            darkcolor="#00eaff",
        )

        self.progress = ttk.Progressbar(
            self.frame,
            orient="horizontal",
            length=500,
            mode="determinate",
            maximum=100,
            style="Falcon.Horizontal.TProgressbar",
        )
        self.progress.pack(pady=40)

        self.animate()

    def animate(self):
        if self.value <= 100:
            self.progress["value"] = self.value
            self.value += 2
            self.root.after(70, self.animate)
        else:
            self.frame.destroy()
            self.finished_callback()
