import shutil
import socket
import subprocess
import tkinter as tk
from pathlib import Path

import config


class SettingsScreen(tk.Frame):
    def __init__(self, parent, show_dashboard):
        super().__init__(
            parent,
            bg=config.BACKGROUND,
            cursor="none",
        )

        self.show_dashboard = show_dashboard
        self.volume_control = self.find_volume_control()
        self.build_interface()
        self.update_system_information()

    def build_interface(self):
        header = tk.Frame(
            self,
            bg=config.PANEL,
            height=54,
            cursor="none",
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="SYSTEM SETTINGS",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 17, "bold"),
        ).pack(side="left", padx=16, pady=10)

        tk.Button(
            header,
            text="HOME",
            command=self.show_dashboard,
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            padx=14,
            pady=5,
            cursor="none",
        ).pack(side="right", padx=10, pady=9)

        body = tk.Frame(
            self,
            bg=config.BACKGROUND,
            cursor="none",
        )
        body.pack(fill="both", expand=True, padx=12, pady=10)

        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        audio_panel = tk.Frame(
            body,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.ACCENT,
        )
        audio_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6),
        )

        tk.Label(
            audio_panel,
            text="AUDIO",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 4))

        self.volume_value = tk.Label(
            audio_panel,
            text="70%",
            bg=config.PANEL,
            fg=config.TEXT,
            font=("DejaVu Sans", 16, "bold"),
        )
        self.volume_value.pack(pady=(15, 2))

        self.volume_slider = tk.Scale(
            audio_panel,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.set_volume,
            showvalue=False,
            resolution=5,
            bg=config.PANEL,
            troughcolor=config.PANEL_LIGHT,
            activebackground=config.ACCENT,
            highlightthickness=0,
            bd=0,
            sliderlength=30,
            cursor="none",
        )
        self.volume_slider.set(70)
        self.volume_slider.pack(
            fill="x",
            padx=18,
            pady=8,
        )

        self.audio_status = tk.Label(
            audio_panel,
            text="CHECKING AUDIO CONTROL",
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            wraplength=300,
        )
        self.audio_status.pack(pady=(6, 14))

        system_panel = tk.Frame(
            body,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.ACCENT,
        )
        system_panel.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 0),
        )

        tk.Label(
            system_panel,
            text="SYSTEM INFORMATION",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 12, "bold"),
        ).pack(anchor="w", padx=12, pady=(12, 5))

        self.hostname_value = self.info_row(
            system_panel,
            "HOSTNAME",
        )
        self.ip_value = self.info_row(
            system_panel,
            "IP ADDRESS",
        )
        self.cpu_value = self.info_row(
            system_panel,
            "CPU TEMPERATURE",
        )
        self.disk_value = self.info_row(
            system_panel,
            "STORAGE",
        )
        self.version_value = self.info_row(
            system_panel,
            "FALCONDECK",
        )

    def info_row(self, parent, title):
        row = tk.Frame(
            parent,
            bg=config.PANEL_LIGHT,
            height=52,
        )
        row.pack(fill="x", padx=9, pady=3)
        row.pack_propagate(False)

        tk.Label(
            row,
            text=title,
            bg=config.PANEL_LIGHT,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 7, "bold"),
        ).pack(anchor="w", padx=9, pady=(5, 0))

        value = tk.Label(
            row,
            text="CHECKING",
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            font=("DejaVu Sans", 9, "bold"),
        )
        value.pack(anchor="w", padx=9)

        return value

    def find_volume_control(self):
        try:
            result = subprocess.run(
                ["amixer", "-D", "default", "scontrols"],
                capture_output=True,
                text=True,
                timeout=3,
            )

            available = result.stdout.lower()

            for control in (
                "Speaker",
                "PCM",
                "Master",
                "Headphone",
                "Digital",
            ):
                if f"'{control.lower()}'" in available:
                    return control

        except (OSError, subprocess.SubprocessError):
            pass

        return None

    def set_volume(self, value):
        try:
            volume = max(0, min(100, int(float(value))))
        except (TypeError, ValueError):
            return

        self.volume_value.config(text=f"{volume}%")

        if not self.volume_control:
            self.audio_status.config(
                text="NO SOFTWARE VOLUME CONTROL FOUND",
                fg=config.DANGER,
            )
            return

        try:
            subprocess.run(
                [
                    "amixer",
                    "-D",
                    "default",
                    "sset",
                    self.volume_control,
                    f"{volume}%",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )

            self.audio_status.config(
                text=f"{self.volume_control.upper()} CONTROL ACTIVE",
                fg=config.SUCCESS,
            )

        except (OSError, subprocess.SubprocessError):
            self.audio_status.config(
                text="VOLUME CONTROL ERROR",
                fg=config.DANGER,
            )

    def cpu_temperature(self):
        try:
            value = Path(
                "/sys/class/thermal/thermal_zone0/temp"
            ).read_text().strip()

            return f"{int(value) / 1000:.1f}°C"

        except (OSError, ValueError):
            return "--"

    def ip_address(self):
        try:
            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
            )
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            sock.close()
            return address
        except OSError:
            return "OFFLINE"

    def storage_information(self):
        try:
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            return f"{free_gb:.1f} GB FREE / {total_gb:.1f} GB"
        except OSError:
            return "--"

    def update_system_information(self):
        self.hostname_value.config(
            text=socket.gethostname(),
        )
        self.ip_value.config(
            text=self.ip_address(),
        )
        self.cpu_value.config(
            text=self.cpu_temperature(),
        )
        self.disk_value.config(
            text=self.storage_information(),
        )
        self.version_value.config(
            text="FALCONDECK OS v2.0",
        )

        self.after(
            5000,
            self.update_system_information,
        )
