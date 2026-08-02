import shutil
import subprocess
import tkinter as tk
from pathlib import Path

import config


class DeveloperScreen(tk.Frame):
    def __init__(self, parent, show_dashboard):
        super().__init__(
            parent,
            bg=config.BACKGROUND,
            cursor="none",
        )

        self.show_dashboard = show_dashboard
        self.project_dir = Path(__file__).resolve().parent

        self.build_interface()
        self.update_status()

    def build_interface(self):
        header = tk.Frame(
            self,
            bg=config.PANEL,
            height=52,
            cursor="none",
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="DEVELOPER MODE",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 17, "bold"),
        ).pack(side="left", padx=14, pady=10)

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
        body.pack(fill="both", expand=True, padx=10, pady=8)

        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        status_panel = tk.Frame(
            body,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.ACCENT,
        )
        status_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 5),
        )

        tk.Label(
            status_panel,
            text="SYSTEM STATUS",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 11, "bold"),
        ).pack(anchor="w", padx=10, pady=(9, 4))

        self.branch_value = self.status_row(
            status_panel,
            "GIT BRANCH",
        )
        self.commit_value = self.status_row(
            status_panel,
            "GIT COMMIT",
        )
        self.changes_value = self.status_row(
            status_panel,
            "WORKING TREE",
        )
        self.adsb_value = self.status_row(
            status_panel,
            "ADS-B SERVICE",
        )
        self.cpu_value = self.status_row(
            status_panel,
            "CPU TEMPERATURE",
        )
        self.memory_value = self.status_row(
            status_panel,
            "MEMORY",
        )
        self.storage_value = self.status_row(
            status_panel,
            "STORAGE",
        )

        controls = tk.Frame(
            body,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.ACCENT,
        )
        controls.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(5, 0),
        )

        tk.Label(
            controls,
            text="MAINTENANCE",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 11, "bold"),
        ).pack(anchor="w", padx=10, pady=(9, 6))

        self.action_button(
            controls,
            "REFRESH STATUS",
            self.update_status,
        )

        self.action_button(
            controls,
            "RESTART ADS-B",
            self.restart_adsb,
        )

        self.action_button(
            controls,
            "GIT FETCH",
            self.git_fetch,
        )

        self.action_button(
            controls,
            "VIEW RECENT LOG",
            self.show_recent_log,
        )

        self.message = tk.Label(
            controls,
            text="DEVELOPER TOOLS READY",
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
            wraplength=340,
            justify="center",
        )
        self.message.pack(
            fill="x",
            padx=12,
            pady=12,
        )

    def status_row(self, parent, title):
        row = tk.Frame(
            parent,
            bg=config.PANEL_LIGHT,
            height=43,
        )
        row.pack(fill="x", padx=8, pady=2)
        row.pack_propagate(False)

        tk.Label(
            row,
            text=title,
            bg=config.PANEL_LIGHT,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 7, "bold"),
        ).pack(anchor="w", padx=8, pady=(4, 0))

        value = tk.Label(
            row,
            text="CHECKING",
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            font=("DejaVu Sans", 9, "bold"),
        )
        value.pack(anchor="w", padx=8)

        return value

    def action_button(self, parent, title, command):
        button = tk.Button(
            parent,
            text=title,
            command=command,
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 10, "bold"),
            pady=10,
            cursor="none",
        )
        button.pack(
            fill="x",
            padx=10,
            pady=4,
        )

    def command_output(self, command):
        try:
            result = subprocess.run(
                command,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=15,
            )

            return (
                result.returncode,
                result.stdout.strip(),
                result.stderr.strip(),
            )

        except (OSError, subprocess.SubprocessError) as error:
            return 1, "", str(error)

    def git_branch(self):
        code, output, _ = self.command_output(
            ["git", "branch", "--show-current"]
        )
        return output if code == 0 and output else "--"

    def git_commit(self):
        code, output, _ = self.command_output(
            ["git", "rev-parse", "--short", "HEAD"]
        )
        return output if code == 0 and output else "--"

    def git_changes(self):
        code, output, _ = self.command_output(
            ["git", "status", "--porcelain"]
        )

        if code != 0:
            return "UNKNOWN", config.DANGER

        if output:
            count = len(output.splitlines())
            return f"{count} LOCAL CHANGE(S)", "#ffb000"

        return "CLEAN", config.SUCCESS

    def adsb_status(self):
        code, output, _ = self.command_output(
            [
                "systemctl",
                "is-active",
                "dump1090-mutability.service",
            ]
        )

        active = code == 0 and output == "active"
        return (
            "RUNNING" if active else "STOPPED",
            config.SUCCESS if active else config.DANGER,
        )

    def cpu_temperature(self):
        try:
            value = Path(
                "/sys/class/thermal/thermal_zone0/temp"
            ).read_text().strip()

            return f"{int(value) / 1000:.1f}°C"

        except (OSError, ValueError):
            return "--"

    def memory_usage(self):
        try:
            lines = Path("/proc/meminfo").read_text().splitlines()
            values = {}

            for line in lines:
                key, value = line.split(":", 1)
                values[key] = int(value.strip().split()[0])

            total = values["MemTotal"]
            available = values["MemAvailable"]
            used_percent = ((total - available) / total) * 100

            return f"{used_percent:.0f}% USED"

        except (OSError, KeyError, ValueError):
            return "--"

    def storage_usage(self):
        try:
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024 ** 3)
            return f"{free_gb:.1f} GB FREE"
        except OSError:
            return "--"

    def update_status(self):
        self.branch_value.config(
            text=self.git_branch(),
        )
        self.commit_value.config(
            text=self.git_commit(),
        )

        changes_text, changes_colour = self.git_changes()
        self.changes_value.config(
            text=changes_text,
            fg=changes_colour,
        )

        adsb_text, adsb_colour = self.adsb_status()
        self.adsb_value.config(
            text=adsb_text,
            fg=adsb_colour,
        )

        self.cpu_value.config(
            text=self.cpu_temperature(),
        )
        self.memory_value.config(
            text=self.memory_usage(),
        )
        self.storage_value.config(
            text=self.storage_usage(),
        )

        if hasattr(self, "message"):
            self.message.config(
                text="STATUS REFRESHED",
                fg=config.SUCCESS,
            )

    def restart_adsb(self):
        self.message.config(
            text="RESTARTING ADS-B...",
            fg=config.ACCENT,
        )
        self.update_idletasks()

        code, _, error = self.command_output(
            [
                "sudo",
                "/usr/bin/systemctl",
                "restart",
                "dump1090-mutability.service",
            ]
        )

        if code == 0:
            self.message.config(
                text="ADS-B RESTARTED",
                fg=config.SUCCESS,
            )
        else:
            self.message.config(
                text=f"ADS-B ERROR: {error or 'PERMISSION DENIED'}",
                fg=config.DANGER,
            )

        self.after(1200, self.update_status)

    def git_fetch(self):
        self.message.config(
            text="CHECKING GITHUB...",
            fg=config.ACCENT,
        )
        self.update_idletasks()

        code, output, error = self.command_output(
            ["git", "fetch", "origin"]
        )

        if code == 0:
            self.message.config(
                text="GITHUB FETCH COMPLETE",
                fg=config.SUCCESS,
            )
        else:
            self.message.config(
                text=f"GIT ERROR: {error or output}",
                fg=config.DANGER,
            )

    def show_recent_log(self):
        code, output, error = self.command_output(
            [
                "journalctl",
                "-u",
                "dump1090-mutability.service",
                "-n",
                "12",
                "--no-pager",
            ]
        )

        window = tk.Toplevel(self)
        window.configure(bg=config.BACKGROUND)
        window.geometry("700x340+50+70")
        window.overrideredirect(True)
        window.attributes("-topmost", True)

        header = tk.Frame(
            window,
            bg=config.PANEL,
            height=46,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="ADS-B RECENT LOG",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 14, "bold"),
        ).pack(side="left", padx=12, pady=9)

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
            pady=4,
        ).pack(side="right", padx=8, pady=7)

        log_text = tk.Text(
            window,
            bg="#05080c",
            fg="#d7e3ea",
            insertbackground="white",
            font=("DejaVu Sans Mono", 8),
            relief="flat",
            wrap="word",
        )
        log_text.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        content = output if code == 0 else error
        log_text.insert("1.0", content or "NO LOG OUTPUT")
        log_text.config(state="disabled")
