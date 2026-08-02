import shutil
import subprocess
import threading
import wave
import tkinter as tk
from datetime import datetime
from pathlib import Path

import config


class AirbandScreen(tk.Frame):
    def __init__(self, parent, show_dashboard):
        super().__init__(parent, bg=config.BACKGROUND, cursor="none")
        self.show_dashboard = show_dashboard
        self.rtl_process = None
        self.audio_process = None
        self.audio_thread = None
        self.recording = False
        self.recording_file = None
        self.wave_writer = None
        self.playback_process = None
        self.recordings_window = None
        self.recordings_dir = (
            Path(__file__).resolve().parent / "recordings"
        )
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.volume_control = self.find_volume_control()
        self.volume = 70
        self.build_interface()
        self.set_volume(self.volume)
        self.update_status()

    def build_interface(self):
        header = tk.Frame(
            self,
            bg=config.PANEL,
            height=54,
            cursor="none",
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Button(
            header,
            text="HOME",
            command=self.return_home,
            bg=config.PANEL_LIGHT,
            fg=config.TEXT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 10, "bold"),
            padx=14,
            pady=5,
            cursor="none",
        ).pack(side="left", padx=8, pady=8)

        tk.Label(
            header,
            text="AIRBAND RADIO",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 17, "bold"),
        ).pack(side="left", padx=8)

        body = tk.Frame(
            self,
            bg=config.BACKGROUND,
            cursor="none",
        )
        body.pack(fill="both", expand=True, padx=12, pady=6)

        status_strip = tk.Frame(
            body,
            bg=config.BACKGROUND,
        )
        status_strip.pack(fill="x", pady=(0, 4))

        def compact_status(parent, title):
            frame = tk.Frame(
                parent,
                bg=config.PANEL,
                highlightthickness=1,
                highlightbackground=config.DIM_TEXT,
            )
            frame.pack(
                side="left",
                fill="x",
                expand=True,
                padx=3,
            )

            tk.Label(
                frame,
                text=title,
                bg=config.PANEL,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 7, "bold"),
            ).pack(anchor="w", padx=9, pady=(5, 0))

            value = tk.Label(
                frame,
                text="CHECKING",
                bg=config.PANEL,
                fg=config.TEXT,
                font=("DejaVu Sans", 9, "bold"),
            )
            value.pack(anchor="w", padx=9, pady=(0, 5))
            return value

        self.sdr_status = compact_status(
            status_strip,
            "RTL-SDR",
        )

        self.audio_status = compact_status(
            status_strip,
            "USB AUDIO",
        )

        self.frequency_label = tk.Label(
            body,
            text="121.500 MHz",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans Mono", 22, "bold"),
            pady=5,
        )
        self.frequency_label.pack(fill="x", pady=(5, 3))

        preset_panel = tk.Frame(
            body,
            bg=config.BACKGROUND,
        )
        preset_panel.pack(fill="x", pady=(0, 4))

        presets = (
            ("EMERGENCY", 121.500),
            ("LUTON TWR", 129.550),
            ("LUTON APP", 129.025),
            ("HEATHROW", 118.500),
        )

        for title, frequency in presets:
            tk.Button(
                preset_panel,
                text=title,
                command=lambda value=frequency: self.set_frequency(value),
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
                activebackground=config.ACCENT,
                activeforeground="#000000",
                relief="flat",
                bd=0,
                font=("DejaVu Sans", 7, "bold"),
                padx=5,
                pady=5,
                cursor="none",
            ).pack(
                side="left",
                expand=True,
                fill="x",
                padx=2,
            )

        volume_panel = tk.Frame(
            body,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.DIM_TEXT,
        )
        volume_panel.pack(fill="x", pady=(2, 4))

        volume_header = tk.Frame(volume_panel, bg=config.PANEL)
        volume_header.pack(fill="x", padx=10, pady=(4, 0))

        tk.Label(
            volume_header,
            text="AIRBAND VOLUME",
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        ).pack(side="left")

        self.volume_value = tk.Label(
            volume_header,
            text=f"{self.volume}%",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 9, "bold"),
        )
        self.volume_value.pack(side="right")

        self.volume_slider = tk.Scale(
            volume_panel,
            from_=0,
            to=100,
            orient="horizontal",
            command=self.set_volume,
            showvalue=False,
            resolution=5,
            bg=config.PANEL,
            fg=config.TEXT,
            troughcolor=config.PANEL_LIGHT,
            activebackground=config.ACCENT,
            highlightthickness=0,
            bd=0,
            sliderlength=26,
            cursor="none",
        )
        self.volume_slider.set(self.volume)
        self.volume_slider.pack(
            fill="x",
            padx=10,
            pady=(0, 4),
        )

        controls = tk.Frame(body, bg=config.BACKGROUND)
        controls.pack(fill="x", pady=4)

        self.control_button(
            controls,
            "−",
            lambda: self.change_frequency(-0.025),
        ).pack(side="left", expand=True, fill="x", padx=4)

        self.listen_button = self.control_button(
            controls,
            "LISTEN",
            self.start_listening,
        )
        self.listen_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=4,
        )

        self.control_button(
            controls,
            "+",
            lambda: self.change_frequency(0.025),
        ).pack(side="left", expand=True, fill="x", padx=4)

        action_row = tk.Frame(
            body,
            bg=config.BACKGROUND,
        )
        action_row.pack(fill="x", pady=(2, 4))

        self.stop_button = self.control_button(
            action_row,
            "STOP",
            self.stop_listening,
        )
        self.stop_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=(0, 3),
        )

        self.record_button = self.control_button(
            action_row,
            "RECORD",
            self.toggle_recording,
        )
        self.record_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=3,
        )

        self.recordings_button = self.control_button(
            action_row,
            "FILES",
            self.open_recordings,
        )
        self.recordings_button.pack(
            side="left",
            expand=True,
            fill="x",
            padx=(3, 0),
        )

        self.message = tk.Label(
            body,
            text="AIRBAND RECEIVER CONTROLS READY",
            bg=config.BACKGROUND,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 9, "bold"),
        )
        self.message.pack(pady=4)

        self.frequency = 121.500

    def status_card(self, parent, title):
        frame = tk.Frame(
            parent,
            bg=config.PANEL,
            highlightthickness=1,
            highlightbackground=config.DIM_TEXT,
        )
        frame.pack(fill="x", pady=4)

        tk.Label(
            frame,
            text=title,
            bg=config.PANEL,
            fg=config.DIM_TEXT,
            font=("DejaVu Sans", 8, "bold"),
        ).pack(anchor="w", padx=12, pady=(7, 0))

        value = tk.Label(
            frame,
            text="CHECKING",
            bg=config.PANEL,
            fg=config.TEXT,
            font=("DejaVu Sans", 11, "bold"),
        )
        value.pack(anchor="w", padx=12, pady=(1, 8))
        return value

    def control_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=config.PANEL_LIGHT,
            fg=config.ACCENT,
            activebackground=config.ACCENT,
            activeforeground="#000000",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 11, "bold"),
            pady=7,
            cursor="none",
        )

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

        self.volume = volume

        if hasattr(self, "volume_value"):
            self.volume_value.config(text=f"{volume}%")

        if not self.volume_control:
            if hasattr(self, "message"):
                self.message.config(
                    text="USB SPEAKER HAS NO SOFTWARE VOLUME CONTROL",
                    fg=config.DIM_TEXT,
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
        except (OSError, subprocess.SubprocessError):
            pass

    def set_frequency(self, frequency):
        frequency = min(
            136.975,
            max(118.000, float(frequency)),
        )

        was_listening = self.rtl_process is not None

        if was_listening:
            self.stop_listening()

        self.frequency = frequency
        self.frequency_label.config(
            text=f"{self.frequency:.3f} MHz"
        )

        self.message.config(
            text=f"TUNED • {self.frequency:.3f} MHz",
            fg=config.ACCENT,
        )

        if was_listening:
            self.after(350, self.start_listening)

    def change_frequency(self, amount):
        self.frequency = min(
            136.975,
            max(118.000, self.frequency + amount),
        )
        self.frequency_label.config(
            text=f"{self.frequency:.3f} MHz"
        )

        if self.rtl_process is not None:
            self.stop_listening()
            self.root_after_start()

    def root_after_start(self):
        self.after(250, self.start_listening)

    def stop_adsb(self):
        try:
            subprocess.run(
                [
                    "sudo",
                    "/usr/bin/systemctl",
                    "stop",
                    "dump1090-mutability.service",
                ],
                check=True,
                timeout=10,
            )
            self.message.config(
                text="ADS-B STOPPED • STARTING AIRBAND",
                fg=config.ACCENT,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            self.message.config(
                text="COULD NOT STOP ADS-B RECEIVER",
                fg=config.DANGER,
            )
            return False

    def start_adsb(self):
        try:
            subprocess.run(
                [
                    "sudo",
                    "/usr/bin/systemctl",
                    "start",
                    "dump1090-mutability.service",
                ],
                check=True,
                timeout=10,
            )
            self.message.config(
                text="ADS-B RECEIVER RESTARTED",
                fg=config.SUCCESS,
            )
        except (OSError, subprocess.SubprocessError):
            self.message.config(
                text="COULD NOT RESTART ADS-B",
                fg=config.DANGER,
            )

    def start_listening(self):
        if self.rtl_process is not None:
            return

        if not self.stop_adsb():
            return

        self.after(1200, self._start_airband_receiver)

    def _start_airband_receiver(self):

        if not shutil.which("rtl_fm"):
            self.message.config(
                text="RTL_FM NOT INSTALLED",
                fg=config.DANGER,
            )
            return

        frequency = f"{self.frequency:.3f}M"

        try:
            self.rtl_process = subprocess.Popen(
                [
                    "rtl_fm",
                    "-M", "am",
                    "-f", frequency,
                    "-s", "12000",
                    "-g", "28",
                    "-E", "dc",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.audio_process = subprocess.Popen(
                [
                    "aplay",
                    "--quiet",
                    "-D", "default",
                    "-t", "raw",
                    "-f", "S16_LE",
                    "-r", "12000",
                    "-c", "1",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self.audio_thread = threading.Thread(
                target=self.forward_audio,
                daemon=True,
            )
            self.audio_thread.start()

            self.message.config(
                text=f"LISTENING • {self.frequency:.3f} MHz AM",
                fg=config.SUCCESS,
            )
            self.listen_button.config(
                text="LISTENING",
                bg=config.SUCCESS,
                fg="#000000",
            )

            self.after(1200, self.check_receiver)

        except OSError as error:
            self.stop_listening()
            self.message.config(
                text=f"RECEIVER ERROR: {error}",
                fg=config.DANGER,
            )

    def open_recordings(self):
        recordings = sorted(
            self.recordings_dir.glob("*.wav"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )

        if self.recordings_window is not None:
            try:
                self.recordings_window.destroy()
            except tk.TclError:
                pass

        self.recordings_window = tk.Toplevel(self)
        self.recordings_window.title("Airband Recordings")
        self.recordings_window.configure(bg=config.BACKGROUND)
        self.recordings_window.geometry("760x400+20+55")
        self.recordings_window.overrideredirect(True)

        header = tk.Frame(
            self.recordings_window,
            bg=config.PANEL,
            height=48,
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="AIRBAND RECORDINGS",
            bg=config.PANEL,
            fg=config.ACCENT,
            font=("DejaVu Sans", 15, "bold"),
        ).pack(side="left", padx=14, pady=10)

        tk.Button(
            header,
            text="CLOSE",
            command=self.close_recordings,
            bg=config.DANGER,
            fg="white",
            activebackground="#B71C1C",
            activeforeground="white",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 9, "bold"),
            padx=14,
            pady=4,
        ).pack(side="right", padx=10, pady=8)

        list_frame = tk.Frame(
            self.recordings_window,
            bg=config.BACKGROUND,
        )
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        if not recordings:
            tk.Label(
                list_frame,
                text="NO RECORDINGS FOUND",
                bg=config.BACKGROUND,
                fg=config.DIM_TEXT,
                font=("DejaVu Sans", 13, "bold"),
            ).pack(expand=True)
            return

        for recording in recordings[:8]:
            row = tk.Frame(
                list_frame,
                bg=config.PANEL,
                highlightthickness=1,
                highlightbackground=config.DIM_TEXT,
            )
            row.pack(fill="x", pady=3)

            tk.Label(
                row,
                text=recording.name,
                bg=config.PANEL,
                fg=config.TEXT,
                font=("DejaVu Sans", 9, "bold"),
                anchor="w",
            ).pack(
                side="left",
                fill="x",
                expand=True,
                padx=10,
                pady=8,
            )

            tk.Button(
                row,
                text="PLAY",
                command=lambda file=recording: self.play_recording(file),
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
                activebackground=config.ACCENT,
                activeforeground="#000000",
                relief="flat",
                bd=0,
                font=("DejaVu Sans", 9, "bold"),
                padx=12,
            ).pack(side="right", padx=3, pady=4)

            tk.Button(
                row,
                text="STOP",
                command=self.stop_playback,
                bg=config.PANEL_LIGHT,
                fg=config.TEXT,
                activebackground=config.DANGER,
                activeforeground="white",
                relief="flat",
                bd=0,
                font=("DejaVu Sans", 9, "bold"),
                padx=12,
            ).pack(side="right", padx=3, pady=4)

    def play_recording(self, recording):
        self.stop_playback()

        try:
            self.playback_process = subprocess.Popen(
                [
                    "aplay",
                    "--quiet",
                    "-D",
                    "default",
                    str(recording),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self.message.config(
                text=f"PLAYING • {recording.name}",
                fg=config.SUCCESS,
            )
        except OSError as error:
            self.message.config(
                text=f"PLAYBACK ERROR: {error}",
                fg=config.DANGER,
            )

    def stop_playback(self):
        if (
            self.playback_process is not None
            and self.playback_process.poll() is None
        ):
            self.playback_process.terminate()

        self.playback_process = None

    def close_recordings(self):
        self.stop_playback()

        if self.recordings_window is not None:
            try:
                self.recordings_window.destroy()
            except tk.TclError:
                pass

        self.recordings_window = None

    def forward_audio(self):
        try:
            while (
                self.rtl_process is not None
                and self.audio_process is not None
                and self.rtl_process.stdout is not None
                and self.audio_process.stdin is not None
            ):
                chunk = self.rtl_process.stdout.read(4096)

                if not chunk:
                    break

                try:
                    self.audio_process.stdin.write(chunk)
                    self.audio_process.stdin.flush()
                except (BrokenPipeError, OSError):
                    break

                if self.recording and self.wave_writer is not None:
                    try:
                        self.wave_writer.writeframes(chunk)
                    except (OSError, wave.Error):
                        pass
        finally:
            if (
                self.audio_process is not None
                and self.audio_process.stdin is not None
            ):
                try:
                    self.audio_process.stdin.close()
                except OSError:
                    pass

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.rtl_process is None:
            self.message.config(
                text="PRESS LISTEN BEFORE RECORDING",
                fg=config.DANGER,
            )
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        frequency = f"{self.frequency:.3f}".replace(".", "_")

        self.recording_file = (
            self.recordings_dir
            / f"airband_{frequency}MHz_{timestamp}.wav"
        )

        try:
            self.wave_writer = wave.open(
                str(self.recording_file),
                "wb",
            )
            self.wave_writer.setnchannels(1)
            self.wave_writer.setsampwidth(2)
            self.wave_writer.setframerate(12000)

            self.recording = True
            self.record_button.config(
                text="STOP REC",
                bg=config.DANGER,
                fg="white",
            )
            self.message.config(
                text=f"RECORDING • {self.frequency:.3f} MHz",
                fg=config.DANGER,
            )
        except (OSError, wave.Error) as error:
            self.wave_writer = None
            self.recording = False
            self.message.config(
                text=f"RECORDING ERROR: {error}",
                fg=config.DANGER,
            )

    def stop_recording(self):
        self.recording = False

        if self.wave_writer is not None:
            try:
                self.wave_writer.close()
            except (OSError, wave.Error):
                pass

        saved_file = self.recording_file
        self.wave_writer = None
        self.recording_file = None

        if hasattr(self, "record_button"):
            self.record_button.config(
                text="START RECORDING",
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
            )

        if saved_file is not None:
            self.message.config(
                text=f"SAVED • {saved_file.name}",
                fg=config.SUCCESS,
            )

    def check_receiver(self):
        if self.rtl_process is None:
            return

        return_code = self.rtl_process.poll()

        if return_code is None:
            self.after(1200, self.check_receiver)
            return

        error_text = ""

        if self.rtl_process.stderr:
            try:
                error_text = self.rtl_process.stderr.read().decode(
                    "utf-8",
                    errors="ignore",
                )
            except Exception:
                error_text = ""

        self.stop_listening()

        if "busy" in error_text.lower():
            message = "RTL-SDR BUSY • STOP ADS-B OR USE SECOND DONGLE"
        elif "no supported devices" in error_text.lower():
            message = "RTL-SDR NOT DETECTED"
        else:
            message = "RECEIVER STOPPED"

        self.message.config(
            text=message,
            fg=config.DANGER,
        )

    def stop_listening(self):
        if self.recording or self.wave_writer is not None:
            self.stop_recording()

        for process in (self.audio_process, self.rtl_process):
            if process is not None and process.poll() is None:
                process.terminate()

        self.audio_process = None
        self.rtl_process = None

        if hasattr(self, "listen_button"):
            self.listen_button.config(
                text="LISTEN",
                bg=config.PANEL_LIGHT,
                fg=config.ACCENT,
            )

        if hasattr(self, "message"):
            self.message.config(
                text="RECEIVER STOPPED",
                fg=config.DIM_TEXT,
            )

    def return_home(self):
        self.stop_playback()

        if self.recordings_window is not None:
            self.close_recordings()

        self.stop_listening()
        self.start_adsb()
        self.after(1200, self.show_dashboard)

    def rtl_sdr_connected(self):
        if not shutil.which("lsusb"):
            return False

        try:
            result = subprocess.run(
                ["lsusb"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            output = result.stdout.lower()
            return (
                "realtek" in output
                or "rtl2838" in output
                or "rtl-sdr" in output
            )
        except (OSError, subprocess.SubprocessError):
            return False

    def usb_audio_connected(self):
        try:
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return "USB Audio" in result.stdout
        except (OSError, subprocess.SubprocessError):
            return False

    def update_status(self):
        sdr_online = self.rtl_sdr_connected()
        audio_online = self.usb_audio_connected()

        self.sdr_status.config(
            text="CONNECTED" if sdr_online else "NOT DETECTED",
            fg=config.SUCCESS if sdr_online else config.DANGER,
        )

        self.audio_status.config(
            text="CONNECTED" if audio_online else "NOT DETECTED",
            fg=config.SUCCESS if audio_online else config.DANGER,
        )

        self.after(5000, self.update_status)
