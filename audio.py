import subprocess
import threading
from pathlib import Path


class AudioController:
    def __init__(self):
        self.running = False
        self.process = None
        self.click_file = Path(__file__).resolve().parent / "sounds" / "click.wav"
        self.heartbeat_file = (
            Path(__file__).resolve().parent
            / "sounds"
            / "heartbeat.wav"
        )

    def start_heartbeat(self):
        if self.running or not self.heartbeat_file.exists():
            return

        self.running = True
        threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
        ).start()

    def _heartbeat_loop(self):
        while self.running:
            self.process = subprocess.Popen(
                [
                    "aplay",
                    "--quiet",
                    "-D",
                    "default",
                    str(self.heartbeat_file),
                ]
            )
            self.process.wait()
            self.process = None

    def play_click(self):
        if not self.click_file.exists():
            return

        subprocess.Popen(
            [
                "aplay",
                "--quiet",
                "-D",
                "default",
                str(self.click_file),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop_heartbeat(self):
        self.running = False

        if self.process:
            self.process.terminate()
            self.process = None

    def close(self):
        self.stop_heartbeat()
